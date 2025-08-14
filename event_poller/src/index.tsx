import { startCrons } from "./jobs/cron.js";
import 'dotenv/config';

console.log("Hybrid GitHub event poller with ETag started...");
startCrons();
