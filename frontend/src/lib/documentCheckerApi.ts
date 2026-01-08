import { API_BASE } from "./apiClient";

// Types
export interface CheckTypeInfo {
  id: string;
  name: string;
  description: string;
  default_enabled: boolean;
}

export interface DocumentCheckIssue {
  id: string;
  category: string;
  severity: "error" | "warning" | "info";
  page_or_slide: number | null;
  line_number: number | null;
  original_text: string;
  suggested_text: string | null;
  explanation: string | null;
  is_accepted: boolean | null;
  created_at: string;
}

export interface DocumentCheckSummary {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  issue_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentCheckDetail {
  id: string;
  filename: string;
  file_type: string;
  original_text: string;
  page_count: number | null;
  status: string;
  error_message: string | null;
  check_types: string[];
  issues: DocumentCheckIssue[];
  issue_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentCheckUploadResponse {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  message: string;
}

export interface DocumentCheckListResponse {
  items: DocumentCheckSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface UserCheckPreference {
  default_check_types: string[];
  custom_terminology: Record<string, string> | null;
}

// Category labels
export const CATEGORY_LABELS: Record<string, string> = {
  typo: "誤字脱字",
  grammar: "文法エラー",
  expression: "表現改善",
  consistency: "表記ゆれ",
  terminology: "専門用語",
  honorific: "敬語・丁寧語",
  readability: "読みやすさ",
};

// Severity labels and colors
export const SEVERITY_CONFIG: Record<
  string,
  { label: string; color: string; bgColor: string }
> = {
  error: {
    label: "エラー",
    color: "text-red-600 dark:text-red-400",
    bgColor: "bg-red-100 dark:bg-red-900/30",
  },
  warning: {
    label: "警告",
    color: "text-yellow-600 dark:text-yellow-400",
    bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
  },
  info: {
    label: "情報",
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
  },
};

// API functions
export async function getCheckTypes(): Promise<CheckTypeInfo[]> {
  const res = await fetch(`${API_BASE}/api/v1/document-checker/check-types`, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error("チェック項目の取得に失敗しました");
  }
  const data = await res.json();
  return data.check_types;
}

export async function uploadDocument(
  file: File,
  checkTypes?: string[]
): Promise<DocumentCheckUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (checkTypes && checkTypes.length > 0) {
    formData.append("check_types", checkTypes.join(","));
  }

  const res = await fetch(`${API_BASE}/api/v1/document-checker/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "ファイルのアップロードに失敗しました");
  }

  return res.json();
}

export async function getDocuments(
  limit = 20,
  offset = 0,
  status?: string
): Promise<DocumentCheckListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (status) {
    params.append("status", status);
  }

  const res = await fetch(
    `${API_BASE}/api/v1/document-checker/documents?${params}`,
    {
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("ドキュメント一覧の取得に失敗しました");
  }

  return res.json();
}

export async function getDocumentDetail(
  documentId: string
): Promise<DocumentCheckDetail> {
  const res = await fetch(
    `${API_BASE}/api/v1/document-checker/documents/${documentId}`,
    {
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("ドキュメント詳細の取得に失敗しました");
  }

  return res.json();
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/document-checker/documents/${documentId}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("ドキュメントの削除に失敗しました");
  }
}

export async function updateIssueStatus(
  issueId: string,
  isAccepted: boolean
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/document-checker/issues/${issueId}`,
    {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ is_accepted: isAccepted }),
    }
  );

  if (!res.ok) {
    throw new Error("問題ステータスの更新に失敗しました");
  }
}

export async function getUserPreferences(): Promise<UserCheckPreference> {
  const res = await fetch(
    `${API_BASE}/api/v1/document-checker/preferences`,
    {
      credentials: "include",
    }
  );

  if (!res.ok) {
    throw new Error("設定の取得に失敗しました");
  }

  return res.json();
}

export async function updateUserPreferences(
  preferences: Partial<UserCheckPreference>
): Promise<UserCheckPreference> {
  const res = await fetch(
    `${API_BASE}/api/v1/document-checker/preferences`,
    {
      method: "PUT",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preferences),
    }
  );

  if (!res.ok) {
    throw new Error("設定の更新に失敗しました");
  }

  return res.json();
}
