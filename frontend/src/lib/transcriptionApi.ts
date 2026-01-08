/**
 * YouTube Transcription API client functions
 */

import { apiClient } from "./apiClient";

// =============================================================================
// Transcription Types
// =============================================================================

export interface Transcription {
  id: string;
  user_id: string;
  youtube_url: string;
  video_id: string;
  video_title: string | null;
  raw_transcript: string | null;
  formatted_transcript: string | null;
  processing_status: "pending" | "processing" | "completed" | "failed";
  processing_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface TranscriptionListItem {
  id: string;
  youtube_url: string;
  video_id: string;
  video_title: string | null;
  processing_status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
}

export interface TranscriptionListResponse {
  items: TranscriptionListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface TranscriptionCreate {
  youtube_url: string;
}

// =============================================================================
// Transcription API Functions
// =============================================================================

/**
 * Create a new transcription request.
 * The transcription will be processed in the background.
 */
export async function createTranscription(
  data: TranscriptionCreate
): Promise<Transcription> {
  const res = await apiClient("/api/v1/transcriptions/", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "文字起こしの作成に失敗しました");
  }
  return res.json();
}

/**
 * List transcriptions for the current user.
 */
export async function listTranscriptions(
  page: number = 1,
  perPage: number = 20,
  statusFilter?: string
): Promise<TranscriptionListResponse> {
  let url = `/api/v1/transcriptions/?page=${page}&per_page=${perPage}`;
  if (statusFilter) {
    url += `&status_filter=${statusFilter}`;
  }
  const res = await apiClient(url);
  if (!res.ok) {
    throw new Error("文字起こし一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific transcription by ID.
 */
export async function getTranscription(
  transcriptionId: string
): Promise<Transcription> {
  const res = await apiClient(`/api/v1/transcriptions/${transcriptionId}`);
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "文字起こしの取得に失敗しました");
  }
  return res.json();
}

/**
 * Delete a transcription.
 */
export async function deleteTranscription(
  transcriptionId: string
): Promise<void> {
  const res = await apiClient(`/api/v1/transcriptions/${transcriptionId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "文字起こしの削除に失敗しました");
  }
}

/**
 * Retry a failed transcription.
 */
export async function retryTranscription(
  transcriptionId: string
): Promise<Transcription> {
  const res = await apiClient(
    `/api/v1/transcriptions/${transcriptionId}/retry`,
    {
      method: "POST",
    }
  );
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "リトライに失敗しました");
  }
  return res.json();
}

// =============================================================================
// Configuration Status
// =============================================================================

export interface TranscriptionConfigStatus {
  configured: boolean;
  whisper_server_url: string | null;
}

/**
 * Check if the transcription service is configured.
 */
export async function getTranscriptionConfigStatus(): Promise<TranscriptionConfigStatus> {
  const res = await apiClient("/api/v1/transcriptions/status/config");
  if (!res.ok) {
    throw new Error("設定状態の取得に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get YouTube thumbnail URL from video ID.
 */
export function getYouTubeThumbnail(videoId: string): string {
  return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
}

/**
 * Get YouTube video URL from video ID.
 */
export function getYouTubeUrl(videoId: string): string {
  return `https://www.youtube.com/watch?v=${videoId}`;
}

/**
 * Validate YouTube URL format.
 */
export function isValidYouTubeUrl(url: string): boolean {
  const patterns = [
    /^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=[\w-]+/,
    /^https?:\/\/youtu\.be\/[\w-]+/,
    /^https?:\/\/(?:www\.)?youtube\.com\/shorts\/[\w-]+/,
    /^https?:\/\/(?:www\.)?youtube\.com\/live\/[\w-]+/,
  ];
  return patterns.some((pattern) => pattern.test(url));
}

/**
 * Get processing status display text.
 */
export function getStatusText(
  status: Transcription["processing_status"]
): string {
  switch (status) {
    case "pending":
      return "待機中";
    case "processing":
      return "処理中";
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    default:
      return status;
  }
}

/**
 * Get processing status color for UI.
 */
export function getStatusColor(
  status: Transcription["processing_status"]
): string {
  switch (status) {
    case "pending":
      return "text-yellow-600 bg-yellow-100";
    case "processing":
      return "text-blue-600 bg-blue-100";
    case "completed":
      return "text-green-600 bg-green-100";
    case "failed":
      return "text-red-600 bg-red-100";
    default:
      return "text-gray-600 bg-gray-100";
  }
}
