"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  LayoutGrid,
  Sparkles,
  FileText,
  Trash2,
  Lightbulb,
  Target,
  Users,
  BarChart3,
  CheckCircle,
  Clock,
  ChevronRight,
  CheckSquare,
  Square,
} from "lucide-react";
import {
  apiClient,
  isAuthenticated,
  logout,
  getUser,
  User,
  createInfographic,
  listInfographics,
  getInfographic,
  deleteInfographic,
  Infographic,
  InfographicListItem,
  InfographicStructure,
  API_BASE,
} from "../../../../lib/apiClient";
import { Header } from "../../../../components/layout/Header";
import { Button } from "../../../../components/ui/Button";
import { Card } from "../../../../components/ui/Card";
import { Badge } from "../../../../components/ui/Badge";
import { Spinner, LoadingScreen } from "../../../../components/ui/Spinner";
import { Modal } from "../../../../components/ui/Modal";

type Source = {
  id: string;
  title: string;
  file_type: string;
};

type Notebook = {
  id: string;
  title: string;
};

// Icon mapping for infographic sections
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  lightbulb: Lightbulb,
  target: Target,
  users: Users,
  chart: BarChart3,
  check: CheckCircle,
  default: Sparkles,
};

// Color mapping for sections
const colorClasses: Record<string, { bg: string; border: string; text: string }> = {
  primary: {
    bg: "bg-primary-50 dark:bg-primary-900/30",
    border: "border-primary-200 dark:border-primary-800",
    text: "text-primary-700 dark:text-primary-300",
  },
  secondary: {
    bg: "bg-surface-100 dark:bg-surface-800",
    border: "border-surface-200 dark:border-surface-700",
    text: "text-surface-700 dark:text-surface-300",
  },
  accent: {
    bg: "bg-accent-50 dark:bg-accent-900/30",
    border: "border-accent-200 dark:border-accent-800",
    text: "text-accent-700 dark:text-accent-300",
  },
  success: {
    bg: "bg-green-50 dark:bg-green-900/30",
    border: "border-green-200 dark:border-green-800",
    text: "text-green-700 dark:text-green-300",
  },
  warning: {
    bg: "bg-amber-50 dark:bg-amber-900/30",
    border: "border-amber-200 dark:border-amber-800",
    text: "text-amber-700 dark:text-amber-300",
  },
};

