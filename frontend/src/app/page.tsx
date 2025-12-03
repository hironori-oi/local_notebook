"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  BookOpen,
  FileText,
  MessageSquare,
  Trash2,
  MoreVertical,
  Search,
  Sparkles,
  FolderOpen,
  Clock,
} from "lucide-react";
import {
  apiClient,
  isAuthenticated,
  getUser,
  logout,
  User,
} from "../lib/apiClient";
import { Header } from "../components/layout/Header";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Card } from "../components/ui/Card";
import { LoadingScreen, Skeleton } from "../components/ui/Spinner";
import { Modal } from "../components/ui/Modal";

type Notebook = {
  id: string;
  title: string;
  description?: string | null;
  created_at?: string;
  source_count?: number;
};

export default function HomePage() {
  const router = useRouter();
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebooks after auth check
  useEffect(() => {
    if (!authChecked) return;

    (async () => {
      setLoading(true);
      try {
        const res = await apiClient("/api/v1/notebooks");
        if (res.status === 401) {
          logout();
          router.push("/login");
          return;
        }
        if (!res.ok) {
          throw new Error("failed");
        }
        setNotebooks(await res.json());
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [authChecked, router]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setCreating(true);

    try {
      const res = await apiClient("/api/v1/notebooks", {
        method: "POST",
        body: JSON.stringify({ title, description: desc }),
      });
      if (res.status === 401) {
        logout();
        router.push("/login");
        return;
      }
      if (!res.ok) {
        alert("Failed to create notebook");
        return;
      }
      const nb = await res.json();
      setNotebooks((prev) => [nb, ...prev]);
      setTitle("");
      setDesc("");
      setIsModalOpen(false);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (notebookId: string) => {
    const res = await apiClient(`/api/v1/notebooks/${notebookId}`, {
      method: "DELETE",
    });

    if (res.status === 401) {
      logout();
      router.push("/login");
      return;
    }
    if (!res.ok) {
      alert("Failed to delete");
      return;
    }

    setNotebooks((prev) => prev.filter((nb) => nb.id !== notebookId));
    setDeleteId(null);
  };

  const filteredNotebooks = notebooks.filter(
    (nb) =>
      nb.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      nb.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

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

        {/* Search & Filters */}
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
                    {/* Icon */}
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 dark:from-primary-500/20 dark:to-accent-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                      <BookOpen className="w-6 h-6 text-primary-600 dark:text-primary-400" />
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
                        {nb.source_count || 0} 件のソース
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {nb.created_at
                          ? new Date(nb.created_at).toLocaleDateString("ja-JP")
                          : "最近"}
                      </span>
                    </div>
                  </div>
                </Link>

                {/* Delete button */}
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDeleteId(nb.id);
                  }}
                  className="absolute top-3 right-3 p-2 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-surface-100 dark:hover:bg-surface-700 transition-all"
                >
                  <MoreVertical className="w-4 h-4 text-surface-400" />
                </button>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
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
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
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
    </div>
  );
}
