import { createGitHubREST } from "../utils/githubRestClient.js";
import { createGitHubQL } from "../utils/githubGraphqlClient.js";
import { publishEventToQueue } from "./rabbitmq.js";
import { db } from "@/db/index.jsx";

const COMMIT_DETAILS_QUERY = `
query($owner: String!, $name: String!, $oid: GitObjectID!) {
  repository(owner: $owner, name: $name) {
    object {
      ... on Commit {
        message
        additions
        deletions
        changedFiles
        commitUrl: url
        author {
          name
          email
          date
        }
        files(first: 100) {
          nodes {
            path
            additions
            deletions
            patch
          }
        }
      }
    }
  }
}
`;

export async function pollUserHybrid(user: any) {
    const restClient = createGitHubREST(user.accessToken);

    // Lazy load username if missing
    if (!user.username) {
        try {
            const profileResp = await restClient.request("GET /user", {
                headers: {
                    authorization: `token ${user.accessToken}`,
                },
            });
            if (profileResp.status !== 200 || !profileResp.data?.login) {
                console.error(`Failed to fetch GitHub profile for userId=${user.userId}`, profileResp.data);
                return;
            }
            const { login, name, bio } = profileResp.data;
            await db.query(
                `UPDATE "account" SET account_username=$1, account_name=$2, account_bio=$3 WHERE "userId"=$4 AND providerId='github'`,
                [login, name || null, bio || null, user.userId]
            );
            user.username = login;
            console.log(`Fetched username: ${login}`);
        } catch (e) {
            console.error("Error fetching GitHub user profile:", e);
            return;
        }
    }

    const headers: Record<string, string> = {};
    // Add ETag header if using caching here as needed.

    let resp;
    try {
        resp = await restClient.request(
            "GET /users/{username}/events",
            {
                username: user.username,
                headers
            },
        );
    } catch (e: any) {
        if (e.status === 304) {
            console.log(`No new events for ${user.username} (304)`);
            return;
        }
        console.error(`Error fetching events for ${user.username}:`, e);
        return;
    }
    if (resp.status !== 200) {
        console.error(`Unexpected status code: ${resp.status} for user ${user.username}`);
        return;
    }

    let newEvents = resp.data;
    let newEtag = resp.headers.etag;

    console.log(`Received ${newEvents.length} events for user ${user.username}`);

    for (const ev of newEvents) {
        let eventId = Number(ev.id);
        let occurredAt = ev.created_at;
        let eventType = ev.type;

        // Insert main event record
        await db.query(
            `INSERT INTO github_event (event_id_gh, occurred_at, "userId", event_type, payload, summary_status, source)
       VALUES ($1, $2, $3, $4, $5, 'pending', 'cron')
       ON CONFLICT DO NOTHING`,
            [eventId, occurredAt, user.userId, eventType, ev]
        );

        const enrichedCommits = [];
        if (eventType === "PushEvent" && ev.payload?.commits && ev.repo?.name) {
            for (const commit of ev.payload.commits) {
                let fileChanges: any[] = [];
                // Use REST API for commit details (including files)
                try {
                    const [owner, repo] = ev.repo.name.split("/");
                    // Use a restClient with the user's accessToken
                    const commitDetailsResp = await restClient.request("GET /repos/{owner}/{repo}/commits/{sha}", {
                        owner,
                        repo,
                        sha: commit.sha,
                    });
                    // commitDetailsResp.data.files is an array
                    fileChanges = (commitDetailsResp.data.files || []).map((f: any) => ({
                        filename: f.filename,
                        additions: f.additions,
                        deletions: f.deletions,
                        patch: f.patch, // can be large — truncate if needed
                    }));
                    // Save summary info to DB if you want
        //             await db.query(
        //                 `INSERT INTO code_change (sha, event_id, occurred_at, additions, deletions, changed_files)
        //  VALUES ($1,
        //          (SELECT event_id FROM github_event WHERE event_id_gh = $2 AND "userId" = $3 LIMIT 1),
        //          $4, $5, $6, $7)
        //  ON CONFLICT DO NOTHING`,
        //                 [
        //                     commit.sha,
        //                     eventId,
        //                     user.userId,
        //                     occurredAt,
        //                     commitDetailsResp.data.stats?.additions || 0,
        //                     commitDetailsResp.data.stats?.deletions || 0,
        //                     fileChanges.map(fc => fc.filename),
        //                 ]
        //             );
                } catch (err) {
                    console.warn(`Failed to enrich commit ${commit.sha}:`, err);
                }

                enrichedCommits.push({
                    message: commit.message,
                    author: commit.author,
                    files: fileChanges,
                });
            }
        }


        // Prepare summarized event to send to MQ
        const summarizedEvent = {
            event_id: eventId,
            user_id: user.userId,
            event_type: eventType,
            occurred_at: occurredAt,
            repo_name: ev.repo?.name ?? null,
            essential_data: {
                actor_login: ev.actor?.login ?? null,
                ref: ev.payload?.ref ?? null,
                commits: enrichedCommits,
                pr_state: ev.payload?.pull_request?.state ?? null,
            },
        };

        await publishEventToQueue(summarizedEvent);
        console.log(`Published summarized event for ${eventId}`);
    }

    let maxEventId = newEvents.length > 0 ? Math.max(...newEvents.map(e => Number(e.id))) : 0;
    await db.query(
        `UPDATE user_polling_state SET
     last_event_fetch = NOW(),
     last_event_id_gh = $1,
     etag = $2,
     next_scheduled_at = NOW() + polling_interval,
     source = 'cron'
     WHERE "userId" = $3`,
        [maxEventId || 0, newEtag || null, user.userId]
    );
    console.log(`Updated polling state for user ${user.userId}`);
}

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




