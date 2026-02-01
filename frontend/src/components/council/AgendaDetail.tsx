"use client";

import { useState } from "react";
import {
  FileText,
  ClipboardList,
  ExternalLink,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Check,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import {
  CouncilAgendaItemDetail,
  CouncilAgendaMaterialDetail,
  CouncilAgendaMaterialCreate,
  PROCESSING_STATUS_LABELS,
  PROCESSING_STATUS_COLORS,
  regenerateAgendaSummary,
  createAgendaMaterial,
  deleteAgendaMaterial,
} from "../../lib/councilApi";

interface AgendaDetailProps {
  agenda: CouncilAgendaItemDetail;
  onRefresh?: () => void;
}

export function AgendaDetail({ agenda, onRefresh }: AgendaDetailProps) {
  const [showMaterialsText, setShowMaterialsText] = useState(false);
  const [showMinutesText, setShowMinutesText] = useState(false);
  const [expandedMaterialIds, setExpandedMaterialIds] = useState<Set<string>>(new Set());
  const [regeneratingMaterials, setRegeneratingMaterials] = useState(false);
  const [regeneratingMinutes, setRegeneratingMinutes] = useState(false);
  const [showAddMaterial, setShowAddMaterial] = useState(false);
  const [newMaterialUrl, setNewMaterialUrl] = useState("");
  const [newMaterialTitle, setNewMaterialTitle] = useState("");
  const [addingMaterial, setAddingMaterial] = useState(false);
  const [deletingMaterialId, setDeletingMaterialId] = useState<string | null>(null);

  const toggleMaterialExpanded = (materialId: string) => {
    setExpandedMaterialIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(materialId)) {
        newSet.delete(materialId);
      } else {
        newSet.add(materialId);
      }
      return newSet;
    });
  };

  const handleAddMaterial = async () => {
    if (!newMaterialUrl.trim()) return;
    setAddingMaterial(true);
    try {
      const nextNumber = agenda.materials.length > 0
        ? Math.max(...agenda.materials.map((m) => m.material_number)) + 1
        : 1;
      await createAgendaMaterial(agenda.id, {
        material_number: nextNumber,
        title: newMaterialTitle.trim() || undefined,
        url: newMaterialUrl.trim(),
      });
      setNewMaterialUrl("");
      setNewMaterialTitle("");
      setShowAddMaterial(false);
      onRefresh?.();
    } catch (error) {
      console.error("Failed to add material:", error);
      alert(error instanceof Error ? error.message : "資料の追加に失敗しました");
    } finally {
      setAddingMaterial(false);
    }
  };

  const handleDeleteMaterial = async (materialId: string) => {
    setDeletingMaterialId(materialId);
    try {
      await deleteAgendaMaterial(agenda.id, materialId);
      onRefresh?.();
    } catch (error) {
      console.error("Failed to delete material:", error);
      alert(error instanceof Error ? error.message : "資料の削除に失敗しました");
    } finally {
      setDeletingMaterialId(null);
    }
  };

  const handleRegenerateMaterials = async () => {
    if (regeneratingMaterials) return;
    setRegeneratingMaterials(true);
    try {
      await regenerateAgendaSummary(agenda.id, "materials");
      onRefresh?.();
    } catch (error) {
      console.error("Failed to regenerate materials summary:", error);
    } finally {
      setRegeneratingMaterials(false);
    }
  };

  const handleRegenerateMinutes = async () => {
    if (regeneratingMinutes) return;
    setRegeneratingMinutes(true);
    try {
      await regenerateAgendaSummary(agenda.id, "minutes");
      onRefresh?.();
    } catch (error) {
      console.error("Failed to regenerate minutes summary:", error);
    } finally {
      setRegeneratingMinutes(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-sm font-semibold">
          議題{agenda.agenda_number}
        </span>
        {agenda.title && (
          <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
            {agenda.title}
          </h3>
        )}
      </div>

      {/* Processing error */}
      {agenda.processing_error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-700 dark:text-red-300">処理エラー</p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">{agenda.processing_error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Materials Section */}
      <section className="bg-surface-50 dark:bg-surface-800/50 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-primary-500" />
            <h4 className="font-semibold text-surface-900 dark:text-surface-100">資料</h4>
            <span className="text-sm text-surface-500 dark:text-surface-400">
              ({agenda.materials.length}件)
            </span>
          </div>
          <button
            onClick={() => setShowAddMaterial(!showAddMaterial)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-primary-600 hover:text-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            追加
          </button>
        </div>

        {/* Add Material Form */}
        {showAddMaterial && (
          <div className="p-4 bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 space-y-3">
            <input
              type="text"
              value={newMaterialTitle}
              onChange={(e) => setNewMaterialTitle(e.target.value)}
              placeholder="資料タイトル（任意）"
              className="w-full px-3 py-2 text-sm border border-surface-300 dark:border-surface-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-700 dark:text-surface-100"
            />
            <input
              type="url"
              value={newMaterialUrl}
              onChange={(e) => setNewMaterialUrl(e.target.value)}
              placeholder="https://..."
              className="w-full px-3 py-2 text-sm border border-surface-300 dark:border-surface-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-700 dark:text-surface-100"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowAddMaterial(false);
                  setNewMaterialUrl("");
                  setNewMaterialTitle("");
                }}
                className="px-3 py-1.5 text-sm text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700 rounded-lg transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={handleAddMaterial}
                disabled={!newMaterialUrl.trim() || addingMaterial}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {addingMaterial && <Loader2 className="w-4 h-4 animate-spin" />}
                追加
              </button>
            </div>
          </div>
        )}

        {/* Materials List */}
        {agenda.materials.length > 0 ? (
          <div className="space-y-3">
            {agenda.materials.map((material) => (
              <div
                key={material.id}
                className="bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 overflow-hidden"
              >
                <div className="p-4 space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-surface-500 dark:text-surface-400">
                        資料{material.material_number}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                          PROCESSING_STATUS_COLORS[material.processing_status] || "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {PROCESSING_STATUS_LABELS[material.processing_status] || material.processing_status}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteMaterial(material.id)}
                      disabled={deletingMaterialId === material.id}
                      className="p-1 text-surface-400 hover:text-red-500 transition-colors disabled:opacity-50"
                      title="削除"
                    >
                      {deletingMaterialId === material.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  {material.title && (
                    <h5 className="text-sm font-medium text-surface-900 dark:text-surface-100">
                      {material.title}
                    </h5>
                  )}
                  <a
                    href={material.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
                  >
                    <ExternalLink className="w-4 h-4" />
                    {material.url.length > 50 ? material.url.substring(0, 50) + "..." : material.url}
                  </a>

                  {/* Processing Error */}
                  {material.processing_status === "failed" && material.processing_error && (
                    <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-red-600 dark:text-red-400">
                          {material.processing_error}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Material Summary */}
                  {material.summary && (
                    <div className="mt-2 p-3 bg-surface-50 dark:bg-surface-700 rounded-lg">
                      <h6 className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">要約</h6>
                      <div className="text-sm text-surface-600 dark:text-surface-300 whitespace-pre-wrap">
                        {material.summary}
                      </div>
                    </div>
                  )}

                  {/* Material Text (collapsible) */}
                  {material.text && (
                    <div className="mt-2">
                      <button
                        onClick={() => toggleMaterialExpanded(material.id)}
                        className="inline-flex items-center gap-1.5 text-xs text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-300 transition-colors"
                      >
                        {expandedMaterialIds.has(material.id) ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                        {expandedMaterialIds.has(material.id) ? "元テキストを隠す" : "元テキストを表示"}
                      </button>
                      {expandedMaterialIds.has(material.id) && (
                        <div className="mt-2 p-3 bg-surface-50 dark:bg-surface-700 rounded-lg max-h-64 overflow-y-auto">
                          <pre className="text-xs text-surface-600 dark:text-surface-300 whitespace-pre-wrap font-sans">
                            {material.text}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : !agenda.materials_url ? (
          <p className="text-sm text-surface-500 dark:text-surface-400 italic text-center py-4">
            資料が登録されていません。「追加」ボタンから資料を追加してください。
          </p>
        ) : null}

        {/* Legacy materials_url support */}
        {agenda.materials_url && (
          <div className="mt-4 pt-4 border-t border-surface-200 dark:border-surface-700">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-surface-500 dark:text-surface-400">レガシー資料URL</span>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                  PROCESSING_STATUS_COLORS[agenda.materials_processing_status] || "bg-gray-100 text-gray-700"
                }`}
              >
                {PROCESSING_STATUS_LABELS[agenda.materials_processing_status] || agenda.materials_processing_status}
              </span>
            </div>
            <a
              href={agenda.materials_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
            >
              <ExternalLink className="w-4 h-4" />
              {agenda.materials_url.length > 50
                ? agenda.materials_url.substring(0, 50) + "..."
                : agenda.materials_url}
            </a>
            {agenda.materials_summary && (
              <div className="mt-2 p-3 bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700">
                <h6 className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">要約</h6>
                <div className="text-sm text-surface-600 dark:text-surface-300 whitespace-pre-wrap">
                  {agenda.materials_summary}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Minutes Section */}
      <section className="bg-surface-50 dark:bg-surface-800/50 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ClipboardList className="w-5 h-5 text-emerald-500" />
            <h4 className="font-semibold text-surface-900 dark:text-surface-100">議事録</h4>
            <span
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs ${
                agenda.minutes_url
                  ? PROCESSING_STATUS_COLORS[agenda.minutes_processing_status] || "bg-gray-100 text-gray-700"
                  : "bg-surface-200 dark:bg-surface-700 text-surface-500"
              }`}
            >
              {agenda.minutes_url
                ? PROCESSING_STATUS_LABELS[agenda.minutes_processing_status] || agenda.minutes_processing_status
                : "URL未設定"}
            </span>
          </div>
          {agenda.minutes_url && agenda.minutes_processing_status === "completed" && (
            <button
              onClick={handleRegenerateMinutes}
              disabled={regeneratingMinutes}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-surface-600 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors disabled:opacity-50"
            >
              {regeneratingMinutes ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              再生成
            </button>
          )}
        </div>

        {agenda.minutes_url && (
          <a
            href={agenda.minutes_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
          >
            <ExternalLink className="w-4 h-4" />
            {agenda.minutes_url.length > 60
              ? agenda.minutes_url.substring(0, 60) + "..."
              : agenda.minutes_url}
          </a>
        )}

        {/* Minutes Summary */}
        {agenda.minutes_summary && (
          <div className="bg-white dark:bg-surface-800 rounded-lg p-4 border border-surface-200 dark:border-surface-700">
            <h5 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">要約</h5>
            <div className="text-sm text-surface-600 dark:text-surface-400 whitespace-pre-wrap">
              {agenda.minutes_summary}
            </div>
          </div>
        )}

        {/* Minutes Text (collapsible) */}
        {agenda.minutes_text && (
          <div>
            <button
              onClick={() => setShowMinutesText(!showMinutesText)}
              className="inline-flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-300 transition-colors"
            >
              {showMinutesText ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
              {showMinutesText ? "元テキストを隠す" : "元テキストを表示"}
            </button>
            {showMinutesText && (
              <div className="mt-3 bg-white dark:bg-surface-800 rounded-lg p-4 border border-surface-200 dark:border-surface-700 max-h-96 overflow-y-auto">
                <pre className="text-sm text-surface-600 dark:text-surface-400 whitespace-pre-wrap font-sans">
                  {agenda.minutes_text}
                </pre>
              </div>
            )}
          </div>
        )}

        {!agenda.minutes_url && (
          <p className="text-sm text-surface-500 dark:text-surface-400 italic">
            議事録URLが設定されていません。議題を編集してURLを追加してください。
          </p>
        )}
      </section>
    </div>
  );
}
