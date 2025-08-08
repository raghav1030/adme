import pkg from "pg";
const { Pool } = pkg;

interface QueryArgs {
    text: string;
    params?: any[];
}

interface ExtendedClient extends ReturnType<InstanceType<typeof Pool>["connect"]> {
    lastQuery?: any;
    query: (...args: any[]) => Promise<any>;
    release: () => void;
}

const pool = new Pool({
    connectionString: process.env.DATABASE_URL_MAIN,
    ssl: { rejectUnauthorized: false }, // better ssl config for pg in Node.js
    max: 20,
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 10000,
});

// Helper to get a client with query tracking and timeout warning
const getClient_ = async (): Promise<ExtendedClient> => {
    const client = (await pool.connect()) as ExtendedClient;
    const { query } = client;
    const { release } = client;

    // Log if client checked out for more than 5 seconds
    const timeout = setTimeout(() => {
        console.error("A client has been checked out for more than 5 seconds!");
        console.error(`The last executed query on this client was:`, client.lastQuery);
    }, 5000);

    // Monkey patch query to track last executed query
    client.query = (...args: any[]) => {
        client.lastQuery = args;
        return query.apply(client, args);
    };

    client.release = () => {
        clearTimeout(timeout);
        client.query = query;
        client.release = release;
        return release.apply(client);
    };

    return client;
};

const db = {
    query: async (text: string, params?: any[]) => {
        try {
            const res = await pool.query(text, params);
            return res;
        } catch (err: any) {
            err.type = "POSTGRESQL_ERROR";
            console.error(err);
            throw err;
        }
    },

    getClient: async (): Promise<ExtendedClient> => {
        return await getClient_();
    },
};

export default db;
