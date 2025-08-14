import { db } from "../db/index.js";

export async function getUsersByPriority(priority: number, limit = 50) {
    const { rows } = await db.query( 
        `SELECT ups.userId, a.accessToken, ups.last_event_id_gh
        FROM user_polling_state ups
        JOIN account a ON a.userId = ups.userId
        WHERE ups.priority = $1
            AND ups.next_scheduled_at <= NOW()
            AND a.providerId = 'github'
        ORDER BY ups.next_scheduled_at ASC
        LIMIT $2`,
        [priority, limit]
    );
    return rows;
}

export const USER_ACTIVITY_QUERY = `
query($username: String!) {
  user(login: $username) {
    login
    repositories(first: 10, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        nameWithOwner
        pushedAt
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 5) {
                nodes {
                  oid
                  messageHeadline
                  committedDate
                  author {
                    name
                    email
                  }
                  changedFilesIfAvailable
                  additions
                  deletions
                }
              }
            }
          }
        }
        pullRequests(last: 5, states: MERGED) {
          nodes {
            title
            additions
            deletions
            changedFiles
            mergedAt
            author {
              login
            }
          }
        }
      }
    }
  }
}`;
