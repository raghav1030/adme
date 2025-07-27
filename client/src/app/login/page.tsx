"use client"

import LoginForm from "@/components/auth/login-form";
import SignupForm from "@/components/auth/signup-form";
import { useState } from "react"


export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true); // State to toggle between login and signup

  const handleLoginClick = () => setIsLogin(true);
  const handleSignupClick = () => setIsLogin(false);

  return (
    <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <div className="w-full max-w-sm">
        {isLogin ? (
          <LoginForm onSignupClick={handleSignupClick} />
        ) : (
          <SignupForm onLoginClick={handleLoginClick} />
        )}
      </div>
    </div>
  );
}
