import { db } from '@/lib/server/db'
import fs from "fs";
import path from "path";

async function runMigrations() {
    try {
        if (process.env.NODE_ENV === "production") {
            console.error("Not allowed to run migrations in production!");
            process.exit(1);
        }

        const migrationsDir = path.join(process.cwd(), "src/db/migrations");

        const files = fs
            .readdirSync(migrationsDir)
            .filter(file => file.endsWith(".sql"))
            .sort();

        if (files.length === 0) {
            console.error("No migration files found in", migrationsDir);
            process.exit(1);
        }

        for (const file of files) {
            const filePath = path.join(migrationsDir, file);
            const sql = fs.readFileSync(filePath, "utf8");

            console.log(`Running migration: ${file}`);
            console.log(sql)
            console.log(sql);
            await db.query(sql);
            console.log(`Migration applied: ${file}`);
        }

        console.log("All migrations executed successfully.");
        process.exit(0);
    } catch (err: any) {
        console.error("Migration error:", err.message || err);
        process.exit(1);
    }
}

runMigrations();
