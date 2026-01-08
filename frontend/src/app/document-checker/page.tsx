"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Upload,
  FileText,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2,
  RefreshCw,
  FileWarning,
  ChevronRight,
  FileCheck,
  Presentation,
} from "lucide-react";
import { Header } from "../../components/layout/Header";
import { Button } from "../../components/ui/Button";
import { getUser, User, isAuthenticated } from "../../lib/apiClient";
import {
  getCheckTypes,
  getDocuments,
  uploadDocument,
  deleteDocument,
  CheckTypeInfo,
  DocumentCheckSummary,
  SEVERITY_CONFIG,
} from "../../lib/documentCheckerApi";
import { SlideGeneratorContent } from "../../components/slide-generator";

type TabType = "checker" | "generator";

export default function DocumentCheckerPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>("checker");
  const [user, setUser] = useState<User | null>(null);
  const [checkTypes, setCheckTypes] = useState<CheckTypeInfo[]>([]);
  const [selectedCheckTypes, setSelectedCheckTypes] = useState<string[]>([]);
  const [documents, setDocuments] = useState<DocumentCheckSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Check auth and get user
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }

    const storedUser = getUser();
    if (storedUser) {
      setUser(storedUser);
    } else {
      router.push("/login");
    }
  }, [router]);

  // Load check types and documents
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [types, docs] = await Promise.all([
        getCheckTypes(),
        getDocuments(50, 0),
      ]);
      setCheckTypes(types);
      setDocuments(docs.items);

      // Set default selected check types
      if (selectedCheckTypes.length === 0) {
        const defaults = types
          .filter((t) => t.default_enabled)
          .map((t) => t.id);
        setSelectedCheckTypes(defaults);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [selectedCheckTypes.length]);

  useEffect(() => {
    if (user && activeTab === "checker") {
      loadData();
    }
  }, [user, activeTab, loadData]);

  // Polling for processing documents
  useEffect(() => {
    if (activeTab !== "checker") return;

    const hasProcessing = documents.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!hasProcessing) return;

    const interval = setInterval(async () => {
      try {
        const docs = await getDocuments(50, 0);
        setDocuments(docs.items);
      } catch (err) {
        console.error("Polling failed:", err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [documents, activeTab]);

  const handleCheckTypeToggle = (checkTypeId: string) => {
    setSelectedCheckTypes((prev) =>
      prev.includes(checkTypeId)
        ? prev.filter((id) => id !== checkTypeId)
        : [...prev, checkTypeId]
    );
  };

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const validTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ];
    if (!validTypes.includes(file.type)) {
      setError("PDFまたはPowerPointファイルのみアップロード可能です");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      await uploadDocument(file, selectedCheckTypes);
      // Refresh documents list
      const docs = await getDocuments(50, 0);
      setDocuments(docs.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "アップロードに失敗しました");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
    // Reset input
    e.target.value = "";
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm("このドキュメントを削除しますか？")) return;
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "processing":
        return <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />;
      case "failed":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-surface-400" />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "completed":
        return "完了";
      case "processing":
        return "処理中";
      case "failed":
        return "失敗";
      default:
        return "待機中";
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-900 dark:to-surface-800">
      <Header user={user} title="SlideStudio" />

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Title */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">
            SlideStudio
          </h1>
          <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
            ドキュメントのチェックやスライド生成をAIがサポートします
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-8 p-1 bg-surface-200 dark:bg-surface-700 rounded-xl">
          <button
            onClick={() => setActiveTab("checker")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
              activeTab === "checker"
                ? "bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 shadow-sm"
                : "text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-surface-200"
            }`}
          >
            <FileCheck className="w-5 h-5" />
            ドキュメントチェック
          </button>
          <button
            onClick={() => setActiveTab("generator")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
              activeTab === "generator"
                ? "bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 shadow-sm"
                : "text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-surface-200"
            }`}
          >
            <Presentation className="w-5 h-5" />
            スライド生成
          </button>
        </div>

        {/* Error Message (for checker tab) */}
        {activeTab === "checker" && error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Document Checker Tab */}
        {activeTab === "checker" && (
          <>
            {/* Upload Area */}
            <div className="mb-8">
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                  dragActive
                    ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                    : "border-surface-300 dark:border-surface-600 hover:border-primary-400"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
              >
                {uploading ? (
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-12 h-12 text-primary-500 animate-spin" />
                    <p className="text-surface-600 dark:text-surface-300">
                      アップロード中...
                    </p>
                  </div>
                ) : (
                  <>
                    <Upload className="w-12 h-12 mx-auto text-surface-400 mb-4" />
                    <p className="text-surface-600 dark:text-surface-300 mb-2">
                      ファイルをドラッグ＆ドロップ、または
                    </p>
                    <label className="inline-block">
                      <input
                        type="file"
                        accept=".pdf,.pptx"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                      <span className="px-4 py-2 bg-primary-500 text-white rounded-lg cursor-pointer hover:bg-primary-600 transition-colors">
                        ファイルを選択
                      </span>
                    </label>
                    <p className="text-sm text-surface-400 mt-3">
                      対応形式: PDF, PowerPoint (.pptx)
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Check Types Selection */}
            <div className="mb-8 p-4 bg-white dark:bg-surface-800 rounded-xl shadow-soft">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-4">
                チェック項目
              </h2>
              <div className="flex flex-wrap gap-2">
                {checkTypes.map((checkType) => (
                  <button
                    key={checkType.id}
                    onClick={() => handleCheckTypeToggle(checkType.id)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      selectedCheckTypes.includes(checkType.id)
                        ? "bg-primary-500 text-white"
                        : "bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-300 hover:bg-surface-200 dark:hover:bg-surface-600"
                    }`}
                    title={checkType.description}
                  >
                    {checkType.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Documents List */}
            <div className="bg-white dark:bg-surface-800 rounded-xl shadow-soft">
              <div className="flex items-center justify-between p-4 border-b border-surface-200 dark:border-surface-700">
                <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                  チェック履歴
                </h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadData}
                  disabled={loading}
                  leftIcon={
                    loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )
                  }
                >
                  更新
                </Button>
              </div>

              {loading && documents.length === 0 ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-12">
                  <FileWarning className="w-12 h-12 mx-auto text-surface-300 mb-4" />
                  <p className="text-surface-500 dark:text-surface-400">
                    チェック履歴がありません
                  </p>
                  <p className="text-sm text-surface-400 mt-1">
                    ファイルをアップロードしてチェックを開始してください
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-surface-200 dark:divide-surface-700">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="p-4 hover:bg-surface-50 dark:hover:bg-surface-750 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div
                          className="flex items-center gap-3 flex-1 cursor-pointer"
                          onClick={() => {
                            if (doc.status === "completed") {
                              router.push(`/document-checker/${doc.id}`);
                            }
                          }}
                        >
                          <div className="w-10 h-10 rounded-lg bg-surface-100 dark:bg-surface-700 flex items-center justify-center">
                            <FileText className="w-5 h-5 text-surface-500" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-surface-900 dark:text-surface-100 truncate">
                              {doc.filename}
                            </p>
                            <div className="flex items-center gap-3 text-sm text-surface-500">
                              <span className="flex items-center gap-1">
                                {getStatusIcon(doc.status)}
                                {getStatusLabel(doc.status)}
                              </span>
                              {doc.status === "completed" && (
                                <>
                                  {doc.error_count > 0 && (
                                    <span className={SEVERITY_CONFIG.error.color}>
                                      {doc.error_count}件のエラー
                                    </span>
                                  )}
                                  {doc.warning_count > 0 && (
                                    <span className={SEVERITY_CONFIG.warning.color}>
                                      {doc.warning_count}件の警告
                                    </span>
                                  )}
                                  {doc.info_count > 0 && (
                                    <span className={SEVERITY_CONFIG.info.color}>
                                      {doc.info_count}件の情報
                                    </span>
                                  )}
                                  {doc.issue_count === 0 && (
                                    <span className="text-green-600 dark:text-green-400">
                                      問題なし
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-2 text-surface-400 hover:text-red-500 transition-colors"
                            title="削除"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                          {doc.status === "completed" && (
                            <button
                              onClick={() => router.push(`/document-checker/${doc.id}`)}
                              className="p-2 text-surface-400 hover:text-primary-500 transition-colors"
                              title="詳細を見る"
                            >
                              <ChevronRight className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* Slide Generator Tab */}
        {activeTab === "generator" && (
          <SlideGeneratorContent onError={(msg) => setError(msg)} />
        )}
      </main>
    </div>
  );
}
