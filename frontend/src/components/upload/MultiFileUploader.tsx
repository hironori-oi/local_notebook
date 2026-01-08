"use client";

import { useState, useRef, DragEvent } from "react";
import { Upload, RefreshCw, Trash2 } from "lucide-react";
import { useMultiFileUpload } from "../../hooks/useMultiFileUpload";
import { UploadQueueItem } from "./UploadQueueItem";
import { Button } from "../ui/Button";
import { SourceInfo } from "../../lib/apiClient";

interface MultiFileUploaderProps {
  notebookId: string;
  onSourceAdded: (source: SourceInfo) => void;
  onAllComplete?: () => void;
  className?: string;
}

export function MultiFileUploader({
  notebookId,
  onSourceAdded,
  onAllComplete,
  className = "",
}: MultiFileUploaderProps) {
  const {
    queue,
    isUploading,
    stats,
    addFiles,
    removeFile,
    startUpload,
    retryFailed,
    clearCompleted,
    clearAll,
  } = useMultiFileUpload({
    notebookId,
    onComplete: onSourceAdded,
    onAllComplete,
  });

  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set to false if we're leaving the drop zone entirely
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      addFiles(files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
    }
    // Reset input so the same file(s) can be selected again
    e.target.value = "";
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200
          ${
            isDragging
              ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20 scale-[1.02]"
              : "border-surface-300 dark:border-surface-600 hover:border-primary-400 hover:bg-surface-50 dark:hover:bg-surface-800/50"
          }
        `}
      >
        <Upload
          className={`w-8 h-8 mx-auto mb-2 transition-colors ${
            isDragging ? "text-primary-500" : "text-surface-400"
          }`}
        />
        <p className="text-sm font-medium text-surface-700 dark:text-surface-200">
          {isDragging
            ? "ここにドロップ"
            : "ファイルをドロップまたはクリックして選択"}
        </p>
        <p className="text-xs text-surface-500 dark:text-surface-400 mt-1">
          PDF, DOCX, TXT, MD（最大50MB/ファイル）
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          onChange={handleFileInputChange}
          className="hidden"
        />
      </div>

      {/* Upload Queue */}
      {queue.length > 0 && (
        <div className="space-y-3">
          {/* Stats Header */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-surface-600 dark:text-surface-300">
              <span className="font-medium">{stats.completed}</span>
              <span className="text-surface-400 dark:text-surface-500">
                /{stats.total}
              </span>
              <span className="ml-1">完了</span>
              {stats.failed > 0 && (
                <span className="ml-2 text-red-500">
                  ({stats.failed}件失敗)
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {stats.failed > 0 && !isUploading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={retryFailed}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                  className="text-xs"
                >
                  再試行
                </Button>
              )}
              {stats.completed > 0 && !isUploading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearCompleted}
                  className="text-xs"
                >
                  完了を削除
                </Button>
              )}
              {queue.length > 0 && !isUploading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                  className="text-xs text-surface-400 hover:text-red-500"
                >
                  すべて削除
                </Button>
              )}
            </div>
          </div>

          {/* Queue List */}
          <ul className="space-y-2 max-h-[300px] overflow-y-auto">
            {queue.map((item) => (
              <UploadQueueItem
                key={item.id}
                item={item}
                onRemove={() => removeFile(item.id)}
              />
            ))}
          </ul>

          {/* Upload Button */}
          {stats.pending > 0 && !isUploading && (
            <Button
              onClick={startUpload}
              className="w-full"
              leftIcon={<Upload className="w-4 h-4" />}
            >
              {stats.pending}件をアップロード
            </Button>
          )}

          {/* Uploading Status */}
          {isUploading && (
            <div className="text-center text-sm text-surface-500 dark:text-surface-400">
              アップロード中...（{stats.uploading}件処理中）
            </div>
          )}
        </div>
      )}
    </div>
  );
}
