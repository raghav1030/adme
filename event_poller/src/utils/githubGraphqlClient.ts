import { graphql } from "@octokit/graphql";

export const createGitHubQL = (token: string) =>
    graphql.defaults({
        headers: {
            authorization: `token ${token}`,
        },
    });
