"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Settings,
  Save,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  Zap,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowLeft,
  Server,
  Brain,
  MessageSquare,
  FileText,
  Mail,
  LayoutGrid,
  FileCode,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { isAuthenticated } from "../../lib/apiClient";
import {
  getLLMSettings,
  updateLLMSettings,
  testLLMConnection,
  getAvailableModels,
  resetLLMSettings,
  getDefaultPrompts,
  updatePrompts,
  resetPrompts,
  LLMSettings,
  LLMSettingsUpdate,
  ModelInfo,
  FEATURE_LABELS,
  PROVIDER_OPTIONS,
  PROMPT_LABELS,
  PROMPT_CATEGORIES,
  FeatureSettings,
  PromptSettings,
  DefaultPrompts,
} from "../../lib/llmSettingsApi";

type FeatureKey = keyof FeatureSettings;

const FEATURE_ICONS: Record<FeatureKey, React.ReactNode> = {
  chat: <MessageSquare className="w-4 h-4" />,
  format: <FileText className="w-4 h-4" />,
  summary: <FileText className="w-4 h-4" />,
  email: <Mail className="w-4 h-4" />,
  infographic: <LayoutGrid className="w-4 h-4" />,
};

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // Settings state
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // Form state
  const [provider, setProvider] = useState("ollama");
  const [apiBaseUrl, setApiBaseUrl] = useState("http://localhost:11434/v1");
  const [apiKey, setApiKey] = useState("");
  const [defaultModel, setDefaultModel] = useState("gpt-oss-120b");
  const [embeddingModel, setEmbeddingModel] = useState("embeddinggemma:300m");
  const [embeddingApiBase, setEmbeddingApiBase] = useState(
    "http://localhost:11434/v1"
  );
  const [embeddingDim, setEmbeddingDim] = useState(768);
  const [featureSettings, setFeatureSettings] = useState<FeatureSettings>({
    chat: { model: null, temperature: 0.1, max_tokens: 4096 },
    format: { model: null, temperature: 0.1, max_tokens: 8192 },
    summary: { model: null, temperature: 0.2, max_tokens: 8192 },
    email: { model: null, temperature: 0.3, max_tokens: 8192 },
    infographic: { model: null, temperature: 0.3, max_tokens: 8192 },
  });

  // Prompt settings state
  const [promptSettings, setPromptSettings] = useState<PromptSettings>({
    council_materials_system: null,
    council_materials_user: null,
    council_minutes_system: null,
    council_minutes_user: null,
    email_system: null,
    email_user: null,
    infographic_system: null,
    infographic_user: null,
    council_infographic_system: null,
    council_infographic_user: null,
    format_system: null,
    format_user: null,
    minute_format_system: null,
    minute_format_user: null,
    summary_system: null,
    summary_user: null,
    minute_summary_system: null,
    minute_summary_user: null,
    document_check_system: null,
    document_check_user: null,
    slide_generation_system: null,
    slide_generation_user: null,
    slide_refinement_system: null,
    slide_refinement_user: null,
  });
  const [defaultPrompts, setDefaultPrompts] = useState<DefaultPrompts | null>(null);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [promptsSaving, setPromptsSaving] = useState(false);
  const [showDefaultPrompts, setShowDefaultPrompts] = useState<Set<keyof PromptSettings>>(new Set());

  // UI state
  const [expandedFeatures, setExpandedFeatures] = useState<Set<FeatureKey>>(
    new Set()
  );
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set()
  );
  const [expandedPrompts, setExpandedPrompts] = useState<Set<keyof PromptSettings>>(
    new Set()
  );

  // Check auth and load settings
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadSettings();
  }, [router]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [data, defaults] = await Promise.all([
        getLLMSettings(),
        getDefaultPrompts(),
      ]);
      setSettings(data);
      setDefaultPrompts(defaults);

      // Update form state
      setProvider(data.provider);
      setApiBaseUrl(data.api_base_url);
      setDefaultModel(data.default_model);
      setEmbeddingModel(data.embedding_model);
      setEmbeddingApiBase(data.embedding_api_base);
      setEmbeddingDim(data.embedding_dim);
      setFeatureSettings(data.feature_settings);
      setPromptSettings(data.prompt_settings || {
        council_materials_system: null,
        council_materials_user: null,
        council_minutes_system: null,
        council_minutes_user: null,
        email_system: null,
        email_user: null,
        infographic_system: null,
        infographic_user: null,
        council_infographic_system: null,
        council_infographic_user: null,
        format_system: null,
        format_user: null,
        minute_format_system: null,
        minute_format_user: null,
        summary_system: null,
        summary_user: null,
        minute_summary_system: null,
        minute_summary_user: null,
        document_check_system: null,
        document_check_user: null,
        slide_generation_system: null,
        slide_generation_user: null,
        slide_refinement_system: null,
        slide_refinement_user: null,
      });
    } catch (error) {
      console.error("Failed to load settings:", error);
      alert("設定の読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const loadModels = useCallback(async () => {
    try {
      setModelsLoading(true);
      const data = await getAvailableModels();
      setAvailableModels(data.models);
    } catch (error) {
      console.error("Failed to load models:", error);
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (settings) {
      loadModels();
    }
  }, [settings, loadModels]);

  const handleSave = async () => {
    try {
      setSaving(true);
      const updateData: LLMSettingsUpdate = {
        provider,
        api_base_url: apiBaseUrl,
        default_model: defaultModel,
        embedding_model: embeddingModel,
        embedding_api_base: embeddingApiBase,
        embedding_dim: embeddingDim,
        feature_settings: featureSettings,
      };

      if (apiKey) {
        updateData.api_key = apiKey;
      }

      const updated = await updateLLMSettings(updateData);
      setSettings(updated);
      setApiKey(""); // Clear API key field
      alert("設定を保存しました");
    } catch (error) {
      console.error("Failed to save settings:", error);
      alert("設定の保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      const result = await testLLMConnection({
        provider,
        api_base_url: apiBaseUrl,
        api_key: apiKey || undefined,
        model: defaultModel,
      });
      setTestResult({
        success: result.success,
        message: result.success
          ? `接続成功 (${result.response_time_ms}ms)`
          : result.message,
      });
    } catch (error) {
      setTestResult({
        success: false,
        message:
          error instanceof Error ? error.message : "接続テストに失敗しました",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("設定をシステムデフォルトにリセットしますか？")) {
      return;
    }
    try {
      setSaving(true);
      const reset = await resetLLMSettings();
      setSettings(reset);
      setProvider(reset.provider);
      setApiBaseUrl(reset.api_base_url);
      setDefaultModel(reset.default_model);
      setEmbeddingModel(reset.embedding_model);
      setEmbeddingApiBase(reset.embedding_api_base);
      setEmbeddingDim(reset.embedding_dim);
      setFeatureSettings(reset.feature_settings);
      setApiKey("");
      alert("設定をリセットしました");
    } catch (error) {
      console.error("Failed to reset settings:", error);
      alert("設定のリセットに失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const toggleFeature = (feature: FeatureKey) => {
    setExpandedFeatures((prev) => {
      const next = new Set(prev);
      if (next.has(feature)) {
        next.delete(feature);
      } else {
        next.add(feature);
      }
      return next;
    });
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const togglePrompt = (prompt: keyof PromptSettings) => {
    setExpandedPrompts((prev) => {
      const next = new Set(prev);
      if (next.has(prompt)) {
        next.delete(prompt);
      } else {
        next.add(prompt);
      }
      return next;
    });
  };

  const hasCustomPromptInCategory = (categoryKey: string): boolean => {
    const category = PROMPT_CATEGORIES[categoryKey];
    if (!category) return false;
    return category.keys.some((key) => promptSettings[key] !== null);
  };

  const toggleShowDefaultPrompt = (prompt: keyof PromptSettings) => {
    setShowDefaultPrompts((prev) => {
      const next = new Set(prev);
      if (next.has(prompt)) {
        next.delete(prompt);
      } else {
        next.add(prompt);
      }
      return next;
    });
  };

  const updatePromptSetting = (
    key: keyof PromptSettings,
    value: string | null
  ) => {
    setPromptSettings((prev) => ({
      ...prev,
      [key]: value === "" ? null : value,
    }));
  };

  const handleSavePrompts = async () => {
    try {
      setPromptsSaving(true);
      const updated = await updatePrompts(promptSettings);
      setSettings(updated);
      setPromptSettings(updated.prompt_settings);
      alert("プロンプト設定を保存しました");
    } catch (error) {
      console.error("Failed to save prompts:", error);
      alert("プロンプト設定の保存に失敗しました");
    } finally {
      setPromptsSaving(false);
    }
  };

  const handleResetPrompts = async () => {
    if (!confirm("プロンプト設定をデフォルトにリセットしますか？")) {
      return;
    }
    try {
      setPromptsSaving(true);
      const updated = await resetPrompts();
      setSettings(updated);
      setPromptSettings(updated.prompt_settings);
      alert("プロンプト設定をリセットしました");
    } catch (error) {
      console.error("Failed to reset prompts:", error);
      alert("プロンプト設定のリセットに失敗しました");
    } finally {
      setPromptsSaving(false);
    }
  };

  const updateFeatureSetting = (
    feature: FeatureKey,
    key: "model" | "temperature" | "max_tokens",
    value: string | number | null
  ) => {
    setFeatureSettings((prev) => ({
      ...prev,
      [feature]: {
        ...prev[feature],
        [key]: value,
      },
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-50 dark:bg-surface-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-900">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-surface-800/80 backdrop-blur-xl border-b border-surface-200 dark:border-surface-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-surface-600 dark:text-surface-400" />
            </button>
            <div className="flex items-center gap-2">
              <Settings className="w-6 h-6 text-primary-500" />
              <h1 className="text-xl font-bold text-surface-900 dark:text-surface-100">
                LLM設定
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={handleReset} disabled={saving}>
              <RotateCcw className="w-4 h-4 mr-2" />
              リセット
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              isLoading={saving}
              leftIcon={<Save className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Basic Settings */}
        <section className="bg-white dark:bg-surface-800 rounded-2xl p-6 shadow-soft">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              基本設定
            </h2>
          </div>

          <div className="grid gap-4">
            {/* Provider */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                プロバイダー
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {PROVIDER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* API Base URL */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                APIベースURL
              </label>
              <Input
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                placeholder="http://localhost:11434/v1"
              />
            </div>

            {/* API Key */}
            {(provider === "openai" || provider === "anthropic") && (
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                  APIキー
                  {settings?.has_api_key && (
                    <span className="ml-2 text-xs text-green-600">
                      (設定済み)
                    </span>
                  )}
                </label>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                />
                <p className="mt-1 text-xs text-surface-500">
                  空欄で保存すると既存のキーを維持します
                </p>
              </div>
            )}

            {/* Default Model */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                デフォルトモデル
              </label>
              <div className="flex gap-2">
                <select
                  value={defaultModel}
                  onChange={(e) => setDefaultModel(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {availableModels.length > 0 ? (
                    availableModels.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name}
                        {model.size ? ` (${model.size})` : ""}
                      </option>
                    ))
                  ) : (
                    <option value={defaultModel}>{defaultModel}</option>
                  )}
                </select>
                <Button
                  variant="secondary"
                  onClick={loadModels}
                  disabled={modelsLoading}
                  className="shrink-0"
                >
                  {modelsLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "更新"
                  )}
                </Button>
              </div>
            </div>

            {/* Connection Test */}
            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="secondary"
                onClick={handleTestConnection}
                disabled={testing}
                leftIcon={
                  testing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4" />
                  )
                }
              >
                接続テスト
              </Button>
              {testResult && (
                <div
                  className={`flex items-center gap-2 text-sm ${
                    testResult.success ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {testResult.success ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <XCircle className="w-4 h-4" />
                  )}
                  {testResult.message}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Embedding Settings */}
        <section className="bg-white dark:bg-surface-800 rounded-2xl p-6 shadow-soft">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              埋め込みモデル設定
            </h2>
          </div>

          <div className="grid gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                埋め込みモデル
              </label>
              <Input
                value={embeddingModel}
                onChange={(e) => setEmbeddingModel(e.target.value)}
                placeholder="embeddinggemma:300m"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                埋め込みAPIベースURL
              </label>
              <Input
                value={embeddingApiBase}
                onChange={(e) => setEmbeddingApiBase(e.target.value)}
                placeholder="http://localhost:11434/v1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                埋め込み次元数
              </label>
              <Input
                type="number"
                value={embeddingDim}
                onChange={(e) => setEmbeddingDim(parseInt(e.target.value) || 768)}
                min={1}
                max={4096}
              />
            </div>
          </div>
        </section>

        {/* Feature Settings */}
        <section className="bg-white dark:bg-surface-800 rounded-2xl p-6 shadow-soft">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              機能別設定
            </h2>
          </div>

          <div className="space-y-2">
            {(Object.keys(FEATURE_LABELS) as FeatureKey[]).map((feature) => (
              <div
                key={feature}
                className="border border-surface-200 dark:border-surface-700 rounded-xl overflow-hidden"
              >
                {/* Feature Header */}
                <button
                  onClick={() => toggleFeature(feature)}
                  className="w-full px-4 py-3 flex items-center justify-between bg-surface-50 dark:bg-surface-700/50 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-primary-500">
                      {FEATURE_ICONS[feature]}
                    </span>
                    <span className="font-medium text-surface-900 dark:text-surface-100">
                      {FEATURE_LABELS[feature]}
                    </span>
                  </div>
                  {expandedFeatures.has(feature) ? (
                    <ChevronDown className="w-5 h-5 text-surface-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-surface-400" />
                  )}
                </button>

                {/* Feature Settings */}
                {expandedFeatures.has(feature) && (
                  <div className="px-4 py-4 space-y-4 bg-white dark:bg-surface-800">
                    {/* Model */}
                    <div>
                      <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                        モデル
                      </label>
                      <select
                        value={featureSettings[feature].model || ""}
                        onChange={(e) =>
                          updateFeatureSetting(
                            feature,
                            "model",
                            e.target.value || null
                          )
                        }
                        className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="">デフォルトを使用</option>
                        {availableModels.map((model) => (
                          <option key={model.name} value={model.name}>
                            {model.name}
                            {model.size ? ` (${model.size})` : ""}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Temperature */}
                    <div>
                      <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                        Temperature: {featureSettings[feature].temperature}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={featureSettings[feature].temperature}
                        onChange={(e) =>
                          updateFeatureSetting(
                            feature,
                            "temperature",
                            parseFloat(e.target.value)
                          )
                        }
                        className="w-full h-2 bg-surface-200 dark:bg-surface-600 rounded-lg appearance-none cursor-pointer accent-primary-500"
                      />
                      <div className="flex justify-between text-xs text-surface-500 mt-1">
                        <span>正確 (0.0)</span>
                        <span>創造的 (1.0)</span>
                      </div>
                    </div>

                    {/* Max Tokens */}
                    <div>
                      <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                        最大トークン数
                      </label>
                      <Input
                        type="number"
                        value={featureSettings[feature].max_tokens}
                        onChange={(e) =>
                          updateFeatureSetting(
                            feature,
                            "max_tokens",
                            parseInt(e.target.value) || 4096
                          )
                        }
                        min={100}
                        max={32768}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Prompt Settings */}
        <section className="bg-white dark:bg-surface-800 rounded-2xl p-6 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                プロンプト設定
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetPrompts}
                disabled={promptsSaving}
              >
                <RotateCcw className="w-4 h-4 mr-1" />
                リセット
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSavePrompts}
                isLoading={promptsSaving}
                leftIcon={<Save className="w-4 h-4" />}
              >
                保存
              </Button>
            </div>
          </div>

          <p className="text-sm text-surface-600 dark:text-surface-400 mb-4">
            各機能で使用するプロンプトをカスタマイズできます。
            空欄の場合はデフォルトプロンプトが使用されます。
          </p>

          <div className="space-y-3">
            {Object.entries(PROMPT_CATEGORIES).map(([categoryKey, category]) => (
              <div
                key={categoryKey}
                className="border border-surface-200 dark:border-surface-700 rounded-xl overflow-hidden"
              >
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(categoryKey)}
                  className="w-full px-4 py-3 flex items-center justify-between bg-surface-50 dark:bg-surface-700/50 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileCode className="w-4 h-4 text-primary-500" />
                    <span className="font-medium text-surface-900 dark:text-surface-100">
                      {category.label}
                    </span>
                    {hasCustomPromptInCategory(categoryKey) && (
                      <span className="text-xs text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30 px-2 py-0.5 rounded">
                        カスタム
                      </span>
                    )}
                  </div>
                  {expandedCategories.has(categoryKey) ? (
                    <ChevronDown className="w-5 h-5 text-surface-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-surface-400" />
                  )}
                </button>

                {/* Category Content */}
                {expandedCategories.has(categoryKey) && (
                  <div className="px-4 py-4 space-y-4 bg-white dark:bg-surface-800">
                    {category.keys.map((promptKey) => (
                      <div key={promptKey} className="border border-surface-100 dark:border-surface-700 rounded-lg overflow-hidden">
                        {/* Prompt Header */}
                        <button
                          onClick={() => togglePrompt(promptKey)}
                          className="w-full px-3 py-2 flex items-center justify-between bg-surface-50/50 dark:bg-surface-700/30 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-surface-700 dark:text-surface-300">
                              {PROMPT_LABELS[promptKey]}
                            </span>
                            {promptSettings[promptKey] && (
                              <span className="text-xs text-green-600 dark:text-green-400">
                                ●
                              </span>
                            )}
                          </div>
                          {expandedPrompts.has(promptKey) ? (
                            <ChevronDown className="w-4 h-4 text-surface-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-surface-400" />
                          )}
                        </button>

                        {/* Prompt Editor */}
                        {expandedPrompts.has(promptKey) && (
                          <div className="px-3 py-3 space-y-3 bg-white dark:bg-surface-800">
                            {/* Show/hide default prompt */}
                            <div className="flex items-center justify-between">
                              <button
                                onClick={() => toggleShowDefaultPrompt(promptKey)}
                                className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                              >
                                {showDefaultPrompts.has(promptKey) ? (
                                  <>
                                    <EyeOff className="w-3 h-3" />
                                    デフォルトを非表示
                                  </>
                                ) : (
                                  <>
                                    <Eye className="w-3 h-3" />
                                    デフォルトを表示
                                  </>
                                )}
                              </button>
                              {promptSettings[promptKey] && (
                                <button
                                  onClick={() => updatePromptSetting(promptKey, null)}
                                  className="text-xs text-red-600 dark:text-red-400 hover:underline"
                                >
                                  クリア
                                </button>
                              )}
                            </div>

                            {/* Default prompt display */}
                            {showDefaultPrompts.has(promptKey) && defaultPrompts && (
                              <div className="bg-surface-50 dark:bg-surface-700/50 rounded-lg p-2">
                                <pre className="text-xs text-surface-700 dark:text-surface-300 whitespace-pre-wrap font-mono max-h-40 overflow-y-auto">
                                  {defaultPrompts[promptKey]}
                                </pre>
                              </div>
                            )}

                            {/* Custom prompt textarea */}
                            <div>
                              <textarea
                                value={promptSettings[promptKey] || ""}
                                onChange={(e) => updatePromptSetting(promptKey, e.target.value)}
                                placeholder="カスタムプロンプトを入力..."
                                className="w-full px-2 py-2 rounded-lg border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-xs min-h-[100px] resize-y"
                              />
                              <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
                                {promptKey.includes("user")
                                  ? "ユーザープロンプトには {text} などのプレースホルダーを含めてください"
                                  : "システムプロンプトはLLMの基本的な動作を定義します"}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
