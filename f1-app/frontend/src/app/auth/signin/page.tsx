import Link from "next/link"

export default function SignInPage() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center p-8">
            <div className="w-full max-w-md border border-white/20 p-8 bg-black">
                <h1 className="text-3xl font-bold mb-8 text-center">Sign In</h1>

                <form className="space-y-4">
                    <div>
                        <label className="block text-sm mb-1">Email</label>
                        <input type="email" className="w-full bg-black border border-white/50 p-2 focus:border-white outline-none" placeholder="analyst@example.com" />
                    </div>
                    <div>
                        <label className="block text-sm mb-1">Password</label>
                        <input type="password" className="w-full bg-black border border-white/50 p-2 focus:border-white outline-none" placeholder="••••••••" />
                    </div>
                    <button className="w-full bg-white text-black font-bold py-2 mt-4 hover:bg-gray-200">
                        Sign In with Email
                    </button>
                </form>

                <div className="my-8 flex items-center text-gray-500 text-sm">
                    <span className="flex-1 border-t border-gray-800"></span>
                    <span className="px-4">OR</span>
                    <span className="flex-1 border-t border-gray-800"></span>
                </div>

                <button className="w-full border border-white text-white font-bold py-2 hover:bg-white/10">
                    Continue with Google
                </button>
            </div>
        </div>
    )
}
