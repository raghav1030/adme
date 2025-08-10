import { betterAuth } from "better-auth";
import { pool } from "./db";
import config from "./config";
import { nextCookies } from "better-auth/next-js";

export const auth = betterAuth({
    database: pool,
    account: {
        accountLinking: {
            enabled: true,
        }
    },
    emailAndPassword: {
        enabled: true,
    },
    socialProviders: {
        github: {
            clientId: config.GITHUB_CLIENT_ID!,
            clientSecret: config.GITHUB_CLIENT_SECRET!
        },
    },
    plugins: [nextCookies()]
});