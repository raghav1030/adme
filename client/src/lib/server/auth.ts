import { betterAuth } from "better-auth";
import { pool } from "./db";
import config from "./config";
import { nextCookies } from "better-auth/next-js";

export const auth = betterAuth({
    database: pool,
    account: {
        accountLinking: {
            enabled: true,
        },
    },
    emailAndPassword: {
        enabled: true,
    },
    socialProviders: {
        github: {
            clientId: config.GITHUB_CLIENT_ID!,
            clientSecret: config.GITHUB_CLIENT_SECRET!,
            scope: ["read:user", "user:email", "repo:status", "re   ad:repo_hook", "write:repo_hook", "events"],
            redirectURI: `http://localhost:3000/api/auth/callback/github`,
        },
    },
    plugins: [nextCookies()]
});