"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun, Plus } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/AuthContext";
import { cn } from "@/lib/utils";

export default function Header() {
    const pathname = usePathname();
    const { theme, setTheme, resolvedTheme } = useTheme();
    const { user, logout } = useAuth();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const toggleTheme = () => {
        setTheme(resolvedTheme === "dark" ? "light" : "dark");
    };

    const isThoughts = pathname.startsWith("/thoughts");
    const isCreate = pathname === "/create";

    return (
        <header className="sticky top-0 z-50 shrink-0 border-b border-zinc-200 bg-white/80 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-950/80 transition-colors">
            <div className="mx-auto flex max-w-2xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
                <div className="flex items-center gap-6">
                    <Link
                        href="/"
                        className="text-lg font-bold tracking-tight text-zinc-900 dark:text-zinc-50 hover:opacity-80 transition-opacity flex items-center gap-2"
                    >
                        <div className="h-7 w-7 rounded-xl bg-gradient-to-tr from-zinc-900 to-zinc-700 dark:from-zinc-100 dark:to-zinc-300 flex items-center justify-center shadow-sm">
                            <span className="text-white dark:text-zinc-900 text-sm font-black">T</span>
                        </div>
                        <span>Thoughts</span>
                    </Link>

                    {/* Desktop Navigation Links */}
                    <nav className="hidden sm:flex items-center gap-4 text-sm font-medium">
                        <Link
                            href="/"
                            className={cn(
                                "transition-colors hover:text-zinc-900 dark:hover:text-zinc-50",
                                !isThoughts ? "text-zinc-900 dark:text-zinc-50" : "text-zinc-500 dark:text-zinc-400"
                            )}
                        >
                            Journal
                        </Link>
                        <Link
                            href="/thoughts"
                            className={cn(
                                "transition-colors hover:text-zinc-900 dark:hover:text-zinc-50",
                                isThoughts ? "text-zinc-900 dark:text-zinc-50" : "text-zinc-500 dark:text-zinc-400"
                            )}
                        >
                            Notes
                        </Link>
                    </nav>
                </div>

                <div className="flex items-center gap-2 sm:gap-4">
                    <button
                        onClick={toggleTheme}
                        className="p-2 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50 transition-colors rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800"
                        aria-label="Toggle theme"
                    >
                        {mounted && resolvedTheme === "dark" ? (
                            <Sun className="h-5 w-5" />
                        ) : (
                            <Moon className="h-5 w-5" />
                        )}
                    </button>

                    {!isCreate && !isThoughts && user && (
                        <Link
                            href="/create"
                            className="inline-flex items-center justify-center gap-2 rounded-full bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-md hover:bg-zinc-800 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 transition-all active:scale-95"
                        >
                            <Plus className="h-4 w-4" />
                            <span className="hidden sm:inline">New journal</span>
                        </Link>
                    )}

                    {user && (
                        <button
                            onClick={logout}
                            className="text-xs font-semibold text-zinc-500 hover:text-red-500 dark:text-zinc-400 dark:hover:text-red-400 ml-2 sm:ml-4 transition-colors p-2"
                        >
                            Logout
                        </button>
                    )}
                </div>
            </div>

            {/* Mobile nav bottom bar */}
            <nav className="flex sm:hidden items-center gap-6 px-4 pb-2 text-sm font-medium overflow-x-auto">
                <Link
                    href="/"
                    className={cn(
                        "pb-2 border-b-2 transition-colors",
                        !isThoughts ? "border-zinc-900 text-zinc-900 dark:border-white dark:text-zinc-50" : "border-transparent text-zinc-500 dark:text-zinc-400"
                    )}
                >
                    Journal
                </Link>
                <Link
                    href="/thoughts"
                    className={cn(
                        "pb-2 border-b-2 transition-colors",
                        isThoughts ? "border-zinc-900 text-zinc-900 dark:border-white dark:text-zinc-50" : "border-transparent text-zinc-500 dark:text-zinc-400"
                    )}
                >
                    Notes
                </Link>
            </nav>
        </header>
    );
}
