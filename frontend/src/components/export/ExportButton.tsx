"use client";

import { useState, useRef, useEffect } from "react";
import { Download, Loader2, FileText, FileCode, ChevronDown } from "lucide-react";
import { Button } from "../ui/Button";
import {
  ExportFormat,
  exportChatSession,
  exportNotebook,
  exportEmail,
  exportMinute,
} from "../../lib/exportApi";

type ExportType = "chat" | "notebook" | "email" | "minute";

interface ExportButtonProps {
  type: ExportType;
  id: string;
  sessionId?: string; // For chat export
  className?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

interface FormatOption {
  format: ExportFormat;
  label: string;
  icon: React.ElementType;
  description: string;
}

const FORMAT_OPTIONS: Record<ExportType, FormatOption[]> = {
  chat: [
    {
      format: "md",
      label: "Markdown",
      icon: FileText,
      description: "見出し・引用付きのMarkdown形式",
    },
    {
      format: "txt",
      label: "テキスト",
      icon: FileText,
      description: "シンプルなテキスト形式",
    },
    {
      format: "json",
      label: "JSON",
      icon: FileCode,
      description: "構造化されたJSON形式",
    },
  ],
  notebook: [
    {
      format: "md",
      label: "Markdown",
      icon: FileText,
      description: "完全なMarkdown形式",
    },
    {
      format: "txt",
      label: "テキスト",
      icon: FileText,
      description: "プレーンテキスト形式",
    },
    {
      format: "json",
      label: "JSON",
      icon: FileCode,
      description: "構造化されたJSON形式",
    },
  ],
  email: [
    {
      format: "txt",
      label: "テキスト",
      icon: FileText,
      description: "そのままコピー可能な形式",
    },
    {
      format: "md",
      label: "Markdown",
      icon: FileText,
      description: "Markdown形式",
    },
  ],
  minute: [
    {
      format: "md",
      label: "Markdown",
      icon: FileText,
      description: "見出し・セクション付きMarkdown",
    },
    {
      format: "txt",
      label: "テキスト",
      icon: FileText,
      description: "プレーンテキスト形式",
    },
  ],
};

export function ExportButton({
  type,
  id,
  sessionId,
  className,
  variant = "ghost",
  size = "sm",
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleExport = async (format: ExportFormat) => {
    setLoading(true);
    setError(null);

    try {
      switch (type) {
        case "chat":
          if (!sessionId) throw new Error("Session ID is required");
          await exportChatSession(sessionId, format);
          break;
        case "notebook":
          await exportNotebook(id, "all", format);
          break;
        case "email":
          await exportEmail(id, format as "txt" | "md");
          break;
        case "minute":
          await exportMinute(id, format);
          break;
      }
      setIsOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エクスポートに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const options = FORMAT_OPTIONS[type];

  return (
    <div className={`relative ${className || ""}`} ref={dropdownRef}>
      <Button
        variant={variant}
        size={size}
        onClick={() => setIsOpen(!isOpen)}
        disabled={loading}
        leftIcon={
          loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )
        }
        rightIcon={<ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? "rotate-180" : ""}`} />}
      >
        エクスポート
      </Button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-surface-800 rounded-xl shadow-soft-lg border border-surface-200 dark:border-surface-700 py-2 z-50 animate-fade-in">
          {error && (
            <div className="px-3 py-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 mx-2 rounded-lg mb-2">
              {error}
            </div>
          )}

          {options.map((option) => (
            <button
              key={option.format}
              onClick={() => handleExport(option.format)}
              disabled={loading}
              className="w-full text-left px-4 py-2.5 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors disabled:opacity-50"
            >
              <div className="flex items-center gap-3">
                <option.icon className="w-4 h-4 text-surface-500" />
                <div>
                  <p className="text-sm font-medium text-surface-900 dark:text-surface-100">
                    {option.label}
                  </p>
                  <p className="text-xs text-surface-500 dark:text-surface-400">
                    {option.description}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
