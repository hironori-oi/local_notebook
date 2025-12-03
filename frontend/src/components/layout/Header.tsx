"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sun, Moon, LogOut, User, BookOpen, Sparkles } from "lucide-react";
import { useTheme } from "../providers/ThemeProvider";
import { Button } from "../ui/Button";
import { Avatar } from "../ui/Avatar";
import { logout, User as UserType } from "../../lib/apiClient";

interface HeaderProps {
  user?: UserType | null;
  showBackButton?: boolean;
  backHref?: string;
  backLabel?: string;
  title?: string;
  subtitle?: string;
}

export function Header({
  user,
  showBackButton = false,
  backHref = "/",
  backLabel = "戻る",
  title,
  subtitle,
}: HeaderProps) {
  const router = useRouter();
  const { theme, setTheme, resolvedTheme } = useTheme();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  return (
    <header className="sticky top-0 z-40 w-full glass-strong border-b border-surface-200/50 dark:border-surface-700/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Left side */}
          <div className="flex items-center gap-4">
            {showBackButton ? (
              <Link
                href={backHref}
                className="flex items-center gap-2 text-sm text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200 transition-colors"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
                {backLabel}
              </Link>
            ) : (
              <Link href="/" className="flex items-center gap-3">
                <div className="relative">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-soft">
                    <BookOpen className="w-5 h-5 text-white" />
                  </div>
                  <Sparkles className="absolute -top-1 -right-1 w-4 h-4 text-amber-400" />
                </div>
                <div className="hidden sm:block">
                  <h1 className="text-lg font-bold text-surface-900 dark:text-surface-100">
                    AI ノートブック
                  </h1>
                  <p className="text-xs text-surface-500 dark:text-surface-400">
                    社内ナレッジベース
                  </p>
                </div>
              </Link>
            )}

            {title && (
              <div className="hidden sm:block pl-4 border-l border-surface-200 dark:border-surface-700">
                {subtitle && (
                  <p className="text-xs text-surface-500 dark:text-surface-400">
                    {subtitle}
                  </p>
                )}
                <h2 className="text-sm font-semibold text-surface-900 dark:text-surface-100">
                  {title}
                </h2>
              </div>
            )}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
              title={resolvedTheme === "dark" ? "ライトモードに切り替え" : "ダークモードに切り替え"}
            >
              {resolvedTheme === "dark" ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>

            {user && (
              <>
                {/* User info */}
                <div className="hidden sm:flex items-center gap-3 pl-2 ml-2 border-l border-surface-200 dark:border-surface-700">
                  <Avatar name={user.display_name} size="sm" />
                  <div className="hidden md:block">
                    <p className="text-sm font-medium text-surface-700 dark:text-surface-200">
                      {user.display_name}
                    </p>
                    <p className="text-xs text-surface-500 dark:text-surface-400">
                      @{user.username}
                    </p>
                  </div>
                </div>

                {/* Logout button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  leftIcon={<LogOut className="w-4 h-4" />}
                  className="text-surface-500"
                >
                  <span className="hidden sm:inline">ログアウト</span>
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
