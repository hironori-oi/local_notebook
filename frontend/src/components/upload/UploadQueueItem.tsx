"use client";

import { Clock, Loader2, CheckCircle, XCircle, X, FileText } from "lucide-react";
import { UploadItem } from "../../hooks/useMultiFileUpload";

interface UploadQueueItemProps {
  item: UploadItem;
  onRemove: () => void;
}

const fileTypeIcons: Record<string, string> = {
  pdf: "PDF",
  docx: "DOCX",
  txt: "TXT",
  md: "MD",
};

function getFileExtension(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  return ext;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export function UploadQueueItem({ item, onRemove }: UploadQueueItemProps) {
  const ext = getFileExtension(item.file.name);
  const typeLabel = fileTypeIcons[ext] || ext.toUpperCase();

  // Determine display config based on upload status and processing status
  const getDisplayConfig = () => {
    // Not yet uploaded or uploading
    if (item.status === "pending") {
      return {
        icon: <Clock className="w-4 h-4 text-surface-400" />,
        bgColor: "bg-surface-50 dark:bg-surface-800",
      };
    }
    if (item.status === "uploading") {
      return {
        icon: <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />,
        bgColor: "bg-primary-50 dark:bg-primary-900/20",
      };
    }
    if (item.status === "failed") {
      return {
        icon: <XCircle className="w-4 h-4 text-red-500" />,
        bgColor: "bg-red-50 dark:bg-red-900/20",
      };
    }
    // Upload completed - check backend processing status
    if (item.status === "completed" && item.source) {
      const processingStatus = item.source.processing_status;
      if (processingStatus === "completed") {
        return {
          icon: <CheckCircle className="w-4 h-4 text-green-500" />,
          bgColor: "bg-green-50 dark:bg-green-900/20",
        };
      }
      if (processingStatus === "failed") {
        return {
          icon: <XCircle className="w-4 h-4 text-red-500" />,
          bgColor: "bg-red-50 dark:bg-red-900/20",
        };
      }
      // pending or processing
      return {
        icon: <Loader2 className="w-4 h-4 text-amber-500 animate-spin" />,
        bgColor: "bg-amber-50 dark:bg-amber-900/20",
      };
    }
    // Fallback
    return {
      icon: <CheckCircle className="w-4 h-4 text-green-500" />,
      bgColor: "bg-green-50 dark:bg-green-900/20",
    };
  };

  const config = getDisplayConfig();

  return (
    <li
      className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${config.bgColor}`}
    >
      {/* Status Icon */}
      <div className="flex-shrink-0">{config.icon}</div>

      {/* File Type Badge */}
      <div className="flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded bg-surface-200 dark:bg-surface-700 text-surface-600 dark:text-surface-300">
        {typeLabel}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-surface-900 dark:text-surface-100 truncate">
          {item.file.name}
        </p>
        <div className="flex items-center gap-2 text-xs text-surface-500 dark:text-surface-400">
          <span>{formatFileSize(item.file.size)}</span>
          {item.status === "completed" && item.source && (
            <span className={
              item.source.processing_status === "completed"
                ? "text-green-600 dark:text-green-400"
                : item.source.processing_status === "failed"
                ? "text-red-500"
                : "text-amber-600 dark:text-amber-400"
            }>
              {item.source.processing_status === "completed"
                ? "処理完了"
                : item.source.processing_status === "failed"
                ? "処理失敗"
                : item.source.processing_status === "processing"
                ? "処理中..."
                : "処理待ち"}
            </span>
          )}
          {item.error && (
            <span className="text-red-500 truncate" title={item.error}>
              {item.error}
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar (only during upload) */}
      {item.status === "uploading" && (
        <div className="w-20 flex-shrink-0">
          <div className="h-1.5 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 transition-all duration-300 ease-out"
              style={{ width: `${item.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Remove Button (only when pending) */}
      {item.status === "pending" && (
        <button
          onClick={onRemove}
          className="flex-shrink-0 p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 transition-colors"
          title="削除"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </li>
  );
}
