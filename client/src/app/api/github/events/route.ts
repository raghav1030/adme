import { Octokit } from "octokit";
import { auth } from "@/lib/server/auth";
import dayjs from "dayjs";
import { headers } from "next/headers";
import { NextResponse } from "next/server";

export async function GET() {
    try {
        const session = await auth.api.getSession({
            headers: await headers(),
        });

        if (!session || dayjs(session?.session.expiresAt).isBefore(dayjs())) {
            return NextResponse.json(
                { error: "Session expired or not found" },
                { status: 401 }
            );
        }

        const ghAccessToken = await auth.api.getAccessToken({
            body: {
                providerId: "github",
                userId: session?.session.userId,
            },
        });

        if (!ghAccessToken || !ghAccessToken.accessToken) {
            return NextResponse.json(
                { error: "GitHub access token not found" },
                { status: 401 }
            );
        }

        const octokit = new Octokit({
            auth: ghAccessToken.accessToken,
        });

        // Get authenticated user's username
        const { data: userData } = await octokit.rest.users.getAuthenticated();
        const username = userData.login;

        // Fetch last 50 events for the authenticated user
        const response = await octokit.request("GET /users/{username}/events", {
            username,
            per_page: 50,
        });

        const events = response.data;

        // Extract commits from push events
        const eventsWithCommits = events.map((event) => {
            if (event.type === "PushEvent" && event.payload && event.payload.commits) {
                return {
                    ...event,
                    commits: event.payload.commits.map((commit) => ({
                        sha: commit.sha,
                        message: commit.message,
                        url: commit.url,
                        author: commit.author,
                    })),
                };
            } else {
                return event;
            }
        });

        // Return events including commit details for push events
        return NextResponse.json({ events: eventsWithCommits });
    } catch (error) {
        return NextResponse.json(
            { error: "Something went wrong while fetching events: " + error },
            { status: 500 }
        );
    }
}

export async function POST() {
    return NextResponse.json(
        { error: "Method POST Not Allowed" },
        { status: 405, headers: { Allow: "GET" } }
    );
}
