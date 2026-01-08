"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  FileText,
  Trash2,
  Download,
  ChevronRight,
  Plus,
  RefreshCw,
} from "lucide-react";
import { Button } from "../ui/Button";
import { SlideInputForm } from "./SlideInputForm";
import { SlidePreview } from "./SlidePreview";
import { RefinementChat } from "./RefinementChat";
import { SlideEditModal } from "./SlideEditModal";
import {
  getProjects,
  getProject,
  createProject,
  deleteProject,
  refineSlides,
  exportProject,
  downloadPptx,
  ProjectSummary,
  ProjectDetail,
  Slide,
  PROJECT_STATUS_LABELS,
  CreateProjectRequest,
} from "../../lib/slideGeneratorApi";

interface SlideGeneratorContentProps {
  onError?: (message: string) => void;
}

export function SlideGeneratorContent({ onError }: SlideGeneratorContentProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [currentProject, setCurrentProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [refining, setRefining] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [editingSlide, setEditingSlide] = useState<Slide | null>(null);
  const [view, setView] = useState<"list" | "project">("list");

  // Load projects
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getProjects(50, 0);
      setProjects(response.items);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "プロジェクトの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Poll for project status
  useEffect(() => {
    if (!currentProject) return;
    if (currentProject.status !== "pending" && currentProject.status !== "generating") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await getProject(currentProject.id);
        setCurrentProject(updated);
        if (updated.status === "completed" || updated.status === "failed") {
          loadProjects();
        }
      } catch (err) {
        console.error("Polling failed:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentProject, loadProjects]);

  const handleCreateProject = async (request: CreateProjectRequest) => {
    try {
      setGenerating(true);
      const project = await createProject(request);
      setCurrentProject(project);
      setView("project");
      loadProjects();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "プロジェクトの作成に失敗しました");
    } finally {
      setGenerating(false);
    }
  };

  const handleOpenProject = async (projectId: string) => {
    try {
      setLoading(true);
      const project = await getProject(projectId);
      setCurrentProject(project);
      setView("project");
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "プロジェクトの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm("このプロジェクトを削除しますか？")) return;
    try {
      await deleteProject(projectId);
      if (currentProject?.id === projectId) {
        setCurrentProject(null);
        setView("list");
      }
      loadProjects();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "プロジェクトの削除に失敗しました");
    }
  };

  const handleRefine = async (instruction: string) => {
    if (!currentProject) return;
    try {
      setRefining(true);
      const response = await refineSlides(currentProject.id, instruction);
      setCurrentProject((prev) =>
        prev
          ? {
              ...prev,
              slides: response.slides,
              messages: [
                ...prev.messages,
                {
                  id: crypto.randomUUID(),
                  role: "user" as const,
                  content: instruction,
                  created_at: new Date().toISOString(),
                },
                {
                  id: crypto.randomUUID(),
                  role: "assistant" as const,
                  content: response.message,
                  created_at: new Date().toISOString(),
                },
              ],
            }
          : null
      );
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "スライドの修正に失敗しました");
    } finally {
      setRefining(false);
    }
  };

  const handleExport = async () => {
    if (!currentProject) return;
    try {
      setExporting(true);
      const blob = await exportProject(currentProject.id);
      downloadPptx(blob, currentProject.title);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "エクスポートに失敗しました");
    } finally {
      setExporting(false);
    }
  };

  const handleSlideUpdate = (updatedSlide: Slide) => {
    setCurrentProject((prev) =>
      prev
        ? {
            ...prev,
            slides: prev.slides.map((s) =>
              s.slide_number === updatedSlide.slide_number ? updatedSlide : s
            ),
          }
        : null
    );
    setEditingSlide(null);
  };

  // Project list view
  if (view === "list") {
    return (
      <div className="space-y-6">
        {/* Create new project form */}
        <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-soft border border-surface-200 dark:border-surface-700 p-6">
          <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-4">
            新規スライド作成
          </h2>
          <SlideInputForm onSubmit={handleCreateProject} loading={generating} />
        </div>

        {/* Project history */}
        <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-soft border border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between p-4 border-b border-surface-200 dark:border-surface-700">
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              プロジェクト履歴
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadProjects}
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

          {loading && projects.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 mx-auto text-surface-300 mb-4" />
              <p className="text-surface-500">プロジェクトがありません</p>
            </div>
          ) : (
            <div className="divide-y divide-surface-200 dark:divide-surface-700">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="p-4 hover:bg-surface-50 dark:hover:bg-surface-750 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div
                      className="flex-1 cursor-pointer"
                      onClick={() => handleOpenProject(project.id)}
                    >
                      <p className="font-medium text-surface-900 dark:text-surface-100">
                        {project.title}
                      </p>
                      <div className="flex items-center gap-3 text-sm text-surface-500">
                        <span>{PROJECT_STATUS_LABELS[project.status] || project.status}</span>
                        <span>{project.slide_count}枚</span>
                        <span>
                          {new Date(project.created_at).toLocaleDateString("ja-JP")}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDeleteProject(project.id)}
                        className="p-2 text-surface-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleOpenProject(project.id)}
                        className="p-2 text-surface-400 hover:text-primary-500 transition-colors"
                      >
                        <ChevronRight className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Project detail view
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setView("list");
              setCurrentProject(null);
            }}
            className="p-2 hover:bg-surface-200 dark:hover:bg-surface-700 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5 rotate-180 text-surface-600 dark:text-surface-300" />
          </button>
          <div>
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              {currentProject?.title}
            </h2>
            <p className="text-sm text-surface-500">
              {currentProject?.slides.length || 0}枚のスライド
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleExport}
            disabled={
              exporting ||
              !currentProject?.slides.length ||
              currentProject?.status !== "completed"
            }
            leftIcon={
              exporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )
            }
          >
            PPTXダウンロード
          </Button>
        </div>
      </div>

      {/* Status indicator */}
      {currentProject?.status === "generating" && (
        <div className="flex items-center gap-3 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-2xl border border-primary-200 dark:border-primary-800">
          <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          <span className="text-primary-700 dark:text-primary-300">
            スライドを生成中...
          </span>
        </div>
      )}

      {currentProject?.status === "failed" && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-2xl border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
          エラー: {currentProject.error_message}
        </div>
      )}

      {/* Content grid */}
      {currentProject?.status === "completed" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Slide preview */}
          <div className="lg:col-span-2">
            <SlidePreview
              slides={currentProject.slides}
              onSlideClick={(slide) => setEditingSlide(slide)}
            />
          </div>

          {/* Refinement chat */}
          <div className="lg:col-span-1">
            <RefinementChat
              messages={currentProject.messages}
              onSend={handleRefine}
              loading={refining}
            />
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editingSlide && currentProject && (
        <SlideEditModal
          projectId={currentProject.id}
          slide={editingSlide}
          onClose={() => setEditingSlide(null)}
          onUpdate={handleSlideUpdate}
        />
      )}
    </div>
  );
}
