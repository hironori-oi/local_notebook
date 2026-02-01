"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  MessageSquare,
  FileText,
  ClipboardList,
  Loader2,
  Sparkles,
  AlertCircle,
  Check,
  Copy,
  StickyNote,
} from "lucide-react";
import {
  CouncilMeetingListItem,
  CouncilAgendaItem,
  CouncilMessage,
  CouncilSourceRef,
  sendCouncilChat,
  getCouncilChatHistory,
  createCouncilNote,
} from "../../lib/councilApi";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { Input } from "../ui/Input";

interface CouncilChatProps {
  councilId: string;
  meetings: CouncilMeetingListItem[];
  sessionId?: string;
  onSessionCreate?: (sessionId: string) => void;
  mode?: "council" | "meeting";
  currentMeetingId?: string;
  agendas?: CouncilAgendaItem[];
}

export function CouncilChat({
  councilId,
  meetings,
  sessionId: initialSessionId,
  onSessionCreate,
  mode = "council",
  currentMeetingId,
  agendas = [],
}: CouncilChatProps) {
  const [messages, setMessages] = useState<CouncilMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const [selectedMeetingIds, setSelectedMeetingIds] = useState<string[]>([]);
  const [selectedAgendaIds, setSelectedAgendaIds] = useState<string[]>([]);
  const [useRag, setUseRag] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [savingNoteMessageId, setSavingNoteMessageId] = useState<string | null>(null);
  // Save note modal state
  const [showSaveNoteModal, setShowSaveNoteModal] = useState(false);
  const [saveNoteMessage, setSaveNoteMessage] = useState<CouncilMessage | null>(null);
  const [saveNoteTitle, setSaveNoteTitle] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load history if session exists
  useEffect(() => {
    if (initialSessionId) {
      loadHistory(initialSessionId);
    }
  }, [initialSessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadHistory = async (sid: string) => {
    try {
      const history = await getCouncilChatHistory(sid);
      setMessages(history.messages);
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setError(null);
    setLoading(true);

    // Add user message optimistically
    const tempUserMessage: CouncilMessage = {
      id: `temp-${Date.now()}`,
      session_id: sessionId || "",
      role: "user",
      content: question,
      source_refs: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      // Determine meeting_ids based on mode
      let meetingIdsToSend: string[] | undefined;
      if (mode === "meeting" && currentMeetingId) {
        meetingIdsToSend = [currentMeetingId];
      } else if (selectedMeetingIds.length > 0) {
        meetingIdsToSend = selectedMeetingIds;
      }

      const response = await sendCouncilChat({
        council_id: councilId,
        question,
        session_id: sessionId,
        meeting_ids: meetingIdsToSend,
        agenda_ids: mode === "meeting" && selectedAgendaIds.length > 0 ? selectedAgendaIds : undefined,
        use_rag: useRag,
      });

      // Update session ID if new
      if (!sessionId && response.session_id) {
        setSessionId(response.session_id);
        onSessionCreate?.(response.session_id);
      }

      // Replace temp message and add assistant response
      setMessages((prev) => {
        const filtered = prev.filter((m) => !m.id.startsWith("temp-"));
        return [
          ...filtered,
          {
            id: `user-${response.message_id}`,
            session_id: response.session_id,
            role: "user",
            content: question,
            source_refs: null,
            created_at: new Date().toISOString(),
          },
          {
            id: response.message_id,
            session_id: response.session_id,
            role: "assistant",
            content: response.answer,
            source_refs: response.sources,
            created_at: new Date().toISOString(),
          },
        ];
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("temp-")));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const toggleMeetingSelection = (meetingId: string) => {
    setSelectedMeetingIds((prev) =>
      prev.includes(meetingId)
        ? prev.filter((id) => id !== meetingId)
        : [...prev, meetingId]
    );
  };

  const selectAllMeetings = () => {
    setSelectedMeetingIds(meetings.map((m) => m.id));
  };

  const deselectAllMeetings = () => {
    setSelectedMeetingIds([]);
  };

  // Agenda selection helpers (for mode="meeting")
  const toggleAgendaSelection = (agendaId: string) => {
    setSelectedAgendaIds((prev) =>
      prev.includes(agendaId)
        ? prev.filter((id) => id !== agendaId)
        : [...prev, agendaId]
    );
  };

  const selectAllAgendas = () => {
    // Only select agendas that have completed processing
    const completedAgendas = agendas.filter(
      (a) => a.materials_processing_status === "completed" || a.minutes_processing_status === "completed"
    );
    setSelectedAgendaIds(completedAgendas.map((a) => a.id));
  };

  const deselectAllAgendas = () => {
    setSelectedAgendaIds([]);
  };

  // Check if agenda has any searchable content
  // Consider agenda searchable if:
  // - materials_processing_status is "completed" (aggregated from individual materials)
  // - OR minutes_processing_status is "completed"
  // - OR has any materials with processing completed (materials_count > 0 with completed status)
  const isAgendaSearchable = (agenda: CouncilAgendaItem) => {
    // Check if materials are processed (aggregated status from backend)
    const hasMaterialsCompleted = agenda.materials_processing_status === "completed";
    // Check if minutes are processed
    const hasMinutesCompleted = agenda.minutes_processing_status === "completed";
    // Check individual materials if available
    const hasCompletedMaterials = agenda.materials?.some(m => m.processing_status === "completed") ?? false;

    return hasMaterialsCompleted || hasMinutesCompleted || hasCompletedMaterials;
  };

  const getSourceLabel = (ref: CouncilSourceRef) => {
    const typeLabel = ref.type === "materials" ? "資料" : "議事録";
    let label = `第${ref.meeting_number}回`;
    if (ref.agenda_title) {
      label += ` - 議題${ref.agenda_number}: ${ref.agenda_title}`;
    } else {
      label += ` - 議題${ref.agenda_number}`;
    }
    label += ` (${typeLabel})`;
    return label;
  };

  // Copy message content to clipboard
  const handleCopyMessage = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  // Open save note modal
  const handleSaveAsNote = (message: CouncilMessage) => {
    // Generate default title from first line
    const firstLine = message.content.split("\n")[0];
    const defaultTitle = firstLine.length > 50 ? firstLine.substring(0, 50) + "..." : firstLine;

    setSaveNoteMessage(message);
    setSaveNoteTitle(defaultTitle);
    setShowSaveNoteModal(true);
  };

  // Actually save the note with custom title
  const handleConfirmSaveNote = async () => {
    if (!saveNoteMessage || !saveNoteTitle.trim()) return;

    setSavingNote(true);
    setSavingNoteMessageId(saveNoteMessage.id);

    try {
      await createCouncilNote({
        council_id: councilId,
        meeting_id: mode === "meeting" && currentMeetingId ? currentMeetingId : undefined,
        title: saveNoteTitle.trim(),
        content: saveNoteMessage.content,
      });

      // Close modal and show success feedback
      setShowSaveNoteModal(false);
      setSaveNoteMessage(null);
      setSaveNoteTitle("");
      setTimeout(() => setSavingNoteMessageId(null), 1500);
    } catch (e) {
      console.error("Failed to save note:", e);
      setError("メモの保存に失敗しました");
      setSavingNoteMessageId(null);
    } finally {
      setSavingNote(false);
    }
  };

  // Close save note modal
  const handleCloseSaveNoteModal = () => {
    setShowSaveNoteModal(false);
    setSaveNoteMessage(null);
    setSaveNoteTitle("");
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-surface-800 rounded-2xl border border-surface-200 dark:border-surface-700 overflow-hidden">
      {/* Selector based on mode */}
      <div className="p-4 border-b border-surface-200 dark:border-surface-700">
        {mode === "council" ? (
          /* Meeting selector for council mode */
          <>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-surface-700 dark:text-surface-300">
                検索対象の開催回
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={selectAllMeetings}
                  className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                >
                  すべて選択
                </button>
                <span className="text-surface-300 dark:text-surface-600">|</span>
                <button
                  onClick={deselectAllMeetings}
                  className="text-xs text-surface-500 dark:text-surface-400 hover:underline"
                >
                  すべて解除
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
              {meetings.map((meeting) => (
                <button
                  key={meeting.id}
                  onClick={() => toggleMeetingSelection(meeting.id)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                    selectedMeetingIds.includes(meeting.id)
                      ? "bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 ring-1 ring-primary-300 dark:ring-primary-700"
                      : "bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400 hover:bg-surface-200 dark:hover:bg-surface-600"
                  }`}
                >
                  {selectedMeetingIds.includes(meeting.id) && (
                    <Check className="w-3 h-3" />
                  )}
                  第{meeting.meeting_number}回
                </button>
              ))}
              {meetings.length === 0 && (
                <p className="text-xs text-surface-400 dark:text-surface-500">
                  開催回がありません
                </p>
              )}
            </div>
          </>
        ) : (
          /* Agenda selector for meeting mode */
          <>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-surface-700 dark:text-surface-300">
                検索対象の議題
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={selectAllAgendas}
                  className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                >
                  すべて選択
                </button>
                <span className="text-surface-300 dark:text-surface-600">|</span>
                <button
                  onClick={deselectAllAgendas}
                  className="text-xs text-surface-500 dark:text-surface-400 hover:underline"
                >
                  すべて解除
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-1.5 max-h-32 overflow-y-auto">
              {agendas.map((agenda) => {
                const searchable = isAgendaSearchable(agenda);
                return (
                  <button
                    key={agenda.id}
                    onClick={() => searchable && toggleAgendaSelection(agenda.id)}
                    disabled={!searchable}
                    className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors text-left ${
                      !searchable
                        ? "bg-surface-50 dark:bg-surface-800 text-surface-400 dark:text-surface-500 cursor-not-allowed"
                        : selectedAgendaIds.includes(agenda.id)
                        ? "bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 ring-1 ring-primary-300 dark:ring-primary-700"
                        : "bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400 hover:bg-surface-200 dark:hover:bg-surface-600"
                    }`}
                  >
                    {selectedAgendaIds.includes(agenda.id) && searchable && (
                      <Check className="w-3 h-3 flex-shrink-0" />
                    )}
                    <span className="flex-shrink-0">議題{agenda.agenda_number}</span>
                    {agenda.title && (
                      <span className="truncate text-surface-500 dark:text-surface-400">
                        {agenda.title}
                      </span>
                    )}
                    {!searchable && (
                      <span className="ml-auto text-surface-400 dark:text-surface-500 text-[10px]">
                        未処理
                      </span>
                    )}
                  </button>
                );
              })}
              {agendas.length === 0 && (
                <p className="text-xs text-surface-400 dark:text-surface-500">
                  議題がありません
                </p>
              )}
            </div>
          </>
        )}

        {/* RAG toggle */}
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-surface-100 dark:border-surface-700">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
              className="w-4 h-4 rounded border-surface-300 dark:border-surface-600 text-primary-500 focus:ring-primary-500"
            />
            <span className="text-xs text-surface-600 dark:text-surface-400">
              資料・議事録を参照して回答
            </span>
          </label>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-100 to-accent-100 dark:from-primary-900/30 dark:to-accent-900/30 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-primary-500" />
            </div>
            <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
              審議会AIアシスタント
            </h3>
            <p className="text-sm text-surface-500 dark:text-surface-400 max-w-md">
              資料や議事録の内容について質問できます。
              検索対象の開催回を選択してから質問してください。
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  message.role === "user"
                    ? "bg-primary-500 text-white"
                    : "bg-surface-100 dark:bg-surface-700"
                }`}
              >
                <div
                  className={`text-sm whitespace-pre-wrap ${
                    message.role === "assistant"
                      ? "text-surface-900 dark:text-surface-100"
                      : ""
                  }`}
                >
                  {message.content}
                </div>

                {/* Action buttons for assistant messages */}
                {message.role === "assistant" && (
                  <div className="flex items-center gap-1 mt-2 pt-2 border-t border-surface-200 dark:border-surface-600">
                    <button
                      onClick={() => handleCopyMessage(message.id, message.content)}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-surface-500 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-surface-200 dark:hover:bg-surface-600 rounded transition-colors"
                      title="コピー"
                    >
                      {copiedMessageId === message.id ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>コピーしました</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>コピー</span>
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleSaveAsNote(message)}
                      disabled={savingNoteMessageId === message.id}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-surface-500 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-surface-200 dark:hover:bg-surface-600 rounded transition-colors disabled:opacity-50"
                      title="メモに保存"
                    >
                      {savingNoteMessageId === message.id ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>保存しました</span>
                        </>
                      ) : (
                        <>
                          <StickyNote className="w-3.5 h-3.5" />
                          <span>メモに保存</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Source references */}
                {message.role === "assistant" &&
                  message.source_refs &&
                  message.source_refs.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-surface-200 dark:border-surface-600">
                      <p className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-2">
                        参照元:
                      </p>
                      <div className="space-y-2">
                        {message.source_refs.map((ref, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2 text-xs bg-surface-50 dark:bg-surface-600 rounded-lg p-2"
                          >
                            {ref.type === "materials" ? (
                              <FileText className="w-3.5 h-3.5 text-primary-500 mt-0.5 flex-shrink-0" />
                            ) : (
                              <ClipboardList className="w-3.5 h-3.5 text-accent-500 mt-0.5 flex-shrink-0" />
                            )}
                            <div>
                              <span className="font-medium text-surface-700 dark:text-surface-300">
                                {getSourceLabel(ref)}
                              </span>
                              <p className="text-surface-500 dark:text-surface-400 mt-0.5 line-clamp-2">
                                {ref.excerpt}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-100 dark:bg-surface-700 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2 text-surface-500 dark:text-surface-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">回答を生成中...</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-surface-200 dark:border-surface-700">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="質問を入力してください..."
            className="flex-1 px-4 py-2.5 text-sm bg-surface-50 dark:bg-surface-700 border border-surface-200 dark:border-surface-600 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            rows={1}
            disabled={loading}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={!input.trim() || loading}
            leftIcon={loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          >
            送信
          </Button>
        </div>
        <p className="text-xs text-surface-400 dark:text-surface-500 mt-2">
          Shift + Enter で改行、Enter で送信
        </p>
      </form>

      {/* Save Note Modal */}
      <Modal
        isOpen={showSaveNoteModal}
        onClose={handleCloseSaveNoteModal}
        title="メモに保存"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              タイトル
            </label>
            <Input
              value={saveNoteTitle}
              onChange={(e) => setSaveNoteTitle(e.target.value)}
              placeholder="メモのタイトルを入力"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              内容プレビュー
            </label>
            <div className="max-h-40 overflow-y-auto p-3 bg-surface-50 dark:bg-surface-700 rounded-lg text-sm text-surface-600 dark:text-surface-400 whitespace-pre-wrap">
              {saveNoteMessage?.content.substring(0, 500)}
              {saveNoteMessage && saveNoteMessage.content.length > 500 && "..."}
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              onClick={handleCloseSaveNoteModal}
              disabled={savingNote}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirmSaveNote}
              disabled={!saveNoteTitle.trim() || savingNote}
              leftIcon={savingNote ? <Loader2 className="w-4 h-4 animate-spin" /> : <StickyNote className="w-4 h-4" />}
            >
              {savingNote ? "保存中..." : "保存"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
