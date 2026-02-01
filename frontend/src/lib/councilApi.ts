/**
 * Council (審議会) API client functions
 */

import { apiClient } from "./apiClient";

// =============================================================================
// Council Types
// =============================================================================

export interface Council {
  id: string;
  owner_id: string;
  owner_display_name: string;
  title: string;
  description: string | null;
  organization: string | null;
  council_type: string | null;
  official_url: string | null;
  is_public: boolean;
  meeting_count: number;
  created_at: string;
  updated_at: string;
}

export interface CouncilCreate {
  title: string;
  description?: string;
  organization?: string;
  council_type?: string;
  official_url?: string;
  // is_public は削除（審議会は常に公開）
}

export interface CouncilUpdate {
  title?: string;
  description?: string;
  organization?: string;
  council_type?: string;
  official_url?: string;
  // is_public は削除（審議会は常に公開）
}

export type CouncilFilterType = "all" | "mine" | "public";

// =============================================================================
// Council Meeting Types
// =============================================================================

export interface CouncilMeeting {
  id: string;
  council_id: string;
  meeting_number: number;
  title: string | null;
  scheduled_at: string;
  agenda_count: number;
  created_at: string;
  updated_at: string;
}

export interface CouncilMeetingListItem extends CouncilMeeting {
  note_count: number;
}

export interface CouncilMeetingDetail {
  id: string;
  council_id: string;
  meeting_number: number;
  title: string | null;
  scheduled_at: string;
  agenda_count: number;
  agendas: CouncilAgendaItem[];
  note_count: number;
  created_at: string;
  updated_at: string;
}

export interface CouncilMeetingCreate {
  meeting_number: number;
  title?: string;
  scheduled_at: string;
}

export interface CouncilMeetingUpdate {
  meeting_number?: number;
  title?: string;
  scheduled_at?: string;
}

// =============================================================================
// Council Agenda Types
// =============================================================================

export interface CouncilAgendaMaterial {
  id: string;
  agenda_id: string;
  material_number: number;
  title: string | null;
  source_type: "url" | "file";
  url: string | null;
  original_filename: string | null;
  processing_status: string;
  has_summary: boolean;
  created_at: string;
  updated_at: string;
}

export interface CouncilAgendaMaterialDetail extends CouncilAgendaMaterial {
  text: string | null;
  summary: string | null;
  processing_error: string | null;
}

export interface CouncilAgendaMaterialCreate {
  material_number: number;
  title?: string;
  url: string;
}

export interface CouncilAgendaMaterialUpdate {
  material_number?: number;
  title?: string;
  url?: string;
}

export interface CouncilAgendaItem {
  id: string;
  meeting_id: string;
  agenda_number: number;
  title: string | null;
  // From list API (CouncilAgendaListItem)
  has_materials_url?: boolean;  // 資料URLあり（レガシー用）- list API only
  has_minutes_url?: boolean;    // 議事録URLあり - list API only
  // From detail API (CouncilAgendaOut)
  materials_url?: string | null;  // Legacy - detail API only
  minutes_url?: string | null;    // detail API only
  materials_processing_status: string;  // Aggregated from materials or legacy
  minutes_processing_status: string;
  has_materials_summary: boolean;  // Legacy or aggregated
  has_minutes_summary: boolean;
  materials_count: number;
  materials?: CouncilAgendaMaterial[];  // Only in detail API
  created_at: string;
  updated_at: string;
}

export interface CouncilAgendaItemDetail {
  id: string;
  meeting_id: string;
  agenda_number: number;
  title: string | null;
  materials_url: string | null;  // Legacy
  minutes_url: string | null;
  materials_text: string | null;  // Legacy
  minutes_text: string | null;
  materials_summary: string | null;  // Legacy
  minutes_summary: string | null;
  materials_processing_status: string;  // Legacy
  minutes_processing_status: string;
  has_materials_summary: boolean;  // Legacy
  has_minutes_summary: boolean;
  processing_error: string | null;
  materials_count: number;
  materials: CouncilAgendaMaterialDetail[];
  created_at: string;
  updated_at: string;
}

export interface CouncilAgendaCreate {
  agenda_number: number;
  title?: string;
  materials_url?: string;  // Legacy
  minutes_url?: string;
  materials?: CouncilAgendaMaterialCreate[];
}

export interface CouncilAgendaUpdate {
  agenda_number?: number;
  title?: string;
  materials_url?: string;  // Legacy
  minutes_url?: string;
}

