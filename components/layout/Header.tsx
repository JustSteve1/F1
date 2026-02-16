"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useState } from "react";

export default function Header() {
    const { user } = useAuth();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/50 backdrop-blur-md">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                {/* Logo */}
                <Link href="/" className="text-2xl font-bold tracking-tighter text-white">
                    InPlay
                </Link>

                {/* Desktop Nav */}
                <nav className="hidden md:flex items-center gap-8">
                    <Link href="/about" className="text-sm font-medium text-white/70 hover:text-white transition-colors">
                        About
                    </Link>
                    <Link href="/frontend/userpaddock" className="text-sm font-medium text-white/70 hover:text-white transition-colors">
                        Latest
                    </Link>
                    {user ? (
                        <Link
                            href="/profile"
                            className="text-sm font-medium text-white hover:text-white/80 transition-colors"
                        >
                            Profile
                        </Link>
                    ) : (
                        <Link
                            href="/login"
                            className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-black hover:bg-white/90 transition-colors"
                        >
                            Sign In
                        </Link>
                    )}
                </nav>

                {/* Mobile Menu Button */}
                <button
                    className="md:hidden text-white"
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-6 h-6"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d={mobileMenuOpen ? "M6 18L18 6M6 6l12 12" : "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"}
                        />
                    </svg>
                </button>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
                <div className="md:hidden absolute top-full left-0 right-0 border-b border-white/10 bg-black/90 backdrop-blur-xl p-6 flex flex-col gap-4">
                    <Link
                        href="/about"
                        className="text-lg font-medium text-white/70 hover:text-white"
                        onClick={() => setMobileMenuOpen(false)}
                    >
                        About
                    </Link>
                    <Link
                        href="/frontend/userpaddock"
                        className="text-lg font-medium text-white/70 hover:text-white"
                        onClick={() => setMobileMenuOpen(false)}
                    >
                        Latest
                    </Link>
                    {user ? (
                        <Link
                            href="/profile"
                            className="text-lg font-medium text-white"
                            onClick={() => setMobileMenuOpen(false)}
                        >
                            Profile
                        </Link>
                    ) : (
                        <Link
                            href="/login"
                            className="text-lg font-medium text-white"
                            onClick={() => setMobileMenuOpen(false)}
                        >
                            Sign In
                        </Link>
                    )}
                </div>
            )}
        </header>
    );
}
