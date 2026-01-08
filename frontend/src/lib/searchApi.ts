/**
 * Search API client functions
 */

import { apiClient } from "./apiClient";

export type SearchResultType = "notebook" | "source" | "minute" | "message";

export interface SearchResult {
  type: SearchResultType;
  id: string;
  title: string;
  snippet: string;
  notebook_id: string | null;
  notebook_title: string | null;
  relevance_score: number;
  created_at: string | null;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  search_time_ms: number;
}

/**
 * Perform global search across all content types
 */
export async function globalSearch(
  query: string,
  types: string = "all",
  limit: number = 20,
  offset: number = 0
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    types,
    limit: String(limit),
    offset: String(offset),
  });

  const res = await apiClient(`/api/v1/search/global?${params}`);

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "検索に失敗しました");
  }

  return res.json();
}

/**
 * Get recently accessed items (shown when search modal opens)
 */
export async function getRecentItems(limit: number = 10): Promise<SearchResult[]> {
  const res = await apiClient(`/api/v1/search/recent?limit=${limit}`);

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "最近のアイテムの取得に失敗しました");
  }

  return res.json();
}

// Type labels for display
export const TYPE_LABELS: Record<SearchResultType, string> = {
  notebook: "ノートブック",
  source: "資料",
  minute: "議事録",
  message: "チャット",
};

// Type icons (icon names for lucide-react)
export const TYPE_ICONS: Record<SearchResultType, string> = {
  notebook: "BookOpen",
  source: "FileText",
  minute: "ClipboardList",
  message: "MessageSquare",
};
