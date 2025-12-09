"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Eye, EyeOff, User, Mail, Lock, Check } from "lucide-react";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const { register, isAuthenticated } = useAuth();
  const { toast } = useToast();
  const router = useRouter();

  // Redirect if already authenticated
  if (isAuthenticated) {
    router.push("/dashboard");
    return null;
  }

  // Password strength indicators
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
  };

  const isPasswordStrong = Object.values(passwordChecks).every(Boolean);
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isPasswordStrong) {
      toast({
        variant: "destructive",
        title: "Weak Password",
        description: "Please meet all password requirements",
      });
      return;
    }

    if (!passwordsMatch) {
      toast({
        variant: "destructive",
        title: "Password Mismatch",
        description: "Passwords do not match",
      });
      return;
    }

    if (!acceptTerms) {
      toast({
        variant: "destructive",
        title: "Terms Required",
        description: "Please accept the terms and conditions",
      });
      return;
    }

    setIsLoading(true);

    try {
      await register({ full_name: fullName, email, password });
      toast({
        title: "Account Created",
        description: "Welcome to NusaTrade! Please login to continue.",
      });
      router.push("/login");
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail || error.message;
      toast({
        variant: "destructive",
        title: "Registration Failed",
        description: errorDetail || "Failed to create account",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <span className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              NusaTrade
            </span>
          </Link>
          <p className="text-slate-400 mt-2">Create your trading account</p>
        </div>

        <Card className="border-slate-700 bg-slate-800/50 backdrop-blur">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-white">Create Account</CardTitle>
            <CardDescription className="text-slate-400">
              Enter your details to get started with AI-powered trading
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {/* Full Name */}
              <div className="space-y-2">
                <Label htmlFor="fullName" className="text-slate-300">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="fullName"
                    type="text"
                    placeholder="John Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-300">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-500"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-300">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pl-10 pr-10 bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {/* Password Strength */}
                {password.length > 0 && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className={`flex items-center gap-1 ${passwordChecks.length ? "text-green-400" : "text-slate-500"}`}>
                      <Check className="w-3 h-3" /> 8+ characters
                    </div>
                    <div className={`flex items-center gap-1 ${passwordChecks.uppercase ? "text-green-400" : "text-slate-500"}`}>
                      <Check className="w-3 h-3" /> Uppercase
                    </div>
                    <div className={`flex items-center gap-1 ${passwordChecks.lowercase ? "text-green-400" : "text-slate-500"}`}>
                      <Check className="w-3 h-3" /> Lowercase
                    </div>
                    <div className={`flex items-center gap-1 ${passwordChecks.number ? "text-green-400" : "text-slate-500"}`}>
                      <Check className="w-3 h-3" /> Number
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-slate-300">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="confirmPassword"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={isLoading}
                    className={`pl-10 bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-500 ${confirmPassword.length > 0
                        ? passwordsMatch
                          ? "border-green-500"
                          : "border-red-500"
                        : ""
                      }`}
                  />
                </div>
                {confirmPassword.length > 0 && !passwordsMatch && (
                  <p className="text-xs text-red-400">Passwords do not match</p>
                )}
              </div>

              {/* Terms and Conditions */}
              <div className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id="terms"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                  className="mt-1 rounded bg-slate-700 border-slate-600"
                />
                <label htmlFor="terms" className="text-sm text-slate-400">
                  I agree to the{" "}
                  <Link href="/terms" className="text-blue-400 hover:underline">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className="text-blue-400 hover:underline">
                    Privacy Policy
                  </Link>
                </label>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col space-y-4">
              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-500 to-emerald-500 hover:opacity-90"
                disabled={isLoading || !isPasswordStrong || !passwordsMatch || !acceptTerms}
              >
                {isLoading ? "Creating Account..." : "Create Account"}
              </Button>

              <div className="text-sm text-center text-slate-400">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="text-blue-400 hover:underline font-medium"
                >
                  Sign in
                </Link>
              </div>
            </CardFooter>
          </form>
        </Card>

        {/* Features Preview */}
        <div className="mt-8 grid grid-cols-3 gap-4 text-center text-xs text-slate-500">
          <div>
            <span className="text-lg">🤖</span>
            <p>AI Trading</p>
          </div>
          <div>
            <span className="text-lg">📈</span>
            <p>ML Bots</p>
          </div>
          <div>
            <span className="text-lg">🔒</span>
            <p>Secure</p>
          </div>
        </div>
      </div>
    </div>
  );
}
