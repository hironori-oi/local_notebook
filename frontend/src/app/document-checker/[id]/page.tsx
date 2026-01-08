"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  FileText,
  List,
  Columns,
  Check,
  X,
} from "lucide-react";
import { Header } from "../../../components/layout/Header";
import { Button } from "../../../components/ui/Button";
import { getUser, User, isAuthenticated } from "../../../lib/apiClient";
import {
  getDocumentDetail,
  updateIssueStatus,
  DocumentCheckDetail,
  DocumentCheckIssue,
  CATEGORY_LABELS,
  SEVERITY_CONFIG,
} from "../../../lib/documentCheckerApi";

type ViewMode = "list" | "diff";

export default function DocumentCheckResultPage() {
  const router = useRouter();
  const params = useParams();
  const documentId = params.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [document, setDocument] = useState<DocumentCheckDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [selectedIssue, setSelectedIssue] = useState<DocumentCheckIssue | null>(null);

  // Check auth
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

  // Load document
  const loadDocument = useCallback(async () => {
    if (!documentId) return;
    try {
      setLoading(true);
      const doc = await getDocumentDetail(documentId);
      setDocument(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ドキュメントの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    if (user && documentId) {
      loadDocument();
    }
  }, [user, documentId, loadDocument]);

  const handleIssueStatusUpdate = async (issueId: string, isAccepted: boolean) => {
    try {
      await updateIssueStatus(issueId, isAccepted);
      // Update local state
      setDocument((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          issues: prev.issues.map((issue) =>
            issue.id === issueId ? { ...issue, is_accepted: isAccepted } : issue
          ),
        };
      });
    } catch (err) {
      console.error("Failed to update issue status:", err);
    }
  };

  // Generate diff view content
  const generateDiffContent = () => {
    if (!document) return { original: "", corrected: "" };

    let originalText = document.original_text;
    let correctedText = document.original_text;

    // Apply accepted corrections
    document.issues
      .filter((issue) => issue.is_accepted === true && issue.suggested_text)
      .forEach((issue) => {
        correctedText = correctedText.replace(
          issue.original_text,
          issue.suggested_text!
        );
      });

    return { original: originalText, corrected: correctedText };
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-900 dark:to-surface-800">
        <Header user={user} title="SlideStudio" />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-900 dark:to-surface-800">
        <Header user={user} title="SlideStudio" />
        <main className="max-w-5xl mx-auto px-4 py-8">
          <div className="p-6 bg-red-50 dark:bg-red-900/20 rounded-xl text-center">
            <AlertCircle className="w-12 h-12 mx-auto text-red-500 mb-4" />
            <p className="text-red-700 dark:text-red-300">
              {error || "ドキュメントが見つかりません"}
            </p>
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => router.push("/document-checker")}
            >
              一覧に戻る
            </Button>
          </div>
        </main>
      </div>
    );
  }

  const { original, corrected } = generateDiffContent();

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-900 dark:to-surface-800">
      <Header user={user} title="ドキュメントチェッカー" />

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Back Button and Title */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => router.push("/document-checker")}
            className="p-2 hover:bg-surface-200 dark:hover:bg-surface-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-surface-600 dark:text-surface-300" />
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-surface-900 dark:text-surface-100">
              {document.filename}
            </h1>
            <p className="text-sm text-surface-500">
              {document.page_count}ページ / {document.issue_count}件の問題
            </p>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className={`p-4 rounded-xl ${SEVERITY_CONFIG.error.bgColor}`}>
            <div className="flex items-center gap-2">
              <AlertCircle className={`w-5 h-5 ${SEVERITY_CONFIG.error.color}`} />
              <span className={`font-semibold ${SEVERITY_CONFIG.error.color}`}>
                {document.error_count}件のエラー
              </span>
            </div>
          </div>
          <div className={`p-4 rounded-xl ${SEVERITY_CONFIG.warning.bgColor}`}>
            <div className="flex items-center gap-2">
              <AlertCircle className={`w-5 h-5 ${SEVERITY_CONFIG.warning.color}`} />
              <span className={`font-semibold ${SEVERITY_CONFIG.warning.color}`}>
                {document.warning_count}件の警告
              </span>
            </div>
          </div>
          <div className={`p-4 rounded-xl ${SEVERITY_CONFIG.info.bgColor}`}>
            <div className="flex items-center gap-2">
              <FileText className={`w-5 h-5 ${SEVERITY_CONFIG.info.color}`} />
              <span className={`font-semibold ${SEVERITY_CONFIG.info.color}`}>
                {document.info_count}件の情報
              </span>
            </div>
          </div>
        </div>

        {/* View Mode Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setViewMode("list")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === "list"
                ? "bg-primary-500 text-white"
                : "bg-white dark:bg-surface-800 text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700"
            }`}
          >
            <List className="w-4 h-4" />
            一覧表示
          </button>
          <button
            onClick={() => setViewMode("diff")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === "diff"
                ? "bg-primary-500 text-white"
                : "bg-white dark:bg-surface-800 text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700"
            }`}
          >
            <Columns className="w-4 h-4" />
            比較表示
          </button>
        </div>

        {/* Content */}
        {viewMode === "list" ? (
          /* List View */
          <div className="space-y-4">
            {document.issues.length === 0 ? (
              <div className="text-center py-12 bg-white dark:bg-surface-800 rounded-xl">
                <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-4" />
                <p className="text-lg font-medium text-surface-900 dark:text-surface-100">
                  問題は見つかりませんでした
                </p>
                <p className="text-surface-500 mt-2">
                  このドキュメントはチェック項目に該当する問題がありませんでした
                </p>
              </div>
            ) : (
              document.issues.map((issue) => (
                <div
                  key={issue.id}
                  className={`p-4 bg-white dark:bg-surface-800 rounded-xl shadow-soft border-l-4 ${
                    issue.severity === "error"
                      ? "border-l-red-500"
                      : issue.severity === "warning"
                      ? "border-l-yellow-500"
                      : "border-l-blue-500"
                  } ${
                    issue.is_accepted === true
                      ? "opacity-60"
                      : issue.is_accepted === false
                      ? "opacity-40"
                      : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      {/* Category and Severity */}
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            SEVERITY_CONFIG[issue.severity].bgColor
                          } ${SEVERITY_CONFIG[issue.severity].color}`}
                        >
                          {SEVERITY_CONFIG[issue.severity].label}
                        </span>
                        <span className="text-sm text-surface-500">
                          {CATEGORY_LABELS[issue.category] || issue.category}
                        </span>
                        {issue.page_or_slide && (
                          <span className="text-sm text-surface-400">
                            ページ {issue.page_or_slide}
                          </span>
                        )}
                      </div>

                      {/* Original Text */}
                      <div className="mb-3">
                        <p className="text-xs text-surface-500 mb-1">問題箇所:</p>
                        <p className="text-surface-900 dark:text-surface-100 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded border-l-2 border-red-400">
                          {issue.original_text}
                        </p>
                      </div>

                      {/* Suggested Text */}
                      {issue.suggested_text && (
                        <div className="mb-3">
                          <p className="text-xs text-surface-500 mb-1">修正案:</p>
                          <p className="text-surface-900 dark:text-surface-100 bg-green-50 dark:bg-green-900/20 px-3 py-2 rounded border-l-2 border-green-400">
                            {issue.suggested_text}
                          </p>
                        </div>
                      )}

                      {/* Explanation */}
                      {issue.explanation && (
                        <p className="text-sm text-surface-600 dark:text-surface-400">
                          {issue.explanation}
                        </p>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col gap-2">
                      {issue.is_accepted === null ? (
                        <>
                          <button
                            onClick={() => handleIssueStatusUpdate(issue.id, true)}
                            className="p-2 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                            title="修正を適用"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleIssueStatusUpdate(issue.id, false)}
                            className="p-2 bg-surface-100 dark:bg-surface-700 text-surface-500 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-colors"
                            title="修正を却下"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <div
                          className={`px-3 py-1 rounded text-xs font-medium ${
                            issue.is_accepted
                              ? "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400"
                              : "bg-surface-100 dark:bg-surface-700 text-surface-500"
                          }`}
                        >
                          {issue.is_accepted ? "適用済み" : "却下"}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Diff View */
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white dark:bg-surface-800 rounded-xl shadow-soft overflow-hidden">
              <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 border-b border-surface-200 dark:border-surface-700">
                <h3 className="font-semibold text-red-700 dark:text-red-300">
                  修正前
                </h3>
              </div>
              <div className="p-4 max-h-[600px] overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-surface-700 dark:text-surface-300 font-sans">
                  {original}
                </pre>
              </div>
            </div>
            <div className="bg-white dark:bg-surface-800 rounded-xl shadow-soft overflow-hidden">
              <div className="px-4 py-3 bg-green-50 dark:bg-green-900/20 border-b border-surface-200 dark:border-surface-700">
                <h3 className="font-semibold text-green-700 dark:text-green-300">
                  修正後（適用済みの修正のみ反映）
                </h3>
              </div>
              <div className="p-4 max-h-[600px] overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-surface-700 dark:text-surface-300 font-sans">
                  {corrected}
                </pre>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
