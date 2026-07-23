import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { NavBar } from "@/components/NavBar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "semestria.",
  description: "A Coursicle-inspired academic planner for University of Manitoba students.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-canvas font-sans text-paper antialiased">
        <NavBar />
        {children}
      </body>
    </html>
  );
}
