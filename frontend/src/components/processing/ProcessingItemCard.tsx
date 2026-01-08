"use client";

import Link from "next/link";
import { Clock, Loader2, CheckCircle, XCircle, FileText, ClipboardList, RotateCcw } from "lucide-react";
import { ProcessingItem, TYPE_LABELS } from "../../lib/processingApi";
import { Button } from "../ui/Button";

interface ProcessingItemCardProps {
  item: ProcessingItem;
  onRetry: () => void;
  isRetrying?: boolean;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("ja-JP", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ProcessingItemCard({ item, onRetry, isRetrying }: ProcessingItemCardProps) {
  const statusConfig = {
    pending: {
      icon: <Clock className="w-5 h-5 text-surface-400" />,
      bgColor: "bg-surface-50 dark:bg-surface-800",
      label: "待機中",
      labelColor: "text-surface-500",
    },
    processing: {
      icon: <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />,
      bgColor: "bg-primary-50 dark:bg-primary-900/20",
      label: "処理中",
      labelColor: "text-primary-600 dark:text-primary-400",
    },
    completed: {
      icon: <CheckCircle className="w-5 h-5 text-green-500" />,
      bgColor: "bg-green-50 dark:bg-green-900/20",
      label: "完了",
      labelColor: "text-green-600 dark:text-green-400",
    },
    failed: {
      icon: <XCircle className="w-5 h-5 text-red-500" />,
      bgColor: "bg-red-50 dark:bg-red-900/20",
      label: "失敗",
      labelColor: "text-red-600 dark:text-red-400",
    },
  };

  const config = statusConfig[item.status];
  const TypeIcon = item.type === "source" ? FileText : ClipboardList;

  return (
    <div className={`p-4 rounded-xl ${config.bgColor} transition-colors`}>
      <div className="flex items-start gap-4">
        {/* Status Icon */}
        <div className="flex-shrink-0 mt-0.5">{config.icon}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {/* Type Badge */}
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-surface-200 dark:bg-surface-700 text-surface-600 dark:text-surface-300">
              <TypeIcon className="w-3 h-3" />
              {TYPE_LABELS[item.type]}
            </span>
            {/* Status Label */}
            <span className={`text-xs font-medium ${config.labelColor}`}>
              {config.label}
            </span>
          </div>

          {/* Title */}
          <h3 className="font-medium text-surface-900 dark:text-surface-100 truncate">
            {item.title}
          </h3>

          {/* Notebook Link */}
          <Link
            href={`/notebooks/${item.notebook_id}`}
            className="text-sm text-surface-500 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 truncate block"
          >
            {item.notebook_title}
          </Link>

          {/* Error Message */}
          {item.error && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 rounded-lg px-3 py-2">
              {item.error}
            </p>
          )}

          {/* Created At */}
          <p className="mt-1 text-xs text-surface-400 dark:text-surface-500">
            {formatDate(item.created_at)}
          </p>
        </div>

        {/* Actions */}
        <div className="flex-shrink-0">
          {(item.status === "failed" || item.status === "pending") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRetry}
              disabled={isRetrying}
              leftIcon={
                isRetrying ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RotateCcw className="w-4 h-4" />
                )
              }
              className="text-xs"
            >
              再試行
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
