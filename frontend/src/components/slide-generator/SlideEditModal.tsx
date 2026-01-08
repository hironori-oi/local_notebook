"use client";

import { useState } from "react";
import { X, Plus, Trash2, Loader2 } from "lucide-react";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { Slide, SlideContent, updateSlide, SLIDE_TYPE_LABELS } from "../../lib/slideGeneratorApi";

interface SlideEditModalProps {
  projectId: string;
  slide: Slide;
  onClose: () => void;
  onUpdate: (updatedSlide: Slide) => void;
}

export function SlideEditModal({ projectId, slide, onClose, onUpdate }: SlideEditModalProps) {
  const [title, setTitle] = useState(slide.title);
  const [slideType, setSlideType] = useState(slide.slide_type);
  const [subtitle, setSubtitle] = useState(slide.content.subtitle || "");
  const [bullets, setBullets] = useState<string[]>(slide.content.bullets || []);
  const [details, setDetails] = useState(slide.content.details || "");
  const [speakerNotes, setSpeakerNotes] = useState(slide.speaker_notes || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddBullet = () => {
    setBullets([...bullets, ""]);
  };

  const handleRemoveBullet = (index: number) => {
    setBullets(bullets.filter((_, i) => i !== index));
  };

  const handleBulletChange = (index: number, value: string) => {
    const newBullets = [...bullets];
    newBullets[index] = value;
    setBullets(newBullets);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const content: SlideContent = {
        bullets: bullets.filter((b) => b.trim()),
        subtitle: subtitle.trim() || undefined,
        details: details.trim() || undefined,
      };

      const updated = await updateSlide(projectId, slide.slide_number, {
        title: title.trim(),
        slide_type: slideType,
        content,
        speaker_notes: speakerNotes.trim() || undefined,
      });

      onUpdate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen onClose={onClose} title={`スライド ${slide.slide_number} を編集`}>
      <div className="space-y-4 max-h-[70vh] overflow-y-auto">
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Slide type */}
        <div>
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
            スライドタイプ
          </label>
          <select
            value={slideType}
            onChange={(e) => setSlideType(e.target.value as Slide["slide_type"])}
            className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                       bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                       transition-all duration-200"
          >
            {Object.entries(SLIDE_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
            タイトル
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                       bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                       transition-all duration-200"
          />
        </div>

        {/* Subtitle */}
        <div>
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
            サブタイトル（任意）
          </label>
          <input
            type="text"
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
            placeholder="サブタイトルを入力"
            className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                       bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                       placeholder:text-surface-400 dark:placeholder:text-surface-500
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                       transition-all duration-200"
          />
        </div>

        {/* Bullets */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">
              箇条書き項目
            </label>
            <button
              type="button"
              onClick={handleAddBullet}
              className="flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 hover:underline"
            >
              <Plus className="w-3 h-3" />
              項目を追加
            </button>
          </div>
          <div className="space-y-2">
            {bullets.map((bullet, index) => (
              <div key={index} className="flex gap-2">
                <span className="text-surface-400 pt-2">•</span>
                <input
                  type="text"
                  value={bullet}
                  onChange={(e) => handleBulletChange(index, e.target.value)}
                  placeholder={`項目 ${index + 1}`}
                  className="flex-1 px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                             bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                             placeholder:text-surface-400 dark:placeholder:text-surface-500
                             focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                             transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveBullet(index)}
                  className="p-2 text-surface-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {bullets.length === 0 && (
              <p className="text-sm text-surface-500 py-2">
                項目がありません。「項目を追加」をクリックして追加してください。
              </p>
            )}
          </div>
        </div>

        {/* Details */}
        <div>
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
            詳細説明（任意）
          </label>
          <textarea
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            placeholder="追加の説明文を入力"
            rows={2}
            className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                       bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                       placeholder:text-surface-400 dark:placeholder:text-surface-500
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                       transition-all duration-200 resize-y"
          />
        </div>

        {/* Speaker notes */}
        <div>
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
            スピーカーノート（任意）
          </label>
          <textarea
            value={speakerNotes}
            onChange={(e) => setSpeakerNotes(e.target.value)}
            placeholder="発表時のメモを入力"
            rows={3}
            className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                       bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                       placeholder:text-surface-400 dark:placeholder:text-surface-500
                       focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                       transition-all duration-200 resize-y"
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-surface-200 dark:border-surface-700">
        <Button variant="secondary" onClick={onClose} disabled={saving}>
          キャンセル
        </Button>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={saving || !title.trim()}
          leftIcon={saving ? <Loader2 className="w-4 h-4 animate-spin" /> : undefined}
        >
          {saving ? "保存中..." : "保存"}
        </Button>
      </div>
    </Modal>
  );
}
