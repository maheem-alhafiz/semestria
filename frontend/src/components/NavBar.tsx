"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV_ITEMS = [
  { href: "/planner", label: "Planner" },
  { href: "/plans", label: "Plans" },
  { href: "/tracker", label: "Degree Tracker" },
] as const;

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-canvas/90 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center justify-between px-6">
        {/* Wordmark: Inter 700, 28px, -0.02em tracking, paper text with
            an accent-colored period -- per the semestria brand spec. */}
        <Link href="/planner" className="text-[28px] font-bold tracking-[-0.02em] text-paper">
          semestria<span className="text-accent">.</span>
        </Link>

        {/* Right side container: Links + Divider + Theme Toggle */}
        <div className="flex items-center gap-4">
          <nav className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={
                    isActive
                      ? "rounded-full bg-elevated px-3.5 py-1.5 text-sm font-medium text-paper"
                      : "rounded-full px-3.5 py-1.5 text-sm text-muted transition-colors hover:text-paper"
                  }
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          
          {/* Subtle vertical line and the toggle button */}
          <div className="flex items-center border-l border-hairline pl-4">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}