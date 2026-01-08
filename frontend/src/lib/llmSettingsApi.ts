/**
 * LLM Settings API client functions
 */

import { apiClient } from "./apiClient";

// Types
export interface FeatureSetting {
  model: string | null;
  temperature: number;
  max_tokens: number;
}

export interface FeatureSettings {
  chat: FeatureSetting;
  format: FeatureSetting;
  summary: FeatureSetting;
  email: FeatureSetting;
  infographic: FeatureSetting;
}

export interface PromptSettings {
  // Council content processing
  council_materials_system: string | null;
  council_materials_user: string | null;
  council_minutes_system: string | null;
  council_minutes_user: string | null;
  // Email generation
  email_system: string | null;
  email_user: string | null;
  // Infographic generation - Notebook
  infographic_system: string | null;
  infographic_user: string | null;
  // Infographic generation - Council
  council_infographic_system: string | null;
  council_infographic_user: string | null;
  // Document formatting
  format_system: string | null;
  format_user: string | null;
  // Minutes formatting
  minute_format_system: string | null;
  minute_format_user: string | null;
  // Document summary
  summary_system: string | null;
  summary_user: string | null;
  // Minutes summary
  minute_summary_system: string | null;
  minute_summary_user: string | null;
  // Document checker
  document_check_system: string | null;
  document_check_user: string | null;
  // Slide generation
  slide_generation_system: string | null;
  slide_generation_user: string | null;
  // Slide refinement
  slide_refinement_system: string | null;
  slide_refinement_user: string | null;
}

export interface LLMSettings {
  id: string;
  user_id: string | null;
  provider: string;
  api_base_url: string;
  has_api_key: boolean;
  default_model: string;
  embedding_model: string;
  embedding_api_base: string;
  embedding_dim: number;
  feature_settings: FeatureSettings;
  prompt_settings: PromptSettings;
  created_at: string;
  updated_at: string;
}

export interface DefaultPrompts {
  // Council content processing
  council_materials_system: string;
  council_materials_user: string;
  council_minutes_system: string;
  council_minutes_user: string;
  // Email generation
  email_system: string;
  email_user: string;
  // Infographic generation - Notebook
  infographic_system: string;
  infographic_user: string;
  // Infographic generation - Council
  council_infographic_system: string;
  council_infographic_user: string;
  // Document formatting
  format_system: string;
  format_user: string;
  // Minutes formatting
  minute_format_system: string;
  minute_format_user: string;
  // Document summary
  summary_system: string;
  summary_user: string;
  // Minutes summary
  minute_summary_system: string;
  minute_summary_user: string;
  // Document checker
  document_check_system: string;
  document_check_user: string;
  // Slide generation
  slide_generation_system: string;
  slide_generation_user: string;
  // Slide refinement
  slide_refinement_system: string;
  slide_refinement_user: string;
}

export interface LLMSettingsUpdate {
  provider?: string;
  api_base_url?: string;
  api_key?: string;
  default_model?: string;
  embedding_model?: string;
  embedding_api_base?: string;
  embedding_dim?: number;
  feature_settings?: Partial<{
    [K in keyof FeatureSettings]: Partial<FeatureSetting>;
  }>;
}

export interface ConnectionTestRequest {
  provider: string;
  api_base_url: string;
  api_key?: string;
  model: string;
}

export interface ConnectionTestResponse {
  success: boolean;
  message: string;
  response_time_ms?: number;
  model_info?: Record<string, unknown>;
  error_detail?: string;
}

export interface ModelInfo {
  name: string;
  size?: string;
  family?: string;
  modified_at?: string;
}

export interface ModelsListResponse {
  models: ModelInfo[];
  provider: string;
}

/**
 * Get current user's LLM settings
 */
export async function getLLMSettings(): Promise<LLMSettings> {
  const res = await apiClient("/api/v1/settings/llm");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch LLM settings");
  }
  return res.json();
}

/**
 * Update LLM settings
 */
export async function updateLLMSettings(
  data: LLMSettingsUpdate
): Promise<LLMSettings> {
  const res = await apiClient("/api/v1/settings/llm", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update LLM settings");
  }
  return res.json();
}

/**
 * Test LLM connection
 */
export async function testLLMConnection(
  data: ConnectionTestRequest
): Promise<ConnectionTestResponse> {
  const res = await apiClient("/api/v1/settings/llm/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to test connection");
  }
  return res.json();
}

/**
 * Get available models from LLM server
 */
export async function getAvailableModels(): Promise<ModelsListResponse> {
  const res = await apiClient("/api/v1/settings/llm/models");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch models");
  }
  return res.json();
}

/**
 * Get system default LLM settings
 */
export async function getDefaultLLMSettings(): Promise<LLMSettings> {
  const res = await apiClient("/api/v1/settings/llm/defaults");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch default settings");
  }
  return res.json();
}

/**
 * Reset LLM settings to system defaults
 */
