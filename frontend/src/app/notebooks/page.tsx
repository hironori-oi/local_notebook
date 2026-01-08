"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  BookOpen,
  FileText,
  Trash2,
  Search,
  FolderOpen,
  Clock,
  Globe,
  Lock,
  User as UserIcon,
  Edit2,
  Save,
} from "lucide-react";
import {
  isAuthenticated,
  getUser,
  logout,
  User,
  Notebook,
  NotebookFilterType,
  fetchNotebooks,
  createNotebook,
  deleteNotebook,
  updateNotebook,
} from "../../lib/apiClient";
import { Header } from "../../components/layout/Header";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Card } from "../../components/ui/Card";
import { LoadingScreen, Skeleton } from "../../components/ui/Spinner";
import { Modal } from "../../components/ui/Modal";

export default function NotebooksPage() {
  const router = useRouter();
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<NotebookFilterType>("all");
  const [editNotebook, setEditNotebook] = useState<Notebook | null>(null);
  const [editNotebookTitle, setEditNotebookTitle] = useState("");
  const [editNotebookDesc, setEditNotebookDesc] = useState("");
  const [savingNotebook, setSavingNotebook] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebooks after auth check or when filter changes
  useEffect(() => {
    if (!authChecked) return;

    (async () => {
      setLoading(true);
      try {
        const data = await fetchNotebooks(filterType);
        setNotebooks(data);
      } catch (e) {
        console.error(e);
        // Check if it's an auth error
        if (e instanceof Error && e.message.includes("401")) {
          logout();
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [authChecked, router, filterType]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setCreating(true);

    try {
      const nb = await createNotebook({
        title,
        description: desc || undefined,
        is_public: isPublic,
      });
      setNotebooks((prev) => [nb, ...prev]);
      setTitle("");
      setDesc("");
      setIsPublic(false);
      setIsModalOpen(false);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("ノートブックの作成に失敗しました");
      }
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (notebookId: string) => {
    try {
      await deleteNotebook(notebookId);
      setNotebooks((prev) => prev.filter((nb) => nb.id !== notebookId));
      setDeleteId(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("削除に失敗しました");
      }
    }
  };

  const handleOpenEdit = (nb: Notebook) => {
    setEditNotebook(nb);
    setEditNotebookTitle(nb.title);
    setEditNotebookDesc(nb.description || "");
  };

  const handleSaveNotebook = async () => {
    if (!editNotebook || !editNotebookTitle.trim()) return;
    setSavingNotebook(true);

    try {
      const updated = await updateNotebook(editNotebook.id, {
        title: editNotebookTitle,
        description: editNotebookDesc || undefined,
      });
      setNotebooks((prev) =>
        prev.map((nb) =>
          nb.id === editNotebook.id
            ? { ...nb, title: updated.title, description: updated.description }
            : nb
        )
      );
      setEditNotebook(null);
      setEditNotebookTitle("");
      setEditNotebookDesc("");
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("保存に失敗しました");
      }
    } finally {
      setSavingNotebook(false);
    }
  };

  const filteredNotebooks = notebooks.filter(
    (nb) =>
      nb.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      nb.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Check if current user is the owner of a notebook
  const isOwner = (notebook: Notebook) => user?.id === notebook.owner_id;

  // Filter type tabs
  const filterTabs: { type: NotebookFilterType; label: string; icon: React.ReactNode }[] = [
    { type: "all", label: "すべて", icon: <FolderOpen className="w-4 h-4" /> },
    { type: "mine", label: "個人用", icon: <Lock className="w-4 h-4" /> },
    { type: "public", label: "公開", icon: <Globe className="w-4 h-4" /> },
  ];

  // Don't render anything until auth check is complete
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
                  ノートブック一覧
                </h1>
                <p className="text-surface-500 dark:text-surface-400">
                  {notebooks.length === 0
                    ? "最初のノートブックを作成しましょう"
                    : `${notebooks.length} 件のノートブック`}
                </p>
              </div>
              <Button
                variant="primary"
                size="lg"
                leftIcon={<Plus className="w-5 h-5" />}
                onClick={() => setIsModalOpen(true)}
              >
                新規作成
              </Button>
            </div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex flex-wrap items-center gap-2">
          {filterTabs.map((tab) => (
            <button
              key={tab.type}
              onClick={() => setFilterType(tab.type)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filterType === tab.type
                  ? "bg-primary-500 text-white shadow-soft"
                  : "bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400 hover:bg-surface-200 dark:hover:bg-surface-700"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        {notebooks.length > 0 && (
          <div className="mb-6">
            <Input
              placeholder="ノートブックを検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
              className="max-w-md"
            />
          </div>
        )}

        {/* Notebooks Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="default" padding="none">
                <div className="p-5">
                  <Skeleton className="h-6 w-3/4 mb-3" />
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
                <div className="px-5 py-3 border-t border-surface-100 dark:border-surface-700">
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : filteredNotebooks.length === 0 ? (
          <Card variant="default" padding="lg" className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-primary-100 to-accent-100 dark:from-primary-900/50 dark:to-accent-900/50 flex items-center justify-center">
              {searchQuery ? (
                <Search className="w-10 h-10 text-primary-500" />
              ) : (
                <FolderOpen className="w-10 h-10 text-primary-500" />
              )}
            </div>
            <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
              {searchQuery ? "ノートブックが見つかりません" : "ノートブックがありません"}
            </h3>
            <p className="text-surface-500 dark:text-surface-400 mb-6 max-w-md mx-auto">
              {searchQuery
                ? "別のキーワードで検索してください"
                : "最初のノートブックを作成して、ナレッジの整理を始めましょう"}
            </p>
            {!searchQuery && (
              <Button
                variant="primary"
                leftIcon={<Plus className="w-4 h-4" />}
                onClick={() => setIsModalOpen(true)}
              >
                ノートブックを作成
              </Button>
            )}
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredNotebooks.map((nb, index) => (
              <Card
                key={nb.id}
                variant="hover"
                padding="none"
                className="group animate-fade-in-up"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <Link href={`/notebooks/${nb.id}`} className="block">
                  <div className="p-5">
                    {/* Header with icon and badge */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 dark:from-primary-500/20 dark:to-accent-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <BookOpen className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                      </div>
                      {/* Public/Private Badge */}
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          nb.is_public
                            ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                            : "bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400"
                        }`}
                      >
                        {nb.is_public ? (
                          <>
                            <Globe className="w-3 h-3" />
                            公開
                          </>
                        ) : (
                          <>
                            <Lock className="w-3 h-3" />
                            個人用
                          </>
                        )}
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                      {nb.title}
                    </h3>

                    {/* Description */}
                    {nb.description && (
                      <p className="text-sm text-surface-500 dark:text-surface-400 line-clamp-2">
                        {nb.description}
                      </p>
                    )}
                  </div>

                  {/* Footer */}
                  <div className="px-5 py-3 border-t border-surface-100 dark:border-surface-700/50 bg-surface-50/50 dark:bg-surface-800/30 flex items-center justify-between">
                    <div className="flex items-center gap-4 text-xs text-surface-400 dark:text-surface-500">
                      <span className="flex items-center gap-1">
                        <FileText className="w-3.5 h-3.5" />
                        {nb.source_count || 0} 件
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {nb.created_at
                          ? new Date(nb.created_at).toLocaleDateString("ja-JP")
                          : "最近"}
                      </span>
                    </div>
                    {/* Owner info (show for other users' public notebooks) */}
                    {!isOwner(nb) && (
                      <span className="flex items-center gap-1 text-xs text-surface-400 dark:text-surface-500">
                        <UserIcon className="w-3.5 h-3.5" />
                        {nb.owner_display_name}
                      </span>
                    )}
                  </div>
                </Link>

                {/* Action buttons (only for owner) - overlay on hover */}
                {isOwner(nb) && (
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-all duration-200 rounded-2xl pointer-events-none" />
                )}
                {isOwner(nb) && (
                  <div className="absolute bottom-16 right-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleOpenEdit(nb);
                      }}
                      className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-primary-50 dark:hover:bg-primary-900/30 text-surface-500 hover:text-primary-500 shadow-md transition-all"
                      title="編集"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setDeleteId(nb.id);
                      }}
                      className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-red-50 dark:hover:bg-red-900/30 text-surface-500 hover:text-red-500 shadow-md transition-all"
                      title="削除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setTitle("");
          setDesc("");
          setIsPublic(false);
        }}
        title="新しいノートブックを作成"
        description="ドキュメントとナレッジを整理するためのノートブックを作成します"
      >
        <div className="space-y-4">
          <Input
            label="タイトル"
            placeholder="例：プロジェクト調査、議事録"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            leftIcon={<BookOpen className="w-4 h-4" />}
          />
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              説明（任意）
            </label>
            <textarea
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="このノートブックの目的を入力してください"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
          </div>

          {/* Public/Private Toggle */}
          <div className="flex items-center justify-between p-4 bg-surface-50 dark:bg-surface-800/50 rounded-xl">
            <div className="flex items-center gap-3">
              {isPublic ? (
                <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <Globe className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-lg bg-surface-100 dark:bg-surface-700 flex items-center justify-center">
                  <Lock className="w-5 h-5 text-surface-500" />
                </div>
              )}
              <div>
                <p className="text-sm font-medium text-surface-900 dark:text-surface-100">
                  {isPublic ? "公開ノートブック" : "個人用ノートブック"}
                </p>
                <p className="text-xs text-surface-500 dark:text-surface-400">
                  {isPublic
                    ? "全ユーザーがアクセス・編集可能"
                    : "自分だけがアクセス可能"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsPublic(!isPublic)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isPublic ? "bg-green-500" : "bg-surface-300 dark:bg-surface-600"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isPublic ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setIsModalOpen(false);
                setTitle("");
                setDesc("");
                setIsPublic(false);
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              isLoading={creating}
              disabled={!title.trim()}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              作成
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="ノートブックを削除"
        description="この操作は取り消せません。すべてのソースとチャット履歴が完全に削除されます。"
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

      {/* Edit Notebook Modal */}
      <Modal
        isOpen={!!editNotebook}
        onClose={() => {
          setEditNotebook(null);
          setEditNotebookTitle("");
          setEditNotebookDesc("");
        }}
        title="ノートブックを編集"
        description="ノートブックのタイトルと説明を変更できます"
      >
        <div className="space-y-4">
          <Input
            label="タイトル"
            placeholder="例：プロジェクト調査、議事録"
            value={editNotebookTitle}
            onChange={(e) => setEditNotebookTitle(e.target.value)}
            leftIcon={<BookOpen className="w-4 h-4" />}
          />
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              説明（任意）
            </label>
            <textarea
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="このノートブックの目的を入力してください"
              value={editNotebookDesc}
              onChange={(e) => setEditNotebookDesc(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setEditNotebook(null);
                setEditNotebookTitle("");
                setEditNotebookDesc("");
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveNotebook}
              isLoading={savingNotebook}
              disabled={!editNotebookTitle.trim()}
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
