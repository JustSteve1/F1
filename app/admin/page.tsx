"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { db } from "@/lib/firebase";
import { collection, getDocs, doc, setDoc, updateDoc, serverTimestamp, query, orderBy } from "firebase/firestore";

interface ReferralCode {
    id: string; // The code itself
    active: boolean;
    createdAt?: any;
}

export default function AdminPage() {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [codes, setCodes] = useState<ReferralCode[]>([]);
    const [newCode, setNewCode] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // simple protection: redirect if not logged in
    useEffect(() => {
        if (!loading && !user) {
            router.push("/login");
        }
    }, [user, loading, router]);

    const fetchCodes = async () => {
        setIsLoading(true);
        try {
            const q = query(collection(db, "referralCodes"), orderBy("createdAt", "desc"));
            const querySnapshot = await getDocs(q);
            const fetchedCodes: ReferralCode[] = [];
            querySnapshot.forEach((doc) => {
                fetchedCodes.push({
                    id: doc.id,
                    active: doc.data().active,
                    createdAt: doc.data().createdAt,
                });
            });
            setCodes(fetchedCodes);
        } catch (error) {
            console.error("Error fetching codes:", error);
            // If the index doesn't exist yet, standard fetch might fail or return empty on orderby. 
            // Fallback to simple fetch if needed, but 'desc' on automated fields usually needs index. 
            // Trying simple fetch if basic query fails or just accepting it might be empty.
            try {
                const simpleSnapshot = await getDocs(collection(db, "referralCodes"));
                const simpleCodes: ReferralCode[] = [];
                simpleSnapshot.forEach((doc) => {
                    simpleCodes.push({ id: doc.id, active: doc.data().active });
                });
                setCodes(simpleCodes);
            } catch (e) {
                console.error("Fallback fetch failed", e);
            }
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (user) {
            fetchCodes();
        }
    }, [user]);

    const handleAddCode = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newCode.trim()) return;
        setIsSubmitting(true);

        try {
            const codeId = newCode.trim();
            await setDoc(doc(db, "referralCodes", codeId), {
                active: true,
                createdAt: serverTimestamp(),
            });
            setNewCode("");
            await fetchCodes(); // Refresh list
        } catch (error) {
            console.error("Error adding code:", error);
            alert("Failed to add code. Check console.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const toggleStatus = async (code: ReferralCode) => {
        try {
            const ref = doc(db, "referralCodes", code.id);
            await updateDoc(ref, {
                active: !code.active,
            });
            // Optimistic update or refresh
            setCodes(codes.map(c => c.id === code.id ? { ...c, active: !c.active } : c));
        } catch (error) {
            console.error("Error updating status:", error);
            alert("Failed to update status.");
        }
    };

    if (loading || !user) return <div className="min-h-screen bg-black text-white flex items-center justify-center">Loading...</div>;

    return (
        <div className="min-h-screen bg-black text-white font-sans p-8 md:p-12">
            <div className="max-w-4xl mx-auto space-y-12">

                <header className="border-b border-white/10 pb-8">
                    <h1 className="text-3xl font-bold tracking-tighter mb-2">Admin: Referral Codes</h1>
                    <p className="text-white/50">Manage access codes for user registration.</p>
                    <a
                        href="/admin/jobs"
                        className="inline-block mt-3 text-xs font-bold uppercase tracking-widest text-[#2596be] hover:underline"
                    >
                        → Telemetry import jobs
                    </a>
                </header>

                <section className="bg-white/5 p-6 rounded-lg border border-white/10">
                    <h2 className="text-xl font-bold mb-4">Add New Code</h2>
                    <form onSubmit={handleAddCode} className="flex gap-4">
                        <input
                            type="text"
                            value={newCode}
                            onChange={(e) => setNewCode(e.target.value)}
                            placeholder="e.g. VIP2026"
                            className="flex-1 bg-black/50 border border-white/20 rounded px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                        />
                        <button
                            type="submit"
                            disabled={isSubmitting || !newCode.trim()}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 px-6 rounded disabled:opacity-50 transition-colors"
                        >
                            {isSubmitting ? "Adding..." : "Add Code"}
                        </button>
                    </form>
                </section>

                <section>
                    <h2 className="text-xl font-bold mb-6">Existing Codes</h2>

                    {isLoading ? (
                        <p className="text-white/30">Loading codes...</p>
                    ) : codes.length === 0 ? (
                        <p className="text-white/30 italic">No referral codes found. Create one above.</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-white/10 text-white/40 text-sm uppercase tracking-wider">
                                        <th className="py-4 px-4">Code</th>
                                        <th className="py-4 px-4">Status</th>
                                        <th className="py-4 px-4 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {codes.map((code) => (
                                        <tr key={code.id} className="hover:bg-white/5 transition-colors">
                                            <td className="py-4 px-4 font-mono text-lg">{code.id}</td>
                                            <td className="py-4 px-4">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${code.active ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                                                    {code.active ? 'Active' : 'Inactive'}
                                                </span>
                                            </td>
                                            <td className="py-4 px-4 text-right">
                                                <button
                                                    onClick={() => toggleStatus(code)}
                                                    className="text-sm text-white/60 hover:text-white transition-colors underline decoration-white/30 hover:decoration-white"
                                                >
                                                    {code.active ? 'Deactivate' : 'Activate'}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

            </div>
        </div>
    );
}
