"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  X,
  BookOpen,
  FileText,
  ClipboardList,
  MessageSquare,
  Loader2,
  Clock,
} from "lucide-react";
import {
  globalSearch,
  getRecentItems,
  SearchResult,
  TYPE_LABELS,
} from "../../lib/searchApi";

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Type icon mapping
const TypeIcon: Record<string, React.ElementType> = {
  notebook: BookOpen,
  source: FileText,
  minute: ClipboardList,
  message: MessageSquare,
};

export function GlobalSearchModal({ isOpen, onClose }: GlobalSearchModalProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recentItems, setRecentItems] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchTime, setSearchTime] = useState<number | null>(null);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      // Load recent items
      loadRecentItems();
    } else {
      // Reset state when closing
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
      setSearchTime(null);
    }
  }, [isOpen]);

  // Load recent items
  const loadRecentItems = async () => {
    try {
      const items = await getRecentItems(8);
      setRecentItems(items);
    } catch (error) {
      console.error("Failed to load recent items:", error);
    }
  };

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSearchTime(null);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await globalSearch(query.trim());
        setResults(response.results);
        setSearchTime(response.search_time_ms);
        setSelectedIndex(0);
      } catch (error) {
        console.error("Search failed:", error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Navigate to result
  const navigateToResult = useCallback(
    (result: SearchResult) => {
      let path = "/";

      switch (result.type) {
        case "notebook":
          path = `/notebooks/${result.id}`;
          break;
        case "source":
          path = `/notebooks/${result.notebook_id}`;
          break;
        case "minute":
          path = `/notebooks/${result.notebook_id}`;
          break;
        case "message":
          path = `/notebooks/${result.notebook_id}`;
          break;
      }

      router.push(path);
      onClose();
    },
    [router, onClose]
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const displayedItems = query ? results : recentItems;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) =>
            Math.min(prev + 1, displayedItems.length - 1)
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (displayedItems[selectedIndex]) {
            navigateToResult(displayedItems[selectedIndex]);
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [query, results, recentItems, selectedIndex, navigateToResult, onClose]
  );

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selectedElement = listRef.current.querySelector(
        `[data-index="${selectedIndex}"]`
      );
      selectedElement?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  const displayedItems = query ? results : recentItems;
  const showingRecent = !query && recentItems.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-surface-900/60 dark:bg-surface-950/80 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 bg-white dark:bg-surface-800 rounded-2xl shadow-soft-xl animate-scale-in overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-surface-200 dark:border-surface-700">
          <Search className="w-5 h-5 text-surface-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="ノートブック、資料、議事録、チャットを検索..."
            className="flex-1 text-base bg-transparent border-none outline-none text-surface-900 dark:text-surface-100 placeholder-surface-400"
            autoComplete="off"
          />
          {loading && <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5 text-surface-400" />
          </button>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[400px] overflow-y-auto">
          {showingRecent && (
            <div className="px-4 py-2 text-xs font-medium text-surface-500 dark:text-surface-400 flex items-center gap-2">
              <Clock className="w-3.5 h-3.5" />
              最近のアイテム
            </div>
          )}

          {displayedItems.length > 0 ? (
            <ul className="py-2">
              {displayedItems.map((result, index) => {
                const Icon = TypeIcon[result.type] || FileText;
                const isSelected = index === selectedIndex;

                return (
                  <li
                    key={`${result.type}-${result.id}`}
                    data-index={index}
                    onClick={() => navigateToResult(result)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-primary-50 dark:bg-primary-900/30"
                        : "hover:bg-surface-50 dark:hover:bg-surface-700/50"
                    }`}
                  >
                    <div
                      className={`p-2 rounded-lg ${
                        isSelected
                          ? "bg-primary-100 dark:bg-primary-800/50"
                          : "bg-surface-100 dark:bg-surface-700"
                      }`}
                    >
                      <Icon
                        className={`w-4 h-4 ${
                          isSelected
                            ? "text-primary-600 dark:text-primary-400"
                            : "text-surface-500"
                        }`}
                      />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p
                          className={`text-sm font-medium truncate ${
                            isSelected
                              ? "text-primary-700 dark:text-primary-300"
                              : "text-surface-900 dark:text-surface-100"
                          }`}
                        >
                          {result.title}
                        </p>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-200 dark:bg-surface-600 text-surface-500 dark:text-surface-400">
                          {TYPE_LABELS[result.type]}
                        </span>
                      </div>

                      {result.snippet && (
                        <p className="text-xs text-surface-500 dark:text-surface-400 truncate mt-0.5">
                          {result.snippet}
                        </p>
                      )}

                      {result.notebook_title && (
                        <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5 flex items-center gap-1">
                          <BookOpen className="w-3 h-3" />
                          {result.notebook_title}
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : query && !loading ? (
            <div className="py-12 text-center">
              <Search className="w-10 h-10 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
              <p className="text-sm text-surface-500 dark:text-surface-400">
                「{query}」に一致する結果がありません
              </p>
              <p className="text-xs text-surface-400 dark:text-surface-500 mt-1">
                別のキーワードで検索してください
              </p>
            </div>
          ) : !query && !showingRecent ? (
            <div className="py-12 text-center">
              <Search className="w-10 h-10 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
              <p className="text-sm text-surface-500 dark:text-surface-400">
                検索キーワードを入力してください
              </p>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-surface-200 dark:border-surface-700 text-xs text-surface-400 dark:text-surface-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-surface-100 dark:bg-surface-700 rounded">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-surface-100 dark:bg-surface-700 rounded">↓</kbd>
              移動
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-surface-100 dark:bg-surface-700 rounded">Enter</kbd>
              開く
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-surface-100 dark:bg-surface-700 rounded">Esc</kbd>
              閉じる
            </span>
          </div>

          {searchTime !== null && (
            <span>{searchTime.toFixed(0)}ms</span>
          )}
        </div>
      </div>
    </div>
  );
}
