import { NextRequest, NextResponse } from "next/server";
import { authClient } from "./lib/client/auth-client";

export async function middleware(request: NextRequest) {

    const session = await authClient.getSession();
    if (!session) {
        return NextResponse.redirect(new URL("/login", request.url));
    }

    if (request.nextUrl.pathname === "/dashboard") {
        return NextResponse.redirect(new URL("/dashboard/overview", request.url));
    }
    if (request.nextUrl.pathname === "/") {
        return NextResponse.redirect(new URL("/dashboard/overview", request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ["/dashboard/:path*", "/"],
};
