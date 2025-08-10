import { createStore } from 'zustand';
import { persist } from 'zustand/middleware';

export type AuthState = {
    isLoggedIn: boolean;
    accessToken: string | null;
    refreshToken: string | null;
    userName: string | null;
};

export type AuthActions = {
    login: (userName: string, accessToken: string, refreshToken: string) => void;
    logout: () => void;
};

export type AuthStore = AuthState & AuthActions;

export const defaultInitState: AuthState = {
    isLoggedIn: false,
    accessToken: null,
    refreshToken: null,
    userName: null,
};

export const useAuthStore = (
    initState: AuthState = defaultInitState
) => {
    return createStore<AuthStore>()(
        persist(
            (set) => ({
                ...initState,
                login: (userName, accessToken, refreshToken) =>
                    set(() => ({
                        isLoggedIn: true,
                        userName,
                        accessToken,
                        refreshToken,
                    })),
                logout: () =>
                    set(() => ({
                        isLoggedIn: false,
                        userName: null,
                        accessToken: null,
                        refreshToken: null,
                    })),
            }),
            {
                name: 'auth',
            }
        )
    );
};
