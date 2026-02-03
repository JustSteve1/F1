import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"
import { PrismaAdapter } from "@auth/prisma-adapter"
import { prisma } from "@/lib/prisma"

export const { handlers, auth, signIn, signOut } = NextAuth({
    adapter: PrismaAdapter(prisma),
    providers: [
        Google({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        }),
        Credentials({
            credentials: {
                email: { label: "Email", type: "email" },
                password: { label: "Password", type: "password" },
            },
            authorize: async (credentials) => {
                // Mock logic strictly for initial setup/dev if no database is connected yet
                // In production, this would verify against the DB using bcrypt
                if (credentials?.email === "test@example.com" && credentials?.password === "password") {
                    return { id: "1", name: "Test User", email: "test@example.com" }
                }
                return null
            },
        }),
    ],
    pages: {
        signIn: "/auth/signin",
        // error: '/auth/error', 
    },
    callbacks: {
        session({ session, user }) {
            if (session.user) {
                session.user.id = user.id
            }
            return session
        }
    }
})
