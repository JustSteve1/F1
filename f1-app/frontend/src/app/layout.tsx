import type { Metadata } from 'next'
import { PT_Serif } from 'next/font/google'
import './globals.css'

const ptSerif = PT_Serif({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-pt-serif',
})

export const metadata: Metadata = {
  title: 'F1 Pitwall',
  description: 'AI-powered F1 analytics and data product',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${ptSerif.variable} font-serif bg-black text-white min-h-screen selection:bg-white selection:text-black`}>
        {children}
      </body>
    </html>
  )
}