export default function InfographicPage() {
  const params = useParams();
  const router = useRouter();
  const notebookId = params?.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [infographics, setInfographics] = useState<InfographicListItem[]>([]);
  const [selectedInfographic, setSelectedInfographic] = useState<Infographic | null>(null);

  // Form state
  const [topic, setTopic] = useState("");
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());
  const [stylePreset, setStylePreset] = useState("default");
  const [generating, setGenerating] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Modal state
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebook, sources, and infographics
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
          const srcData = await srcRes.json();
          // API returns {items: [...], total, offset} format
          const loadedSources: Source[] = srcData.items || srcData;
          setSources(loadedSources);
          setSelectedSourceIds(new Set(loadedSources.map((s) => s.id)));
        }

        // Load infographics
        const infographicsData = await listInfographics(notebookId);
        setInfographics(infographicsData.infographics);
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

  const handleSelectAllSources = () => {
    setSelectedSourceIds(new Set(sources.map((s) => s.id)));
  };

  const handleDeselectAllSources = () => {
    setSelectedSourceIds(new Set());
  };

  const handleGenerate = async () => {
    if (!topic.trim() || generating) return;

    setGenerating(true);
    try {
      const infographic = await createInfographic(
        notebookId,
        topic,
        Array.from(selectedSourceIds),
        stylePreset
      );

      // Add to list and select it
      setInfographics((prev) => [
        {
          id: infographic.id,
          notebook_id: infographic.notebook_id,
          title: infographic.title,
          topic: infographic.topic,
          style_preset: infographic.style_preset,
          created_at: infographic.created_at,
        },
        ...prev,
      ]);
      setSelectedInfographic(infographic);
      setTopic("");
    } catch (e) {
      console.error(e);
      alert("インフォグラフィックの生成に失敗しました");
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectInfographic = async (item: InfographicListItem) => {
    setLoadingDetail(true);
    try {
      const detail = await getInfographic(item.id);
      setSelectedInfographic(detail);
    } catch (e) {
      console.error(e);
      alert("インフォグラフィックの読み込みに失敗しました");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;

    try {
      await deleteInfographic(deleteId);
      setInfographics((prev) => prev.filter((i) => i.id !== deleteId));
      if (selectedInfographic?.id === deleteId) {
        setSelectedInfographic(null);
      }
      setDeleteId(null);
    } catch (e) {
      console.error(e);
      alert("削除に失敗しました");
    }
  };

  const getIcon = (hint: string | null | undefined) => {
    const IconComponent = iconMap[hint || "default"] || iconMap.default;
    return IconComponent;
  };

  const getColorClasses = (hint: string | null | undefined) => {
    return colorClasses[hint || "primary"] || colorClasses.primary;
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
        title="インフォグラフィック生成"
        subtitle={notebook?.title}
      />

      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel - Generation Form & History */}
        <aside className="w-80 border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 flex flex-col">
          {/* Generation Form */}
          <div className="p-4 border-b border-surface-200 dark:border-surface-700 space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
                トピック / テーマ
              </label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="インフォグラフィックにしたい内容を入力..."
                rows={3}
                className="w-full px-3 py-2 text-sm bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* Source Selection */}
            {sources.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-surface-700 dark:text-surface-300">
                    参照ソース
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={handleSelectAllSources}
                      className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                    >
                      全選択
                    </button>
                    <button
                      onClick={handleDeselectAllSources}
                      className="text-xs text-surface-500 hover:underline"
                    >
                      解除
                    </button>
                  </div>
                </div>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {sources.map((src) => (
                    <button
                      key={src.id}
                      onClick={() => handleToggleSource(src.id)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg transition-colors ${
                        selectedSourceIds.has(src.id)
                          ? "bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
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

            <Button
              variant="primary"
              className="w-full"
              onClick={handleGenerate}
              isLoading={generating}
              disabled={!topic.trim() || generating}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              {generating ? "生成中..." : "インフォグラフィックを生成"}
            </Button>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-3">
              生成履歴 ({infographics.length})
            </h3>
            {infographics.length === 0 ? (
              <div className="text-center py-8">
                <LayoutGrid className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
                <p className="text-sm text-surface-500 dark:text-surface-400">
                  インフォグラフィックがありません
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {infographics.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleSelectInfographic(item)}
                    className={`group p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedInfographic?.id === item.id
                        ? "bg-primary-100 dark:bg-primary-900/50 border border-primary-300 dark:border-primary-700"
                        : "bg-surface-50 dark:bg-surface-800 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-surface-700 dark:text-surface-200 truncate">
                          {item.title}
                        </p>
                        <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(item.created_at)}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteId(item.id);
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

        {/* Main Content - Infographic Display */}
        <section className="flex-1 overflow-y-auto p-6">
          {loadingDetail ? (
            <div className="h-full flex items-center justify-center">
              <Spinner size="lg" />
            </div>
          ) : selectedInfographic ? (
            <div className="max-w-4xl mx-auto animate-fade-in">
              {/* Header */}
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                  {selectedInfographic.structure.title}
                </h1>
                {selectedInfographic.structure.subtitle && (
                  <p className="text-lg text-surface-500 dark:text-surface-400">
                    {selectedInfographic.structure.subtitle}
                  </p>
                )}
              </div>

              {/* Sections Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {selectedInfographic.structure.sections.map((section, idx) => {
                  const Icon = getIcon(section.icon_hint);
                  const colors = getColorClasses(section.color_hint);
                  const colorIndex = idx % Object.keys(colorClasses).length;
                  const colorKey = Object.keys(colorClasses)[colorIndex];
                  const sectionColors = section.color_hint
                    ? colors
                    : colorClasses[colorKey];

                  return (
                    <Card
                      key={section.id}
                      variant="default"
                      padding="lg"
                      className={`${sectionColors.bg} ${sectionColors.border} border-2`}
                    >
                      {/* Section Image */}
                      {section.image_url && (
                        <div className="mb-4 -mx-4 -mt-4">
                          <img
                            src={`${API_BASE}${section.image_url}`}
                            alt={section.heading}
                            className="w-full h-48 object-cover rounded-t-lg"
                            onError={(e) => {
                              // Hide image on error
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        </div>
                      )}
                      <div className="flex items-start gap-4">
                        <div
                          className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${sectionColors.text} bg-white dark:bg-surface-900`}
                        >
                          <Icon className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                          <h3
                            className={`text-lg font-semibold mb-3 ${sectionColors.text}`}
                          >
                            {section.heading}
                          </h3>
                          <ul className="space-y-2">
                            {section.key_points.map((point, i) => (
                              <li
                                key={i}
                                className="flex items-start gap-2 text-sm text-surface-700 dark:text-surface-300"
                              >
                                <ChevronRight className="w-4 h-4 flex-shrink-0 mt-0.5 text-surface-400" />
                                <span>{point}</span>
                              </li>
                            ))}
                          </ul>
                          {section.detail && (
                            <p className="mt-3 text-xs text-surface-500 dark:text-surface-400 italic">
                              {section.detail}
                            </p>
                          )}
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>

              {/* Footer Note */}
              {selectedInfographic.structure.footer_note && (
                <div className="text-center">
                  <p className="text-sm text-surface-500 dark:text-surface-400 italic">
                    {selectedInfographic.structure.footer_note}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent-500 to-primary-500 flex items-center justify-center mb-6 shadow-lg">
                <LayoutGrid className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                インフォグラフィックを生成
              </h2>
              <p className="text-surface-500 dark:text-surface-400 max-w-md">
                トピックを入力して、ソースから自動的にインフォグラフィックを生成します。
                生成されたインフォグラフィックはカードグリッド形式で表示されます。
              </p>
            </div>
          )}
        </section>
      </main>

      {/* Delete Modal */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="インフォグラフィックを削除"
        description="このインフォグラフィックを完全に削除します。"
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
    </div>
  );
}
