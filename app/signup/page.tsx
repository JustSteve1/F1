"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function SignupPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [name, setName] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { signup, logOut } = useAuth(); // Import logOut
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);

        // Validation
        if (!name.trim()) {
            setError("Name is required");
            setIsSubmitting(false);
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            setError("Please enter a valid email address");
            setIsSubmitting(false);
            return;
        }

        if (password.length < 8) {
            setError("Password must be at least 8 characters long");
            setIsSubmitting(false);
            return;
        }

        try {
            await signup(email, password, name);

            // Send Notification Email (Fire and forget, or await if critical)
            await fetch('/api/signup-notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email }),
            });

            // Show success message
            setSuccess(true);

            // Sign out immediately so they aren't logged in
            await logOut();

            // Redirect to home after a delay
            setTimeout(() => {
                router.push("/");
            }, 3000);

        } catch (err: any) {
            setError(err.message || "Failed to create an account");
            setIsSubmitting(false); // Only stop submitting on error
        }
    };

    if (success) {
        return (
            <div className="flex min-h-screen flex-col justify-center items-center bg-black px-6 py-12 lg:px-8">
                <div className="text-center space-y-4">
                    <h2 className="text-3xl font-light text-white">Thank you</h2>
                    <p className="text-white/60">Please check your email.</p>
                    <p className="text-xs text-white/30 pt-8">Redirecting to home...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen flex-col justify-center bg-black px-6 py-12 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-sm">
                <h2 className="mt-10 text-center text-2xl font-light tracking-tight text-white">
                    Join InPlay
                </h2>
                <p className="mt-2 text-center text-sm text-white/50">
                    Create your account to get started
                </p>
            </div>

            <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
                <form className="space-y-6" onSubmit={handleSubmit}>
                    <div>
                        <label htmlFor="name" className="block text-sm font-medium leading-6 text-white/80">
                            Name
                        </label>
                        <div className="mt-2">
                            <input
                                id="name"
                                name="name"
                                type="text"
                                autoComplete="name"
                                required
                                placeholder="Your full name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="block w-full rounded-md border-0 bg-white/5 py-1.5 text-white shadow-sm ring-1 ring-inset ring-white/10 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6 pl-3"
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="email" className="block text-sm font-medium leading-6 text-white/80">
                            Email address
                        </label>
                        <div className="mt-2">
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                required
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="block w-full rounded-md border-0 bg-white/5 py-1.5 text-white shadow-sm ring-1 ring-inset ring-white/10 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6 pl-3"
                            />
                        </div>
                    </div>

                    <div>
                        <div className="flex items-center justify-between">
                            <label htmlFor="password" className="block text-sm font-medium leading-6 text-white/80">
                                Password
                            </label>
                        </div>
                        <div className="mt-2">
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="new-password"
                                required
                                placeholder="Min 8 characters"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="block w-full rounded-md border-0 bg-white/5 py-1.5 text-white shadow-sm ring-1 ring-inset ring-white/10 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6 pl-3"
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="rounded-md bg-red-500/10 p-3 text-sm text-red-500 text-center border border-red-500/20">
                            {error}
                        </div>
                    )}

                    <div>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex w-full justify-center rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-semibold leading-6 text-white shadow-sm hover:bg-indigo-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isSubmitting ? "Creating account..." : "Sign up"}
                        </button>
                    </div>
                </form>

                <p className="mt-10 text-center text-sm text-white/40">
                    Already a member?{" "}
                    <Link href="/login" className="font-semibold leading-6 text-white/80 hover:text-white">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}
