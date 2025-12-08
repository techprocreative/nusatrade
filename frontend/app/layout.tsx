import "./globals.css";
import type { ReactNode } from "react";
import { AuthProvider } from "@/contexts/AuthContext";
import { ReactQueryProvider } from "@/lib/react-query";
import { Toaster } from "@/components/ui/toaster";

export const metadata = {
  title: "Forex AI Platform",
  description: "AI-powered forex trading platform with ML bots and LLM supervisor"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <ReactQueryProvider>
          <AuthProvider>
            {children}
            <Toaster />
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
