"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useLoginWith2FA } from "@/hooks/api/use2FA";
import { Shield } from "lucide-react";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpToken, setTotpToken] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const loginWith2FA = useLoginWith2FA();
  const { toast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Check if 2FA is required from URL params
  useEffect(() => {
    if (searchParams.get('requires2fa') === 'true') {
      setRequires2FA(true);
    }
  }, [searchParams]);

  // Redirect if already authenticated
  if (isAuthenticated) {
    router.push("/dashboard");
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (requires2FA) {
        // Login with 2FA
        const response = await loginWith2FA.mutateAsync({
          email,
          password,
          totp_token: totpToken,
        });
        
        // Save tokens and redirect
        localStorage.setItem('token', response.access_token);
        if (response.refresh_token) {
          localStorage.setItem('refreshToken', response.refresh_token);
        }
        router.push('/dashboard');
        
        toast({
          title: "Success",
          description: "Logged in successfully with 2FA",
        });
      } else {
        // Regular login
        await login({ email, password });
        toast({
          title: "Success",
          description: "Logged in successfully",
        });
      }
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail || error.message;
      
      // Check if 2FA is required
      if (errorDetail.toLowerCase().includes('2fa')) {
        setRequires2FA(true);
        toast({
          title: "2FA Required",
          description: "Please enter your 2FA code",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Login Failed",
          description: errorDetail || "Invalid credentials",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <CardTitle className="text-2xl font-bold">Login</CardTitle>
            {requires2FA && (
              <Shield className="w-5 h-5 text-green-500" />
            )}
          </div>
          <CardDescription>
            {requires2FA 
              ? "Enter your 2FA code from authenticator app"
              : "Enter your email and password to access your account"}
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            
            {requires2FA && (
              <div className="space-y-2">
                <Label htmlFor="totp">2FA Code</Label>
                <Input
                  id="totp"
                  type="text"
                  placeholder="000000"
                  maxLength={6}
                  value={totpToken}
                  onChange={(e) => setTotpToken(e.target.value.replace(/\D/g, ""))}
                  required
                  disabled={isLoading}
                  className="font-mono text-center text-lg tracking-widest"
                />
                <p className="text-xs text-muted-foreground">
                  Enter the 6-digit code from your authenticator app
                </p>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || (requires2FA && totpToken.length !== 6)}
            >
              {isLoading ? "Signing in..." : "Sign in"}
            </Button>
            
            {requires2FA && (
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => {
                  setRequires2FA(false);
                  setTotpToken("");
                }}
              >
                Back to Login
              </Button>
            )}
            
            <div className="flex flex-col space-y-2 text-sm text-center">
              <Link
                href="/forgot-password"
                className="text-muted-foreground hover:text-foreground"
              >
                Forgot password?
              </Link>
              <div>
                Don&apos;t have an account?{" "}
                <Link
                  href="/register"
                  className="text-primary hover:underline"
                >
                  Create account
                </Link>
              </div>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