// =============================================================================
// Council Note Types
// =============================================================================

export interface CouncilNote {
  id: string;
  council_id: string;
  meeting_id: string | null;
  user_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CouncilNoteListItem {
  id: string;
  council_id: string;
  meeting_id: string | null;
  meeting_number: number | null;
  user_id: string;
  user_display_name: string;
  title: string;
  content_preview: string;
  created_at: string;
  updated_at: string;
}

export interface CouncilNoteCreate {
  council_id: string;
  meeting_id?: string;
  title: string;
  content: string;
}

export interface CouncilNoteUpdate {
  title?: string;
  content?: string;
}

// =============================================================================
// Council Chat Types
// =============================================================================

export interface CouncilChatSession {
  id: string;
  council_id: string;
  title: string;
  selected_meeting_ids: string[] | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface CouncilChatSessionListResponse {
  sessions: CouncilChatSession[];
  total: number;
}

export interface CouncilMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  source_refs: CouncilSourceRef[] | null;
  created_at: string;
}

export interface CouncilSourceRef {
  meeting_id: string;
  meeting_number: number;
  agenda_id: string;
  agenda_number: number;
  agenda_title: string | null;
  type: "materials" | "minutes";
  excerpt: string;
}

export interface CouncilChatHistoryResponse {
  session_id: string;
  council_id: string;
  messages: CouncilMessage[];
  total: number;
}

export interface CouncilChatRequest {
  council_id: string;
  question: string;
  session_id?: string;
  meeting_ids?: string[];
  agenda_ids?: string[];
  use_rag?: boolean;
}

export interface CouncilChatResponse {
  answer: string;
  sources: CouncilSourceRef[];
  message_id: string;
  session_id: string;
}

// =============================================================================
// Council Search Types
// =============================================================================

export interface CouncilSearchResult {
  id: string;
  type: "council" | "meeting" | "note";
  title: string;
  description: string | null;
  council_id: string | null;
  council_title: string | null;
  meeting_id: string | null;
  meeting_number: number | null;
  relevance_score: number;
  created_at: string;
  match_context: string | null;
}

export interface CouncilSearchResponse {
  query: string;
  council_id: string | null;
  results: CouncilSearchResult[];
  total: number;
}

// =============================================================================
// Calendar Types
// =============================================================================

export interface CalendarMeeting {
  id: string;
  meeting_number: number;
  title: string | null;
  scheduled_at: string;
  agenda_count: number;
}

export interface CalendarResponse {
  council_id: string;
  view: "week" | "month";
  start_date: string;
  end_date: string;
  meetings: CalendarMeeting[];
}

export interface GlobalCalendarMeeting {
  id: string;
  council_id: string;
  council_title: string;
  council_organization: string | null;
  meeting_number: number;
  title: string | null;
  scheduled_at: string;
  agenda_count: number;
}

export interface GlobalCalendarResponse {
  view: "week" | "month";
  start_date: string;
  end_date: string;
  meetings: GlobalCalendarMeeting[];
  council_count: number;
}

// =============================================================================
// Council API Functions
// =============================================================================

/**
 * Fetch councils with optional filter
 */
export async function fetchCouncils(
  filterType: CouncilFilterType = "all"
): Promise<Council[]> {
  const res = await apiClient(`/api/v1/councils?filter_type=${filterType}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "審議会一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific council
 */
export async function getCouncil(councilId: string): Promise<Council> {
  const res = await apiClient(`/api/v1/councils/${councilId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "審議会の取得に失敗しました");
  }
  return res.json();
}

/**
 * Create a new council
 */
export async function createCouncil(data: CouncilCreate): Promise<Council> {
  const res = await apiClient("/api/v1/councils", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "審議会の作成に失敗しました");
  }
  return res.json();
}

/**
 * Update a council
 */
export async function updateCouncil(
  councilId: string,
  data: CouncilUpdate
): Promise<Council> {
  const res = await apiClient(`/api/v1/councils/${councilId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "審議会の更新に失敗しました");
  }
  return res.json();
}

/**
 * Delete a council
 */
export async function deleteCouncil(councilId: string): Promise<void> {
  const res = await apiClient(`/api/v1/councils/${councilId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "審議会の削除に失敗しました");
  }
}

/**
 * Get calendar data for a council
 */
