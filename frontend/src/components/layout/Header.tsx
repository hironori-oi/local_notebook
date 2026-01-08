"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sun, Moon, LogOut, BookOpen, Sparkles, Settings, Search, Users, Building2, Youtube, User as UserIcon, ChevronDown, FileText, Presentation } from "lucide-react";
import { useTheme } from "../providers/ThemeProvider";
import { Button } from "../ui/Button";
import { Avatar } from "../ui/Avatar";
import { ProcessingBadge } from "../processing";
import { GlobalSearchModal } from "../search";
import { useGlobalSearch } from "../../hooks/useGlobalSearch";
import { logout, isAdmin, User as UserType } from "../../lib/apiClient";

interface HeaderProps {
  user?: UserType | null;
  showBackButton?: boolean;
  backHref?: string;
  backLabel?: string;
  title?: React.ReactNode;
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
  const { isOpen: searchOpen, open: openSearch, close: closeSearch } = useGlobalSearch();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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
            {/* Search button */}
            <button
              onClick={openSearch}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-100 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 hover:bg-surface-200 dark:hover:bg-surface-700 transition-all"
              title="検索 (Ctrl+K)"
            >
              <Search className="w-4 h-4" />
              <span className="text-sm">検索</span>
              <kbd className="hidden md:inline px-1.5 py-0.5 text-[10px] bg-surface-200 dark:bg-surface-700 rounded">⌘K</kbd>
            </button>

            {/* Mobile search button */}
            <button
              onClick={openSearch}
              className="sm:hidden p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
              title="検索"
            >
              <Search className="w-5 h-5" />
            </button>

            {/* Processing badge */}
            <ProcessingBadge />

            {/* Councils link */}
            <Link
              href="/councils"
              className="p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
              title="審議会管理"
            >
              <Building2 className="w-5 h-5" />
            </Link>

            {/* Notebooks link */}
            <Link
              href="/notebooks"
              className="p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
              title="ノートブック"
            >
              <FileText className="w-5 h-5" />
            </Link>

            {/* SlideStudio link */}
            <Link
              href="/document-checker"
              className="p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
              title="SlideStudio"
            >
              <Presentation className="w-5 h-5" />
            </Link>

            {/* Transcription link */}
            <Link
              href="/transcription"
              className="p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
              title="YouTube文字起こし"
            >
              <Youtube className="w-5 h-5" />
            </Link>

            {/* Settings dropdown */}
            <div className="relative" ref={settingsRef}>
              <button
                onClick={() => setSettingsOpen(!settingsOpen)}
                className="p-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
                title="設定"
              >
                <Settings className="w-5 h-5" />
              </button>

              {/* Dropdown menu */}
              {settingsOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-surface-800 rounded-xl shadow-lg border border-surface-200 dark:border-surface-700 py-2 z-50">
                  {/* LLM Settings */}
                  <Link
                    href="/settings"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                    onClick={() => setSettingsOpen(false)}
                  >
                    <Settings className="w-4 h-4 text-surface-400" />
                    LLM設定
                  </Link>

                  {/* User profile */}
                  <Link
                    href="/settings/profile"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                    onClick={() => setSettingsOpen(false)}
                  >
                    <UserIcon className="w-4 h-4 text-surface-400" />
                    ユーザー情報
                  </Link>

                  {/* Admin link (admin only) */}
                  {user && isAdmin(user) && (
                    <Link
                      href="/admin/users"
                      className="flex items-center gap-3 px-4 py-2.5 text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                      onClick={() => setSettingsOpen(false)}
                    >
                      <Users className="w-4 h-4 text-surface-400" />
                      ユーザー管理
                    </Link>
                  )}

                  {/* Divider */}
                  <div className="border-t border-surface-200 dark:border-surface-700 my-2" />

                  {/* Theme toggle */}
                  <button
                    onClick={() => {
                      toggleTheme();
                      setSettingsOpen(false);
                    }}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors w-full text-left"
                  >
                    {resolvedTheme === "dark" ? (
                      <>
                        <Sun className="w-4 h-4 text-surface-400" />
                        ライトモードに切り替え
                      </>
                    ) : (
                      <>
                        <Moon className="w-4 h-4 text-surface-400" />
                        ダークモードに切り替え
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

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

      {/* Global Search Modal */}
      <GlobalSearchModal isOpen={searchOpen} onClose={closeSearch} />
    </header>
  );
}
