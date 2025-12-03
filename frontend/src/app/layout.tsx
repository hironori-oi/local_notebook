import "./globals.css";
import type { ReactNode } from "react";
import { ThemeProvider } from "../components/providers/ThemeProvider";

export const metadata = {
  title: "AI Notebook - Internal Knowledge Base",
  description: "NotebookLM-like application for internal document analysis",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body className="min-h-screen bg-surface-50 dark:bg-surface-950 text-surface-900 dark:text-surface-100 transition-colors duration-300">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
