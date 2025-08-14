import { authClient } from "../auth-client";

export const listUserAccountsWithProfile = async () => {
    const response = await authClient.listAccounts();
    const accounts = response.data;
    if (!accounts || accounts.length === 0) {
        return [];
    }
    const profiles = await Promise.all(
        accounts.map(async (acc) => {
            try {
                const profileResponse = await authClient.accountInfo({
                    accountId: acc.accountId,
                });
                return {
                    ...acc,
                    profile: {
                        user: profileResponse.data?.user,
                        data: profileResponse.data?.data,
                    },
                };
            } catch (err) {
                return {
                    ...acc,
                    profile: null,
                };
            }
        })
    );
    return profiles;
};

export const linkSocialAccount = async (provider: string) => {
    try {
        console.log(provider)
        const response = await authClient.linkSocial({ provider });
        return response.data;
    } catch (error) {
        throw new Error("Failed to link social account: " + (error as Error).message);
    }
}

export const unlinkSocialAccount = async (provider: string) => {
    try {
        console.log(provider)
        const response = await authClient.unlinkAccount({ providerId: provider });
        return response.data;
    } catch (error) {
        console.log(error)
        throw new Error("Failed to link social account: " + (error as Error).message);
    }
}