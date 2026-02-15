"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export function AuthLoginTile() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { login, signInWithGoogle } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsSubmitting(true);
        try {
            await login(email, password);
            router.push("/profile");
        } catch (err: any) {
            setError(err.message || "Failed to sign in");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleGoogleSignIn = async () => {
        setError("");
        try {
            await signInWithGoogle();
            router.push("/profile");
        } catch (err: any) {
            setError(err.message || "Failed to sign in with Google");
        }
    };

    return (
        <Card className="h-full flex flex-col justify-center border border-white/10 bg-white/5 backdrop-blur-sm rounded-sm hover:border-white/30 transition-all duration-500">
            <CardHeader>
                <CardTitle className="text-3xl font-black uppercase tracking-tighter text-white">Welcome Back</CardTitle>
                <CardDescription className="text-white/60 font-light tracking-wide uppercase text-xs">Sign in to your account</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <label htmlFor="email" className="text-xs font-bold uppercase tracking-widest text-white/50">
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            placeholder="PILOT@F1.COM"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="flex h-12 w-full rounded-sm border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/20 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 transition-all"
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <label htmlFor="password" className="text-xs font-bold uppercase tracking-widest text-white/50">
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="flex h-12 w-full rounded-sm border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/20 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 transition-all"
                            required
                        />
                    </div>
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="inline-flex items-center justify-center rounded-sm text-sm font-bold uppercase tracking-widest ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-white text-black hover:bg-white/90 h-12 w-full mt-4"
                    >
                        {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        Sign In
                    </button>
                </form>

                <div className="relative my-8">
                    <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-white/10" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase tracking-widest">
                        <span className="bg-black px-2 text-white/40">Or</span>
                    </div>
                </div>

                <button
                    type="button"
                    onClick={handleGoogleSignIn}
                    className="inline-flex items-center justify-center rounded-sm text-sm font-bold uppercase tracking-widest ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-white/10 bg-white/5 text-white hover:bg-white/10 h-12 w-full"
                >
                    <svg className="mr-2 h-4 w-4" aria-hidden="true" viewBox="0 0 24 24">
                        <path
                            fill="currentColor"
                            d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"
                        />
                    </svg>
                    Google
                </button>
            </CardContent>
        </Card>
    );
}
