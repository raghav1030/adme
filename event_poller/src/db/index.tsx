import { Pool } from "pg";
import type { PoolClient, QueryResultRow } from "pg";
import { configDotenv } from "dotenv";
configDotenv()
export interface ExtendedClient extends PoolClient {
    lastQuery?: any;
    query: (...args: any[]) => Promise<any>;
    release: () => void;
}
console.log(process.env.DATABASE_URL);
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: false, // set to { rejectUnauthorized: false } in prod if needed
    max: 20,
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 10000,
});

const getClient_ = async (): Promise<ExtendedClient> => {
    const client = (await pool.connect()) as ExtendedClient;
    const originalQuery = client.query;
    const originalRelease = client.release;

    const timeout = setTimeout(() => {
        console.error("Client has been checked out for more than 5 seconds!");
        console.error("Last executed query was:", client.lastQuery);
    }, 5000);

    client.query = (...args: any[]) => {
        client.lastQuery = args;
        return originalQuery.apply(client, args);
    };

    client.release = () => {
        clearTimeout(timeout);
        client.query = originalQuery;
        client.release = originalRelease;
        return originalRelease.apply(client);
    };

    return client;
};

const db = {
    query: async <T extends QueryResultRow = any>(text: string, params?: any[]) => {
        try {
            const res = await pool.query<T>(text, params);
            return res;
        } catch (err: any) {
            err.type = "POSTGRESQL_ERROR";
            console.error("DB query error:", err);
            throw err;
        }
    },

    getClient: async (): Promise<ExtendedClient> => {
        return await getClient_();
    },
};

export { db };
