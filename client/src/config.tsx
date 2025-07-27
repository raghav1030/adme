export const config = {
    runtime: "edge",
    BASE_API_URL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1",
}