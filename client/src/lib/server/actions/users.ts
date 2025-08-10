"use server"

import { auth } from "@/lib/server/auth"
import { headers } from "next/headers"

export const signInWithEmail = async (credentials: { email: string, password: string }) => {
    try {
        const response = await auth.api.signInEmail({
            body: {
                email: credentials.email,
                password: credentials.password,
            },
            headers: await headers(),

        })
        return response
    } catch (error) {
        throw new Error("Failed to sign in: " + (error as Error).message);
    }
}
export const signUpWithEmail = async (credentials: { email: string, password: string, username: string }) => {
    try {
        console.log(credentials)

        const response = await auth.api.signUpEmail({
            body: {
                email: credentials.email,
                password: credentials.password,
                name: credentials.username,
            },
            headers: await headers(),
        })
        return response
    } catch (error) {
        throw new Error("Failed to sign up: " + (error as Error).message);
    }
}
export const signInWithSocial = async ({ provider }: { provider: string }) => {
    try {
        const response = await auth.api.signInSocial({
            body: {
                provider: provider,
            },
        })
        return response;
    } catch (error) {
        throw new Error("Failed to authorize github: " + (error as Error).message);
    }
}