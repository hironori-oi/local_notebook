import { API_BASE } from "./apiClient";

// Types
export interface SlideContent {
  bullets: string[];
  subtitle?: string;
  details?: string;
}

export interface Slide {
  id: string;
  slide_number: number;
  slide_type: "title" | "section" | "content" | "conclusion";
  title: string;
  content: SlideContent;
  speaker_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SlideMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ProjectSummary {
  id: string;
  title: string;
  status: string;
  slide_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail {
  id: string;
  title: string;
  source_text: string;
  target_slide_count?: number;
  key_points?: string;
  template_id?: string;
  style_id?: string;
  status: string;
  error_message?: string;
  slides: Slide[];
  messages: SlideMessage[];
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface Template {
  id: string;
  name: string;
  description?: string;
  original_filename: string;
  slide_count: number;
  created_at: string;
}

export interface TemplateListResponse {
  items: Template[];
  total: number;
}

export interface StyleSettings {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  fonts: {
    title: string;
    body: string;
  };
  sizes: {
    title: number;
    subtitle: number;
    body: number;
  };
  layout_preference: "modern" | "classic" | "minimal";
}

export interface Style {
  id: string;
  name: string;
  description?: string;
  settings: StyleSettings;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface StyleListResponse {
  items: Style[];
  total: number;
}

export interface CreateProjectRequest {
  title: string;
  source_text: string;
  target_slide_count?: number;
  key_points?: string;
  template_id?: string;
  style_id?: string;
}

export interface RefineResponse {
  message: string;
  slides: Slide[];
}

// Slide type labels
export const SLIDE_TYPE_LABELS: Record<string, string> = {
  title: "タイトル",
  section: "セクション",
  content: "コンテンツ",
  conclusion: "まとめ",
};

// Project status labels
export const PROJECT_STATUS_LABELS: Record<string, string> = {
  draft: "下書き",
  pending: "待機中",
  generating: "生成中",
  completed: "完了",
  failed: "エラー",
};

// API functions
export async function createProject(
  request: CreateProjectRequest
): Promise<ProjectDetail> {
  const res = await fetch(`${API_BASE}/api/v1/slide-generator/projects`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "プロジェクトの作成に失敗しました");
  }

  return res.json();
}

export async function getProjects(
  limit = 20,
  offset = 0
): Promise<ProjectListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/projects?${params}`,
    {
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("プロジェクト一覧の取得に失敗しました");
  }

  return res.json();
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/projects/${projectId}`,
    {
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("プロジェクトの取得に失敗しました");
  }

  return res.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/projects/${projectId}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("プロジェクトの削除に失敗しました");
  }
}

export async function updateSlide(
  projectId: string,
  slideNumber: number,
  updates: {
    title?: string;
    content?: SlideContent;
    speaker_notes?: string;
    slide_type?: string;
  }
): Promise<Slide> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/projects/${projectId}/slides/${slideNumber}`,
    {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    }
  );

  if (!res.ok) {
    throw new Error("スライドの更新に失敗しました");
  }

  return res.json();
}

export async function refineSlides(
  projectId: string,
  instruction: string
): Promise<RefineResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/projects/${projectId}/refine`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ instruction }),
    }
  );

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "スライドの修正に失敗しました");
  }

  return res.json();
}

export async function exportProject(projectId: string): Promise<Blob> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/projects/${projectId}/export`,
    {
      method: "POST",
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("エクスポートに失敗しました");
  }

  return res.blob();
}

// Template functions
export async function uploadTemplate(
  file: File,
  name: string,
  description?: string
): Promise<Template> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  if (description) {
    formData.append("description", description);
  }

  const res = await fetch(`${API_BASE}/api/v1/slide-generator/templates`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "テンプレートのアップロードに失敗しました");
  }

  return res.json();
}

export async function getTemplates(): Promise<TemplateListResponse> {
  const res = await fetch(`${API_BASE}/api/v1/slide-generator/templates`, {
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("テンプレート一覧の取得に失敗しました");
  }

  return res.json();
}

export async function deleteTemplate(templateId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/templates/${templateId}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("テンプレートの削除に失敗しました");
  }
}

// Style functions
export async function createStyle(
  name: string,
  settings: StyleSettings,
  description?: string,
  isDefault = false
): Promise<Style> {
  const res = await fetch(`${API_BASE}/api/v1/slide-generator/styles`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      description,
      settings,
      is_default: isDefault,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "スタイルの作成に失敗しました");
  }

  return res.json();
}

export async function getStyles(): Promise<StyleListResponse> {
  const res = await fetch(`${API_BASE}/api/v1/slide-generator/styles`, {
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("スタイル一覧の取得に失敗しました");
  }

  return res.json();
}

export async function updateStyle(
  styleId: string,
  updates: {
    name?: string;
    description?: string;
    settings?: StyleSettings;
    is_default?: boolean;
  }
): Promise<Style> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/styles/${styleId}`,
    {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    }
  );

  if (!res.ok) {
    throw new Error("スタイルの更新に失敗しました");
  }

  return res.json();
}

export async function deleteStyle(styleId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/slide-generator/styles/${styleId}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("スタイルの削除に失敗しました");
  }
}

// Utility function to download exported file
export function downloadPptx(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".pptx") ? filename : `${filename}.pptx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
