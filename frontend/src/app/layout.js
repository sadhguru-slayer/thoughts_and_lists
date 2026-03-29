import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "@/lib/AuthContext";
import { JournalProvider } from "@/lib/JournalContext";
import { ThoughtsProvider } from "@/lib/ThoughtsContext";
import { ThemeProvider } from "@/components/theme-provider";
import Header from "@/components/journal/Header";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "Thoughts & Journal",
  description: "Thoughts and lists — journal entries",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-screen flex-col bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider>
            <ThoughtsProvider>
              <JournalProvider>
                <Header />
                <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-6 sm:px-6">
                  {children}
                </main>
              </JournalProvider>
            </ThoughtsProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
