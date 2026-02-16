"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { DashboardGrid } from "@/components/profile/DashboardGrid";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Loader2 } from "lucide-react";

export default function ProfilePage() {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.push("/login");
        }
    }, [user, loading, router]);

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-black text-white">
                <Loader2 className="h-8 w-8 animate-spin text-white/20" />
            </div>
        );
    }

    if (!user) {
        return null;
    }

    return (
        <DashboardShell>
            <DashboardGrid />
        </DashboardShell>
    );
}