export async function getCouncilCalendar(
  councilId: string,
  view: "week" | "month" = "month",
  date?: string
): Promise<CalendarResponse> {
  const params = new URLSearchParams({ view });
  if (date) {
    params.set("date", date);
  }
  const res = await apiClient(`/api/v1/councils/${councilId}/calendar?${params}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "カレンダーデータの取得に失敗しました");
  }
  return res.json();
}

/**
 * Get global calendar for all accessible councils
 */
export async function getGlobalCalendar(
  view: "week" | "month" = "month",
  date?: string,
  filterType: CouncilFilterType = "all"
): Promise<GlobalCalendarResponse> {
  const params = new URLSearchParams({ view, filter_type: filterType });
  if (date) {
    params.set("date", date);
  }
  const res = await apiClient(`/api/v1/councils/calendar?${params}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "全体カレンダーの取得に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Council Meeting API Functions
// =============================================================================

/**
 * List meetings for a council
 */
export async function listCouncilMeetings(
  councilId: string
): Promise<CouncilMeetingListItem[]> {
  const res = await apiClient(`/api/v1/council-meetings/council/${councilId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "開催回一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Create a new meeting
 */
export async function createCouncilMeeting(
  councilId: string,
  data: CouncilMeetingCreate
): Promise<CouncilMeeting> {
  const res = await apiClient(`/api/v1/council-meetings/council/${councilId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "開催回の作成に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific meeting
 */
export async function getCouncilMeeting(
  meetingId: string
): Promise<CouncilMeetingDetail> {
  // Use /detail endpoint to get full meeting info including summaries
  const res = await apiClient(`/api/v1/council-meetings/${meetingId}/detail`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "開催回の取得に失敗しました");
  }
  return res.json();
}

/**
 * Update a meeting
 */
export async function updateCouncilMeeting(
  meetingId: string,
  data: CouncilMeetingUpdate
): Promise<CouncilMeeting> {
  const res = await apiClient(`/api/v1/council-meetings/${meetingId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "開催回の更新に失敗しました");
  }
  return res.json();
}

/**
 * Delete a meeting
 */
export async function deleteCouncilMeeting(meetingId: string): Promise<void> {
  const res = await apiClient(`/api/v1/council-meetings/${meetingId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "開催回の削除に失敗しました");
  }
}

// =============================================================================
// Council Agenda API Functions
// =============================================================================

/**
 * List agendas for a meeting
 */
export async function listMeetingAgendas(
  meetingId: string
): Promise<CouncilAgendaItem[]> {
  const res = await apiClient(`/api/v1/council-agendas/meeting/${meetingId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議題一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific agenda
 */
export async function getAgenda(agendaId: string): Promise<CouncilAgendaItem> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議題の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get agenda detail (including text and summary)
 */
export async function getAgendaDetail(
  agendaId: string
): Promise<CouncilAgendaItemDetail> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}/detail`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議題詳細の取得に失敗しました");
  }
  return res.json();
}

/**
 * Create a new agenda
 */
export async function createAgenda(
  meetingId: string,
  data: CouncilAgendaCreate
): Promise<CouncilAgendaItem> {
  const res = await apiClient(`/api/v1/council-agendas/meeting/${meetingId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議題の作成に失敗しました");
  }
  return res.json();
}

/**
 * Update an agenda
 */
export async function updateAgenda(
  agendaId: string,
  data: CouncilAgendaUpdate
): Promise<CouncilAgendaItem> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議題の更新に失敗しました");
  }
  return res.json();
}

/**
 * Delete an agenda
 */
export async function deleteAgenda(agendaId: string): Promise<void> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "議題の削除に失敗しました");
  }
}

/**
 * Regenerate summary for an agenda
 */
export async function regenerateAgendaSummary(
  agendaId: string,
  target: "materials" | "minutes" | "both" = "both"
): Promise<CouncilAgendaItem> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}/regenerate`, {
    method: "POST",
    body: JSON.stringify({ target }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "要約の再生成に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Council Agenda Material API Functions
// =============================================================================

/**
 * List materials for an agenda
 */
export async function listAgendaMaterials(
  agendaId: string
): Promise<CouncilAgendaMaterial[]> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}/materials`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "資料一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific material
 */
export async function getAgendaMaterial(
  agendaId: string,
  materialId: string
): Promise<CouncilAgendaMaterialDetail> {
  const res = await apiClient(
    `/api/v1/council-agendas/${agendaId}/materials/${materialId}`
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "資料の取得に失敗しました");
  }
  return res.json();
}

/**
 * Create a new material for an agenda
 */
export async function createAgendaMaterial(
  agendaId: string,
  data: CouncilAgendaMaterialCreate
): Promise<CouncilAgendaMaterial> {
  const res = await apiClient(`/api/v1/council-agendas/${agendaId}/materials`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "資料の追加に失敗しました");
  }
  return res.json();
}

/**
 * Upload a PDF file as material
 *
 * The PDF is used for text extraction only - it is not stored permanently.
 * The URL is stored so users can access the original document.
 */
export async function uploadAgendaMaterial(
  agendaId: string,
  file: File,
  url: string,
  title?: string
): Promise<CouncilAgendaMaterial> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("url", url);
  if (title) {
    formData.append("title", title);
  }

  // Use apiClientMultipart for consistency with other upload functions
  const { apiClientMultipart } = await import("./apiClient");
  const res = await apiClientMultipart(
    `/api/v1/council-agendas/${agendaId}/materials/upload`,
    formData
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "ファイルのアップロードに失敗しました");
  }
  return res.json();
}

/**
 * Update a material
 */
export async function updateAgendaMaterial(
  agendaId: string,
  materialId: string,
  data: CouncilAgendaMaterialUpdate
): Promise<CouncilAgendaMaterial> {
  const res = await apiClient(
    `/api/v1/council-agendas/${agendaId}/materials/${materialId}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "資料の更新に失敗しました");
  }
  return res.json();
}

/**
 * Delete a material
 */
export async function deleteAgendaMaterial(
  agendaId: string,
  materialId: string
): Promise<void> {
  const res = await apiClient(
    `/api/v1/council-agendas/${agendaId}/materials/${materialId}`,
    {
      method: "DELETE",
    }
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "資料の削除に失敗しました");
  }
}

// =============================================================================
// Council Note API Functions
// =============================================================================

/**
 * List notes for a council
 */
export async function listCouncilNotes(
  councilId: string,
  meetingId?: string
): Promise<CouncilNoteListItem[]> {
  const params = meetingId ? `?meeting_id=${meetingId}` : "";
  const res = await apiClient(
    `/api/v1/council-notes/council/${councilId}${params}`
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "メモ一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific note
 */
export async function getCouncilNote(noteId: string): Promise<CouncilNote> {
  const res = await apiClient(`/api/v1/council-notes/${noteId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "メモの取得に失敗しました");
  }
  return res.json();
}

/**
 * Create a new note
 */
export async function createCouncilNote(
  data: CouncilNoteCreate
): Promise<CouncilNote> {
  const res = await apiClient("/api/v1/council-notes", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "メモの作成に失敗しました");
  }
  return res.json();
}

/**
 * Update a note
 */
export async function updateCouncilNote(
  noteId: string,
  data: CouncilNoteUpdate
): Promise<CouncilNote> {
  const res = await apiClient(`/api/v1/council-notes/${noteId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "メモの更新に失敗しました");
  }
  return res.json();
}

/**
 * Delete a note
 */
export async function deleteCouncilNote(noteId: string): Promise<void> {
  const res = await apiClient(`/api/v1/council-notes/${noteId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "メモの削除に失敗しました");
  }
}

// =============================================================================
// Council Chat API Functions
// =============================================================================

/**
 * Send a chat message
 */
export async function sendCouncilChat(
  data: CouncilChatRequest
): Promise<CouncilChatResponse> {
  const res = await apiClient("/api/v1/council-chat", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "チャットの送信に失敗しました");
  }
  return res.json();
}

/**
 * List chat sessions for a council
 */
export async function listCouncilChatSessions(
  councilId: string
): Promise<CouncilChatSessionListResponse> {
  const res = await apiClient(`/api/v1/council-chat/sessions/${councilId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "セッション一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Create a new chat session
 */
export async function createCouncilChatSession(
  councilId: string,
  title: string,
  selectedMeetingIds?: string[]
): Promise<CouncilChatSession> {
  const res = await apiClient(`/api/v1/council-chat/sessions/${councilId}`, {
    method: "POST",
    body: JSON.stringify({
      title,
      selected_meeting_ids: selectedMeetingIds,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "セッションの作成に失敗しました");
  }
  return res.json();
}

/**
 * Update a chat session
 */
export async function updateCouncilChatSession(
  sessionId: string,
  data: { title?: string; selected_meeting_ids?: string[] }
): Promise<CouncilChatSession> {
  const res = await apiClient(`/api/v1/council-chat/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "セッションの更新に失敗しました");
  }
  return res.json();
}

/**
 * Delete a chat session
 */
export async function deleteCouncilChatSession(sessionId: string): Promise<void> {
  const res = await apiClient(`/api/v1/council-chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "セッションの削除に失敗しました");
  }
}

/**
 * Get chat history for a session
 */
export async function getCouncilChatHistory(
  sessionId: string
): Promise<CouncilChatHistoryResponse> {
  const res = await apiClient(`/api/v1/council-chat/history/${sessionId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "履歴の取得に失敗しました");
  }
  return res.json();
}

/**
 * Delete all chat history for a council
 */
export async function deleteCouncilChatHistory(councilId: string): Promise<void> {
  const res = await apiClient(`/api/v1/council-chat/history/${councilId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "履歴の削除に失敗しました");
  }
}

// =============================================================================
// Council Search API Functions
// =============================================================================

/**
 * Search councils and meetings
 */
export async function searchCouncils(
  query: string,
  councilId?: string,
  limit: number = 20
): Promise<CouncilSearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
  });
  if (councilId) {
    params.set("council_id", councilId);
  }
  const res = await apiClient(`/api/v1/council-search?${params}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "検索に失敗しました");
  }
  return res.json();
}

// =============================================================================
// Helper Constants
// =============================================================================

export const COUNCIL_TYPES = [
  { value: "審議会", label: "審議会" },
  { value: "部会", label: "部会" },
  { value: "委員会", label: "委員会" },
  { value: "小委員会", label: "小委員会" },
  { value: "研究会", label: "研究会" },
  { value: "その他", label: "その他" },
];

export const PROCESSING_STATUS_LABELS: Record<string, string> = {
  pending: "待機中",
  processing: "処理中",
  completed: "完了",
  failed: "失敗",
};

export const PROCESSING_STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

// =============================================================================
// Council Infographic Types
// =============================================================================

export interface InfographicSection {
  id: string;
  heading: string;
  icon_hint?: string;
  color_hint?: string;
  key_points: string[];
  detail?: string;
  image_prompt_en?: string;
  image_url?: string;
}

export interface InfographicStructure {
  title: string;
  subtitle?: string;
  sections: InfographicSection[];
  footer_note?: string;
}

export interface CouncilInfographic {
  id: string;
  council_id: string;
  meeting_id?: string;
  title: string;
  topic?: string;
  structure: InfographicStructure;
  style_preset: string;
  created_at: string;
  updated_at: string;
}

export interface CouncilInfographicListItem {
  id: string;
  council_id: string;
  meeting_id?: string;
  title: string;
  topic?: string;
  style_preset: string;
  created_at: string;
}

export interface CouncilInfographicListResponse {
  infographics: CouncilInfographicListItem[];
  total: number;
}

export interface CouncilInfographicCreate {
  topic: string;
  agenda_ids?: string[];
  style_preset?: string;
}

// =============================================================================
// Council Infographic API Functions
// =============================================================================

/**
 * Create a new infographic for a council meeting
 */
export async function createCouncilInfographic(
  councilId: string,
  meetingId: string,
  data: CouncilInfographicCreate
): Promise<CouncilInfographic> {
  const res = await apiClient(
    `/api/v1/council-infographics/${councilId}/meeting/${meetingId}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "インフォグラフィックの生成に失敗しました");
  }
  return res.json();
}

/**
 * List infographics for a council meeting
 */
export async function listCouncilInfographics(
  councilId: string,
  meetingId: string
): Promise<CouncilInfographicListResponse> {
  const res = await apiClient(
    `/api/v1/council-infographics/${councilId}/meeting/${meetingId}`
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "インフォグラフィック一覧の取得に失敗しました");
  }
  return res.json();
}

/**
 * Get a specific infographic
 */
export async function getCouncilInfographic(
  infographicId: string
): Promise<CouncilInfographic> {
  const res = await apiClient(
    `/api/v1/council-infographics/detail/${infographicId}`
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "インフォグラフィックの取得に失敗しました");
  }
  return res.json();
}

/**
 * Delete an infographic
 */
export async function deleteCouncilInfographic(
  infographicId: string
): Promise<void> {
  const res = await apiClient(`/api/v1/council-infographics/${infographicId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "インフォグラフィックの削除に失敗しました");
  }
}
