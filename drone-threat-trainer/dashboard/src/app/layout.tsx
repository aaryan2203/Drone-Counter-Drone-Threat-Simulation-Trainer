import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Drone Threat Simulation Trainer",
  description: "Tactical simulation and trainee evaluation platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-cyan-500 selection:text-slate-950">
        {children}
      </body>
    </html>
  );
}
