import { db } from "../db/index.js";
import { createGitHubREST } from "../utils/githubRestClient.js";
import { createGitHubQL } from "../utils/githubGraphqlClient.js";

// Example enrichment query for commit details
const COMMIT_DETAILS_QUERY = `
query($owner: String!, $name: String!, $oid: GitObjectID!) {
  repository(owner: $owner, name: $name) {
    object(oid: $oid) {
      ... on Commit {
        oid
        message
        changedFilesIfAvailable
        additions
        deletions
        author { name email date }
      }
    }
  }
}
`;

// === Fetch DB users for polling ===
export async function getUsersByPriority(priority: number, limit = 50) {
    const { rows } = await db.query(
        `SELECT ups."userId", a."accessToken", a."account_username" AS "username",
            ups."last_event_id_gh", ups."etag"
     FROM "user_polling_state" ups
     JOIN "account" a ON a."userId" = ups."userId"
     WHERE ups."priority" = $1
       AND ups."next_scheduled_at" <= NOW()
       AND a."providerId" = 'github'
     ORDER BY ups."next_scheduled_at" ASC
     LIMIT $2`,
        [priority, limit]
    );
    return rows;
}

// === Hybrid Poll Function ===
export async function pollUserHybrid(user: any) {
    console.log(`[pollUserHybrid] Polling user:`, user.username);

    const restClient = createGitHubREST(user.accessToken);

    // Prepare request headers with ETag
    const headers: any = {};
    if (user.etag) {
        headers["If-None-Match"] = user.etag;
        console.log(`[pollUserHybrid] Using ETag:`, user.etag);
    }

    // REST call
    console.log(`[pollUserHybrid] Fetching events for user:`, user.username);
    const resp = await restClient.request("GET /users/{username}/events", {
        username: user.username,
        headers,
    });

    console.log(`[pollUserHybrid] REST response status:`, resp.status);

    if (Number(resp.status) === 304) {
        console.log(`[pollUserHybrid] No new events for ${user.username}`);
        return;
    }

    const newEtag = resp.headers.etag;
    const newEvents = resp.data;

    console.log(`[pollUserHybrid] Received ${newEvents.length} new events for ${user.username}`);
    console.log(`[pollUserHybrid] New ETag:`, newEtag);

    for (const ev of newEvents) {
        const eventId = parseInt(ev.id);
        const occurredAt = ev.created_at;
        const eventType = ev.type;

        console.log(`[pollUserHybrid] Processing event:`, { eventId, eventType, occurredAt });

        // Insert event into DB
        await db.query(
            `INSERT INTO "github_event"
       ("event_id_gh","occurred_at","userId","event_type","payload","summary_status","source")
       VALUES ($1,$2,$3,$4,$5,'pending','cron')
       ON CONFLICT ("userId","event_id_gh","occurred_at") DO NOTHING`,
            [eventId, occurredAt, user.userId, eventType, ev]
        );
        console.log(`[pollUserHybrid] Inserted event ${eventId} into DB`);

        // Example conditional enrichment
        if (eventType === "PushEvent" && ev.payload?.commits) {
            console.log(`[pollUserHybrid] Enriching PushEvent with ${ev.payload.commits.length} commits`);
            for (const commit of ev.payload.commits) {
                if (!commit.message || !commit.author) {
                    const [owner, repo] = ev.repo.name.split("/");
                    const graphqlClient = createGitHubQL(user.accessToken);
                    console.log(`[pollUserHybrid] Fetching commit details for SHA:`, commit.sha);
                    const commitData: any = await graphqlClient(COMMIT_DETAILS_QUERY, {
                        owner,
                        name: repo,
                        oid: commit.sha,
                    });

                    console.log(`[pollUserHybrid] Commit details:`, commitData);

                    await db.query(
                        `INSERT INTO "code_change"
             ("event_id","occurred_at","sha","patch","files_changed")
             VALUES (
                 (SELECT "event_id" FROM "github_event"
                  WHERE "event_id_gh" = $1 AND "userId" = $2 LIMIT 1),
                 $3, $4, NULL, $5
             )`,
                        [
                            eventId,
                            user.userId,
                            occurredAt,
                            commit.sha,
                            {
                                additions: commitData.repository.object.additions,
                                deletions: commitData.repository.object.deletions,
                                changedFiles: commitData.repository.object.changedFilesIfAvailable,
                            },
                        ]
                    );
                    console.log(`[pollUserHybrid] Inserted code_change for commit ${commit.sha}`);
                }
            }
        }
    }

    // Update polling state with new ETag & fetch time
    const maxEventId = Math.max(...newEvents.map((e) => parseInt(e.id)));
    console.log(`[pollUserHybrid] Updating polling state for user:`, user.userId, {
        maxEventId,
        newEtag,
    });
    await db.query(
        `UPDATE "user_polling_state"
     SET "last_event_fetch" = NOW(),
         "last_event_id_gh" = $1,
         "etag" = $2,
         "next_scheduled_at" = NOW() + "polling_interval",
         "source" = 'cron',
         "updatedAt" = NOW()
     WHERE "userId" = $3`,
        [maxEventId || user.last_event_id_gh, newEtag || user.etag, user.userId]
    );
    console.log(`[pollUserHybrid] Polling state updated for user:`, user.userId);
}
