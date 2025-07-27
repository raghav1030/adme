"use client"

import { useState } from "react"
import { useRouter } from "next/navigation" // For redirection
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
import { config } from "@/config" // Assuming config.BASE_API_URL is defined here

interface SignupFormProps extends React.ComponentProps<"div"> {
    onLoginClick: () => void; // Function to switch to login form
}

export default function SignupForm({
    className,
    onLoginClick,
    ...props
}: SignupFormProps) {
    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [retypePassword, setRetypePassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();

    const handleSignup = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        if (password !== retypePassword) {
            toast.error("Passwords do not match.");
            setIsLoading(false);
            return;
        }

        try {
            const response = await axios.post(`${config.BASE_API_URL}/auth/signup`, {
                full_name: fullName,
                email,
                password,
                retype_password: retypePassword,
            });

            if (response.status === 201) {
                const { message, user, tokens } = response.data;
                // Store tokens (e.g., in localStorage)
                localStorage.setItem("access_token", tokens.access_token);
                localStorage.setItem("refresh_token", tokens.refresh_token);
                // You might also want to store user info if needed
                localStorage.setItem("user_profile", JSON.stringify(user));

                toast.success(message || "Account created and logged in successfully!");
                router.push("/dashboard"); // Redirect to a dashboard or home page
            } else {
                toast.error(response.data.detail || "Signup failed. Please try again.");
            }
        } catch (err: any) {
            console.error("Signup error:", err);
            const errorMessage = err.response?.data?.detail || "An unexpected error occurred during signup.";
            toast.error(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className={cn("flex flex-col gap-6", className)} {...props}>
            <Card>
                <CardHeader>
                    <CardTitle>Create your account</CardTitle>
                    <CardDescription>
                        Enter your details below to create a new account
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSignup}>
                        <div className="flex flex-col gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="fullName">Full Name</Label>
                                <Input
                                    id="fullName"
                                    type="text"
                                    placeholder="John Doe"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-2">
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
                            <div className="grid gap-2">
                                <Label htmlFor="password">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="retypePassword">Retype Password</Label>
                                <Input
                                    id="retypePassword"
                                    type="password"
                                    required
                                    value={retypePassword}
                                    onChange={(e) => setRetypePassword(e.target.value)}
                                />
                            </div>
                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading ? "Creating Account..." : "Sign Up"}
                            </Button>
                        </div>
                        <div className="mt-4 text-center text-sm">
                            Already have an account?{" "}
                            <a
                                href="#"
                                onClick={(e) => {
                                    e.preventDefault();
                                    onLoginClick();
                                }}
                                className="underline underline-offset-4"
                            >
                                Login
                            </a>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
