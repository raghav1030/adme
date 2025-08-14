import cron from "node-cron";
import { getUsersByPriority, pollUserHybrid } from "../services/poller.js";

export async function startCrons() {
    // Active users every 30s
    // cron.schedule("*/30 * * * * *", async () => {
    //     const users = await getUsersByPriority(1);
    //     for (const u of users) await pollUserHybrid(u);
    // });

    // // Regular users every 1h
    // cron.schedule("0 * * * *", async () => {
    //     const users = await getUsersByPriority(2);
    //     for (const u of users) await pollUserHybrid(u);
    // });

    // // Dormant users every 6h
    // cron.schedule("0 */6 * * *", async () => {
    //     const users = await getUsersByPriority(3);
    //     for (const u of users) await pollUserHybrid(u);
    // });
    const users1 = await getUsersByPriority(1);
    const users2 = await getUsersByPriority(2);
    const users3 = await getUsersByPriority(3);
    console.log(users1, users2, users3);
    // for (const u of users) await pollUserHybrid(u);
}
