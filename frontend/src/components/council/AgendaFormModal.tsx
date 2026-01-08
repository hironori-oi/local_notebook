"use client";

import { useState, useEffect } from "react";
import { X, ListOrdered, FileText, ClipboardList, Loader2, Plus, Trash2 } from "lucide-react";
import {
  CouncilAgendaItem,
  CouncilAgendaCreate,
  CouncilAgendaUpdate,
  CouncilAgendaMaterialCreate,
  createAgenda,
  updateAgenda,
} from "../../lib/councilApi";
import { Modal } from "../ui/Modal";

interface MaterialFormItem {
  id: string; // for React key
  material_number: number;
  title: string;
  url: string;
}

interface AgendaFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (agenda: CouncilAgendaItem) => void;
  meetingId: string;
  agenda?: CouncilAgendaItem; // If provided, edit mode
  nextAgendaNumber?: number; // Suggested number for new agenda
}

export function AgendaFormModal({
  isOpen,
  onClose,
  onSuccess,
  meetingId,
  agenda,
  nextAgendaNumber = 1,
}: AgendaFormModalProps) {
  const isEditMode = !!agenda;

  const [agendaNumber, setAgendaNumber] = useState(agenda?.agenda_number || nextAgendaNumber);
  const [title, setTitle] = useState(agenda?.title || "");
  const [materialsUrl, setMaterialsUrl] = useState(agenda?.materials_url || "");
  const [minutesUrl, setMinutesUrl] = useState(agenda?.minutes_url || "");
  const [materials, setMaterials] = useState<MaterialFormItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens/closes or agenda changes
  useEffect(() => {
    if (isOpen) {
      setAgendaNumber(agenda?.agenda_number || nextAgendaNumber);
      setTitle(agenda?.title || "");
      setMaterialsUrl(agenda?.materials_url || "");
      setMinutesUrl(agenda?.minutes_url || "");
      // Initialize materials from agenda if editing
      if (agenda?.materials && agenda.materials.length > 0) {
        setMaterials(
          agenda.materials.map((m) => ({
            id: m.id,
            material_number: m.material_number,
            title: m.title || "",
            url: m.url,
          }))
        );
      } else {
        setMaterials([]);
      }
      setError(null);
    }
  }, [isOpen, agenda, nextAgendaNumber]);

  const addMaterial = () => {
    const nextNumber = materials.length > 0
      ? Math.max(...materials.map((m) => m.material_number)) + 1
      : 1;
    setMaterials([
      ...materials,
      {
        id: `new-${Date.now()}`,
        material_number: nextNumber,
        title: "",
        url: "",
      },
    ]);
  };

  const removeMaterial = (id: string) => {
    setMaterials(materials.filter((m) => m.id !== id));
  };

  const updateMaterial = (id: string, field: keyof MaterialFormItem, value: string | number) => {
    setMaterials(
      materials.map((m) => (m.id === id ? { ...m, [field]: value } : m))
    );
  };

  const validateUrl = (url: string): boolean => {
    if (!url) return true; // Empty is valid
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!agendaNumber || agendaNumber < 1) {
      setError("議題番号は1以上の数値を入力してください");
      return;
    }

    if (materialsUrl && !validateUrl(materialsUrl)) {
      setError("資料URLの形式が正しくありません");
      return;
    }

    if (minutesUrl && !validateUrl(minutesUrl)) {
      setError("議事録URLの形式が正しくありません");
      return;
    }

    // Validate materials
    for (const mat of materials) {
      if (!mat.url) {
        setError(`資料${mat.material_number}のURLを入力してください`);
        return;
      }
      if (!validateUrl(mat.url)) {
        setError(`資料${mat.material_number}のURLの形式が正しくありません`);
        return;
      }
    }

    setIsSubmitting(true);

    try {
      let result: CouncilAgendaItem;

      if (isEditMode && agenda) {
        // Note: When editing, materials need to be managed separately via the material API
        const updateData: CouncilAgendaUpdate = {};
        if (agendaNumber !== agenda.agenda_number) {
          updateData.agenda_number = agendaNumber;
        }
        if (title !== agenda.title) {
          updateData.title = title || undefined;
        }
        if (materialsUrl !== agenda.materials_url) {
          updateData.materials_url = materialsUrl || undefined;
        }
        if (minutesUrl !== agenda.minutes_url) {
          updateData.minutes_url = minutesUrl || undefined;
        }
        result = await updateAgenda(agenda.id, updateData);
      } else {
        // For new agendas, include materials in the create request
        const createMaterials: CouncilAgendaMaterialCreate[] = materials
          .filter((m) => m.url)
          .map((m) => ({
            material_number: m.material_number,
            title: m.title || undefined,
            url: m.url,
          }));

        const createData: CouncilAgendaCreate = {
          agenda_number: agendaNumber,
          title: title || undefined,
          materials_url: materialsUrl || undefined,
          minutes_url: minutesUrl || undefined,
          materials: createMaterials.length > 0 ? createMaterials : undefined,
        };
        result = await createAgenda(meetingId, createData);
      }

      onSuccess(result);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-surface-900 dark:text-surface-100 flex items-center gap-2">
            <ListOrdered className="w-5 h-5" />
            {isEditMode ? "議題を編集" : "議題を追加"}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Agenda Number */}
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              議題番号 <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="1"
              value={agendaNumber}
              onChange={(e) => setAgendaNumber(parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 border border-surface-300 dark:border-surface-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-800 dark:text-surface-100"
              required
            />
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              議題タイトル
              <span className="text-surface-400 font-normal ml-1">(任意)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例: 電力需給見通しについて"
              className="w-full px-3 py-2 border border-surface-300 dark:border-surface-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-800 dark:text-surface-100"
            />
          </div>

          {/* Materials Section */}
          <div className="border border-surface-200 dark:border-surface-700 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-surface-700 dark:text-surface-300 flex items-center gap-1.5">
                <FileText className="w-4 h-4" />
                資料
                <span className="text-surface-400 font-normal ml-1">({materials.length}件)</span>
              </label>
              {!isEditMode && (
                <button
                  type="button"
                  onClick={addMaterial}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-primary-600 hover:text-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  追加
                </button>
              )}
            </div>

            {materials.length === 0 ? (
              <p className="text-sm text-surface-500 dark:text-surface-400 text-center py-2">
                {isEditMode
                  ? "資料は議題詳細画面から追加・編集できます"
                  : "「追加」ボタンで資料を追加できます"}
              </p>
            ) : (
              <div className="space-y-3">
                {materials.map((mat) => (
                  <div
                    key={mat.id}
                    className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-surface-500 dark:text-surface-400">
                        資料 {mat.material_number}
                      </span>
                      {!isEditMode && (
                        <button
                          type="button"
                          onClick={() => removeMaterial(mat.id)}
                          className="p-1 text-surface-400 hover:text-red-500 transition-colors"
                          title="削除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    <input
                      type="text"
                      value={mat.title}
                      onChange={(e) => updateMaterial(mat.id, "title", e.target.value)}
                      placeholder="資料タイトル（任意）"
                      className="w-full px-2 py-1.5 text-sm border border-surface-300 dark:border-surface-600 rounded focus:ring-1 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-700 dark:text-surface-100"
                      disabled={isEditMode}
                    />
                    <input
                      type="url"
                      value={mat.url}
                      onChange={(e) => updateMaterial(mat.id, "url", e.target.value)}
                      placeholder="https://www.example.go.jp/..."
                      className="w-full px-2 py-1.5 text-sm border border-surface-300 dark:border-surface-600 rounded focus:ring-1 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-700 dark:text-surface-100"
                      required
                      disabled={isEditMode}
                    />
                  </div>
                ))}
              </div>
            )}
            <p className="text-xs text-surface-500 dark:text-surface-400">
              PDF、HTML、テキストファイルに対応
            </p>
          </div>

          {/* Minutes URL */}
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1 flex items-center gap-1.5">
              <ClipboardList className="w-4 h-4" />
              議事録URL
              <span className="text-surface-400 font-normal ml-1">(任意)</span>
            </label>
            <input
              type="url"
              value={minutesUrl}
              onChange={(e) => setMinutesUrl(e.target.value)}
              placeholder="https://www.example.go.jp/..."
              className="w-full px-3 py-2 border border-surface-300 dark:border-surface-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-surface-800 dark:text-surface-100"
            />
            <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
              PDF、HTML、テキストファイルに対応しています
            </p>
          </div>

          {/* Info message */}
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              URLを設定すると、自動的に内容を取得し要約を生成します。
              URLは後から追加・変更することもできます。
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-surface-200 dark:border-surface-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 rounded-lg transition-colors"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {isEditMode ? "保存" : "追加"}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
