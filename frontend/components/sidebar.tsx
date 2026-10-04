"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, MessageSquare, FileText, Search, Moon, Sun, Beaker } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

const navItems = [
  { name: "Dashboard", href: "/", icon: Activity },
  { name: "Chat", href: "/chat", icon: MessageSquare },
  { name: "Documents", href: "/documents", icon: FileText },
  { name: "Search", href: "/search", icon: Search },
];

const DISCLAIMER = "Wellness decision-support tool, not a medical device. Not for diagnosis or emergencies.";

/** Compact top bar for narrow screens, where a fixed 256px sidebar would leave almost no room for content. */
function MobileNav({ pathname }: { pathname: string }) {
  return (
    <header className="flex md:hidden items-center justify-between border-b border-border bg-card px-3 h-14 flex-shrink-0">
      <span className="flex items-center text-lg font-bold tracking-tight text-foreground">
        <Beaker className="h-5 w-5 mr-1.5" />
        PHIRE
      </span>
      <nav className="flex items-center gap-1" aria-label="Primary">
        {navItems.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            aria-label={item.name}
            aria-current={pathname === item.href ? "page" : undefined}
            className={cn(
              "rounded-md p-2 transition-colors",
              pathname === item.href ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/50"
            )}
          >
            <item.icon className="h-5 w-5" aria-hidden="true" />
          </Link>
        ))}
      </nav>
    </header>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <>
    <MobileNav pathname={pathname} />
    <div className="hidden md:flex h-screen w-64 flex-shrink-0 flex-col border-r border-border bg-card">
      <div className="flex h-16 items-center px-6 border-b border-border">
        <Beaker className="h-6 w-6 text-foreground mr-2" />
        <span className="text-xl font-bold tracking-tight text-foreground">PHIRE</span>
      </div>

      <nav className="flex-1 space-y-1 px-4 py-6">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-secondary text-foreground font-semibold"
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              )}
            >
              <item.icon
                className={cn(
                  "mr-3 h-5 w-5 flex-shrink-0",
                  isActive ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
                )}
                aria-hidden="true"
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex w-full items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
          >
            {theme === "dark" ? (
              <>
                <Sun className="mr-2 h-4 w-4" />
                Light Mode
              </>
            ) : (
              <>
                <Moon className="mr-2 h-4 w-4" />
                Dark Mode
              </>
            )}
          </button>
        )}
        <p className="mt-3 text-[11px] leading-snug text-muted-foreground text-center">{DISCLAIMER}</p>
      </div>
    </div>
    </>
  );
}
