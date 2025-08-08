"use client"
import { config } from "@/config";
import { useAuthStore } from "@/lib/stores/auth-store";
import axios from "axios";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function Home() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false)
  const { accessToken } = useAuthStore()

  const handleLoginSuccess = (message: string, user: any, tokens: any) => {
    // localStorage.setItem("access_token", tokens.access_token);
    // localStorage.setItem("refresh_token", tokens.refresh_token);
    // localStorage.setItem("user_profile", JSON.stringify(user));
    toast.success(message);
    router.push("/dashboard");
  };

  useEffect(() => {
    if (!accessToken) {
      router.replace('/login')
    }
  }, [])

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (code && state) {
      setIsLoading(true);
      // Replace the URL to remove query params
      router.replace(window.location.pathname);

      axios.get(`${config.BASE_API_URL}/auth/oauth/github/callback`, {
        params: { code, state }
      })
        .then(response => {
          if (response.status === 200) {
            const { message, user, tokens } = response.data;
            handleLoginSuccess(message, user, tokens);
          } else {
            toast.error(response.data.detail || "GitHub login callback failed.");
          }
        })
        .catch(err => {
          console.error("GitHub callback error:", err);
          const errorMessage = err.response?.data?.detail || "An unexpected error occurred during GitHub callback.";
          toast.error(errorMessage);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [searchParams, router]);

  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      {isLoading ? "Loading..." : "Home Page"}
    </div>
  );
}
