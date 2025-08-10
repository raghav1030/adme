"use client";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listUserAccountsWithProfile, linkSocialAccount, unlinkSocialAccount } from "@/lib/client/helpers/accounts";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { IconBrandGithub, IconBrandLinkedin, IconBrandReddit, IconBrandTwitter, IconBrandX } from "@tabler/icons-react";
const providers = [
    {
        id: "github",
        name: "GitHub",
        description: "Connect your GitHub account",
        icon: <IconBrandGithub className="h-7 w-7" />,
    },
    {
        id: "linkedin",
        name: "LinkedIn",
        description: "Connect your LinkedIn account",
        icon: <IconBrandLinkedin className="h-7 w-7 text-blue-700" />,
    },
    {
        id: "twitter",
        name: "Twitter",
        description: "Connect your Twitter account",
        icon: <IconBrandX className="h-7 w-7 text-sky-500" />,
    },
    {
        id: "reddit",
        name: "Reddit",
        description: "Connect your Reddit account",
        icon: <IconBrandReddit className="h-7 w-7 text-orange-500" />,
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
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["userAccounts"] }),
    });

    const unlinkMutation = useMutation({
        mutationFn: unlinkSocialAccount,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["userAccounts"] }),
    });

    return (
        <div>
            <h1 className="text-2xl font-bold mb-8">Integrations</h1>
            <div className="grid gap-6 sm:grid-cols-2">
                {(isLoading || isFetching) ? (
                    // Skeleton loader
                    providers.map((p) => (
                        <div className="p-5 border rounded-lg flex flex-col gap-6 bg-muted" key={p.id}>
                            <div className="flex items-center space-x-4">
                                <Skeleton className="h-12 w-12 rounded-full" />
                                <div className="flex-1">
                                    <Skeleton className="h-4 w-[120px] mb-1" />
                                    <Skeleton className="h-4 w-[80px]" />
                                </div>
                            </div>
                            <Skeleton className="h-8 w-20 rounded" />
                        </div>
                    ))
                ) : (
                    // Provider cards
                    providers.map((p) => {
                        const acc = data?.find((a) => a.provider === p.id);

                        return (
                            <div className="p-5 border rounded-lg flex flex-col justify-between gap-6 bg-background" key={p.id}>
                                <div className="flex items-center gap-4">
                                    {p.icon}
                                    <div>
                                        <div className="text-lg font-semibold">{p.name}</div>
                                        <div className="text-sm text-muted-foreground">{p.description}</div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between mt-4">
                                    {/* Profile details if linked */}
                                    {acc?.profile && (
                                        <div className="flex items-center gap-2">
                                            {acc.profile.avatar_url && (
                                                <img
                                                    src={acc.profile.avatar_url}
                                                    alt={acc.profile.login || acc.profile.username || p.id}
                                                    className="h-8 w-8 rounded-full border"
                                                />
                                            )}
                                            <span className="text-sm font-medium">
                                                @{acc.profile.login || acc.profile.username || acc.profile.email}
                                            </span>
                                        </div>
                                    )}

                                    {/* Action button */}
                                    {acc ? (
                                        <Button
                                            variant="destructive"
                                            size="sm"
                                            disabled={unlinkMutation.isLoading && unlinkMutation.variables === p.id}
                                            onClick={() => unlinkMutation.mutate(p.id)}
                                        >
                                            {unlinkMutation.isLoading && unlinkMutation.variables === p.id
                                                ? "Unlinking..."
                                                : "Unlink"}
                                        </Button>
                                    ) : (
                                        <Button
                                            variant="default"
                                            size="sm"
                                            disabled={linkMutation.isLoading && linkMutation.variables === p.id}
                                            onClick={() => linkMutation.mutate(p.id)}
                                        >
                                            {linkMutation.isLoading && linkMutation.variables === p.id
                                                ? "Linking..."
                                                : "Link"}
                                        </Button>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Error message */}
            {error && <div className="text-red-500 mt-4">{(error as Error).message}</div>}

            {/* Refresh button */}
            <div className="flex justify-end mt-8">
                <Button variant="outline" onClick={() => refetch()} disabled={isLoading || isFetching}>
                    Refresh
                </Button>
            </div>
        </div>
    );
}
