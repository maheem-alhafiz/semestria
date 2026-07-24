"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

//NEW NAV_ITEMS from GEMINI:
const NAV_ITEMS = [
  { href: "/", label: "Search" },
  { href: "/planner", label: "Planner" },
  { href: "/plans", label: "Plans" },
  { href: "/tracker", label: "Degree Tracker" },
] as const;

// OLD NAV_ITEMS
//const NAV_ITEMS = [
  //{ href: "/", label: "Search" },
  //{ href: "/planner", label: "Planner" },
  //{ href: "/plans", label: "Plans" },
//] as const;

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-canvas/90 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center justify-between px-6">
        {/* Wordmark: Inter 700, 28px, -0.02em tracking, paper text with
            an accent-colored period -- per the semestria brand spec. */}
        <Link href="/" className="text-[28px] font-bold tracking-[-0.02em] text-paper">
          semestria<span className="text-accent">.</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
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
      </div>
    </header>
  );
}
