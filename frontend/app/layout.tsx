import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "INSURVAS Partner Pipeline",
  description: "Partner outreach and tracking tool",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <nav className="border-b bg-white px-6 py-3">
            <div className="flex items-center gap-6">
              <Link href="/" className="text-lg font-semibold">
                INSURVAS Pipeline
              </Link>
              <div className="flex gap-4 text-sm">
                <Link href="/partners" className="text-gray-600 hover:text-gray-900">
                  Partners
                </Link>
                <Link href="/board" className="text-gray-600 hover:text-gray-900">
                  Board
                </Link>
                <Link href="/attention" className="text-gray-600 hover:text-gray-900">
                  Attention
                </Link>
                <Link href="/discover" className="text-gray-600 hover:text-gray-900">
                  Discover
                </Link>
                <Link href="/config" className="text-gray-600 hover:text-gray-900">
                  Config
                </Link>
              </div>
            </div>
          </nav>
          <main className="px-6 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
