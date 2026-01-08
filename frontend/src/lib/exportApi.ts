/**
 * Export API client functions
 */

import { apiClient } from "./apiClient";

export type ExportFormat = "md" | "txt" | "json";

/**
 * Download a blob as a file
 */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Extract filename from Content-Disposition header
 */
function getFilenameFromHeader(
  headers: Headers,
  defaultFilename: string
): string {
  const contentDisposition = headers.get("Content-Disposition");
  if (!contentDisposition) return defaultFilename;

  // Try to match filename*=UTF-8''encoded format (RFC 5987)
  const rfc5987Match = contentDisposition.match(/filename\*=UTF-8''([^;\s]+)/);
  if (rfc5987Match) {
    try {
      return decodeURIComponent(rfc5987Match[1]);
    } catch {
      // Fall through to other methods
    }
  }

  // Try to match filename="..." format
  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/);
  if (quotedMatch) {
    return quotedMatch[1];
  }

  // Try to match filename=... format (unquoted)
  const unquotedMatch = contentDisposition.match(/filename=([^;\s]+)/);
  if (unquotedMatch) {
    return unquotedMatch[1];
  }

  return defaultFilename;
}

/**
 * Export a chat session
 */
export async function exportChatSession(
  sessionId: string,
  format: ExportFormat = "md"
): Promise<void> {
  const res = await apiClient(
    `/api/v1/export/chat/session/${sessionId}?format=${format}`
  );

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "チャットのエクスポートに失敗しました");
  }

  const blob = await res.blob();
  const filename = getFilenameFromHeader(
    res.headers,
    `chat_export.${format}`
  );
  downloadBlob(blob, filename);
}

/**
 * Export an entire notebook
 */
export async function exportNotebook(
  notebookId: string,
  include: string = "all",
  format: ExportFormat = "md"
): Promise<void> {
  const params = new URLSearchParams({ include, format });
  const res = await apiClient(
    `/api/v1/export/notebook/${notebookId}?${params}`
  );

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "ノートブックのエクスポートに失敗しました");
  }

  const blob = await res.blob();
  const filename = getFilenameFromHeader(
    res.headers,
    `notebook_export.${format}`
  );
  downloadBlob(blob, filename);
}

/**
 * Export a generated email
 */
export async function exportEmail(
  emailId: string,
  format: "md" | "txt" = "txt"
): Promise<void> {
  const res = await apiClient(
    `/api/v1/export/email/${emailId}?format=${format}`
  );

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "メールのエクスポートに失敗しました");
  }

  const blob = await res.blob();
  const filename = getFilenameFromHeader(
    res.headers,
    `email_export.${format}`
  );
  downloadBlob(blob, filename);
}

/**
 * Export a minute
 */
export async function exportMinute(
  minuteId: string,
  format: ExportFormat = "md"
): Promise<void> {
  const res = await apiClient(
    `/api/v1/export/minute/${minuteId}?format=${format}`
  );

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議事録のエクスポートに失敗しました");
  }

  const blob = await res.blob();
  const filename = getFilenameFromHeader(
    res.headers,
    `minute_export.${format}`
  );
  downloadBlob(blob, filename);
}
