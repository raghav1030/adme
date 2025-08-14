import { Octokit } from "octokit";

export const createGitHubREST = (token: string) => {
    return new Octokit({ auth: token });
};
