"use client";

import { useState, useEffect } from "react";
import { Loader2, FileText, Palette } from "lucide-react";
import { Button } from "../ui/Button";
import {
  getTemplates,
  getStyles,
  Template,
  Style,
  CreateProjectRequest,
} from "../../lib/slideGeneratorApi";

interface SlideInputFormProps {
  onSubmit: (request: CreateProjectRequest) => void;
  loading?: boolean;
}

export function SlideInputForm({ onSubmit, loading = false }: SlideInputFormProps) {
  const [title, setTitle] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [targetSlideCount, setTargetSlideCount] = useState<number | undefined>();
  const [keyPoints, setKeyPoints] = useState("");
  const [templateId, setTemplateId] = useState<string | undefined>();
  const [styleId, setStyleId] = useState<string | undefined>();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [styles, setStyles] = useState<Style[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    // Load templates and styles
    const loadOptions = async () => {
      try {
        const [templatesRes, stylesRes] = await Promise.all([
          getTemplates(),
          getStyles(),
        ]);
        setTemplates(templatesRes.items);
        setStyles(stylesRes.items);

        // Set default style if available
        const defaultStyle = stylesRes.items.find((s) => s.is_default);
        if (defaultStyle) {
          setStyleId(defaultStyle.id);
        }
      } catch (err) {
        console.error("Failed to load templates/styles:", err);
      }
    };
    loadOptions();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !sourceText.trim()) return;

    onSubmit({
      title: title.trim(),
      source_text: sourceText.trim(),
      target_slide_count: targetSlideCount,
      key_points: keyPoints.trim() || undefined,
      template_id: templateId,
      style_id: styleId,
    });
  };

  const isValid = title.trim() && sourceText.trim();

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
          タイトル <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="プレゼンテーションのタイトル"
          className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                     bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                     placeholder:text-surface-400 dark:placeholder:text-surface-500
                     focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                     transition-all duration-200"
          disabled={loading}
        />
      </div>

      {/* Source text */}
      <div>
        <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
          資料内容 <span className="text-red-500">*</span>
        </label>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          placeholder="スライドにしたい内容を入力してください。文章、箇条書き、メモなど形式は問いません。"
          rows={8}
          className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                     bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                     placeholder:text-surface-400 dark:placeholder:text-surface-500
                     focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                     transition-all duration-200 resize-y"
          disabled={loading}
        />
        <p className="mt-1 text-xs text-surface-500">
          {sourceText.length}文字
        </p>
      </div>

      {/* Advanced options toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
      >
        {showAdvanced ? "▼ 詳細オプションを閉じる" : "▶ 詳細オプションを開く"}
      </button>

      {showAdvanced && (
        <div className="space-y-4 p-4 border border-surface-200 dark:border-surface-700 rounded-xl bg-surface-50 dark:bg-surface-800/50">
          {/* Slide count */}
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              目標スライド枚数（任意）
            </label>
            <input
              type="number"
              value={targetSlideCount ?? ""}
              onChange={(e) => setTargetSlideCount(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="例: 10"
              min={1}
              max={50}
              className="w-32 px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                         bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                         placeholder:text-surface-400 dark:placeholder:text-surface-500
                         focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                         transition-all duration-200"
              disabled={loading}
            />
          </div>

          {/* Key points */}
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              重点ポイント（任意）
            </label>
            <textarea
              value={keyPoints}
              onChange={(e) => setKeyPoints(e.target.value)}
              placeholder="特に強調したいポイントや含めたい内容があれば入力してください"
              rows={3}
              className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                         bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                         placeholder:text-surface-400 dark:placeholder:text-surface-500
                         focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                         transition-all duration-200 resize-y"
              disabled={loading}
            />
          </div>

          {/* Template selection */}
          {templates.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                <FileText className="w-4 h-4 inline mr-1" />
                テンプレート（任意）
              </label>
              <select
                value={templateId ?? ""}
                onChange={(e) => setTemplateId(e.target.value || undefined)}
                className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                           bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                           transition-all duration-200"
                disabled={loading}
              >
                <option value="">デフォルト</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.slide_count}枚)
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Style selection */}
          {styles.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                <Palette className="w-4 h-4 inline mr-1" />
                スタイル（任意）
              </label>
              <select
                value={styleId ?? ""}
                onChange={(e) => setStyleId(e.target.value || undefined)}
                className="w-full px-4 py-2.5 text-sm border border-surface-200 dark:border-surface-700 rounded-xl
                           bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100
                           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                           transition-all duration-200"
                disabled={loading}
              >
                <option value="">デフォルト</option>
                {styles.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} {s.is_default && "(デフォルト)"}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Submit button */}
      <Button
        type="submit"
        variant="primary"
        disabled={!isValid || loading}
        leftIcon={loading ? <Loader2 className="w-4 h-4 animate-spin" /> : undefined}
        className="w-full"
      >
        {loading ? "生成中..." : "スライドを生成"}
      </Button>
    </form>
  );
}
