"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ProfilePage() {
    const { user, loading, logOut } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.push("/login");
        }
    }, [user, loading, router]);

    const handleSignOut = async () => {
        try {
            await logOut();
            router.push("/login");
        } catch (error) {
            console.error("Failed to sign out", error);
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-black text-white">
                <p>Loading...</p>
            </div>
        );
    }

    if (!user) {
        return null; // Will redirect
    }

    return (
        <div className="min-h-screen bg-black text-white">
            <header className="border-b border-white/10 bg-black/70 backdrop-blur p-4">
                <div className="mx-auto max-w-5xl flex justify-between items-center">
                    <h1 className="text-xl font-bold tracking-tight text-white">InPlay Profile</h1>
                    <button
                        onClick={handleSignOut}
                        className="rounded-md bg-white/10 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-white/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white transition-colors"
                    >
                        Sign out
                    </button>
                </div>
            </header>
            <main className="mx-auto max-w-5xl px-4 py-12">
                <div className="overflow-hidden rounded-lg bg-white/5 shadow ring-1 ring-white/10">
                    <div className="px-4 py-5 sm:px-6">
                        <h3 className="text-base font-semibold leading-6 text-white">User Information</h3>
                        <p className="mt-1 max-w-2xl text-sm text-white/50">Personal details and application access.</p>
                    </div>
                    <div className="border-t border-white/10 px-4 py-5 sm:p-0">
                        <dl className="sm:divide-y sm:divide-white/10">
                            <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                                <dt className="text-sm font-medium text-white/70">Display Name</dt>
                                <dd className="mt-1 text-sm text-white sm:col-span-2 sm:mt-0">{user.displayName || "N/A"}</dd>
                            </div>
                            <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                                <dt className="text-sm font-medium text-white/70">Email address</dt>
                                <dd className="mt-1 text-sm text-white sm:col-span-2 sm:mt-0">{user.email}</dd>
                            </div>
                            <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                                <dt className="text-sm font-medium text-white/70">User ID</dt>
                                <dd className="mt-1 text-sm font-mono text-white/50 sm:col-span-2 sm:mt-0">{user.uid}</dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </main>
        </div>
    );
}
