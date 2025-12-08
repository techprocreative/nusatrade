"use client";

import { useState } from "react";
import Link from "next/link";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");

  return (
    <div style={{ maxWidth: 360, margin: "0 auto", display: "grid", gap: 12 }}>
      <h1>Forgot Password</h1>
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <button>Send reset link</button>
      <Link href="/login">Back to login</Link>
    </div>
  );
}
