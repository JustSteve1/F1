import Link from "next/link";
import { Home, User, Settings, LogOut, Factory, Monitor } from "lucide-react";

export function Sidebar() {
    return (
        <div className="hidden h-screen w-16 flex-col items-center justify-between border-r border-white/10 bg-black py-4 md:flex">
            <div className="flex flex-col items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-white text-black font-black tracking-tighter text-xl">
                    F1
                </div>
                <nav className="flex flex-col gap-4 mt-4">
                    <Link
                        href="/"
                        className="flex h-10 w-10 items-center justify-center rounded-sm text-white/50 transition-colors hover:bg-white/10 hover:text-white"
                    >
                        <Home className="h-5 w-5" />
                        <span className="sr-only">Home</span>
                    </Link>
                    <Link
                        href="/profile"
                        className="flex h-10 w-10 items-center justify-center rounded-sm text-black bg-white transition-colors"
                    >
                        <User className="h-5 w-5" />
                        <span className="sr-only">Profile</span>
                    </Link>
                    <Link
                        href="/userfactory"
                        className="flex h-10 w-10 items-center justify-center rounded-sm text-white/50 transition-colors hover:bg-white/10 hover:text-white"
                    >
                        <Factory className="h-5 w-5" />
                        <span className="sr-only">Factory</span>
                    </Link>
                    <Link
                        href="/userpitwall"
                        className="flex h-10 w-10 items-center justify-center rounded-sm text-white/50 transition-colors hover:bg-white/10 hover:text-white"
                    >
                        <Monitor className="h-5 w-5" />
                        <span className="sr-only">Pitwall</span>
                    </Link>
                    <Link
                        href="/settings"
                        className="flex h-10 w-10 items-center justify-center rounded-sm text-white/50 transition-colors hover:bg-white/10 hover:text-white"
                    >
                        <Settings className="h-5 w-5" />
                        <span className="sr-only">Settings</span>
                    </Link>
                </nav>
            </div>
            <div className="flex flex-col items-center gap-4">
                {/* Bottom actions if needed */}
            </div>
        </div>
    );
}
