"use client";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    listUserAccountsWithProfile,
    linkSocialAccount,
    unlinkSocialAccount,
} from "@/lib/client/helpers/accounts";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
    IconBrandGithub,
    IconBrandLinkedin,
    IconBrandReddit,
    IconBrandX,
} from "@tabler/icons-react";

const providers = [
    {
        id: "github",
        name: "GitHub",
        description: "Connect your GitHub account",
        icon: <IconBrandGithub className="h-6 w-6" />,
    },
    {
        id: "linkedin",
        name: "LinkedIn",
        description: "Connect your LinkedIn account",
        icon: <IconBrandLinkedin className="h-6 w-6 text-blue-700" />,
    },
    {
        id: "twitter",
        name: "Twitter / X",
        description: "Connect your Twitter account",
        icon: <IconBrandX className="h-6 w-6 text-sky-500" />,
    },
    {
        id: "reddit",
        name: "Reddit",
        description: "Connect your Reddit account",
        icon: <IconBrandReddit className="h-6 w-6 text-orange-500" />,
    },
];

export default function IntegrationsPageClient() {
    const queryClient = useQueryClient();

    const { data, refetch, isLoading, isFetching, error } = useQuery({
        queryKey: ["userAccounts"],
        queryFn: listUserAccountsWithProfile,
    });

    const linkMutation = useMutation({
        mutationFn: linkSocialAccount,
        onSuccess: () =>
            queryClient.invalidateQueries({ queryKey: ["userAccounts"] }),
    });

    const unlinkMutation = useMutation({
        mutationFn: unlinkSocialAccount,
        onSuccess: () =>
            queryClient.invalidateQueries({ queryKey: ["userAccounts"] }),
    });

    console.log(data);

    return (
        <div className="w-full p-3">
            {data?.user && (
                <div className="flex items-center justify-between p-4 mb-6 border rounded-md bg-background">
                    <div className="flex items-center gap-4">
                        <img
                            src={data.user.image}
                            alt={data.user.name}
                            className="h-16 w-16 rounded-full border object-cover"
                        />
                        <div>
                            <div className="text-lg font-semibold">
                                {data.user.name}
                            </div>
                            <div className="text-muted-foreground text-sm">
                                {data.user.email}
                            </div>
                        </div>
                    </div>
                    <Button variant="outline" size="sm">
                        Change
                    </Button>
                </div>
            )}

            <h1 className="text-2xl font-bold mb-4">Connected Accounts</h1>
            <p className="text-muted-foreground mb-8">
                Manage and link your social accounts to enable integrations and
                synchronisation.
            </p>

            {/* Connected Accounts List */}
            <div className="divide-y border rounded-md bg-background">
                {isLoading || isFetching
                    ? providers.map((p) => (
                        <div
                            key={p.id}
                            className="flex items-center justify-between p-4 gap-3"
                        >
                            <div className="flex items-center gap-4 flex-1">
                                <Skeleton className="h-10 w-10 rounded-full" />
                                <div className="flex-1">
                                    <Skeleton className="h-4 w-32 mb-2" />
                                    <Skeleton className="h-3 w-48" />
                                </div>
                            </div>
                            <Skeleton className="h-8 w-20 rounded-md" />
                        </div>
                    ))
                    : providers.map((p) => {
                        const acc = data?.find?.((a) => a.provider === p.id) || null;
                        return (
                            <div
                                key={p.id}
                                className="flex items-center justify-between p-4 gap-3"
                            >
                                {/* Left: icon + name/desc */}
                                <div className="flex items-center gap-4 flex-1">
                                    <div className="flex items-center justify-center h-10 w-10 rounded-full border bg-muted">
                                        {p.icon}
                                    </div>
                                    <div>
                                        <div className="font-medium">{p.name}</div>
                                        <div className="text-sm text-muted-foreground">
                                            {p.description}
                                        </div>
                                    </div>
                                </div>

                                {/* Middle: account info */}
                                <div className="flex-1 text-sm text-muted-foreground">
                                    {acc?.profile ? (
                                        <div className="flex items-center gap-2">
                                            {acc.profile.data.avatar_url && (
                                                <img
                                                    src={acc.profile.data.avatar_url}
                                                    alt={
                                                        acc.profile.data.login ||
                                                        acc.profile.data.username ||
                                                        p.id
                                                    }
                                                    className="h-6 w-6 rounded-full border"
                                                />
                                            )}
                                            <span>
                                                @{acc.profile.data.login ||
                                                    acc.profile.data.username ||
                                                    acc.profile.data.email}
                                            </span>
                                        </div>
                                    ) : (
                                        <span className="italic text-muted-foreground">
                                            Not connected
                                        </span>
                                    )}
                                </div>

                                {/* Right: Link/Unlink button */}
                                {acc ? (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        disabled={
                                            unlinkMutation.isPending &&
                                            unlinkMutation.variables === p.id
                                        }
                                        onClick={() => unlinkMutation.mutate(p.id)}
                                    >
                                        {unlinkMutation.isPending &&
                                            unlinkMutation.variables === p.id
                                            ? "Unlinking..."
                                            : "Unlink"}
                                    </Button>
                                ) : (
                                    <Button
                                        size="sm"
                                        disabled={
                                            linkMutation.isPending &&
                                            linkMutation.variables === p.id
                                        }
                                        onClick={() => linkMutation.mutate(p.id)}
                                    >
                                        {linkMutation.isPending &&
                                            linkMutation.variables === p.id
                                            ? "Linking..."
                                            : "Link"}
                                    </Button>
                                )}
                            </div>
                        );
                    })}
            </div>

            {error && (
                <div className="text-red-500 mt-4">
                    {(error as Error).message}
                </div>
            )}

            <div className="flex justify-end mt-4">
                <Button
                    variant="outline"
                    onClick={() => refetch()}
                    disabled={isLoading || isFetching}
                >
                    Refresh
                </Button>
            </div>
        </div>
    );
}
