"use client"

import { useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import axios from "axios"
import { config } from "@/config"

interface LoginFormProps extends React.ComponentProps<"div"> {
  onSignupClick: () => void;
}

export default function LoginForm({
  className,
  onSignupClick,
  ...props
}: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleLoginSuccess = (message: string, user: any, tokens: any) => {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    localStorage.setItem("user_profile", JSON.stringify(user));
    toast.success(message);
    router.push("/dashboard");
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await axios.post(`${config.BASE_API_URL}/auth/login/email-password`, {
        email,
        password,
      });

      if (response.status === 200) {
        const { message, user, tokens } = response.data;
        handleLoginSuccess(message, user, tokens);
      } else {
        toast.error(response.data.detail || "Login failed. Please check your credentials.");
      }
    } catch (err: any) {
      console.error("Email login error:", err);
      const errorMessage = err.response?.data?.detail || "An unexpected error occurred during login.";
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGithubLogin = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${config.BASE_API_URL}/auth/oauth/github`);
      if (response.status !== 200) {
        throw new Error("Failed to get GitHub login URL.");
      }
      // For OAuth, you still need to redirect the browser
      window.location.href = response.data;
    } catch (err: any) {
      console.error("GitHub login error:", err);
      toast.error(err.message || "An unexpected error occurred during GitHub login.");
      setIsLoading(false);
    }
  };

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, router]);

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader>
          <CardTitle>Login to your account</CardTitle>
          <CardDescription>
            Enter your email below to login to your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleEmailLogin}>
            <div className="flex flex-col gap-6">
              <div className="grid gap-3">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="m@example.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="grid gap-3">
                <div className="flex items-center">
                  <Label htmlFor="password">Password</Label>
                  <a
                    href="#"
                    className="ml-auto inline-block text-sm underline-offset-4 hover:underline"
                  >
                    Forgot your password?
                  </a>
                </div>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Logging In..." : "Login"}
              </Button>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">
                    Or continue with
                  </span>
                </div>
              </div>
              <Button
                variant="outline"
                className="w-full"
                onClick={handleGithubLogin}
                disabled={isLoading}
              >
                {isLoading ? "Redirecting..." : "Login with GitHub"}
              </Button>
              <Button variant="outline" className="w-full" disabled={isLoading}>
                Login with Google
              </Button>
            </div>
            <div className="mt-4 text-center text-sm">
              Don&apos;t have an account?{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  onSignupClick();
                }}
                className="underline underline-offset-4"
              >
                Sign up
              </a>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
