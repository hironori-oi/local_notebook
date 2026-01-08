export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Local storage keys
const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

// Auth types
export interface User {
  id: string;
  username: string;
  display_name: string;
  role: "admin" | "user";
}

// Helper function to check if user is admin
export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  token: AuthToken;
}

// Token management
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// User management
export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    const parsed = JSON.parse(userStr);
    // Ensure role exists (for backwards compatibility with old stored data)
    return {
      ...parsed,
      role: parsed.role || "user",
    };
  } catch {
    return null;
  }
}

export function setUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function removeUser(): void {
  localStorage.removeItem(USER_KEY);
}

// Auth state - now based on user info (cookie is HTTPOnly so we can't read it)
export function isAuthenticated(): boolean {
  return getUser() !== null;
}

export async function logoutFromServer(): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Ignore errors during logout - we'll clear local state anyway
  }
}

export function logout(): void {
  // Clear local state
  removeToken();
  removeUser();
  // Also clear server-side cookie (fire and forget)
  logoutFromServer();
}

// API client with authentication via HTTPOnly cookie
export function apiClient(path: string, init?: RequestInit) {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  };

  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include", // Send cookies with requests
  });
}

// API client for multipart/form-data (file uploads)
export function apiClientMultipart(path: string, formData: FormData) {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
    credentials: "include", // Send cookies with requests
  });
}

// Auth API functions
export async function login(
  username: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    credentials: "include", // Receive and store HTTPOnly cookie
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ログインに失敗しました");
  }

  const data: AuthResponse = await res.json();
  // Token is now stored in HTTPOnly cookie by the server
  // Store user info for UI display
  setUser(data.user);
  return data;
}

export async function register(
  username: string,
  password: string,
  displayName: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      password,
      display_name: displayName,
    }),
    credentials: "include", // Receive and store HTTPOnly cookie
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ユーザー登録に失敗しました");
  }

  const data: AuthResponse = await res.json();
  // Token is now stored in HTTPOnly cookie by the server
  // Store user info for UI display
  setUser(data.user);
  return data;
}

// Change password
export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  const res = await apiClient("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "パスワードの変更に失敗しました");
  }
}

