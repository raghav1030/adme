import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

export async function middleware(request: NextRequest) {
    const sessionCookie = getSessionCookie(request);
    console.log(sessionCookie)
    // THIS IS NOT SECURE!
    // This is the recommended approach to optimistically redirect users
    // We recommend handling auth checks in each page/route
    if (!sessionCookie) {
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
    matcher: ["/dashboard/:path*", '/'], // Specify the routes the middleware applies to
};