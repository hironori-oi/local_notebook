"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Presentation,
  Sparkles,
  Trash2,
  Download,
  Clock,
  ChevronLeft,
  ChevronRight,
  FileText,
  CheckSquare,
  Square,
  StickyNote,
} from "lucide-react";
import {
  apiClient,
  isAuthenticated,
  logout,
  getUser,
  User,
  API_BASE,
  createSlideDeck,
  listSlideDecks,
  getSlideDeck,
  downloadSlideDeckPptx,
  deleteSlideDeck,
  SlideDeck,
  SlideDeckListItem,
  SlideData,
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

// Slide layout styling
const layoutStyles: Record<string, { bgClass: string; titleSize: string }> = {
  title: {
    bgClass: "bg-gradient-to-br from-primary-500 to-accent-500",
    titleSize: "text-2xl",
  },
  content: {
    bgClass: "bg-white dark:bg-surface-800",
    titleSize: "text-lg",
  },
  section: {
    bgClass: "bg-gradient-to-br from-primary-600 to-primary-400",
    titleSize: "text-xl",
  },
  two_column: {
    bgClass: "bg-white dark:bg-surface-800",
    titleSize: "text-lg",
  },
  bullet: {
    bgClass: "bg-white dark:bg-surface-800",
    titleSize: "text-lg",
  },
  conclusion: {
    bgClass: "bg-gradient-to-br from-accent-500 to-primary-500",
    titleSize: "text-xl",
  },
};

export default function SlidesPage() {
  const params = useParams();
  const router = useRouter();
  const notebookId = params?.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [slideDecks, setSlideDecks] = useState<SlideDeckListItem[]>([]);
  const [selectedDeck, setSelectedDeck] = useState<SlideDeck | null>(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

  // Form state
  const [topic, setTopic] = useState("");
  const [targetSlides, setTargetSlides] = useState(8);
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());
  const [generating, setGenerating] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Modal state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [showSpeakerNotes, setShowSpeakerNotes] = useState(false);

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebook, sources, and slide decks
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
          setSelectedSourceIds(new Set(loadedSources.map((s) => s.id)));
        }

        // Load slide decks
        const decksData = await listSlideDecks(notebookId);
        setSlideDecks(decksData.slide_decks);
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
      const deck = await createSlideDeck(
        notebookId,
        topic,
        Array.from(selectedSourceIds),
        targetSlides
      );

      // Add to list and select it
      setSlideDecks((prev) => [
        {
          id: deck.id,
          notebook_id: deck.notebook_id,
          title: deck.title,
          topic: deck.topic,
          slide_count: deck.slide_count,
          pptx_available: deck.pptx_available,
          created_at: deck.created_at,
        },
        ...prev,
      ]);
      setSelectedDeck(deck);
      setCurrentSlideIndex(0);
      setTopic("");
    } catch (e) {
      console.error(e);
      alert("スライドデッキの生成に失敗しました");
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectDeck = async (item: SlideDeckListItem) => {
    setLoadingDetail(true);
    try {
      const detail = await getSlideDeck(item.id);
      setSelectedDeck(detail);
      setCurrentSlideIndex(0);
    } catch (e) {
      console.error(e);
      alert("スライドデッキの読み込みに失敗しました");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDownload = async () => {
    if (!selectedDeck || downloading) return;

    setDownloading(true);
    try {
      const blob = await downloadSlideDeckPptx(selectedDeck.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedDeck.title}.pptx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      console.error(e);
      alert("ダウンロードに失敗しました");
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;

    try {
      await deleteSlideDeck(deleteId);
      setSlideDecks((prev) => prev.filter((d) => d.id !== deleteId));
      if (selectedDeck?.id === deleteId) {
        setSelectedDeck(null);
        setCurrentSlideIndex(0);
      }
      setDeleteId(null);
    } catch (e) {
      console.error(e);
      alert("削除に失敗しました");
    }
  };

  const handlePrevSlide = () => {
    setCurrentSlideIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNextSlide = () => {
    if (!selectedDeck) return;
    setCurrentSlideIndex((prev) =>
      Math.min(selectedDeck.outline.slides.length - 1, prev + 1)
    );
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

  const getSlideStyle = (layout: string) => {
    return layoutStyles[layout] || layoutStyles.content;
  };

  const renderSlidePreview = (slide: SlideData, isMain: boolean = false) => {
    const style = getSlideStyle(slide.layout);
    const isGradient = style.bgClass.includes("gradient");
    const hasImage = slide.image_url;

    return (
      <div
        className={`${
          isMain ? "aspect-[16/9] w-full" : "aspect-[16/9] w-full"
        } ${style.bgClass} rounded-lg border border-surface-200 dark:border-surface-700 overflow-hidden ${
          isMain ? "shadow-lg" : "shadow-sm"
        }`}
      >
        <div className={`w-full h-full p-4 flex ${hasImage && isMain ? "gap-4" : "flex-col"}`}>
          {/* Text Content */}
          <div className={`flex flex-col ${hasImage && isMain ? "flex-1" : "w-full"}`}>
            {/* Slide Title */}
            <h3
              className={`${isMain ? style.titleSize : "text-xs"} font-bold ${
                isGradient ? "text-white" : "text-surface-800 dark:text-surface-100"
              } ${isMain ? "mb-4" : "mb-2"} line-clamp-2`}
            >
              {slide.title}
            </h3>

            {/* Subtitle (for title slides) */}
            {slide.subtitle && (
              <p
                className={`${isMain ? "text-base" : "text-xs"} ${
                  isGradient ? "text-white/80" : "text-surface-500 dark:text-surface-400"
                } mb-2`}
              >
                {slide.subtitle}
              </p>
            )}

            {/* Bullets */}
            {slide.bullets && slide.bullets.length > 0 && (
              <ul className={`space-y-1 flex-1 overflow-hidden ${isMain ? "" : "text-xs"}`}>
                {slide.bullets.slice(0, isMain ? undefined : 3).map((bullet, i) => (
                  <li
                    key={i}
                    className={`flex items-start gap-2 ${
                      isGradient ? "text-white/90" : "text-surface-700 dark:text-surface-200"
                    } ${isMain ? "text-sm" : "text-xs"}`}
                  >
                    <span className="flex-shrink-0 mt-1">•</span>
                    <span className={isMain ? "" : "line-clamp-1"}>{bullet}</span>
                  </li>
                ))}
                {!isMain && slide.bullets.length > 3 && (
                  <li className="text-xs text-surface-400">
                    +{slide.bullets.length - 3} more...
                  </li>
                )}
              </ul>
            )}

            {/* Visual hint indicator */}
            {slide.visual_hint && isMain && !hasImage && (
              <div className="mt-auto pt-2">
                <Badge variant="secondary" size="sm">
                  {slide.visual_hint}
                </Badge>
              </div>
            )}
          </div>

          {/* Slide Image */}
          {hasImage && isMain && (
            <div className="w-2/5 flex-shrink-0 flex items-center justify-center">
              <img
                src={`${API_BASE}${slide.image_url}`}
                alt={slide.title}
                className="max-w-full max-h-full object-contain rounded-lg shadow-md"
                onError={(e) => {
                  // Hide image on error
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  const currentSlide = selectedDeck?.outline.slides[currentSlideIndex];

  return (
    <div className="h-screen flex flex-col bg-surface-50 dark:bg-surface-950">
      <Header
        user={user}
        showBackButton
        backHref={`/notebooks/${notebookId}`}
        backLabel="ノートブックに戻る"
        title="スライド生成"
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
                placeholder="プレゼンテーションのトピックを入力..."
                rows={3}
                className="w-full px-3 py-2 text-sm bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* Slide count */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
                スライド枚数: {targetSlides}枚
              </label>
              <input
                type="range"
                min={3}
                max={20}
                value={targetSlides}
                onChange={(e) => setTargetSlides(Number(e.target.value))}
                className="w-full h-2 bg-surface-200 dark:bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
              />
              <div className="flex justify-between text-xs text-surface-400 mt-1">
                <span>3枚</span>
                <span>20枚</span>
              </div>
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
              {generating ? "生成中..." : "スライドを生成"}
            </Button>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-3">
              生成履歴 ({slideDecks.length})
            </h3>
            {slideDecks.length === 0 ? (
              <div className="text-center py-8">
                <Presentation className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
                <p className="text-sm text-surface-500 dark:text-surface-400">
                  スライドデッキがありません
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {slideDecks.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleSelectDeck(item)}
                    className={`group p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedDeck?.id === item.id
                        ? "bg-primary-100 dark:bg-primary-900/50 border border-primary-300 dark:border-primary-700"
                        : "bg-surface-50 dark:bg-surface-800 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-surface-700 dark:text-surface-200 truncate">
                          {item.title}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="secondary" size="sm">
                            {item.slide_count}枚
                          </Badge>
                          {item.pptx_available && (
                            <Badge variant="success" size="sm">
                              PPTX
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-surface-400 dark:text-surface-500 mt-1 flex items-center gap-1">
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

        {/* Main Content - Slide Preview */}
        <section className="flex-1 flex flex-col overflow-hidden">
          {loadingDetail ? (
            <div className="flex-1 flex items-center justify-center">
              <Spinner size="lg" />
            </div>
          ) : selectedDeck && currentSlide ? (
            <>
              {/* Main Slide Display */}
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="max-w-4xl mx-auto">
                  {/* Header with title and actions */}
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-bold text-surface-900 dark:text-surface-100">
                        {selectedDeck.title}
                      </h2>
                      <p className="text-sm text-surface-500">
                        {selectedDeck.slide_count}枚のスライド
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setShowSpeakerNotes(!showSpeakerNotes)}
                        leftIcon={<StickyNote className="w-4 h-4" />}
                        className={showSpeakerNotes ? "bg-primary-100 dark:bg-primary-900/50" : ""}
                      >
                        ノート
                      </Button>
                      {selectedDeck.pptx_available && (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={handleDownload}
                          isLoading={downloading}
                          leftIcon={<Download className="w-4 h-4" />}
                        >
                          PPTX
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Main Slide */}
                  <div className="animate-fade-in">
                    {renderSlidePreview(currentSlide, true)}
                  </div>

                  {/* Speaker Notes */}
                  {showSpeakerNotes && currentSlide.speaker_notes && (
                    <div className="mt-4 p-4 bg-surface-100 dark:bg-surface-800 rounded-lg animate-fade-in">
                      <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2 flex items-center gap-2">
                        <StickyNote className="w-4 h-4" />
                        スピーカーノート
                      </h4>
                      <p className="text-sm text-surface-600 dark:text-surface-400 whitespace-pre-wrap">
                        {currentSlide.speaker_notes}
                      </p>
                    </div>
                  )}

                  {/* Navigation */}
                  <div className="flex items-center justify-center gap-4 mt-6">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handlePrevSlide}
                      disabled={currentSlideIndex === 0}
                      leftIcon={<ChevronLeft className="w-4 h-4" />}
                    >
                      前へ
                    </Button>
                    <span className="text-sm text-surface-600 dark:text-surface-400 min-w-[80px] text-center">
                      {currentSlideIndex + 1} / {selectedDeck.outline.slides.length}
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleNextSlide}
                      disabled={currentSlideIndex === selectedDeck.outline.slides.length - 1}
                      rightIcon={<ChevronRight className="w-4 h-4" />}
                    >
                      次へ
                    </Button>
                  </div>
                </div>
              </div>

              {/* Thumbnail Strip */}
              <div className="border-t border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 p-4">
                <div className="flex gap-3 overflow-x-auto pb-2">
                  {selectedDeck.outline.slides.map((slide, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentSlideIndex(idx)}
                      className={`flex-shrink-0 w-32 transition-all ${
                        idx === currentSlideIndex
                          ? "ring-2 ring-primary-500 ring-offset-2 dark:ring-offset-surface-800"
                          : "opacity-70 hover:opacity-100"
                      }`}
                    >
                      {renderSlidePreview(slide, false)}
                      <p className="text-xs text-center mt-1 text-surface-500 truncate">
                        {idx + 1}. {slide.title}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mb-6 shadow-lg">
                <Presentation className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                スライドデッキを生成
              </h2>
              <p className="text-surface-500 dark:text-surface-400 max-w-md">
                トピックを入力して、ソースから自動的にプレゼンテーション用のスライドを生成します。
                生成後はPowerPointファイルとしてダウンロードできます。
              </p>
            </div>
          )}
        </section>
      </main>

      {/* Delete Modal */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="スライドデッキを削除"
        description="このスライドデッキとPPTXファイルを完全に削除します。"
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