export async function resetLLMSettings(): Promise<LLMSettings> {
  const res = await apiClient("/api/v1/settings/llm/reset", {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to reset settings");
  }
  return res.json();
}

// Feature labels for UI
export const FEATURE_LABELS: Record<keyof FeatureSettings, string> = {
  chat: "チャット（RAG）",
  format: "テキスト整形",
  summary: "要約生成",
  email: "メール生成",
  infographic: "インフォグラフィック",
};

// Provider labels
export const PROVIDER_OPTIONS = [
  { value: "ollama", label: "Ollama" },
  { value: "vllm", label: "vLLM" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
];

// Default feature settings for reference
export const DEFAULT_FEATURE_SETTINGS: FeatureSettings = {
  chat: { model: null, temperature: 0.1, max_tokens: 4096 },
  format: { model: null, temperature: 0.1, max_tokens: 8192 },
  summary: { model: null, temperature: 0.2, max_tokens: 8192 },
  email: { model: null, temperature: 0.3, max_tokens: 8192 },
  infographic: { model: null, temperature: 0.3, max_tokens: 8192 },
};

// Prompt labels for UI - grouped by category
export const PROMPT_LABELS: Record<keyof PromptSettings, string> = {
  // Council content processing
  council_materials_system: "審議会資料要約（システム）",
  council_materials_user: "審議会資料要約（ユーザー）",
  council_minutes_system: "審議会議事録要約（システム）",
  council_minutes_user: "審議会議事録要約（ユーザー）",
  // Email generation
  email_system: "メール生成（システム）",
  email_user: "メール生成（ユーザー）",
  // Infographic generation - Notebook
  infographic_system: "インフォグラフィック（システム）",
  infographic_user: "インフォグラフィック（ユーザー）",
  // Infographic generation - Council
  council_infographic_system: "審議会インフォグラフィック（システム）",
  council_infographic_user: "審議会インフォグラフィック（ユーザー）",
  // Document formatting
  format_system: "テキスト整形（システム）",
  format_user: "テキスト整形（ユーザー）",
  // Minutes formatting
  minute_format_system: "議事録整形（システム）",
  minute_format_user: "議事録整形（ユーザー）",
  // Document summary
  summary_system: "資料要約（システム）",
  summary_user: "資料要約（ユーザー）",
  // Minutes summary
  minute_summary_system: "議事録要約（システム）",
  minute_summary_user: "議事録要約（ユーザー）",
  // Document checker
  document_check_system: "校正チェック（システム）",
  document_check_user: "校正チェック（ユーザー）",
  // Slide generation
  slide_generation_system: "スライド生成（システム）",
  slide_generation_user: "スライド生成（ユーザー）",
  // Slide refinement
  slide_refinement_system: "スライド修正（システム）",
  slide_refinement_user: "スライド修正（ユーザー）",
};

// Prompt categories for grouped display
export const PROMPT_CATEGORIES: Record<string, { label: string; keys: (keyof PromptSettings)[] }> = {
  council: {
    label: "審議会資料処理",
    keys: ["council_materials_system", "council_materials_user", "council_minutes_system", "council_minutes_user"],
  },
  email: {
    label: "メール生成",
    keys: ["email_system", "email_user"],
  },
  infographic: {
    label: "インフォグラフィック（ノートブック）",
    keys: ["infographic_system", "infographic_user"],
  },
  council_infographic: {
    label: "インフォグラフィック（審議会）",
    keys: ["council_infographic_system", "council_infographic_user"],
  },
  format: {
    label: "テキスト整形",
    keys: ["format_system", "format_user"],
  },
  minute_format: {
    label: "議事録整形",
    keys: ["minute_format_system", "minute_format_user"],
  },
  summary: {
    label: "資料要約",
    keys: ["summary_system", "summary_user"],
  },
  minute_summary: {
    label: "議事録要約",
    keys: ["minute_summary_system", "minute_summary_user"],
  },
  document_check: {
    label: "校正チェック",
    keys: ["document_check_system", "document_check_user"],
  },
  slide_generation: {
    label: "スライド生成",
    keys: ["slide_generation_system", "slide_generation_user"],
  },
  slide_refinement: {
    label: "スライド修正",
    keys: ["slide_refinement_system", "slide_refinement_user"],
  },
};

/**
 * Get default hardcoded prompts
 */
export async function getDefaultPrompts(): Promise<DefaultPrompts> {
  const res = await apiClient("/api/v1/settings/llm/prompts/defaults");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch default prompts");
  }
  return res.json();
}

/**
 * Update prompt settings
 */
export async function updatePrompts(
  promptSettings: Partial<PromptSettings>
): Promise<LLMSettings> {
  const res = await apiClient("/api/v1/settings/llm/prompts", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt_settings: promptSettings }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update prompts");
  }
  return res.json();
}

/**
 * Reset prompts to defaults
 */
export async function resetPrompts(): Promise<LLMSettings> {
  const res = await apiClient("/api/v1/settings/llm/prompts/reset", {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to reset prompts");
  }
  return res.json();
}
