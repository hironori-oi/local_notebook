"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Upload,
  FileText,
  MessageSquare,
  BookMarked,
  Send,
  Trash2,
  Plus,
  ChevronLeft,
  Bot,
  User,
  Sparkles,
  FileUp,
  X,
  Bookmark,
  ExternalLink,
  RotateCcw,
  Clock,
  Search,
  MessageCircle,
  MessagesSquare,
  Edit2,
  Check,
  CheckSquare,
  Square,
  LayoutGrid,
  Presentation,
} from "lucide-react";
import {
  apiClient,
  apiClientMultipart,
  isAuthenticated,
  logout,
  getUser,
  User as UserType,
  ChatSession,
  getSessions,
  createSession,
  deleteSession,
  getSessionHistory,
  updateSessionTitle,
  updateNoteTitle,
  deleteNoteById,
  updateSourceTitle,
} from "../../../lib/apiClient";
import { Header } from "../../../components/layout/Header";
import { Button } from "../../../components/ui/Button";
import { Card } from "../../../components/ui/Card";
import { Badge } from "../../../components/ui/Badge";
import { Avatar } from "../../../components/ui/Avatar";
import { Spinner, LoadingScreen, Skeleton } from "../../../components/ui/Spinner";
import { Modal } from "../../../components/ui/Modal";
import { MarkdownRenderer } from "../../../components/ui/MarkdownRenderer";

type Notebook = {
  id: string;
  title: string;
  description?: string | null;
};

type Source = {
  id: string;
  title: string;
  file_type: string;
  created_at: string;
};

type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  timestamp?: Date;
};

type Note = {
  id: string;
  title: string;
  question?: string;
  answer?: string;
  source_refs?: string[];
  created_at: string;
};

