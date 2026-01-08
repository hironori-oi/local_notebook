/**
 * Processing Status API client functions
 */

import { apiClient } from "./apiClient";

export interface ProcessingItem {
  id: string;
  type: "source" | "minute";
  title: string;
  notebook_id: string;
  notebook_title: string;
  status: "pending" | "processing" | "completed" | "failed";
  error: string | null;
  created_at: string;
}

export interface ProcessingStats {
  pending: number;
  processing: number;
  completed_today: number;
  failed_today: number;
}

export interface ProcessingDashboard {
  stats: ProcessingStats;
  items: ProcessingItem[];
}

/**
 * Get processing statistics (lightweight for badge)
 */
export async function getProcessingStats(): Promise<ProcessingStats> {
  const res = await apiClient("/api/v1/processing/stats");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch processing stats");
  }
  return res.json();
}

/**
 * Get processing dashboard with items and stats
 */
export async function getProcessingDashboard(
  status: string = "all",
  limit: number = 50
): Promise<ProcessingDashboard> {
  const params = new URLSearchParams({
    status,
    limit: String(limit),
  });
  const res = await apiClient(`/api/v1/processing/dashboard?${params}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch processing dashboard");
  }
  return res.json();
}

/**
 * Retry failed processing for a source or minute
 */
export async function retryProcessing(
  type: "source" | "minute",
  id: string
): Promise<{ message: string; id: string; type: string }> {
  const res = await apiClient(`/api/v1/processing/retry/${type}/${id}`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to retry processing");
  }
  return res.json();
}

// Status labels for UI
export const STATUS_LABELS: Record<string, string> = {
  all: "すべて",
  pending: "待機中",
  processing: "処理中",
  completed: "完了",
  failed: "失敗",
};

// Type labels for UI
export const TYPE_LABELS: Record<string, string> = {
  source: "資料",
  minute: "議事録",
};
