"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { use2FAStatus, useSetup2FA, useVerify2FA, useDisable2FA } from "@/hooks/api/use2FA";
import { Shield, Key, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import Image from "next/image";

export default function SecurityPage() {
  const { toast } = useToast();
  const { data: status, isLoading: statusLoading } = use2FAStatus();
  const setup2FA = useSetup2FA();
  const verify2FA = useVerify2FA();
  const disable2FA = useDisable2FA();

  const [setupData, setSetupData] = useState<{ secret: string; qr_code: string } | null>(null);
  const [verifyToken, setVerifyToken] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableToken, setDisableToken] = useState("");
  const [showDisableForm, setShowDisableForm] = useState(false);

  const handleSetup2FA = async () => {
    try {
      const data = await setup2FA.mutateAsync();
      setSetupData(data);
      toast({
        title: "2FA Setup Started",
        description: "Scan the QR code with your authenticator app",
      });
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Setup Failed",
        description: error.response?.data?.detail || "Failed to setup 2FA",
      });
    }
  };

  const handleVerify2FA = async () => {
    if (verifyToken.length !== 6) {
      toast({
        variant: "destructive",
        title: "Invalid Token",
        description: "Please enter a 6-digit code",
      });
      return;
    }

    try {
      await verify2FA.mutateAsync({ token: verifyToken });
      toast({
        title: "2FA Enabled Successfully! ✅",
        description: "Your account is now more secure",
      });
      setSetupData(null);
      setVerifyToken("");
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Verification Failed",
        description: error.response?.data?.detail || "Invalid TOTP code",
      });
    }
  };

  const handleDisable2FA = async () => {
    if (!disablePassword || disableToken.length !== 6) {
      toast({
        variant: "destructive",
        title: "Missing Information",
        description: "Please provide password and TOTP code",
      });
      return;
    }

    try {
      await disable2FA.mutateAsync({
        password: disablePassword,
        totp_token: disableToken,
      });
      toast({
        title: "2FA Disabled",
        description: "Two-factor authentication has been disabled",
      });
      setShowDisableForm(false);
      setDisablePassword("");
      setDisableToken("");
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Disable Failed",
        description: error.response?.data?.detail || "Failed to disable 2FA",
      });
    }
  };

  if (statusLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Security Settings</h1>
        <p className="text-slate-400 mt-1">Manage your account security and authentication</p>
      </div>

      {/* 2FA Status Card */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className={`w-8 h-8 ${status?.enabled ? 'text-green-500' : 'text-yellow-500'}`} />
              <div>
                <CardTitle className="text-white">Two-Factor Authentication</CardTitle>
                <CardDescription>
                  {status?.enabled
                    ? "Your account is protected with 2FA"
                    : "Add an extra layer of security to your account"}
                </CardDescription>
              </div>
            </div>
            {status?.enabled ? (
              <CheckCircle2 className="w-6 h-6 text-green-500" />
            ) : (
              <AlertCircle className="w-6 h-6 text-yellow-500" />
            )}
          </div>
        </CardHeader>
        <CardContent>
          {!status?.enabled && !setupData && (
            <div className="space-y-4">
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <p className="text-blue-400 text-sm">
                  <strong>Why enable 2FA?</strong>
                  <br />
                  Two-factor authentication adds an extra layer of security by requiring both your password and
                  a code from your authenticator app to sign in.
                </p>
              </div>
              <Button
                onClick={handleSetup2FA}
                disabled={setup2FA.isPending}
                className="w-full sm:w-auto"
              >
                {setup2FA.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Setting up...
                  </>
                ) : (
                  <>
                    <Key className="w-4 h-4 mr-2" />
                    Enable 2FA
                  </>
                )}
              </Button>
            </div>
          )}

          {setupData && (
            <div className="space-y-6">
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold text-white mb-2">Step 1: Scan QR Code</h3>
                  <p className="text-sm text-slate-400 mb-4">
                    Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                  </p>
                  <div className="flex justify-center p-4 bg-white rounded-lg">
                    <img
                      src={setupData.qr_code}
                      alt="2FA QR Code"
                      className="w-64 h-64"
                    />
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">Step 2: Save Backup Code</h3>
                  <p className="text-sm text-slate-400 mb-2">
                    Save this secret code in a safe place. You can use it to recover access if you lose your device.
                  </p>
                  <div className="p-3 bg-slate-900 border border-slate-700 rounded-lg font-mono text-sm text-white">
                    {setupData.secret}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">Step 3: Verify</h3>
                  <p className="text-sm text-slate-400 mb-2">
                    Enter the 6-digit code from your authenticator app to complete setup
                  </p>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      placeholder="000000"
                      maxLength={6}
                      value={verifyToken}
                      onChange={(e) => setVerifyToken(e.target.value.replace(/\D/g, ""))}
                      className="font-mono text-center text-lg tracking-widest"
                    />
                    <Button
                      onClick={handleVerify2FA}
                      disabled={verify2FA.isPending || verifyToken.length !== 6}
                    >
                      {verify2FA.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        "Verify"
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              <Button
                variant="outline"
                onClick={() => {
                  setSetupData(null);
                  setVerifyToken("");
                }}
              >
                Cancel
              </Button>
            </div>
          )}

          {status?.enabled && !showDisableForm && (
            <div className="space-y-4">
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                <p className="text-green-400 text-sm">
                  Your account is protected with two-factor authentication.
                  You&apos;ll need to enter a code from your authenticator app when signing in.
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={() => setShowDisableForm(true)}
              >
                Disable 2FA
              </Button>
            </div>
          )}

          {status?.enabled && showDisableForm && (
            <div className="space-y-4">
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-red-400 text-sm">
                  ⚠️ Disabling 2FA will make your account less secure.
                </p>
              </div>

              <div className="space-y-3">
                <div>
                  <Label htmlFor="disable-password">Your Password</Label>
                  <Input
                    id="disable-password"
                    type="password"
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    placeholder="Enter your password"
                  />
                </div>

                <div>
                  <Label htmlFor="disable-token">Current 2FA Code</Label>
                  <Input
                    id="disable-token"
                    type="text"
                    maxLength={6}
                    value={disableToken}
                    onChange={(e) => setDisableToken(e.target.value.replace(/\D/g, ""))}
                    placeholder="000000"
                    className="font-mono text-center text-lg tracking-widest"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={handleDisable2FA}
                  disabled={disable2FA.isPending}
                >
                  {disable2FA.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Disabling...
                    </>
                  ) : (
                    "Confirm Disable"
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowDisableForm(false);
                    setDisablePassword("");
                    setDisableToken("");
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Other Security Settings */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Password</CardTitle>
          <CardDescription>Change your password regularly to keep your account secure</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline">
            Change Password
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Active Sessions</CardTitle>
          <CardDescription>Manage devices that are currently logged in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg">
              <div>
                <p className="font-medium text-white">Current Session</p>
                <p className="text-sm text-slate-400">Windows • Chrome • Jakarta, Indonesia</p>
              </div>
              <span className="text-xs text-green-400">Active now</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