export default function NotebookDetailPage() {
  const params = useParams();
  const router = useRouter();
  const notebookId = params?.id as string;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [user, setUser] = useState<UserType | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [deleteSourceId, setDeleteSourceId] = useState<string | null>(null);
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [saveNoteModal, setSaveNoteModal] = useState<ChatMessage | null>(null);
  const [noteTitle, setNoteTitle] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [activePanel, setActivePanel] = useState<"sources" | "notes" | "sessions">("sessions");
  const [useRAG, setUseRAG] = useState(true);

  // Source selection state for RAG
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());

  // Session management state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [deleteSessionId, setDeleteSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  // Note editing state
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteTitle, setEditingNoteTitle] = useState("");

  // Source editing state
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);
  const [editingSourceTitle, setEditingSourceTitle] = useState("");

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebook, sources, and notes
  useEffect(() => {
    if (!authChecked) return;

    const loadData = async () => {
      try {
        const [nbRes, srcRes, notesRes] = await Promise.all([
          apiClient(`/api/v1/notebooks/${notebookId}`),
          apiClient(`/api/v1/sources/notebook/${notebookId}`),
          apiClient(`/api/v1/notes/notebook/${notebookId}`),
        ]);

        if (nbRes.status === 401) {
          logout();
          router.push("/login");
          return;
        }

        if (nbRes.ok) setNotebook(await nbRes.json());
        if (srcRes.ok) {
          const loadedSources: Source[] = await srcRes.json();
          setSources(loadedSources);
          // Auto-select all sources by default
          setSelectedSourceIds(new Set(loadedSources.map((s) => s.id)));
        }
        if (notesRes.ok) setNotes(await notesRes.json());

        // Load sessions
        await loadSessions();
      } catch (e) {
        console.error(e);
      }
    };

    loadData();
  }, [authChecked, notebookId, router]);

  // Load sessions
  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await getSessions(notebookId);
      setSessions(data.sessions);
    } catch (e) {
      console.error("Failed to load sessions:", e);
    } finally {
      setSessionsLoading(false);
    }
  };

  // Load messages for current session
  useEffect(() => {
    if (!currentSessionId) {
      setMessages([]);
      return;
    }

    const loadSessionMessages = async () => {
      try {
        const data = await getSessionHistory(currentSessionId);
        setMessages(
          data.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            sources: m.source_refs || undefined,
            timestamp: new Date(m.created_at),
          }))
        );
      } catch (e) {
        console.error("Failed to load session messages:", e);
      }
    };

    loadSessionMessages();
  }, [currentSessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [question]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("notebook_id", notebookId);
      formData.append("file", file);

      const res = await apiClientMultipart("/api/v1/sources/upload", formData);

      if (res.status === 401) {
        logout();
        router.push("/login");
        return;
      }

      if (!res.ok) {
        const error = await res.json();
        alert(error.detail || "Upload failed");
        return;
      }

      const data = await res.json();
      setSources((prev) => [...prev, data.source]);
      // Auto-select newly uploaded source
      setSelectedSourceIds((prev) => new Set([...prev, data.source.id]));
    } catch (e) {
      console.error(e);
      alert("Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDeleteSource = async () => {
    if (!deleteSourceId) return;

    const res = await apiClient(`/api/v1/sources/${deleteSourceId}`, {
      method: "DELETE",
    });

    if (res.status === 401) {
      logout();
      router.push("/login");
      return;
    }

    if (!res.ok) {
      alert("Delete failed");
      return;
    }

    setSources((prev) => prev.filter((s) => s.id !== deleteSourceId));
    // Remove from selected sources
    setSelectedSourceIds((prev) => {
      const newSet = new Set(prev);
      newSet.delete(deleteSourceId);
      return newSet;
    });
    setDeleteSourceId(null);
  };

  // Source selection handlers
  const handleToggleSourceSelection = (sourceId: string) => {
    setSelectedSourceIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sourceId)) {
        newSet.delete(sourceId);
      } else {
        newSet.add(sourceId);
      }
      return newSet;
    });
  };

  const handleSelectAllSources = () => {
    setSelectedSourceIds(new Set(sources.map((s) => s.id)));
  };

  const handleDeselectAllSources = () => {
    setSelectedSourceIds(new Set());
  };

  // Create new session
  const handleNewSession = async () => {
    try {
      const session = await createSession(notebookId);
      setSessions((prev) => [session, ...prev]);
      setCurrentSessionId(session.id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create session:", e);
      alert("セッションの作成に失敗しました");
    }
  };

  // Delete session
  const handleDeleteSession = async () => {
    if (!deleteSessionId) return;

    try {
      await deleteSession(deleteSessionId);
      setSessions((prev) => prev.filter((s) => s.id !== deleteSessionId));
      if (currentSessionId === deleteSessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      setDeleteSessionId(null);
    } catch (e) {
      console.error("Failed to delete session:", e);
      alert("セッションの削除に失敗しました");
    }
  };

  // Select session
  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  // Start editing session title
  const handleStartEditSession = (session: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditingTitle(session.title || "");
  };

  // Save edited session title
  const handleSaveSessionTitle = async (sessionId: string) => {
    if (!editingTitle.trim()) {
      setEditingSessionId(null);
      setEditingTitle("");
      return;
    }

    try {
      const updatedSession = await updateSessionTitle(sessionId, editingTitle.trim());
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId ? { ...s, title: updatedSession.title } : s
        )
      );
      setEditingSessionId(null);
      setEditingTitle("");
    } catch (e) {
      console.error("Failed to update session title:", e);
      alert("タイトルの更新に失敗しました");
    }
  };

  // Cancel editing
  const handleCancelEditSession = () => {
    setEditingSessionId(null);
    setEditingTitle("");
  };

  // Handle key down in edit input
  const handleEditKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveSessionTitle(sessionId);
    } else if (e.key === "Escape") {
      handleCancelEditSession();
    }
  };

  // Note editing handlers
  const handleStartEditNote = (note: Note, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingNoteId(note.id);
    setEditingNoteTitle(note.title);
  };

  const handleSaveNoteTitle = async (noteId: string) => {
    if (!editingNoteTitle.trim()) {
      setEditingNoteId(null);
      setEditingNoteTitle("");
      return;
    }

    try {
      const updatedNote = await updateNoteTitle(noteId, editingNoteTitle.trim());
      setNotes((prev) =>
        prev.map((n) =>
          n.id === noteId ? { ...n, title: updatedNote.title } : n
        )
      );
      if (selectedNote?.id === noteId) {
        setSelectedNote({ ...selectedNote, title: updatedNote.title });
      }
      setEditingNoteId(null);
      setEditingNoteTitle("");
    } catch (e) {
      console.error("Failed to update note title:", e);
      alert("タイトルの更新に失敗しました");
    }
  };

  const handleCancelEditNote = () => {
    setEditingNoteId(null);
    setEditingNoteTitle("");
  };

  const handleNoteEditKeyDown = (e: React.KeyboardEvent, noteId: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveNoteTitle(noteId);
    } else if (e.key === "Escape") {
      handleCancelEditNote();
    }
  };

  const handleDeleteNoteFromList = async (noteId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteNoteId(noteId);
  };

  // Source editing handlers
  const handleStartEditSource = (source: Source, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSourceId(source.id);
    setEditingSourceTitle(source.title);
  };

  const handleSaveSourceTitle = async (sourceId: string) => {
    if (!editingSourceTitle.trim()) {
      setEditingSourceId(null);
      setEditingSourceTitle("");
      return;
    }

    try {
      const updatedSource = await updateSourceTitle(sourceId, editingSourceTitle.trim());
      setSources((prev) =>
        prev.map((s) =>
          s.id === sourceId ? { ...s, title: updatedSource.title } : s
        )
      );
      setEditingSourceId(null);
      setEditingSourceTitle("");
    } catch (e) {
      console.error("Failed to update source title:", e);
      alert("タイトルの更新に失敗しました");
    }
  };

  const handleCancelEditSource = () => {
    setEditingSourceId(null);
    setEditingSourceTitle("");
  };

  const handleSourceEditKeyDown = (e: React.KeyboardEvent, sourceId: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveSourceTitle(sourceId);
    } else if (e.key === "Escape") {
      handleCancelEditSource();
    }
  };

  const handleSend = async () => {
    if (!question.trim() || loading) return;

    // Use RAG only if enabled and there are selected sources
    const selectedSourcesArray = Array.from(selectedSourceIds);
    const shouldUseRAG = useRAG && selectedSourcesArray.length > 0;

    const userMsg: ChatMessage = {
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await apiClient("/api/v1/chat", {
        method: "POST",
        body: JSON.stringify({
          notebook_id: notebookId,
          session_id: currentSessionId,
          source_ids: shouldUseRAG ? selectedSourcesArray : [],
          question: userMsg.content,
          use_rag: shouldUseRAG,
        }),
      });

      if (res.status === 401) {
        logout();
        router.push("/login");
        return;
      }

      const data = await res.json();

      // If no session was selected, a new one was created
      if (!currentSessionId && data.session_id) {
        setCurrentSessionId(data.session_id);
        await loadSessions();
      }

      const aiMsg: ChatMessage = {
        id: data.message_id,
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (e) {
      console.error(e);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "エラーが発生しました。もう一度お試しください。",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNote = async () => {
    if (!saveNoteModal?.id || !noteTitle.trim()) return;

    setSavingNote(true);
    try {
      const res = await apiClient(`/api/v1/notes/${notebookId}`, {
        method: "POST",
        body: JSON.stringify({
          message_id: saveNoteModal.id,
          title: noteTitle,
        }),
      });

      if (res.status === 401) {
        logout();
        router.push("/login");
        return;
      }

      if (!res.ok) {
        const error = await res.json();
        alert(error.detail || "Failed to save note");
        return;
      }

      const note = await res.json();
      setNotes((prev) => [note, ...prev]);
      setSaveNoteModal(null);
      setNoteTitle("");
      setActivePanel("notes");
    } catch (e) {
      console.error(e);
      alert("Failed to save note");
    } finally {
      setSavingNote(false);
    }
  };

  const handleDeleteNote = async () => {
    if (!deleteNoteId) return;

    try {
      const res = await apiClient(`/api/v1/notes/${deleteNoteId}`, {
        method: "DELETE",
      });

      if (res.status === 401) {
        logout();
        router.push("/login");
        return;
      }

      if (!res.ok) {
        alert("Delete failed");
        return;
      }

      setNotes((prev) => prev.filter((n) => n.id !== deleteNoteId));
      if (selectedNote?.id === deleteNoteId) {
        setSelectedNote(null);
      }
      setDeleteNoteId(null);
    } catch (e) {
      console.error(e);
      alert("Delete failed");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getFileIcon = (fileType: string) => {
    return <FileText className="w-4 h-4" />;
  };

  const getFileColor = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case "pdf":
        return "text-red-500";
      case "docx":
      case "doc":
        return "text-blue-500";
      case "txt":
      case "md":
        return "text-surface-500";
      default:
        return "text-surface-400";
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
    } else if (days === 1) {
      return "昨日";
    } else if (days < 7) {
      return `${days}日前`;
    } else {
      return date.toLocaleDateString("ja-JP");
    }
  };

  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  return (
    <div className="h-screen flex flex-col bg-surface-50 dark:bg-surface-950">
      <Header
        user={user}
        showBackButton
        backHref="/"
        backLabel="一覧に戻る"
        title={notebook?.title}
        subtitle="ノートブック"
      />

      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel - Sessions/Sources/Notes */}
        <aside className="w-80 border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 flex flex-col">
          {/* Panel Tabs */}
          <div className="flex border-b border-surface-200 dark:border-surface-700">
            <button
              onClick={() => setActivePanel("sessions")}
              className={`flex-1 px-3 py-3 text-xs font-medium transition-colors ${
                activePanel === "sessions"
                  ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-500"
                  : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              }`}
            >
              <MessagesSquare className="w-4 h-4 inline-block mr-1" />
              会話 ({sessions.length})
            </button>
            <button
              onClick={() => setActivePanel("sources")}
              className={`flex-1 px-3 py-3 text-xs font-medium transition-colors ${
                activePanel === "sources"
                  ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-500"
                  : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              }`}
            >
              <FileText className="w-4 h-4 inline-block mr-1" />
              ソース ({sources.length})
            </button>
            <button
              onClick={() => setActivePanel("notes")}
              className={`flex-1 px-3 py-3 text-xs font-medium transition-colors ${
                activePanel === "notes"
                  ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-500"
                  : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              }`}
            >
              <BookMarked className="w-4 h-4 inline-block mr-1" />
              ノート ({notes.length})
            </button>
          </div>

          {/* Generation Tools Navigation */}
          <div className="flex gap-2 p-3 border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/50">
            <Link
              href={`/notebooks/${notebookId}/infographic`}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-surface-600 dark:text-surface-300 bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 hover:border-accent-400 dark:hover:border-accent-600 hover:bg-accent-50 dark:hover:bg-accent-900/20 transition-all"
            >
              <LayoutGrid className="w-4 h-4" />
              インフォグラフィック
            </Link>
            <Link
              href={`/notebooks/${notebookId}/slides`}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-surface-600 dark:text-surface-300 bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 hover:border-primary-400 dark:hover:border-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all"
            >
              <Presentation className="w-4 h-4" />
              スライド生成
            </Link>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activePanel === "sessions" ? (
              <div className="space-y-3">
                {/* New Session Button */}
                <button
                  onClick={handleNewSession}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-xl cursor-pointer hover:border-primary-400 dark:hover:border-primary-600 hover:bg-primary-50/50 dark:hover:bg-primary-900/20 transition-all group"
                >
                  <Plus className="w-5 h-5 text-surface-400 group-hover:text-primary-500 transition-colors" />
                  <span className="text-sm text-surface-500 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                    新しい会話を開始
                  </span>
                </button>

                {/* Sessions List */}
                {sessionsLoading ? (
                  <div className="flex justify-center py-8">
                    <Spinner size="md" />
                  </div>
                ) : sessions.length === 0 ? (
                  <div className="text-center py-8">
                    <MessagesSquare className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
                    <p className="text-sm text-surface-500 dark:text-surface-400">
                      会話履歴がありません
                    </p>
                    <p className="text-xs text-surface-400 dark:text-surface-500 mt-1">
                      新しい会話を開始してください
                    </p>
                  </div>
                ) : (
                  sessions.map((session) => (
                    <div
                      key={session.id}
                      onClick={() => handleSelectSession(session.id)}
                      className={`group p-3 rounded-xl cursor-pointer transition-colors ${
                        currentSessionId === session.id
                          ? "bg-primary-100 dark:bg-primary-900/50 border border-primary-300 dark:border-primary-700"
                          : "bg-surface-50 dark:bg-surface-800 hover:bg-surface-100 dark:hover:bg-surface-700"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <MessageSquare
                          className={`w-4 h-4 mt-0.5 ${
                            currentSessionId === session.id
                              ? "text-primary-600 dark:text-primary-400"
                              : "text-surface-400"
                          }`}
                        />
                        <div className="flex-1 min-w-0">
                          {editingSessionId === session.id ? (
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="text"
                                value={editingTitle}
                                onChange={(e) => setEditingTitle(e.target.value)}
                                onKeyDown={(e) => handleEditKeyDown(e, session.id)}
                                className="flex-1 px-2 py-1 text-sm bg-white dark:bg-surface-700 border border-primary-300 dark:border-primary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                                autoFocus
                              />
                              <button
                                onClick={() => handleSaveSessionTitle(session.id)}
                                className="p-1 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-all"
                              >
                                <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                              </button>
                              <button
                                onClick={handleCancelEditSession}
                                className="p-1 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-all"
                              >
                                <X className="w-4 h-4 text-surface-500" />
                              </button>
                            </div>
                          ) : (
                            <p
                              className={`text-sm font-medium truncate ${
                                currentSessionId === session.id
                                  ? "text-primary-700 dark:text-primary-300"
                                  : "text-surface-700 dark:text-surface-200"
                              }`}
                            >
                              {session.title || "新しい会話"}
                            </p>
                          )}
                          <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5 flex items-center gap-2">
                            <span>{session.message_count}件のメッセージ</span>
                            <span>·</span>
                            <span>{formatDate(session.updated_at)}</span>
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          {editingSessionId !== session.id && (
                            <button
                              onClick={(e) => handleStartEditSession(session, e)}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-all"
                            >
                              <Edit2 className="w-4 h-4 text-surface-500 dark:text-surface-400" />
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteSessionId(session.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : activePanel === "sources" ? (
              <div className="space-y-3">
                {/* Upload Button */}
                <label className="block">
                  <div className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-xl cursor-pointer hover:border-primary-400 dark:hover:border-primary-600 hover:bg-primary-50/50 dark:hover:bg-primary-900/20 transition-all group">
                    {uploading ? (
                      <>
                        <Spinner size="sm" />
                        <span className="text-sm text-surface-500">アップロード中...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-5 h-5 text-surface-400 group-hover:text-primary-500 transition-colors" />
                        <span className="text-sm text-surface-500 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                          ドキュメントをアップロード
                        </span>
                      </>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={uploading}
                  />
                </label>

                {/* Source Selection Controls */}
                {sources.length > 0 && (
                  <div className="flex items-center justify-between px-1">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleSelectAllSources}
                        className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
                      >
                        すべて選択
                      </button>
                      <span className="text-surface-300 dark:text-surface-600">|</span>
                      <button
                        onClick={handleDeselectAllSources}
                        className="text-xs text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-300 transition-colors"
                      >
                        すべて解除
                      </button>
                    </div>
                    <span className="text-xs text-surface-500 dark:text-surface-400">
                      {selectedSourceIds.size}/{sources.length} 選択中
                    </span>
                  </div>
                )}

                {/* Sources List */}
                {sources.length === 0 ? (
                  <div className="text-center py-8">
                    <FileUp className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
                    <p className="text-sm text-surface-500 dark:text-surface-400">
                      ソースがありません
                    </p>
                    <p className="text-xs text-surface-400 dark:text-surface-500 mt-1">
                      PDF、DOCX、TXTファイルをアップロード
                    </p>
                  </div>
                ) : (
                  sources.map((src) => {
                    const isSelected = selectedSourceIds.has(src.id);
                    const isEditing = editingSourceId === src.id;
                    return (
                      <div
                        key={src.id}
                        onClick={() => !isEditing && handleToggleSourceSelection(src.id)}
                        className={`group p-3 rounded-xl cursor-pointer transition-all ${
                          isSelected
                            ? "bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800"
                            : "bg-surface-50 dark:bg-surface-800 border border-transparent hover:bg-surface-100 dark:hover:bg-surface-700"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {/* Checkbox */}
                          <div className="mt-0.5">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                            ) : (
                              <Square className="w-4 h-4 text-surface-400 dark:text-surface-500" />
                            )}
                          </div>
                          {/* File Icon */}
                          <div className={`mt-0.5 ${getFileColor(src.file_type)}`}>
                            {getFileIcon(src.file_type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            {isEditing ? (
                              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                <input
                                  type="text"
                                  value={editingSourceTitle}
                                  onChange={(e) => setEditingSourceTitle(e.target.value)}
                                  onKeyDown={(e) => handleSourceEditKeyDown(e, src.id)}
                                  className="flex-1 px-2 py-1 text-sm bg-white dark:bg-surface-700 border border-primary-300 dark:border-primary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                                  autoFocus
                                />
                                <button
                                  onClick={() => handleSaveSourceTitle(src.id)}
                                  className="p-1 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-all"
                                >
                                  <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                                </button>
                                <button
                                  onClick={handleCancelEditSource}
                                  className="p-1 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-all"
                                >
                                  <X className="w-4 h-4 text-surface-500" />
                                </button>
                              </div>
                            ) : (
                              <p className={`text-sm font-medium truncate ${
                                isSelected
                                  ? "text-primary-700 dark:text-primary-300"
                                  : "text-surface-700 dark:text-surface-200"
                              }`}>
                                {src.title}
                              </p>
                            )}
                            <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5">
                              {src.file_type.toUpperCase()}
                            </p>
                          </div>
                          {!isEditing && (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={(e) => handleStartEditSource(src, e)}
                                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-all"
                              >
                                <Edit2 className="w-4 h-4 text-surface-500 dark:text-surface-400" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDeleteSourceId(src.id);
                                }}
                                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
                              >
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {selectedNote ? (
                  <div className="animate-fade-in">
                    <button
                      onClick={() => setSelectedNote(null)}
                      className="flex items-center gap-1 text-sm text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200 mb-4 transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      一覧に戻る
                    </button>
                    <Card variant="default" padding="md">
                      <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-4">
                        {selectedNote.title}
                      </h3>
                      {selectedNote.question && (
                        <div className="mb-4">
                          <p className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">
                            質問
                          </p>
                          <p className="text-sm text-surface-700 dark:text-surface-200 bg-surface-50 dark:bg-surface-800 p-3 rounded-lg">
                            {selectedNote.question}
                          </p>
                        </div>
                      )}
                      {selectedNote.answer && (
                        <div className="mb-4">
                          <p className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">
                            回答
                          </p>
                          <div className="text-sm text-surface-700 dark:text-surface-200 bg-surface-50 dark:bg-surface-800 p-3 rounded-lg">
                            <MarkdownRenderer content={selectedNote.answer} />
                          </div>
                        </div>
                      )}
                      {selectedNote.source_refs && selectedNote.source_refs.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-4">
                          {selectedNote.source_refs.map((ref, i) => (
                            <Badge key={i} variant="secondary" size="sm">
                              {ref}
                            </Badge>
                          ))}
                        </div>
                      )}
                      <Button
                        variant="danger"
                        size="sm"
                        leftIcon={<Trash2 className="w-4 h-4" />}
                        onClick={() => setDeleteNoteId(selectedNote.id)}
                      >
                        ノートを削除
                      </Button>
                    </Card>
                  </div>
                ) : notes.length === 0 ? (
                  <div className="text-center py-8">
                    <BookMarked className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-3" />
                    <p className="text-sm text-surface-500 dark:text-surface-400">
                      保存されたノートがありません
                    </p>
                    <p className="text-xs text-surface-400 dark:text-surface-500 mt-1">
                      チャットの重要な回答を保存しましょう
                    </p>
                  </div>
                ) : (
                  notes.map((note) => (
                    <div
                      key={note.id}
                      onClick={() => editingNoteId !== note.id && setSelectedNote(note)}
                      className="p-3 bg-surface-50 dark:bg-surface-800 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-700 cursor-pointer transition-colors group"
                    >
                      <div className="flex items-start gap-3">
                        <Bookmark className="w-4 h-4 text-accent-500 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          {editingNoteId === note.id ? (
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="text"
                                value={editingNoteTitle}
                                onChange={(e) => setEditingNoteTitle(e.target.value)}
                                onKeyDown={(e) => handleNoteEditKeyDown(e, note.id)}
                                className="flex-1 px-2 py-1 text-sm bg-white dark:bg-surface-700 border border-primary-300 dark:border-primary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                                autoFocus
                              />
                              <button
                                onClick={() => handleSaveNoteTitle(note.id)}
                                className="p-1 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-all"
                              >
                                <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                              </button>
                              <button
                                onClick={handleCancelEditNote}
                                className="p-1 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-all"
                              >
                                <X className="w-4 h-4 text-surface-500" />
                              </button>
                            </div>
                          ) : (
                            <p className="text-sm font-medium text-surface-700 dark:text-surface-200 truncate">
                              {note.title}
                            </p>
                          )}
                          <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(note.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        {editingNoteId !== note.id && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => handleStartEditNote(note, e)}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-600 transition-all"
                            >
                              <Edit2 className="w-4 h-4 text-surface-500 dark:text-surface-400" />
                            </button>
                            <button
                              onClick={(e) => handleDeleteNoteFromList(note.id, e)}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </aside>

        {/* Main Chat Area */}
        <section className="flex-1 flex flex-col bg-surface-50 dark:bg-surface-900">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center px-4">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mb-6 shadow-glow-primary">
                  <Sparkles className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                  {currentSessionId ? "会話を続けましょう" : "新しい会話を始めましょう"}
                </h2>
                <p className="text-surface-500 dark:text-surface-400 max-w-md mb-8">
                  {currentSessionId
                    ? "このセッションで会話を続けることができます。前の会話を覚えています。"
                    : "質問を入力すると新しい会話セッションが自動的に作成されます。"}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
                  {[
                    "要点をまとめて",
                    "重要なポイントは何ですか？",
                    "手法について説明して",
                    "特定の情報を探して",
                  ].map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setQuestion(suggestion)}
                      className="text-left px-4 py-3 text-sm text-surface-600 dark:text-surface-300 bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 hover:border-primary-300 dark:hover:border-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-6">
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-4 animate-fade-in-up ${
                      msg.role === "user" ? "flex-row-reverse" : ""
                    }`}
                    style={{ animationDelay: `${idx * 50}ms` }}
                  >
                    {msg.role === "assistant" ? (
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center flex-shrink-0 shadow-soft">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                    ) : (
                      <Avatar name={user?.display_name} size="md" variant="rounded" />
                    )}

                    <div
                      className={`flex-1 max-w-[85%] ${
                        msg.role === "user" ? "flex flex-col items-end" : ""
                      }`}
                    >
                      <div
                        className={`px-4 py-3 rounded-2xl ${
                          msg.role === "user"
                            ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-br-md"
                            : "bg-white dark:bg-surface-800 text-surface-800 dark:text-surface-100 border border-surface-200 dark:border-surface-700 rounded-bl-md shadow-soft-sm"
                        }`}
                      >
                        {msg.role === "assistant" ? (
                          <MarkdownRenderer content={msg.content} className="text-sm" />
                        ) : (
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">
                            {msg.content}
                          </p>
                        )}
                      </div>

                      {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {msg.sources.map((ref, i) => (
                            <Badge key={i} variant="secondary" size="sm">
                              <FileText className="w-3 h-3" />
                              {ref}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {msg.role === "assistant" && msg.id && (
                        <button
                          onClick={() => setSaveNoteModal(msg)}
                          className="flex items-center gap-1.5 mt-2 px-3 py-1.5 text-xs text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
                        >
                          <Bookmark className="w-3.5 h-3.5" />
                          ノートに保存
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex gap-4 animate-fade-in">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center flex-shrink-0 shadow-soft">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div className="bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft-sm">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 p-4">
            <div className="max-w-3xl mx-auto">
              {/* RAGモード切替 */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setUseRAG(true)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all ${
                      useRAG
                        ? "bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 font-medium"
                        : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <Search className="w-3.5 h-3.5" />
                    RAG検索
                  </button>
                  <button
                    onClick={() => setUseRAG(false)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all ${
                      !useRAG
                        ? "bg-accent-100 dark:bg-accent-900/50 text-accent-700 dark:text-accent-300 font-medium"
                        : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <MessageCircle className="w-3.5 h-3.5" />
                    自由入力
                  </button>
                </div>
                {useRAG && sources.length === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <FileUp className="w-3.5 h-3.5" />
                    RAG検索にはソースが必要です
                  </p>
                )}
                {useRAG && sources.length > 0 && selectedSourceIds.size === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <Square className="w-3.5 h-3.5" />
                    ソースを選択してください
                  </p>
                )}
                {useRAG && selectedSourceIds.size > 0 && (
                  <p className="text-xs text-primary-600 dark:text-primary-400 flex items-center gap-1">
                    <CheckSquare className="w-3.5 h-3.5" />
                    {selectedSourceIds.size}件のソースを使用
                  </p>
                )}
              </div>
              <div className="flex gap-3 items-end">
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    className="w-full px-4 py-3 pr-12 text-sm bg-surface-50 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-xl resize-none transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    rows={1}
                    placeholder={
                      useRAG
                        ? "ドキュメントについて質問してください...（Shift+Enterで改行）"
                        : "自由にメッセージを入力してください...（Shift+Enterで改行）"
                    }
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={handleKeyDown}
                  />
                </div>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleSend}
                  disabled={loading || !question.trim()}
                  className="flex-shrink-0"
                >
                  {loading ? <Spinner size="sm" variant="white" /> : <Send className="w-5 h-5" />}
                </Button>
              </div>
              <p className="text-xs text-surface-400 dark:text-surface-500 mt-2">
                {useRAG
                  ? "RAG検索モード：アップロードしたドキュメントから関連情報を検索して回答します"
                  : "自由入力モード：ドキュメントを参照せず、AIと直接対話します"
                }
                {currentSessionId && " | 会話履歴は自動的に引き継がれます"}
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Delete Source Modal */}
      <Modal
        isOpen={!!deleteSourceId}
        onClose={() => setDeleteSourceId(null)}
        title="ソースを削除"
        description="ソースと関連するデータが完全に削除されます。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteSourceId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteSource}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Delete Note Modal */}
      <Modal
        isOpen={!!deleteNoteId}
        onClose={() => setDeleteNoteId(null)}
        title="ノートを削除"
        description="保存されたノートが完全に削除されます。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteNoteId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteNote}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Delete Session Modal */}
      <Modal
        isOpen={!!deleteSessionId}
        onClose={() => setDeleteSessionId(null)}
        title="会話を削除"
        description="この会話とすべてのメッセージが完全に削除されます。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteSessionId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteSession}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Save Note Modal */}
      <Modal
        isOpen={!!saveNoteModal}
        onClose={() => {
          setSaveNoteModal(null);
          setNoteTitle("");
        }}
        title="ノートに保存"
        description="後で参照できるようにタイトルを付けて保存します"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              ノートのタイトル
            </label>
            <input
              type="text"
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              placeholder="わかりやすいタイトルを入力..."
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setSaveNoteModal(null);
                setNoteTitle("");
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveNote}
              isLoading={savingNote}
              disabled={!noteTitle.trim()}
              leftIcon={<Bookmark className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
