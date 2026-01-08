"use client";

import { useState, useCallback, useRef } from "react";
import { apiClientMultipart, SourceInfo } from "../lib/apiClient";

export interface UploadItem {
  id: string;
  file: File;
  status: "pending" | "uploading" | "completed" | "failed";
  progress: number;
  error?: string;
  source?: SourceInfo;
}

export interface UploadStats {
  total: number;
  pending: number;
  uploading: number;
  completed: number;
  failed: number;
}

interface UseMultiFileUploadOptions {
  notebookId: string;
  maxConcurrent?: number;
  onComplete?: (source: SourceInfo) => void;
  onAllComplete?: () => void;
  onError?: (file: File, error: string) => void;
}

export function useMultiFileUpload(options: UseMultiFileUploadOptions) {
  const { notebookId, maxConcurrent = 2, onComplete, onAllComplete, onError } = options;
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const addFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files);

    // Filter for valid file types
    const validExtensions = [".pdf", ".docx", ".txt", ".md"];
    const validFiles = fileArray.filter((file) => {
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
      return validExtensions.includes(ext);
    });

    if (validFiles.length === 0) return;

    const newItems: UploadItem[] = validFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: "pending" as const,
      progress: 0,
    }));

    setQueue((prev) => [...prev, ...newItems]);
  }, []);

  const removeFile = useCallback((id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const updateItemStatus = useCallback(
    (id: string, updates: Partial<UploadItem>) => {
      setQueue((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
      );
    },
    []
  );

  const uploadFile = useCallback(
    async (item: UploadItem) => {
      updateItemStatus(item.id, { status: "uploading", progress: 10 });

      try {
        const formData = new FormData();
        formData.append("notebook_id", notebookId);
        formData.append("file", item.file);

        const res = await apiClientMultipart("/api/v1/sources/upload", formData);

        if (res.status === 401) {
          throw new Error("認証エラー: 再ログインしてください");
        }

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || `アップロード失敗: ${res.status}`);
        }

        const source = await res.json();

        updateItemStatus(item.id, {
          status: "completed",
          progress: 100,
          source,
        });

        onComplete?.(source);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "アップロードに失敗しました";
        updateItemStatus(item.id, {
          status: "failed",
          error: errorMessage,
        });
        onError?.(item.file, errorMessage);
      }
    },
    [notebookId, updateItemStatus, onComplete, onError]
  );

  const startUpload = useCallback(async () => {
    const pending = queue.filter((item) => item.status === "pending");
    if (pending.length === 0) return;

    setIsUploading(true);
    abortControllerRef.current = new AbortController();

    try {
      // Process in batches of maxConcurrent
      for (let i = 0; i < pending.length; i += maxConcurrent) {
        if (abortControllerRef.current?.signal.aborted) break;

        const batch = pending.slice(i, i + maxConcurrent);
        await Promise.all(batch.map((item) => uploadFile(item)));
      }

      onAllComplete?.();
    } finally {
      setIsUploading(false);
      abortControllerRef.current = null;
    }
  }, [queue, maxConcurrent, uploadFile, onAllComplete]);

  const cancelUpload = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsUploading(false);
  }, []);

  const retryFailed = useCallback(() => {
    setQueue((prev) =>
      prev.map((item) =>
        item.status === "failed"
          ? { ...item, status: "pending" as const, error: undefined, progress: 0 }
          : item
      )
    );
  }, []);

  const clearCompleted = useCallback(() => {
    setQueue((prev) => prev.filter((item) => item.status !== "completed"));
  }, []);

  const clearAll = useCallback(() => {
    if (!isUploading) {
      setQueue([]);
    }
  }, [isUploading]);

  const stats: UploadStats = {
    total: queue.length,
    pending: queue.filter((q) => q.status === "pending").length,
    uploading: queue.filter((q) => q.status === "uploading").length,
    completed: queue.filter((q) => q.status === "completed").length,
    failed: queue.filter((q) => q.status === "failed").length,
  };

  return {
    queue,
    isUploading,
    stats,
    addFiles,
    removeFile,
    startUpload,
    cancelUpload,
    retryFailed,
    clearCompleted,
    clearAll,
  };
}
