"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Mail,
  Sparkles,
  FileText,
  Trash2,
  Clock,
  CheckSquare,
  Square,
  Copy,
  Check,
  Save,
  FileCheck,
  ClipboardList,
  Edit2,
  User,
} from "lucide-react";
import {
  apiClient,
  isAuthenticated,
  logout,
  getUser,
  User as UserType,
  generateEmail,
  listEmails,
  getEmail,
  saveEmail,
  deleteEmail,
  updateEmail,
  GeneratedEmail,
  EmailGenerateResponse,
  EmailContent,
  listMinutes,
  MinuteListItem,
} from "../../../../lib/apiClient";
import { Header } from "../../../../components/layout/Header";
import { Button } from "../../../../components/ui/Button";
import { Card } from "../../../../components/ui/Card";
import { Badge } from "../../../../components/ui/Badge";
import { Spinner, LoadingScreen } from "../../../../components/ui/Spinner";
import { Modal } from "../../../../components/ui/Modal";
import { ExportButton } from "../../../../components/export";

type Source = {
  id: string;
  title: string;
  file_type: string;
};

type Notebook = {
  id: string;
  title: string;
};

export default function EmailPage() {
  const params = useParams();
  const router = useRouter();
  const notebookId = params?.id as string;

  const [user, setUser] = useState<UserType | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [minutes, setMinutes] = useState<MinuteListItem[]>([]);
  const [emails, setEmails] = useState<GeneratedEmail[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<GeneratedEmail | null>(null);

  // Generated content (not yet saved)
  const [generatedContent, setGeneratedContent] = useState<EmailGenerateResponse | null>(null);
  const [editableBody, setEditableBody] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  // Form state
  const [topic, setTopic] = useState("");
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());
  const [selectedMinuteIds, setSelectedMinuteIds] = useState<Set<string>>(new Set());
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Modal state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [saveTitle, setSaveTitle] = useState("");
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebook, sources, minutes, and emails
  useEffect(() => {
    if (!authChecked) return;

    const loadData = async () => {
      try {
        const [nbRes, srcRes] = await Promise.all([
          apiClient(`/api/v1/notebooks/${notebookId}`),
          apiClient(`/api/v1/sources/notebook/${notebookId}`),
        ]);

        if (nbRes.status === 401) {
          logout();
          router.push("/login");
          return;
        }

        if (nbRes.ok) setNotebook(await nbRes.json());
        if (srcRes.ok) {
          const loadedSources: Source[] = await srcRes.json();
          setSources(loadedSources);
          // Auto-select all sources as documents
          setSelectedSourceIds(new Set(loadedSources.map((s) => s.id)));
        }

        // Load minutes
        const minutesData = await listMinutes(notebookId);
        setMinutes(minutesData);
        // Auto-select all minutes
        setSelectedMinuteIds(new Set(minutesData.map((m) => m.id)));

        // Load saved emails
        const emailsData = await listEmails(notebookId);
        setEmails(emailsData);
      } catch (e) {
        console.error(e);
      }
    };

    loadData();
  }, [authChecked, notebookId, router]);

  const handleToggleSource = (sourceId: string) => {
    setSelectedSourceIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sourceId)) {
        newSet.delete(sourceId);
      } else {
        newSet.add(sourceId);
      }
      return newSet;
    });
  };

  const handleToggleMinute = (minuteId: string) => {
    setSelectedMinuteIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(minuteId)) {
        newSet.delete(minuteId);
      } else {
        newSet.add(minuteId);
      }
      return newSet;
    });
  };

  const handleGenerate = async () => {
    if (!topic.trim() || generating) return;

    const sourceIds = Array.from(selectedSourceIds);
    const minuteIds = Array.from(selectedMinuteIds);

    if (sourceIds.length === 0 && minuteIds.length === 0) {
      alert("少なくとも1つの資料または議事録を選択してください");
      return;
    }

    setGenerating(true);
    setSelectedEmail(null);
    setGeneratedContent(null);

    try {
      const result = await generateEmail(notebookId, topic, sourceIds, minuteIds);
      // Debug logging
      console.log("=== Email Generation Result ===");
      console.log("email_body:", result.email_body);
      console.log("content:", result.content);
      console.log("content.document_summary:", result.content?.document_summary);
      console.log("content.speaker_opinions:", result.content?.speaker_opinions);
      console.log("================================");
      setGeneratedContent(result);
      setEditableBody(result.email_body);
      setIsEditing(false);
    } catch (e: unknown) {
      console.error(e);
      const errorMessage = e instanceof Error ? e.message : "メールの生成に失敗しました";
      alert(errorMessage);
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectEmail = async (email: GeneratedEmail) => {
    setLoadingDetail(true);
    setGeneratedContent(null);
    try {
      const detail = await getEmail(email.id);
      setSelectedEmail(detail);
      setEditableBody(detail.email_body);
      setIsEditing(false);
    } catch (e) {
      console.error(e);
      alert("メールの読み込みに失敗しました");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleSaveEmail = async () => {
    if (!saveTitle.trim()) return;

    setSaving(true);
    try {
      const saved = await saveEmail(notebookId, {
        title: saveTitle,
        topic: generatedContent?.topic || topic,
        email_body: editableBody,
        structured_content: generatedContent?.content,
        document_source_ids: Array.from(selectedSourceIds),
        minute_ids: Array.from(selectedMinuteIds),
      });

      setEmails((prev) => [saved, ...prev]);
      setSelectedEmail(saved);
      setGeneratedContent(null);
      setShowSaveModal(false);
      setSaveTitle("");
    } catch (e: any) {
      console.error(e);
      alert(e.message || "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateEmail = async () => {
    if (!selectedEmail) return;

    setSaving(true);
    try {
      const updated = await updateEmail(selectedEmail.id, { email_body: editableBody });
      setSelectedEmail(updated);
      setEmails((prev) =>
        prev.map((e) => (e.id === updated.id ? updated : e))
      );
      setIsEditing(false);
    } catch (e) {
      console.error(e);
      alert("更新に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;

    try {
      await deleteEmail(deleteId);
      setEmails((prev) => prev.filter((e) => e.id !== deleteId));
      if (selectedEmail?.id === deleteId) {
        setSelectedEmail(null);
      }
      setDeleteId(null);
    } catch (e) {
      console.error(e);
      alert("削除に失敗しました");
    }
  };

  const handleCopy = async () => {
    const textToCopy = editableBody;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Get display content (either generated or selected saved email)
  const displayContent = generatedContent || selectedEmail;
  const structuredContent = generatedContent?.content || (selectedEmail?.structured_content as EmailContent | null);

  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  return (
    <div className="h-screen flex flex-col bg-surface-50 dark:bg-surface-950">
      <Header
        user={user}
        showBackButton
        backHref={`/notebooks/${notebookId}`}
        backLabel="ノートブックに戻る"
        title="メール生成"
        subtitle={notebook?.title}
      />

      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel - Generation Form & History */}
        <aside className="w-80 border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 flex flex-col">
          {/* Generation Form */}
          <div className="p-4 border-b border-surface-200 dark:border-surface-700 space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
                メールの主題 / トピック
              </label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="例: プロジェクトXの進捗報告について..."
                rows={2}
                className="w-full px-3 py-2 text-sm bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* Sources (Documents) */}
            {sources.length > 0 && (
              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
                  <FileCheck className="w-4 h-4 text-blue-500" />
                  資料 ({sources.length})
                </label>
                <div className="max-h-24 overflow-y-auto space-y-1">
                  {sources.map((src) => (
                    <button
                      key={src.id}
                      onClick={() => handleToggleSource(src.id)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg transition-colors ${
                        selectedSourceIds.has(src.id)
                          ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                          : "hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-600 dark:text-surface-400"
                      }`}
                    >
                      {selectedSourceIds.has(src.id) ? (
                        <CheckSquare className="w-3.5 h-3.5 flex-shrink-0" />
                      ) : (
                        <Square className="w-3.5 h-3.5 flex-shrink-0" />
                      )}
                      <span className="truncate">{src.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Minutes */}
            {minutes.length > 0 && (
              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
                  <ClipboardList className="w-4 h-4 text-green-500" />
                  議事録 ({minutes.length})
                </label>
                <div className="max-h-24 overflow-y-auto space-y-1">
                  {minutes.map((minute) => (
                    <button
                      key={minute.id}
                      onClick={() => handleToggleMinute(minute.id)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg transition-colors ${
                        selectedMinuteIds.has(minute.id)
                          ? "bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                          : "hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-600 dark:text-surface-400"
                      }`}
                    >
                      {selectedMinuteIds.has(minute.id) ? (
                        <CheckSquare className="w-3.5 h-3.5 flex-shrink-0" />
                      ) : (
                        <Square className="w-3.5 h-3.5 flex-shrink-0" />
                      )}
                      <span className="truncate">{minute.title}</span>
                      {minute.document_count > 0 && (
                        <span className="ml-auto text-[10px] px-1.5 py-0.5 bg-surface-200 dark:bg-surface-700 rounded">
                          {minute.document_count}件
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Warning if no sources or minutes */}
            {sources.length === 0 && minutes.length === 0 && (
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  メール生成には資料または議事録が必要です。ノートブック詳細ページで資料をアップロードするか、議事録を作成してください。
                </p>
              </div>
            )}

            <Button
              variant="primary"
              className="w-full"
              onClick={handleGenerate}
              isLoading={generating}
              disabled={!topic.trim() || generating || (selectedSourceIds.size === 0 && selectedMinuteIds.size === 0)}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              {generating ? "生成中..." : "メールを生成"}
            </Button>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-3">
              保存済みメール ({emails.length})
            </h3>
            {emails.length === 0 ? (
              <div className="text-center py-8">
                <Mail className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
                <p className="text-sm text-surface-500 dark:text-surface-400">
                  保存されたメールがありません
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {emails.map((email) => (
                  <div
                    key={email.id}
                    onClick={() => handleSelectEmail(email)}
                    className={`group p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedEmail?.id === email.id
                        ? "bg-primary-100 dark:bg-primary-900/50 border border-primary-300 dark:border-primary-700"
                        : "bg-surface-50 dark:bg-surface-800 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-surface-700 dark:text-surface-200 truncate">
                          {email.title}
                        </p>
                        {email.topic && (
                          <p className="text-xs text-surface-500 dark:text-surface-400 truncate">
                            {email.topic}
                          </p>
                        )}
                        <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(email.created_at)}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteId(email.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* Main Content - Email Display */}
        <section className="flex-1 overflow-y-auto p-6">
          {loadingDetail ? (
            <div className="h-full flex items-center justify-center">
              <Spinner size="lg" />
            </div>
          ) : displayContent ? (
            <div className="max-w-3xl mx-auto animate-fade-in">
              {/* Action Bar */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {generatedContent && !selectedEmail && (
                    <Badge variant="success">新規生成</Badge>
                  )}
                  {selectedEmail && (
                    <Badge variant="secondary">保存済み</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    leftIcon={copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                  >
                    {copied ? "コピー済み" : "コピー"}
                  </Button>
                  {generatedContent && !selectedEmail && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        setSaveTitle(topic || "");
                        setShowSaveModal(true);
                      }}
                      leftIcon={<Save className="w-4 h-4" />}
                    >
                      保存
                    </Button>
                  )}
                  {selectedEmail && isEditing && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditableBody(selectedEmail.email_body);
                          setIsEditing(false);
                        }}
                      >
                        キャンセル
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleUpdateEmail}
                        isLoading={saving}
                        leftIcon={<Save className="w-4 h-4" />}
                      >
                        更新
                      </Button>
                    </>
                  )}
                  {selectedEmail && !isEditing && (
                    <>
                      <ExportButton
                        type="email"
                        id={selectedEmail.id}
                        variant="ghost"
                        size="sm"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsEditing(true)}
                        leftIcon={<Edit2 className="w-4 h-4" />}
                      >
                        編集
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {/* Email Body */}
              <Card variant="default" padding="lg" className="mb-6">
                <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-4">
                  メール本文
                </h3>
                {isEditing || (generatedContent && !selectedEmail) ? (
                  <textarea
                    value={editableBody}
                    onChange={(e) => setEditableBody(e.target.value)}
                    className="w-full h-96 px-4 py-3 text-sm bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg resize-none font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                ) : (
                  <div className="bg-surface-50 dark:bg-surface-800 rounded-lg p-4">
                    <pre className="whitespace-pre-wrap text-sm text-surface-700 dark:text-surface-300 font-mono">
                      {editableBody}
                    </pre>
                  </div>
                )}
              </Card>

              {/* Structured Content (if available) */}
              {structuredContent && (
                <Card variant="default" padding="lg">
                  <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-4">
                    抽出された内容
                  </h3>

                  {/* Document Summary */}
                  {structuredContent.document_summary && (
                    <div className="mb-6">
                      <h4 className="flex items-center gap-2 text-sm font-medium text-blue-700 dark:text-blue-300 mb-2">
                        <FileCheck className="w-4 h-4" />
                        資料の要約
                      </h4>
                      <p className="text-sm text-surface-700 dark:text-surface-300 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                        {structuredContent.document_summary}
                      </p>
                    </div>
                  )}

                  {/* Speaker Opinions */}
                  {structuredContent.speaker_opinions && structuredContent.speaker_opinions.length > 0 && (
                    <div className="mb-6">
                      <h4 className="flex items-center gap-2 text-sm font-medium text-green-700 dark:text-green-300 mb-2">
                        <ClipboardList className="w-4 h-4" />
                        発言者別の意見
                      </h4>
                      <div className="space-y-3">
                        {structuredContent.speaker_opinions.map((opinion, idx) => (
                          <div key={idx} className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
                            <p className="flex items-center gap-2 text-sm font-medium text-green-800 dark:text-green-200 mb-2">
                              <User className="w-4 h-4" />
                              {opinion.speaker}
                            </p>
                            <ul className="space-y-1 ml-6">
                              {opinion.opinions.map((op, i) => (
                                <li key={i} className="text-sm text-surface-700 dark:text-surface-300 list-disc">
                                  {op}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Additional Notes */}
                  {structuredContent.additional_notes && (
                    <div>
                      <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
                        補足事項
                      </h4>
                      <p className="text-sm text-surface-600 dark:text-surface-400 italic">
                        {structuredContent.additional_notes}
                      </p>
                    </div>
                  )}
                </Card>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mb-6 shadow-lg">
                <Mail className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                メールを生成
              </h2>
              <p className="text-surface-500 dark:text-surface-400 max-w-md mb-4">
                トピックを入力し、資料と議事録を選択してメール本文を自動生成します。
                資料からは要約を、議事録からは発言者別の意見を抽出します。
              </p>
              <div className="flex items-center gap-4 text-sm text-surface-400 dark:text-surface-500">
                <span className="flex items-center gap-1">
                  <FileCheck className="w-4 h-4 text-blue-500" />
                  資料: 要約作成
                </span>
                <span className="flex items-center gap-1">
                  <ClipboardList className="w-4 h-4 text-green-500" />
                  議事録: 意見抽出
                </span>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Delete Modal */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="メールを削除"
        description="この保存されたメールを完全に削除します。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDelete}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Save Modal */}
      <Modal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        title="メールを保存"
        description="後で参照できるようにタイトルを付けて保存します"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              タイトル
            </label>
            <input
              type="text"
              value={saveTitle}
              onChange={(e) => setSaveTitle(e.target.value)}
              placeholder="わかりやすいタイトルを入力..."
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setShowSaveModal(false)}>
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveEmail}
              isLoading={saving}
              disabled={!saveTitle.trim()}
              leftIcon={<Save className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
