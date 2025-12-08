"use client";

import { useState } from "react";
import Link from "next/link";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  return (
    <div style={{ maxWidth: 360, margin: "0 auto", display: "grid", gap: 12 }}>
      <h1>Register</h1>
      <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full name" />
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" />
      <button>Create account</button>
      <Link href="/login">Already have an account?</Link>
    </div>
  );
}