// Get current user info from server
export async function getCurrentUser(): Promise<User> {
  const res = await apiClient("/api/v1/auth/me");
  if (!res.ok) {
    throw new Error("ユーザー情報の取得に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Chat Session Types and Functions
// =============================================================================

export interface ChatSession {
  id: string;
  notebook_id: string;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListResponse {
  sessions: ChatSession[];
  total: number;
}

export interface ChatMessage {
  id: string;
  session_id: string | null;
  notebook_id: string;
  user_id: string | null;
  role: "user" | "assistant";
  content: string;
  source_refs: string[] | null;
  status: "pending" | "generating" | "completed" | "failed";
  error_message?: string | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
  total: number;
}

// Get all sessions for a notebook
export async function getSessions(notebookId: string): Promise<ChatSessionListResponse> {
  const res = await apiClient(`/api/v1/chat/sessions/${notebookId}`);
  if (!res.ok) {
    throw new Error("セッションの取得に失敗しました");
  }
  return res.json();
}

// Create a new session
export async function createSession(
  notebookId: string,
  title?: string
): Promise<ChatSession> {
  const res = await apiClient(`/api/v1/chat/sessions/${notebookId}`, {
    method: "POST",
    body: JSON.stringify({ title: title || null }),
  });
  if (!res.ok) {
    throw new Error("セッションの作成に失敗しました");
  }
  return res.json();
}

// Delete a session
export async function deleteSession(sessionId: string): Promise<void> {
  const res = await apiClient(`/api/v1/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("セッションの削除に失敗しました");
  }
}

// Update session title
export async function updateSessionTitle(
  sessionId: string,
  title: string
): Promise<ChatSession> {
  const res = await apiClient(`/api/v1/chat/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    throw new Error("セッションの更新に失敗しました");
  }
  return res.json();
}

// Get chat history for a session
export async function getSessionHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const res = await apiClient(`/api/v1/chat/history/session/${sessionId}`);
  if (!res.ok) {
    throw new Error("履歴の取得に失敗しました");
  }
  return res.json();
}

// Clear all chat history for a notebook
export async function clearChatHistory(notebookId: string): Promise<void> {
  const res = await apiClient(`/api/v1/chat/history/${notebookId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("履歴の削除に失敗しました");
  }
}

// =============================================================================
// Async Chat Types and Functions
// =============================================================================

export interface AsyncChatRequest {
  notebook_id: string;
  session_id?: string;
  source_ids?: string[];
  question: string;
  use_rag?: boolean;
  use_formatted_text?: boolean;
}

export interface AsyncChatResponse {
  user_message_id: string;
  assistant_message_id: string;
  session_id: string;
  status: "pending";
}

export interface MessageStatusResponse {
  message_id: string;
  status: "pending" | "generating" | "completed" | "failed";
  content?: string | null;
  source_refs?: string[] | null;
  error_message?: string | null;
}

// Submit a chat question for background processing
export async function sendChatAsync(data: AsyncChatRequest): Promise<AsyncChatResponse> {
  const res = await apiClient("/api/v1/chat/async", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "チャットの送信に失敗しました");
  }
  return res.json();
}

// Check the status of a message being generated
export async function getMessageStatus(messageId: string): Promise<MessageStatusResponse> {
  const res = await apiClient(`/api/v1/chat/status/${messageId}`);
  if (!res.ok) {
    throw new Error("メッセージ状態の取得に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Note API Functions
// =============================================================================

export interface NoteInfo {
  id: string;
  notebook_id: string;
  message_id: string;
  title: string;
  content?: string | null;
  created_by: string;
  created_at: string;
  updated_at?: string | null;
  question?: string;
  answer?: string;
  source_refs?: string[];
}

export interface NoteUpdateData {
  title?: string;
  content?: string;
}

// Update note (title and/or content)
export async function updateNote(
  noteId: string,
  data: NoteUpdateData
): Promise<NoteInfo> {
  const res = await apiClient(`/api/v1/notes/${noteId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("ノートの更新に失敗しました");
  }
  return res.json();
}

// Update note title (backward compatibility)
export async function updateNoteTitle(
  noteId: string,
  title: string
): Promise<NoteInfo> {
  return updateNote(noteId, { title });
}

// Delete note
export async function deleteNoteById(noteId: string): Promise<void> {
  const res = await apiClient(`/api/v1/notes/${noteId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("ノートの削除に失敗しました");
  }
}

// =============================================================================
// Source API Functions
// =============================================================================

export interface SourceInfo {
  id: string;
  notebook_id: string;
  title: string;
  file_type: string;
  folder_id?: string | null;
  folder_name?: string | null;
  processing_status: string; // pending, processing, completed, failed
  has_summary?: boolean;
  created_at: string;
}

export interface SourceDetail {
  id: string;
  notebook_id: string;
  title: string;
  file_type: string;
  processing_status: string;
  processing_error?: string | null;
  full_text?: string | null;
  formatted_text?: string | null;
  summary?: string | null;
  created_at: string;
}

// Update source title
export async function updateSource(
  sourceId: string,
  data: { title?: string }
): Promise<SourceInfo> {
  const res = await apiClient(`/api/v1/sources/${sourceId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("ソースの更新に失敗しました");
  }
  return res.json();
}

// Update source title (alias for backwards compatibility)
export async function updateSourceTitle(
  sourceId: string,
  title: string
): Promise<SourceInfo> {
  return updateSource(sourceId, { title });
}

// =============================================================================
// Source Folder Types and Functions
// =============================================================================

export interface SourceFolder {
  id: string;
  notebook_id: string;
  name: string;
  position: number;
  source_count: number;
  created_at: string;
  updated_at: string;
}

// List folders for a notebook
export async function listFolders(notebookId: string): Promise<SourceFolder[]> {
  const res = await apiClient(`/api/v1/folders/notebook/${notebookId}`);
  if (!res.ok) {
    throw new Error("フォルダ一覧の取得に失敗しました");
  }
  return res.json();
}

// Create a new folder
export async function createFolder(
  notebookId: string,
  name: string
): Promise<SourceFolder> {
  const res = await apiClient(`/api/v1/folders/notebook/${notebookId}`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "フォルダの作成に失敗しました");
  }
  return res.json();
}

// Update a folder
export async function updateFolder(
  folderId: string,
  name: string
): Promise<SourceFolder> {
  const res = await apiClient(`/api/v1/folders/${folderId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "フォルダの更新に失敗しました");
  }
  return res.json();
}

// Delete a folder
export async function deleteFolder(folderId: string): Promise<void> {
  const res = await apiClient(`/api/v1/folders/${folderId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "フォルダの削除に失敗しました");
  }
}

// Reorder folders
export async function reorderFolders(
  notebookId: string,
  folderIds: string[]
): Promise<SourceFolder[]> {
  const res = await apiClient(`/api/v1/folders/notebook/${notebookId}/reorder`, {
    method: "PUT",
    body: JSON.stringify({ folder_ids: folderIds }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "フォルダの並び替えに失敗しました");
  }
  return res.json();
}

// Move a source to a folder (or remove from folder)
export async function moveSource(
  sourceId: string,
  folderId: string | null
): Promise<SourceInfo> {
  const res = await apiClient(`/api/v1/sources/${sourceId}/move`, {
    method: "PATCH",
    body: JSON.stringify({ folder_id: folderId }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ソースの移動に失敗しました");
  }
  return res.json();
}

// Get source detail (including summary info)
export async function getSourceDetail(sourceId: string): Promise<SourceDetail> {
  const res = await apiClient(`/api/v1/sources/${sourceId}/detail`);
  if (!res.ok) {
    throw new Error("ソース詳細の取得に失敗しました");
  }
  return res.json();
}

// Update source summary/formatted_text
export async function updateSourceSummary(
  sourceId: string,
  data: { formatted_text?: string; summary?: string }
): Promise<SourceDetail> {
  const res = await apiClient(`/api/v1/sources/${sourceId}/summary`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("要約の更新に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Infographic Types and Functions
// =============================================================================

export interface InfographicSection {
  id: string;
  heading: string;
  icon_hint?: string | null;
  color_hint?: string | null;
  key_points: string[];
  detail?: string | null;
  image_prompt_en?: string | null;
  image_url?: string | null;
}

export interface InfographicStructure {
  title: string;
  subtitle?: string | null;
  sections: InfographicSection[];
  footer_note?: string | null;
}

export interface Infographic {
  id: string;
  notebook_id: string;
  title: string;
  topic?: string | null;
  structure: InfographicStructure;
  style_preset: string;
  created_at: string;
  updated_at: string;
}

export interface InfographicListItem {
  id: string;
  notebook_id: string;
  title: string;
  topic?: string | null;
  style_preset: string;
  created_at: string;
}

export interface InfographicListResponse {
  infographics: InfographicListItem[];
  total: number;
}

// Create a new infographic
export async function createInfographic(
  notebookId: string,
  topic: string,
  sourceIds?: string[],
  stylePreset?: string
): Promise<Infographic> {
  const res = await apiClient(`/api/v1/infographics/${notebookId}`, {
    method: "POST",
    body: JSON.stringify({
      topic,
      source_ids: sourceIds || [],
      style_preset: stylePreset || "default",
    }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "インフォグラフィックの生成に失敗しました");
  }
  return res.json();
}

// List infographics for a notebook
export async function listInfographics(
  notebookId: string
): Promise<InfographicListResponse> {
  const res = await apiClient(`/api/v1/infographics/${notebookId}`);
  if (!res.ok) {
    throw new Error("インフォグラフィック一覧の取得に失敗しました");
  }
  return res.json();
}

// Get a specific infographic
export async function getInfographic(
  infographicId: string
): Promise<Infographic> {
  const res = await apiClient(`/api/v1/infographics/detail/${infographicId}`);
  if (!res.ok) {
    throw new Error("インフォグラフィックの取得に失敗しました");
  }
  return res.json();
}

// Delete an infographic
export async function deleteInfographic(infographicId: string): Promise<void> {
  const res = await apiClient(`/api/v1/infographics/${infographicId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("インフォグラフィックの削除に失敗しました");
  }
}

// =============================================================================
// Email Types and Functions
// =============================================================================

export interface SpeakerOpinion {
  speaker: string;
  opinions: string[];
}

export interface EmailContent {
  document_summary: string;
  speaker_opinions: SpeakerOpinion[];
  additional_notes?: string | null;
}

export interface EmailGenerateResponse {
  topic: string;
  email_body: string;
  content: EmailContent;
  sources_used: number;
  generated_at: string;
}

export interface GeneratedEmail {
  id: string;
  notebook_id: string;
  title: string;
  topic?: string | null;
  email_body: string;
  structured_content?: EmailContent | null;
  document_source_ids?: string[] | null;
  minute_ids?: string[] | null;
  created_at: string;
  updated_at: string;
}

// Generate email content from sources and minutes
export async function generateEmail(
  notebookId: string,
  topic: string,
  documentSourceIds: string[],
  minuteIds: string[]
): Promise<EmailGenerateResponse> {
  const res = await apiClient(`/api/v1/emails/generate/${notebookId}`, {
    method: "POST",
    body: JSON.stringify({
      topic,
      document_source_ids: documentSourceIds,
      minute_ids: minuteIds,
    }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "メールの生成に失敗しました");
  }
  return res.json();
}

// Save generated email
export async function saveEmail(
  notebookId: string,
  data: {
    title: string;
    topic?: string;
    email_body: string;
    structured_content?: EmailContent;
    document_source_ids?: string[];
    minute_ids?: string[];
  }
): Promise<GeneratedEmail> {
  const res = await apiClient(`/api/v1/emails/${notebookId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "メールの保存に失敗しました");
  }
  return res.json();
}

// List saved emails for a notebook
export async function listEmails(notebookId: string): Promise<GeneratedEmail[]> {
  const res = await apiClient(`/api/v1/emails/${notebookId}`);
  if (!res.ok) {
    throw new Error("メール一覧の取得に失敗しました");
  }
  return res.json();
}

// Get a specific saved email
export async function getEmail(emailId: string): Promise<GeneratedEmail> {
  const res = await apiClient(`/api/v1/emails/detail/${emailId}`);
  if (!res.ok) {
    throw new Error("メールの取得に失敗しました");
  }
  return res.json();
}

// Update a saved email
export async function updateEmail(
  emailId: string,
  data: { title?: string; email_body?: string }
): Promise<GeneratedEmail> {
  const res = await apiClient(`/api/v1/emails/${emailId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("メールの更新に失敗しました");
  }
  return res.json();
}

// Delete a saved email
export async function deleteEmail(emailId: string): Promise<void> {
  const res = await apiClient(`/api/v1/emails/${emailId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("メールの削除に失敗しました");
  }
}

// =============================================================================
// Minute (Meeting Minutes) Types and Functions
// =============================================================================

export interface Minute {
  id: string;
  notebook_id: string;
  title: string;
  content: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface MinuteListItem {
  id: string;
  notebook_id: string;
  title: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface MinuteDetail {
  id: string;
  notebook_id: string;
  title: string;
  content: string;
  document_ids: string[];
  processing_status: string;
  processing_error?: string | null;
  formatted_content?: string | null;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

// List minutes for a notebook
export async function listMinutes(notebookId: string): Promise<MinuteListItem[]> {
  const res = await apiClient(`/api/v1/minutes/notebook/${notebookId}`);
  if (!res.ok) {
    throw new Error("議事録一覧の取得に失敗しました");
  }
  return res.json();
}

// Create a new minute
export async function createMinute(
  notebookId: string,
  data: {
    title: string;
    content: string;
    document_ids?: string[];
  }
): Promise<Minute> {
  const res = await apiClient(`/api/v1/minutes/notebook/${notebookId}`, {
    method: "POST",
    body: JSON.stringify({
      title: data.title,
      content: data.content,
      document_ids: data.document_ids || [],
    }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "議事録の作成に失敗しました");
  }
  return res.json();
}

// Get a specific minute
export async function getMinute(minuteId: string): Promise<Minute> {
  const res = await apiClient(`/api/v1/minutes/${minuteId}`);
  if (!res.ok) {
    throw new Error("議事録の取得に失敗しました");
  }
  return res.json();
}

// Update a minute
export async function updateMinute(
  minuteId: string,
  data: { title?: string; content?: string }
): Promise<Minute> {
  const res = await apiClient(`/api/v1/minutes/${minuteId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("議事録の更新に失敗しました");
  }
  return res.json();
}

// Update minute's linked documents
export async function updateMinuteDocuments(
  minuteId: string,
  documentIds: string[]
): Promise<Minute> {
  const res = await apiClient(`/api/v1/minutes/${minuteId}/documents`, {
    method: "PUT",
    body: JSON.stringify({ document_ids: documentIds }),
  });
  if (!res.ok) {
    throw new Error("議事録の関連資料更新に失敗しました");
  }
  return res.json();
}

// Delete a minute
export async function deleteMinute(minuteId: string): Promise<void> {
  const res = await apiClient(`/api/v1/minutes/${minuteId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("議事録の削除に失敗しました");
  }
}

// Get minute detail (including summary info)
export async function getMinuteDetail(minuteId: string): Promise<MinuteDetail> {
  const res = await apiClient(`/api/v1/minutes/${minuteId}/detail`);
  if (!res.ok) {
    throw new Error("議事録詳細の取得に失敗しました");
  }
  return res.json();
}

// Update minute summary/formatted_content
export async function updateMinuteSummary(
  minuteId: string,
  data: { formatted_content?: string; summary?: string }
): Promise<MinuteDetail> {
  const res = await apiClient(`/api/v1/minutes/${minuteId}/summary`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("要約の更新に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Admin API Functions (User Management)
// =============================================================================

export interface AdminUser {
  id: string;
  username: string;
  display_name: string;
  role: "admin" | "user";
  created_at: string;
}

export interface AdminUserListResponse {
  users: AdminUser[];
  total: number;
}

export interface AdminUserCreate {
  username: string;
  password: string;
  display_name: string;
  role?: "admin" | "user";
}

export interface AdminUserUpdate {
  display_name?: string;
  role?: "admin" | "user";
  password?: string;
}

// List all users (admin only)
export async function listUsers(): Promise<AdminUserListResponse> {
  const res = await apiClient("/api/v1/admin/users");
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ユーザー一覧の取得に失敗しました");
  }
  return res.json();
}

// Create a new user (admin only)
export async function createUser(data: AdminUserCreate): Promise<AdminUser> {
  const res = await apiClient("/api/v1/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ユーザーの作成に失敗しました");
  }
  return res.json();
}

// Get a specific user (admin only)
export async function getUserById(userId: string): Promise<AdminUser> {
  const res = await apiClient(`/api/v1/admin/users/${userId}`);
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ユーザーの取得に失敗しました");
  }
  return res.json();
}

// Update a user (admin only)
export async function updateUser(
  userId: string,
  data: AdminUserUpdate
): Promise<AdminUser> {
  const res = await apiClient(`/api/v1/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ユーザーの更新に失敗しました");
  }
  return res.json();
}

// Delete a user (admin only)
export async function deleteUser(userId: string): Promise<void> {
  const res = await apiClient(`/api/v1/admin/users/${userId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ユーザーの削除に失敗しました");
  }
}

// Promote user to admin (admin only)
export async function promoteToAdmin(userId: string): Promise<AdminUser> {
  const res = await apiClient(`/api/v1/admin/users/${userId}/promote`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "管理者への昇格に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Notebook Types and Functions
// =============================================================================

export interface Notebook {
  id: string;
  title: string;
  description?: string | null;
  is_public: boolean;
  owner_id: string;
  owner_display_name: string;
  source_count: number;
  created_at: string;
  updated_at: string;
}

export interface NotebookCreate {
  title: string;
  description?: string;
  is_public?: boolean;
}

export interface NotebookUpdate {
  title?: string;
  description?: string;
  is_public?: boolean;
}

export type NotebookFilterType = "all" | "mine" | "public";

// Paginated response type for notebooks
interface NotebookListResponse {
  items: Notebook[];
  total: number;
  offset: number;
  limit: number;
}

// Fetch notebooks with optional filter
export async function fetchNotebooks(
  filterType: NotebookFilterType = "all"
): Promise<Notebook[]> {
  const res = await apiClient(`/api/v1/notebooks?filter_type=${filterType}`);
  if (!res.ok) {
    throw new Error("ノートブック一覧の取得に失敗しました");
  }
  const data: NotebookListResponse = await res.json();
  return data.items;
}

// Get a specific notebook
export async function getNotebook(notebookId: string): Promise<Notebook> {
  const res = await apiClient(`/api/v1/notebooks/${notebookId}`);
  if (!res.ok) {
    throw new Error("ノートブックの取得に失敗しました");
  }
  return res.json();
}

// Create a new notebook
export async function createNotebook(data: NotebookCreate): Promise<Notebook> {
  const res = await apiClient("/api/v1/notebooks", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ノートブックの作成に失敗しました");
  }
  return res.json();
}

// Update a notebook
export async function updateNotebook(
  notebookId: string,
  data: NotebookUpdate
): Promise<Notebook> {
  const res = await apiClient(`/api/v1/notebooks/${notebookId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ノートブックの更新に失敗しました");
  }
  return res.json();
}

// Delete a notebook
export async function deleteNotebook(notebookId: string): Promise<void> {
  const res = await apiClient(`/api/v1/notebooks/${notebookId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "ノートブックの削除に失敗しました");
  }
}
