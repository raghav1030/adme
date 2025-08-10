import { loadEnvConfig } from "@next/env";

const projectDir = process.cwd()
loadEnvConfig(projectDir)

const config = {
    DATABASE_URL: process.env.DATABASE_URL,
    GITHUB_CLIENT_ID: process.env.GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET: process.env.GITHUB_CLIENT_SECRET
}

export default config