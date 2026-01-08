"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Trash2,
  Search,
  Clock,
  RefreshCw,
  Copy,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  Youtube,
  FileText,
} from "lucide-react";
import { isAuthenticated, getUser, logout, User } from "../../lib/apiClient";
import { Header } from "../../components/layout/Header";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Card } from "../../components/ui/Card";
import { LoadingScreen, Skeleton } from "../../components/ui/Spinner";
import { Modal } from "../../components/ui/Modal";
import {
  Transcription,
  TranscriptionListItem,
  listTranscriptions,
  createTranscription,
  deleteTranscription,
  getTranscription,
  retryTranscription,
  getTranscriptionConfigStatus,
  getYouTubeThumbnail,
  getYouTubeUrl,
  isValidYouTubeUrl,
  getStatusText,
  getStatusColor,
} from "../../lib/transcriptionApi";

export default function TranscriptionPage() {
  const router = useRouter();
  const [transcriptions, setTranscriptions] = useState<TranscriptionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Create modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  // Detail modal
  const [selectedTranscription, setSelectedTranscription] = useState<Transcription | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Delete modal
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Search
  const [searchQuery, setSearchQuery] = useState("");

  // Copy feedback
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Polling for processing items
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  // Configuration status
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null);

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load transcriptions
  const loadTranscriptions = useCallback(async () => {
    try {
      const data = await listTranscriptions(1, 100);
      setTranscriptions(data.items);

      // Track processing items
      const newProcessingIds = new Set<string>();
      data.items.forEach((item) => {
        if (item.processing_status === "pending" || item.processing_status === "processing") {
          newProcessingIds.add(item.id);
        }
      });
      setProcessingIds(newProcessingIds);
    } catch (e) {
      console.error(e);
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      }
    }
  }, [router]);

  useEffect(() => {
    if (!authChecked) return;

    (async () => {
      setLoading(true);
      try {
        // Check if Whisper server is configured
        const configStatus = await getTranscriptionConfigStatus();
        setIsConfigured(configStatus.configured);

        // Load transcriptions
        await loadTranscriptions();
      } catch (e) {
        console.error(e);
        setIsConfigured(false);
      } finally {
        setLoading(false);
      }
    })();
  }, [authChecked, loadTranscriptions]);

  // Polling for processing items
  useEffect(() => {
    if (processingIds.size === 0) return;

    const interval = setInterval(async () => {
      await loadTranscriptions();
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [processingIds.size, loadTranscriptions]);

  // Handle create
  const handleCreate = async () => {
    if (!youtubeUrl.trim()) return;

    if (!isValidYouTubeUrl(youtubeUrl)) {
      setCreateError("有効なYouTube URLを入力してください");
      return;
    }

    setCreating(true);
    setCreateError("");

    try {
      await createTranscription({ youtube_url: youtubeUrl });
      await loadTranscriptions();
      setYoutubeUrl("");
      setIsCreateModalOpen(false);
    } catch (e) {
      if (e instanceof Error) {
        setCreateError(e.message);
      } else {
        setCreateError("文字起こしの作成に失敗しました");
      }
    } finally {
      setCreating(false);
    }
  };

  // Handle view detail
  const handleViewDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const detail = await getTranscription(id);
      setSelectedTranscription(detail);
    } catch (e) {
      console.error(e);
    } finally {
      setDetailLoading(false);
    }
  };

  // Handle delete
  const handleDelete = async (id: string) => {
    try {
      await deleteTranscription(id);
      setTranscriptions((prev) => prev.filter((t) => t.id !== id));
      setDeleteId(null);
    } catch (e) {
      console.error(e);
      alert("削除に失敗しました");
    }
  };

  // Handle retry
  const handleRetry = async (id: string) => {
    try {
      await retryTranscription(id);
      await loadTranscriptions();
      if (selectedTranscription?.id === id) {
        const detail = await getTranscription(id);
        setSelectedTranscription(detail);
      }
    } catch (e) {
      console.error(e);
      alert("リトライに失敗しました");
    }
  };

  // Handle copy
  const handleCopy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  // Filter transcriptions
  const filteredTranscriptions = transcriptions.filter(
    (t) =>
      t.video_title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.youtube_url.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Status icon
  const getStatusIcon = (status: TranscriptionListItem["processing_status"]) => {
    switch (status) {
      case "pending":
        return <Clock className="w-4 h-4" />;
      case "processing":
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case "completed":
        return <CheckCircle2 className="w-4 h-4" />;
      case "failed":
        return <AlertCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
      <Header user={user} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Hero Section */}
        <div className="relative mb-8 overflow-hidden">
          <div className="relative z-10">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div>
                <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                  YouTube文字起こし
                </h1>
                <p className="text-surface-500 dark:text-surface-400">
                  YouTube動画の音声を文字起こしして、整形されたテキストを生成します
                </p>
              </div>
              <Button
                variant="primary"
                size="lg"
                leftIcon={<Plus className="w-5 h-5" />}
                onClick={() => setIsCreateModalOpen(true)}
                disabled={isConfigured === false}
              >
                新規文字起こし
              </Button>
            </div>
          </div>
        </div>

        {/* Not configured warning */}
        {isConfigured === false && (
          <Card variant="default" padding="lg" className="mb-6 border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-900/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-1">
                  文字起こしサーバーが設定されていません
                </h3>
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  Whisperサーバーが別PCで起動されていることを確認し、管理者に WHISPER_SERVER_URL の設定を依頼してください。
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Search */}
        {transcriptions.length > 0 && (
          <div className="mb-6">
            <Input
              placeholder="動画タイトルやURLで検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
              className="max-w-md"
            />
          </div>
        )}

        {/* Transcriptions List */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="default" padding="none">
                <Skeleton className="h-40 w-full rounded-t-2xl" />
                <div className="p-4">
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : filteredTranscriptions.length === 0 ? (
          <Card variant="default" padding="lg" className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-red-100 to-pink-100 dark:from-red-900/50 dark:to-pink-900/50 flex items-center justify-center">
              {searchQuery ? (
                <Search className="w-10 h-10 text-red-500" />
              ) : (
                <Youtube className="w-10 h-10 text-red-500" />
              )}
            </div>
            <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
              {searchQuery ? "文字起こしが見つかりません" : "文字起こしがありません"}
            </h3>
            <p className="text-surface-500 dark:text-surface-400 mb-6 max-w-md mx-auto">
              {searchQuery
                ? "別のキーワードで検索してください"
                : "YouTube動画のURLを入力して、文字起こしを開始しましょう"}
            </p>
            {!searchQuery && (
              <Button
                variant="primary"
                leftIcon={<Plus className="w-4 h-4" />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                文字起こしを開始
              </Button>
            )}
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTranscriptions.map((t, index) => (
              <Card
                key={t.id}
                variant="hover"
                padding="none"
                className="group animate-fade-in-up cursor-pointer"
                style={{ animationDelay: `${index * 50}ms` }}
                onClick={() => handleViewDetail(t.id)}
              >
                {/* Thumbnail */}
                <div className="relative aspect-video bg-surface-200 dark:bg-surface-700 rounded-t-2xl overflow-hidden">
                  <img
                    src={getYouTubeThumbnail(t.video_id)}
                    alt={t.video_title || "YouTube動画"}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "/placeholder-video.png";
                    }}
                  />
                  {/* Status badge */}
                  <div
                    className={`absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                      t.processing_status
                    )}`}
                  >
                    {getStatusIcon(t.processing_status)}
                    {getStatusText(t.processing_status)}
                  </div>
                </div>

                {/* Content */}
                <div className="p-4">
                  <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-1 line-clamp-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                    {t.video_title || "タイトル取得中..."}
                  </h3>
                  <div className="flex items-center gap-2 text-xs text-surface-400 dark:text-surface-500">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(t.created_at).toLocaleDateString("ja-JP")}
                  </div>
                </div>

                {/* Action buttons */}
                <div className="absolute bottom-16 right-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
                  <a
                    href={getYouTubeUrl(t.video_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-red-50 dark:hover:bg-red-900/30 text-surface-500 hover:text-red-500 shadow-md transition-all"
                    title="YouTubeで開く"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                  {t.processing_status === "failed" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRetry(t.id);
                      }}
                      className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-surface-500 hover:text-blue-500 shadow-md transition-all"
                      title="リトライ"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteId(t.id);
                    }}
                    className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-red-50 dark:hover:bg-red-900/30 text-surface-500 hover:text-red-500 shadow-md transition-all"
                    title="削除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setYoutubeUrl("");
          setCreateError("");
        }}
        title="YouTube動画の文字起こし"
        description="動画のURLを入力してください。音声を自動で文字起こしし、読みやすいテキストに整形します。"
      >
        <div className="space-y-4">
          <Input
            label="YouTube URL"
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => {
              setYoutubeUrl(e.target.value);
              setCreateError("");
            }}
            leftIcon={<Youtube className="w-4 h-4" />}
            error={createError}
          />

          <div className="text-xs text-surface-500 dark:text-surface-400">
            <p>対応URL形式:</p>
            <ul className="list-disc list-inside ml-2 mt-1">
              <li>https://www.youtube.com/watch?v=...</li>
              <li>https://youtu.be/...</li>
              <li>https://www.youtube.com/shorts/...</li>
              <li>https://www.youtube.com/live/...</li>
            </ul>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setIsCreateModalOpen(false);
                setYoutubeUrl("");
                setCreateError("");
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              isLoading={creating}
              disabled={!youtubeUrl.trim()}
              leftIcon={<FileText className="w-4 h-4" />}
            >
              文字起こし開始
            </Button>
          </div>
        </div>
      </Modal>

      {/* Detail Modal */}
      <Modal
        isOpen={!!selectedTranscription}
        onClose={() => setSelectedTranscription(null)}
        title={selectedTranscription?.video_title || "文字起こし結果"}
        size="lg"
      >
        {detailLoading ? (
          <div className="py-8 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-500" />
            <p className="mt-2 text-surface-500">読み込み中...</p>
          </div>
        ) : selectedTranscription ? (
          <div className="space-y-4">
            {/* Status */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-surface-500">ステータス:</span>
              <span
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                  selectedTranscription.processing_status
                )}`}
              >
                {getStatusIcon(selectedTranscription.processing_status)}
                {getStatusText(selectedTranscription.processing_status)}
              </span>
              {selectedTranscription.processing_status === "failed" && (
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<RefreshCw className="w-3 h-3" />}
                  onClick={() => handleRetry(selectedTranscription.id)}
                >
                  リトライ
                </Button>
              )}
            </div>

            {/* Error message */}
            {selectedTranscription.processing_error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-600 dark:text-red-400">
                {selectedTranscription.processing_error}
              </div>
            )}

            {/* Processing message */}
            {(selectedTranscription.processing_status === "pending" ||
              selectedTranscription.processing_status === "processing") && (
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500 mb-2" />
                <p className="text-blue-600 dark:text-blue-400">
                  {selectedTranscription.processing_status === "pending"
                    ? "処理待機中です..."
                    : "文字起こし処理中です..."}
                </p>
                <p className="text-xs text-blue-500 mt-1">
                  このページは自動で更新されます
                </p>
              </div>
            )}

            {/* Transcript */}
            {selectedTranscription.formatted_transcript && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                    整形済みテキスト
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={
                      copiedId === "formatted" ? (
                        <CheckCircle2 className="w-3 h-3 text-green-500" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )
                    }
                    onClick={() =>
                      handleCopy(selectedTranscription.formatted_transcript!, "formatted")
                    }
                  >
                    {copiedId === "formatted" ? "コピーしました" : "コピー"}
                  </Button>
                </div>
                <div className="p-4 bg-surface-100 dark:bg-surface-800 rounded-lg max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm text-surface-700 dark:text-surface-300 font-sans">
                    {selectedTranscription.formatted_transcript}
                  </pre>
                </div>
              </div>
            )}

            {/* Raw transcript (collapsible) */}
            {selectedTranscription.raw_transcript && (
              <details className="group">
                <summary className="cursor-pointer text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300">
                  生の文字起こしテキストを表示
                </summary>
                <div className="mt-2">
                  <div className="flex items-center justify-end mb-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      leftIcon={
                        copiedId === "raw" ? (
                          <CheckCircle2 className="w-3 h-3 text-green-500" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )
                      }
                      onClick={() =>
                        handleCopy(selectedTranscription.raw_transcript!, "raw")
                      }
                    >
                      {copiedId === "raw" ? "コピーしました" : "コピー"}
                    </Button>
                  </div>
                  <div className="p-4 bg-surface-100 dark:bg-surface-800 rounded-lg max-h-48 overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-xs text-surface-500 dark:text-surface-400 font-sans">
                      {selectedTranscription.raw_transcript}
                    </pre>
                  </div>
                </div>
              </details>
            )}

            {/* YouTube link */}
            <div className="pt-2 border-t border-surface-200 dark:border-surface-700">
              <a
                href={getYouTubeUrl(selectedTranscription.video_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              >
                <Youtube className="w-4 h-4" />
                YouTubeで動画を見る
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        ) : null}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="文字起こしを削除"
        description="この操作は取り消せません。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteId && handleDelete(deleteId)}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>
    </div>
  );
}
