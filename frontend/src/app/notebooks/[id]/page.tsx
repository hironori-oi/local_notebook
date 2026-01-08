"use client";

import { useEffect, useState, useRef, useCallback } from "react";
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
  ChevronRight,
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
  Mail,
  FileCheck,
  ClipboardList,
  Eye,
  AlertCircle,
  Loader2,
  Save,
  PanelLeftClose,
  PanelLeft,
  GripVertical,
  Globe,
  Lock,
  Folder,
  FolderOpen,
  FolderPlus,
  ChevronDown,
  MoreVertical,
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
  updateNote,
  deleteNoteById,
  updateSource,
  MinuteListItem,
  listMinutes,
  createMinute,
  getMinute,
  updateMinute,
  deleteMinute,
  updateMinuteDocuments,
  Minute,
  SourceDetail,
  getSourceDetail,
  updateSourceSummary,
  MinuteDetail,
  getMinuteDetail,
  updateMinuteSummary,
  Notebook as NotebookType,
  updateNotebook,
  SourceFolder,
  listFolders,
  createFolder,
  updateFolder,
  deleteFolder,
  moveSource,
  sendChatAsync,
  getMessageStatus,
  clearChatHistory,
  ChatMessage as ApiChatMessage,
} from "../../../lib/apiClient";
import { usePendingMessages } from "../../../hooks/usePendingMessages";
import { Header } from "../../../components/layout/Header";
import { Button } from "../../../components/ui/Button";
import { Card } from "../../../components/ui/Card";
import { Badge } from "../../../components/ui/Badge";
import { Avatar } from "../../../components/ui/Avatar";
import { Input } from "../../../components/ui/Input";
import { Spinner, LoadingScreen, Skeleton } from "../../../components/ui/Spinner";
import { Modal } from "../../../components/ui/Modal";
import { MarkdownRenderer } from "../../../components/ui/MarkdownRenderer";
import { MultiFileUploader } from "../../../components/upload";
import { ExportButton } from "../../../components/export";

type Notebook = {
  id: string;
  title: string;
  description?: string | null;
  is_public?: boolean;
  owner_id?: string;
  owner_display_name?: string;
};

type Source = {
  id: string;
  title: string;
  file_type: string;
  folder_id?: string | null;
  folder_name?: string | null;
  created_at: string;
};

type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  timestamp?: Date;
  status?: "pending" | "generating" | "completed" | "failed";
  error_message?: string | null;
};

type Note = {
  id: string;
  notebook_id: string;
  message_id: string;
  title: string;
  content?: string | null;
  question?: string;
  answer?: string;
  source_refs?: string[];
  created_at: string;
  updated_at?: string | null;
};

// Helper function to clean up excessive newlines in text
function cleanupText(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(/\r\n/g, "\n")           // Normalize line endings
    .replace(/\n{3,}/g, "\n\n")        // Replace 3+ newlines with 2
    .replace(/^\s+|\s+$/g, "")         // Trim start and end
    .replace(/[ \t]+\n/g, "\n")        // Remove trailing spaces on lines
    .replace(/\n[ \t]+/g, "\n");       // Remove leading spaces on lines (except indentation)
}

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
  const [activePanel, setActivePanel] = useState<"sources" | "notes" | "sessions" | "minutes">("sessions");
  const [chatMode, setChatMode] = useState<"rag" | "fulltext" | "free">("rag");

  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(320); // default 320px (w-80)
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);

  // Minutes (meeting minutes) state
  const [minutes, setMinutes] = useState<MinuteListItem[]>([]);
  const [minutesLoading, setMinutesLoading] = useState(false);
  const [showMinuteModal, setShowMinuteModal] = useState(false);
  const [editingMinute, setEditingMinute] = useState<Minute | null>(null);
  const [minuteTitle, setMinuteTitle] = useState("");
  const [minuteContent, setMinuteContent] = useState("");
  const [minuteDocumentIds, setMinuteDocumentIds] = useState<string[]>([]);
  const [savingMinute, setSavingMinute] = useState(false);
  const [deleteMinuteId, setDeleteMinuteId] = useState<string | null>(null);

  // Source selection state for RAG
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());

  // Session management state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [deleteSessionId, setDeleteSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [clearingAll, setClearingAll] = useState(false);

  // Note editing state
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteTitle, setEditingNoteTitle] = useState("");
  const [isEditingNoteContent, setIsEditingNoteContent] = useState(false);
  const [editingNoteContent, setEditingNoteContent] = useState("");
  const [savingNoteContent, setSavingNoteContent] = useState(false);

  // Source editing state
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);
  const [editingSourceTitle, setEditingSourceTitle] = useState("");

  // Source detail modal state
  const [showSourceDetailModal, setShowSourceDetailModal] = useState(false);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [sourceDetailLoading, setSourceDetailLoading] = useState(false);
  const [editingFormattedText, setEditingFormattedText] = useState("");
  const [editingSummary, setEditingSummary] = useState("");
  const [savingSourceDetail, setSavingSourceDetail] = useState(false);
  const [isEditingSourceDetail, setIsEditingSourceDetail] = useState(false);

  // Minute detail modal state
  const [showMinuteDetailModal, setShowMinuteDetailModal] = useState(false);
  const [minuteDetail, setMinuteDetail] = useState<MinuteDetail | null>(null);
  const [minuteDetailLoading, setMinuteDetailLoading] = useState(false);
  const [editingMinuteFormattedContent, setEditingMinuteFormattedContent] = useState("");
  const [editingMinuteSummary, setEditingMinuteSummary] = useState("");
  const [savingMinuteDetail, setSavingMinuteDetail] = useState(false);
  const [isEditingMinuteDetail, setIsEditingMinuteDetail] = useState(false);

  // Processing time state
  const [uploadElapsedTime, setUploadElapsedTime] = useState<number | null>(null);
  const [minuteSaveElapsedTime, setMinuteSaveElapsedTime] = useState<number | null>(null);
  const [sourceDetailElapsedTime, setSourceDetailElapsedTime] = useState<number | null>(null);
  const [minuteDetailElapsedTime, setMinuteDetailElapsedTime] = useState<number | null>(null);

  // Notebook settings modal state
  const [showNotebookSettingsModal, setShowNotebookSettingsModal] = useState(false);
  const [savingNotebookSettings, setSavingNotebookSettings] = useState(false);
  const [editNotebookTitle, setEditNotebookTitle] = useState("");
  const [editNotebookDesc, setEditNotebookDesc] = useState("");

  // Folder management state
  const [folders, setFolders] = useState<SourceFolder[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [editingFolderName, setEditingFolderName] = useState("");
  const [deleteFolderId, setDeleteFolderId] = useState<string | null>(null);
  const [movingSourceId, setMovingSourceId] = useState<string | null>(null);
  const [showMoveModal, setShowMoveModal] = useState(false);

  // Callback for updating messages from pending status polling
  const handleMessageUpdate = useCallback(
    (messageId: string, updates: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId ? { ...msg, ...updates } : msg
        )
      );
    },
    []
  );

  // Convert local ChatMessage to ApiChatMessage format for polling hook
  const apiMessages: ApiChatMessage[] = messages
    .filter((m) => m.id)
    .map((m) => ({
      id: m.id!,
      session_id: currentSessionId,
      notebook_id: notebookId,
      user_id: null,
      role: m.role,
      content: m.content,
      source_refs: m.sources || null,
      status: m.status || "completed",
      error_message: m.error_message,
      created_at: m.timestamp?.toISOString() || new Date().toISOString(),
    }));

  // Poll for pending message status
  const { hasPending } = usePendingMessages({
    messages: apiMessages,
    onMessageUpdate: (messageId, updates) => {
      handleMessageUpdate(messageId, {
        content: updates.content || "",
        sources: updates.source_refs || undefined,
        status: updates.status,
        error_message: updates.error_message,
      });
    },
    pollingInterval: 2000,
    enabled: messages.some(
      (m) => m.status === "pending" || m.status === "generating"
    ),
  });

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load notebook, sources, notes, and minutes
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
        // Load minutes
        await loadMinutesList();
        // Load folders
        await loadFoldersList();
      } catch (e) {
        console.error(e);
      }
    };

    loadData();
  }, [authChecked, notebookId, router]);

  // Load folders list
  const loadFoldersList = async () => {
    try {
      const data = await listFolders(notebookId);
      setFolders(data);
      // Default expand all folders
      setExpandedFolders(new Set(data.map((f) => f.id)));
    } catch (e) {
      console.error("Failed to load folders:", e);
    }
  };

  // Load minutes list
  const loadMinutesList = async () => {
    setMinutesLoading(true);
    try {
      const data = await listMinutes(notebookId);
      setMinutes(data);
    } catch (e) {
      console.error("Failed to load minutes:", e);
    } finally {
      setMinutesLoading(false);
    }
  };

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
    setUploadElapsedTime(null);
    const startTime = Date.now();
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
      setUploadElapsedTime((Date.now() - startTime) / 1000);
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

  // Open notebook settings modal
  const handleOpenNotebookSettings = () => {
    if (!notebook) return;
    setEditNotebookTitle(notebook.title);
    setEditNotebookDesc(notebook.description || "");
    setShowNotebookSettingsModal(true);
  };

  // Notebook settings handler - toggle public/private
  const handleToggleNotebookPublic = async () => {
    if (!notebook) return;
    setSavingNotebookSettings(true);
    try {
      const updated = await updateNotebook(notebookId, {
        is_public: !notebook.is_public,
      });
      setNotebook((prev) => prev ? { ...prev, is_public: updated.is_public } : prev);
    } catch (e) {
      console.error(e);
      alert("設定の更新に失敗しました");
    } finally {
      setSavingNotebookSettings(false);
    }
  };

  // Save notebook title and description
  const handleSaveNotebookSettings = async () => {
    if (!notebook || !editNotebookTitle.trim()) return;
    setSavingNotebookSettings(true);
    try {
      const updated = await updateNotebook(notebookId, {
        title: editNotebookTitle,
        description: editNotebookDesc || undefined,
      });
      setNotebook((prev) => prev ? {
        ...prev,
        title: updated.title,
        description: updated.description
      } : prev);
      setShowNotebookSettingsModal(false);
    } catch (e) {
      console.error(e);
      alert("設定の更新に失敗しました");
    } finally {
      setSavingNotebookSettings(false);
    }
  };

  // Check if current user is the owner
  const isOwner = notebook && user ? notebook.owner_id === user.id : false;

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

  // Clear all sessions
  const handleClearAllSessions = async () => {
    setClearingAll(true);
    try {
      await clearChatHistory(notebookId);
      setSessions([]);
      setCurrentSessionId(null);
      setMessages([]);
      setShowClearAllModal(false);
    } catch (e) {
      console.error("Failed to clear all sessions:", e);
      alert("履歴の削除に失敗しました");
    } finally {
      setClearingAll(false);
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

  // Note content editing handlers
  const handleStartEditNoteContent = () => {
    if (!selectedNote) return;
    // Use custom content if set, otherwise use original answer
    setEditingNoteContent(selectedNote.content || selectedNote.answer || "");
    setIsEditingNoteContent(true);
  };

  const handleSaveNoteContent = async () => {
    if (!selectedNote) return;
    setSavingNoteContent(true);
    try {
      const updatedNote = await updateNote(selectedNote.id, {
        content: editingNoteContent
      });
      // Update notes list
      setNotes((prev) =>
        prev.map((n) =>
          n.id === selectedNote.id ? { ...n, content: updatedNote.content } : n
        )
      );
      // Update selected note
      setSelectedNote({ ...selectedNote, content: updatedNote.content });
      setIsEditingNoteContent(false);
      setEditingNoteContent("");
    } catch (e) {
      console.error("Failed to update note content:", e);
      alert("メモの保存に失敗しました");
    } finally {
      setSavingNoteContent(false);
    }
  };

  const handleCancelEditNoteContent = () => {
    setIsEditingNoteContent(false);
    setEditingNoteContent("");
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
      const updatedSource = await updateSource(sourceId, { title: editingSourceTitle.trim() });
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

  // Folder handlers
  const handleToggleFolder = (folderId: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    setCreatingFolder(true);
    try {
      const folder = await createFolder(notebookId, newFolderName.trim());
      setFolders((prev) => [...prev, folder]);
      setExpandedFolders((prev) => new Set([...prev, folder.id]));
      setNewFolderName("");
      setShowCreateFolderModal(false);
    } catch (e) {
      console.error("Failed to create folder:", e);
      alert("フォルダの作成に失敗しました");
    } finally {
      setCreatingFolder(false);
    }
  };

  const handleStartEditFolder = (folder: SourceFolder, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingFolderId(folder.id);
    setEditingFolderName(folder.name);
  };

  const handleSaveFolderName = async (folderId: string) => {
    if (!editingFolderName.trim()) {
      setEditingFolderId(null);
      setEditingFolderName("");
      return;
    }
    try {
      const updated = await updateFolder(folderId, editingFolderName.trim());
      setFolders((prev) =>
        prev.map((f) => (f.id === folderId ? { ...f, name: updated.name } : f))
      );
      setEditingFolderId(null);
      setEditingFolderName("");
    } catch (e) {
      console.error("Failed to update folder:", e);
      alert("フォルダ名の更新に失敗しました");
    }
  };

  const handleCancelEditFolder = () => {
    setEditingFolderId(null);
    setEditingFolderName("");
  };

  const handleFolderEditKeyDown = (e: React.KeyboardEvent, folderId: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveFolderName(folderId);
    } else if (e.key === "Escape") {
      handleCancelEditFolder();
    }
  };

  const handleDeleteFolder = async () => {
    if (!deleteFolderId) return;
    try {
      await deleteFolder(deleteFolderId);
      setFolders((prev) => prev.filter((f) => f.id !== deleteFolderId));
      // Also remove sources in this folder from state
      setSources((prev) => prev.filter((s) => s.folder_id !== deleteFolderId));
      setDeleteFolderId(null);
    } catch (e) {
      console.error("Failed to delete folder:", e);
      alert("フォルダの削除に失敗しました");
    }
  };

  const handleOpenMoveModal = (sourceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setMovingSourceId(sourceId);
    setShowMoveModal(true);
  };

  const handleMoveSource = async (targetFolderId: string | null) => {
    if (!movingSourceId) return;
    try {
      const updated = await moveSource(movingSourceId, targetFolderId);
      setSources((prev) =>
        prev.map((s) =>
          s.id === movingSourceId
            ? { ...s, folder_id: updated.folder_id, folder_name: updated.folder_name }
            : s
        )
      );
      // Update folder source counts
      await loadFoldersList();
      setShowMoveModal(false);
      setMovingSourceId(null);
    } catch (e) {
      console.error("Failed to move source:", e);
      alert("ソースの移動に失敗しました");
    }
  };

  // Get sources by folder
  const getSourcesByFolder = useCallback((folderId: string | null) => {
    return sources.filter((s) =>
      folderId === null ? !s.folder_id : s.folder_id === folderId
    );
  }, [sources]);

  // Source detail handlers
  const handleOpenSourceDetail = async (sourceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setShowSourceDetailModal(true);
    setSourceDetailLoading(true);
    try {
      const detail = await getSourceDetail(sourceId);
      setSourceDetail(detail);
      setEditingFormattedText(detail.formatted_text || "");
      setEditingSummary(detail.summary || "");
    } catch (error) {
      console.error("Failed to load source detail:", error);
      alert("ソース詳細の読み込みに失敗しました");
      setShowSourceDetailModal(false);
    } finally {
      setSourceDetailLoading(false);
    }
  };

  const handleCloseSourceDetail = () => {
    setShowSourceDetailModal(false);
    setSourceDetail(null);
    setEditingFormattedText("");
    setEditingSummary("");
    setIsEditingSourceDetail(false);
  };

  const handleSaveSourceDetail = async () => {
    if (!sourceDetail) return;
    setSavingSourceDetail(true);
    setSourceDetailElapsedTime(null);
    const startTime = Date.now();
    try {
      const updated = await updateSourceSummary(sourceDetail.id, {
        formatted_text: editingFormattedText,
        summary: editingSummary,
      });
      setSourceDetail(updated);
      setSourceDetailElapsedTime((Date.now() - startTime) / 1000);
      setIsEditingSourceDetail(false);
    } catch (error) {
      console.error("Failed to update source detail:", error);
      alert("要約情報の更新に失敗しました");
    } finally {
      setSavingSourceDetail(false);
    }
  };

  // Minute detail handlers
  const handleOpenMinuteDetail = async (minuteId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setShowMinuteDetailModal(true);
    setMinuteDetailLoading(true);
    try {
      const detail = await getMinuteDetail(minuteId);
      setMinuteDetail(detail);
      setEditingMinuteFormattedContent(detail.formatted_content || "");
      setEditingMinuteSummary(detail.summary || "");
    } catch (error) {
      console.error("Failed to load minute detail:", error);
      alert("議事録詳細の読み込みに失敗しました");
      setShowMinuteDetailModal(false);
    } finally {
      setMinuteDetailLoading(false);
    }
  };

  const handleCloseMinuteDetail = () => {
    setShowMinuteDetailModal(false);
    setMinuteDetail(null);
    setEditingMinuteFormattedContent("");
    setEditingMinuteSummary("");
    setIsEditingMinuteDetail(false);
  };

  const handleSaveMinuteDetail = async () => {
    if (!minuteDetail) return;
    setSavingMinuteDetail(true);
    setMinuteDetailElapsedTime(null);
    const startTime = Date.now();
    try {
      const updated = await updateMinuteSummary(minuteDetail.id, {
        formatted_content: editingMinuteFormattedContent,
        summary: editingMinuteSummary,
      });
      setMinuteDetail(updated);
      setMinuteDetailElapsedTime((Date.now() - startTime) / 1000);
      setIsEditingMinuteDetail(false);
    } catch (error) {
      console.error("Failed to update minute detail:", error);
      alert("要約情報の更新に失敗しました");
    } finally {
      setSavingMinuteDetail(false);
    }
  };

  // Minute handlers
  const handleOpenMinuteModal = (minute?: Minute) => {
    if (minute) {
      setEditingMinute(minute);
      setMinuteTitle(minute.title);
      setMinuteContent(minute.content);
      setMinuteDocumentIds(minute.document_ids || []);
    } else {
      setEditingMinute(null);
      setMinuteTitle("");
      setMinuteContent("");
      setMinuteDocumentIds([]);
    }
    setShowMinuteModal(true);
  };

  const handleCloseMinuteModal = () => {
    setShowMinuteModal(false);
    setEditingMinute(null);
    setMinuteTitle("");
    setMinuteContent("");
    setMinuteDocumentIds([]);
  };

  const handleSaveMinute = async () => {
    if (!minuteTitle.trim() || !minuteContent.trim()) return;

    setSavingMinute(true);
    setMinuteSaveElapsedTime(null);
    const startTime = Date.now();
    try {
      if (editingMinute) {
        // Update existing minute
        await updateMinute(editingMinute.id, {
          title: minuteTitle.trim(),
          content: minuteContent.trim(),
        });
        // Update document links if changed
        const currentDocIds = editingMinute.document_ids || [];
        if (JSON.stringify(currentDocIds.sort()) !== JSON.stringify(minuteDocumentIds.sort())) {
          await updateMinuteDocuments(editingMinute.id, minuteDocumentIds);
        }
      } else {
        // Create new minute
        await createMinute(notebookId, {
          title: minuteTitle.trim(),
          content: minuteContent.trim(),
          document_ids: minuteDocumentIds,
        });
      }
      await loadMinutesList();
      setMinuteSaveElapsedTime((Date.now() - startTime) / 1000);
      handleCloseMinuteModal();
    } catch (e) {
      console.error("Failed to save minute:", e);
      alert(editingMinute ? "議事録の更新に失敗しました" : "議事録の作成に失敗しました");
    } finally {
      setSavingMinute(false);
    }
  };

  const handleEditMinute = async (minuteId: string) => {
    try {
      const minute = await getMinute(minuteId);
      handleOpenMinuteModal(minute);
    } catch (e) {
      console.error("Failed to load minute:", e);
      alert("議事録の読み込みに失敗しました");
    }
  };

  const handleDeleteMinuteConfirm = async () => {
    if (!deleteMinuteId) return;

    try {
      await deleteMinute(deleteMinuteId);
      setMinutes((prev) => prev.filter((m) => m.id !== deleteMinuteId));
      setDeleteMinuteId(null);
    } catch (e) {
      console.error("Failed to delete minute:", e);
      alert("議事録の削除に失敗しました");
    }
  };

  const handleToggleMinuteDocument = (docId: string) => {
    setMinuteDocumentIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSend = async () => {
    if (!question.trim() || loading) return;

    const selectedSourcesArray = Array.from(selectedSourceIds);

    // Determine flags based on chat mode
    const useRag = chatMode === "rag" && selectedSourcesArray.length > 0;
    const useFormattedText = chatMode === "fulltext" && selectedSourcesArray.length > 0;

    const userMsg: ChatMessage = {
      role: "user",
      content: question,
      timestamp: new Date(),
      status: "completed",
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setLoading(true);

    try {
      // Use async chat API for background processing
      const data = await sendChatAsync({
        notebook_id: notebookId,
        session_id: currentSessionId || undefined,
        source_ids: (useRag || useFormattedText) ? selectedSourcesArray : [],
        question: userMsg.content,
        use_rag: useRag,
        use_formatted_text: useFormattedText,
      });

      // If no session was selected, a new one was created
      if (!currentSessionId && data.session_id) {
        setCurrentSessionId(data.session_id);
        await loadSessions();
      }

      // Add assistant message with pending status
      // The usePendingMessages hook will poll for completion
      const aiMsg: ChatMessage = {
        id: data.assistant_message_id,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        status: "pending",
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
          status: "failed",
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

  const getFileColor = (fileType: string | undefined | null) => {
    if (!fileType) return "text-surface-400";
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

  // Sidebar resize handlers
  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  const stopResizing = useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = useCallback(
    (e: MouseEvent) => {
      if (isResizing && sidebarRef.current) {
        const newWidth = e.clientX - sidebarRef.current.getBoundingClientRect().left;
        // Min 200px, max 600px
        if (newWidth >= 200 && newWidth <= 600) {
          setSidebarWidth(newWidth);
        }
      }
    },
    [isResizing]
  );

  // Add mouse event listeners for resizing
  useEffect(() => {
    if (isResizing) {
      window.addEventListener("mousemove", resize);
      window.addEventListener("mouseup", stopResizing);
    }
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, [isResizing, resize, stopResizing]);

  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  return (
    <div className={`h-screen flex flex-col bg-surface-50 dark:bg-surface-950 ${isResizing ? "cursor-col-resize select-none" : ""}`}>
      <Header
        user={user}
        showBackButton
        backHref="/"
        backLabel="一覧に戻る"
        title={
          <span className="flex items-center gap-2">
            {notebook?.title}
            {notebook && (
              <button
                onClick={isOwner ? handleOpenNotebookSettings : undefined}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-all ${
                  notebook.is_public
                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                    : "bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400"
                } ${isOwner ? "hover:ring-2 hover:ring-primary-300 dark:hover:ring-primary-600 cursor-pointer" : "cursor-default"}`}
                title={isOwner ? "クリックして公開設定を変更" : undefined}
              >
                {notebook.is_public ? (
                  <>
                    <Globe className="w-3 h-3" />
                    公開
                  </>
                ) : (
                  <>
                    <Lock className="w-3 h-3" />
                    個人用
                  </>
                )}
                {isOwner && <Edit2 className="w-3 h-3 ml-0.5 opacity-60" />}
              </button>
            )}
          </span>
        }
        subtitle="ノートブック"
      />

      <main className="flex-1 flex overflow-hidden">
        {/* Sidebar Toggle Button (when collapsed) */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex-shrink-0 w-10 h-full border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 flex flex-col items-center pt-3 hover:bg-surface-50 dark:hover:bg-surface-800 transition-colors"
            title="サイドバーを開く"
          >
            <PanelLeft className="w-5 h-5 text-surface-500 dark:text-surface-400" />
          </button>
        )}

        {/* Left Panel - Sessions/Sources/Notes */}
        {sidebarOpen && (
          <aside
            ref={sidebarRef}
            style={{ width: sidebarWidth }}
            className="relative flex-shrink-0 border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 flex flex-col"
          >
            {/* Panel Header with Close Button */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-surface-200 dark:border-surface-700">
              <span className="text-xs font-medium text-surface-500 dark:text-surface-400">パネル</span>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
                title="サイドバーを閉じる"
              >
                <PanelLeftClose className="w-4 h-4 text-surface-500 dark:text-surface-400" />
              </button>
            </div>

            {/* Panel Tabs */}
            <div className="flex border-b border-surface-200 dark:border-surface-700">
              <button
                onClick={() => setActivePanel("sessions")}
                className={`flex-1 px-2 py-3 text-xs font-medium transition-colors ${
                  activePanel === "sessions"
                    ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-500"
                    : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
                }`}
              >
                <MessagesSquare className="w-4 h-4 inline-block mr-0.5" />
                会話
              </button>
              <button
                onClick={() => setActivePanel("sources")}
                className={`flex-1 px-2 py-3 text-xs font-medium transition-colors ${
                  activePanel === "sources"
                    ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-500"
                    : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
                }`}
              >
                <FileText className="w-4 h-4 inline-block mr-0.5" />
                資料
              </button>
            <button
              onClick={() => setActivePanel("notes")}
              className={`flex-1 px-2 py-3 text-xs font-medium transition-colors ${
                activePanel === "notes"
                  ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-500"
                  : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              }`}
            >
              <BookMarked className="w-4 h-4 inline-block mr-0.5" />
              ノート
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
              href={`/notebooks/${notebookId}/email`}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-surface-600 dark:text-surface-300 bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 hover:border-primary-400 dark:hover:border-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all"
            >
              <Mail className="w-4 h-4" />
              メール生成
            </Link>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activePanel === "sessions" ? (
              <div className="space-y-3">
                {/* Session Action Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={handleNewSession}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-xl cursor-pointer hover:border-primary-400 dark:hover:border-primary-600 hover:bg-primary-50/50 dark:hover:bg-primary-900/20 transition-all group"
                  >
                    <Plus className="w-5 h-5 text-surface-400 group-hover:text-primary-500 transition-colors" />
                    <span className="text-sm text-surface-500 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                      新しい会話を開始
                    </span>
                  </button>
                  {sessions.length > 0 && (
                    <button
                      onClick={() => setShowClearAllModal(true)}
                      className="px-3 py-3 border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-xl cursor-pointer hover:border-red-400 dark:hover:border-red-600 hover:bg-red-50/50 dark:hover:bg-red-900/20 transition-all group"
                      title="すべての会話を削除"
                    >
                      <Trash2 className="w-5 h-5 text-surface-400 group-hover:text-red-500 transition-colors" />
                    </button>
                  )}
                </div>

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
                {/* Multi-File Uploader */}
                <MultiFileUploader
                  notebookId={notebookId}
                  onSourceAdded={(source) => {
                    setSources((prev) => [...prev, source]);
                    setSelectedSourceIds((prev) => new Set([...prev, source.id]));
                  }}
                />

                {/* Folder & Source Selection Controls */}
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowCreateFolderModal(true)}
                      className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
                    >
                      <FolderPlus className="w-3.5 h-3.5" />
                      フォルダ作成
                    </button>
                    {sources.length > 0 && (
                      <>
                        <span className="text-surface-300 dark:text-surface-600">|</span>
                        <button
                          onClick={handleSelectAllSources}
                          className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
                        >
                          全選択
                        </button>
                        <span className="text-surface-300 dark:text-surface-600">|</span>
                        <button
                          onClick={handleDeselectAllSources}
                          className="text-xs text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-300 transition-colors"
                        >
                          解除
                        </button>
                      </>
                    )}
                  </div>
                  {sources.length > 0 && (
                    <span className="text-xs text-surface-500 dark:text-surface-400">
                      {selectedSourceIds.size}/{sources.length}
                    </span>
                  )}
                </div>

                {/* Sources List with Folders */}
                {sources.length === 0 && folders.length === 0 ? (
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
                  <>
                    {/* Folders */}
                    {folders.map((folder) => {
                      const folderSources = getSourcesByFolder(folder.id);
                      const isExpanded = expandedFolders.has(folder.id);
                      const isFolderEditing = editingFolderId === folder.id;
                      return (
                        <div key={folder.id} className="space-y-1">
                          {/* Folder Header */}
                          <div
                            onClick={() => !isFolderEditing && handleToggleFolder(folder.id)}
                            className="group flex items-center gap-2 p-2 rounded-lg bg-surface-100 dark:bg-surface-800 cursor-pointer hover:bg-surface-150 dark:hover:bg-surface-750 transition-colors"
                          >
                            <button className="text-surface-500 dark:text-surface-400">
                              {isExpanded ? (
                                <FolderOpen className="w-4 h-4 text-amber-500" />
                              ) : (
                                <Folder className="w-4 h-4 text-amber-500" />
                              )}
                            </button>
                            {isFolderEditing ? (
                              <div className="flex-1 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                <input
                                  type="text"
                                  value={editingFolderName}
                                  onChange={(e) => setEditingFolderName(e.target.value)}
                                  onKeyDown={(e) => handleFolderEditKeyDown(e, folder.id)}
                                  className="flex-1 px-2 py-0.5 text-sm bg-white dark:bg-surface-700 border border-primary-300 dark:border-primary-600 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                                  autoFocus
                                />
                                <button
                                  onClick={() => handleSaveFolderName(folder.id)}
                                  className="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900/30"
                                >
                                  <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                                </button>
                                <button
                                  onClick={handleCancelEditFolder}
                                  className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                >
                                  <X className="w-3.5 h-3.5 text-surface-500" />
                                </button>
                              </div>
                            ) : (
                              <>
                                <span className="flex-1 text-sm font-medium text-surface-700 dark:text-surface-200 truncate">
                                  {folder.name}
                                </span>
                                <span className="text-xs text-surface-400 dark:text-surface-500">
                                  {folderSources.length}
                                </span>
                                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                                  <button
                                    onClick={(e) => handleStartEditFolder(folder, e)}
                                    className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                  >
                                    <Edit2 className="w-3.5 h-3.5 text-surface-500 dark:text-surface-400" />
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setDeleteFolderId(folder.id);
                                    }}
                                    className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
                                  >
                                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                  </button>
                                </div>
                                <ChevronDown className={`w-4 h-4 text-surface-400 transition-transform ${isExpanded ? "" : "-rotate-90"}`} />
                              </>
                            )}
                          </div>
                          {/* Folder Sources */}
                          {isExpanded && folderSources.length > 0 && (
                            <div className="ml-4 space-y-1">
                              {folderSources.map((src) => {
                                const isSelected = selectedSourceIds.has(src.id);
                                const isEditing = editingSourceId === src.id;
                                return (
                                  <div
                                    key={src.id}
                                    onClick={() => !isEditing && handleToggleSourceSelection(src.id)}
                                    className={`group p-2 rounded-lg cursor-pointer transition-all ${
                                      isSelected
                                        ? "bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800"
                                        : "bg-surface-50 dark:bg-surface-800/50 border border-transparent hover:bg-surface-100 dark:hover:bg-surface-700"
                                    }`}
                                  >
                                    <div className="flex items-center gap-2">
                                      <div className="flex-shrink-0">
                                        {isSelected ? (
                                          <CheckSquare className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                                        ) : (
                                          <Square className="w-4 h-4 text-surface-400 dark:text-surface-500" />
                                        )}
                                      </div>
                                      <div className={`flex-shrink-0 ${getFileColor(src.file_type)}`}>
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
                                              className="flex-1 px-2 py-0.5 text-sm bg-white dark:bg-surface-700 border border-primary-300 dark:border-primary-600 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                                              autoFocus
                                            />
                                            <button
                                              onClick={() => handleSaveSourceTitle(src.id)}
                                              className="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900/30"
                                            >
                                              <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                                            </button>
                                            <button
                                              onClick={handleCancelEditSource}
                                              className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                            >
                                              <X className="w-3.5 h-3.5 text-surface-500" />
                                            </button>
                                          </div>
                                        ) : (
                                          <p className={`text-sm truncate ${
                                            isSelected
                                              ? "text-primary-700 dark:text-primary-300"
                                              : "text-surface-700 dark:text-surface-200"
                                          }`}>
                                            {src.title}
                                          </p>
                                        )}
                                      </div>
                                      {!isEditing && (
                                        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                                          <button
                                            onClick={(e) => handleOpenSourceDetail(src.id, e)}
                                            className="p-1 rounded hover:bg-primary-100 dark:hover:bg-primary-900/30"
                                            title="詳細"
                                          >
                                            <Eye className="w-3.5 h-3.5 text-primary-500 dark:text-primary-400" />
                                          </button>
                                          <button
                                            onClick={(e) => handleOpenMoveModal(src.id, e)}
                                            className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                            title="移動"
                                          >
                                            <Folder className="w-3.5 h-3.5 text-surface-500 dark:text-surface-400" />
                                          </button>
                                          <button
                                            onClick={(e) => handleStartEditSource(src, e)}
                                            className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                          >
                                            <Edit2 className="w-3.5 h-3.5 text-surface-500 dark:text-surface-400" />
                                          </button>
                                          <button
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              setDeleteSourceId(src.id);
                                            }}
                                            className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
                                          >
                                            <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* Unfiled Sources (no folder) */}
                    {getSourcesByFolder(null).length > 0 && (
                      <div className="space-y-1">
                        {folders.length > 0 && (
                          <div className="flex items-center gap-2 px-2 py-1">
                            <FileText className="w-4 h-4 text-surface-400" />
                            <span className="text-xs text-surface-500 dark:text-surface-400">
                              未整理 ({getSourcesByFolder(null).length})
                            </span>
                          </div>
                        )}
                        {getSourcesByFolder(null).map((src) => {
                          const isSelected = selectedSourceIds.has(src.id);
                          const isEditing = editingSourceId === src.id;
                          return (
                            <div
                              key={src.id}
                              onClick={() => !isEditing && handleToggleSourceSelection(src.id)}
                              className={`group p-2 rounded-lg cursor-pointer transition-all ${
                                isSelected
                                  ? "bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800"
                                  : "bg-surface-50 dark:bg-surface-800 border border-transparent hover:bg-surface-100 dark:hover:bg-surface-700"
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                <div className="flex-shrink-0">
                                  {isSelected ? (
                                    <CheckSquare className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                                  ) : (
                                    <Square className="w-4 h-4 text-surface-400 dark:text-surface-500" />
                                  )}
                                </div>
                                <div className={`flex-shrink-0 ${getFileColor(src.file_type)}`}>
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
                                        className="flex-1 px-2 py-0.5 text-sm bg-white dark:bg-surface-700 border border-primary-300 dark:border-primary-600 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                                        autoFocus
                                      />
                                      <button
                                        onClick={() => handleSaveSourceTitle(src.id)}
                                        className="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900/30"
                                      >
                                        <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                                      </button>
                                      <button
                                        onClick={handleCancelEditSource}
                                        className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                      >
                                        <X className="w-3.5 h-3.5 text-surface-500" />
                                      </button>
                                    </div>
                                  ) : (
                                    <p className={`text-sm truncate ${
                                      isSelected
                                        ? "text-primary-700 dark:text-primary-300"
                                        : "text-surface-700 dark:text-surface-200"
                                    }`}>
                                      {src.title}
                                    </p>
                                  )}
                                </div>
                                {!isEditing && (
                                  <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                                    <button
                                      onClick={(e) => handleOpenSourceDetail(src.id, e)}
                                      className="p-1 rounded hover:bg-primary-100 dark:hover:bg-primary-900/30"
                                      title="詳細"
                                    >
                                      <Eye className="w-3.5 h-3.5 text-primary-500 dark:text-primary-400" />
                                    </button>
                                    <button
                                      onClick={(e) => handleOpenMoveModal(src.id, e)}
                                      className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                      title="フォルダに移動"
                                    >
                                      <Folder className="w-3.5 h-3.5 text-surface-500 dark:text-surface-400" />
                                    </button>
                                    <button
                                      onClick={(e) => handleStartEditSource(src, e)}
                                      className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                                    >
                                      <Edit2 className="w-3.5 h-3.5 text-surface-500 dark:text-surface-400" />
                                    </button>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setDeleteSourceId(src.id);
                                      }}
                                      className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
                                    >
                                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}

                {/* === 議事録セクション === */}
                <div className="border-t border-surface-200 dark:border-surface-700 pt-3 mt-3">
                  <div className="flex items-center justify-between mb-2 px-1">
                    <span className="text-xs font-medium text-surface-500 dark:text-surface-400 flex items-center gap-1.5">
                      <ClipboardList className="w-4 h-4 text-green-500" />
                      議事録
                    </span>
                    <span className="text-xs text-surface-400 dark:text-surface-500">
                      {minutes.length}件
                    </span>
                  </div>

                  {/* New Minute Button */}
                  <button
                    onClick={() => handleOpenMinuteModal()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-lg cursor-pointer hover:border-green-400 dark:hover:border-green-600 hover:bg-green-50/50 dark:hover:bg-green-900/20 transition-all group"
                  >
                    <Plus className="w-4 h-4 text-surface-400 group-hover:text-green-500 transition-colors" />
                    <span className="text-xs text-surface-500 group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">
                      新しい議事録を作成
                    </span>
                  </button>

                  {minuteSaveElapsedTime !== null && (
                    <p className="text-xs text-surface-500 text-center mt-1">
                      処理時間: {minuteSaveElapsedTime.toFixed(1)}秒
                    </p>
                  )}

                  {/* Minutes List */}
                  {minutesLoading ? (
                    <div className="flex justify-center py-4">
                      <Spinner size="sm" />
                    </div>
                  ) : minutes.length > 0 && (
                    <div className="space-y-1 mt-2">
                      {minutes.map((minute) => (
                        <div
                          key={minute.id}
                          className="group p-2 bg-surface-50 dark:bg-surface-800 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <ClipboardList className="w-4 h-4 text-green-500 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-surface-700 dark:text-surface-200 truncate">
                                {minute.title}
                              </p>
                              <div className="flex items-center gap-1.5 mt-0.5 text-xs text-surface-400 dark:text-surface-500">
                                <span>{minute.document_count}件の資料</span>
                                <span>·</span>
                                <span>{formatDate(minute.updated_at)}</span>
                              </div>
                            </div>
                            <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                              <button
                                onClick={(e) => handleOpenMinuteDetail(minute.id, e)}
                                className="p-1 rounded hover:bg-primary-100 dark:hover:bg-primary-900/30"
                                title="詳細"
                              >
                                <Eye className="w-3.5 h-3.5 text-primary-500 dark:text-primary-400" />
                              </button>
                              <button
                                onClick={() => handleEditMinute(minute.id)}
                                className="p-1 rounded hover:bg-surface-200 dark:hover:bg-surface-600"
                              >
                                <Edit2 className="w-3.5 h-3.5 text-surface-500 dark:text-surface-400" />
                              </button>
                              <button
                                onClick={() => setDeleteMinuteId(minute.id)}
                                className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
                              >
                                <Trash2 className="w-3.5 h-3.5 text-red-500" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : activePanel === "notes" ? (
              <div className="space-y-3">
                {selectedNote ? (
                  <div className="animate-fade-in">
                    <button
                      onClick={() => {
                        setSelectedNote(null);
                        setIsEditingNoteContent(false);
                        setEditingNoteContent("");
                      }}
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

                      {/* Note Content - Editable */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs font-medium text-surface-500 dark:text-surface-400">
                            {selectedNote.content ? "メモ内容（編集済み）" : "回答"}
                          </p>
                          {!isEditingNoteContent && (
                            <button
                              onClick={handleStartEditNoteContent}
                              className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                            >
                              <Edit2 className="w-3 h-3" />
                              編集
                            </button>
                          )}
                        </div>
                        {isEditingNoteContent ? (
                          <div className="space-y-2">
                            <textarea
                              value={editingNoteContent}
                              onChange={(e) => setEditingNoteContent(e.target.value)}
                              className="w-full h-48 p-3 text-sm text-surface-700 dark:text-surface-200 bg-white dark:bg-surface-700 border border-surface-300 dark:border-surface-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
                              placeholder="メモの内容を入力..."
                            />
                            <div className="flex gap-2">
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={handleSaveNoteContent}
                                isLoading={savingNoteContent}
                                leftIcon={<Save className="w-4 h-4" />}
                              >
                                保存
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleCancelEditNoteContent}
                                disabled={savingNoteContent}
                              >
                                キャンセル
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="text-sm text-surface-700 dark:text-surface-200 bg-surface-50 dark:bg-surface-800 p-3 rounded-lg whitespace-pre-wrap">
                            {selectedNote.content || selectedNote.answer || "（内容なし）"}
                          </div>
                        )}
                      </div>

                      {/* Original answer reference (shown only if custom content is set) */}
                      {selectedNote.content && selectedNote.answer && (
                        <div className="mb-4">
                          <p className="text-xs font-medium text-surface-400 dark:text-surface-500 mb-1">
                            元の回答
                          </p>
                          <div className="text-sm text-surface-500 dark:text-surface-400 bg-surface-100 dark:bg-surface-900 p-3 rounded-lg whitespace-pre-wrap max-h-32 overflow-y-auto">
                            {selectedNote.answer}
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

                      {selectedNote.updated_at && (
                        <p className="text-xs text-surface-400 dark:text-surface-500 mb-3">
                          最終更新: {new Date(selectedNote.updated_at).toLocaleString()}
                        </p>
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
            ) : null}
          </div>

          {/* Resize Handle */}
          <div
            onMouseDown={startResizing}
            className={`absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-primary-400 dark:hover:bg-primary-600 transition-colors ${
              isResizing ? "bg-primary-500" : "bg-transparent"
            }`}
            title="ドラッグして幅を調整"
          >
            <div className="absolute top-1/2 -translate-y-1/2 -right-1 w-3 h-8 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <GripVertical className="w-3 h-3 text-surface-400" />
            </div>
          </div>
        </aside>
        )}

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
                            : msg.status === "failed"
                            ? "bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-700 rounded-bl-md shadow-soft-sm"
                            : "bg-white dark:bg-surface-800 text-surface-800 dark:text-surface-100 border border-surface-200 dark:border-surface-700 rounded-bl-md shadow-soft-sm"
                        }`}
                      >
                        {msg.role === "assistant" && (msg.status === "pending" || msg.status === "generating") ? (
                          <div className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
                            <span className="text-sm text-surface-500 dark:text-surface-400">
                              {msg.status === "pending" ? "回答を準備中..." : "回答を生成中..."}
                            </span>
                          </div>
                        ) : msg.status === "failed" ? (
                          <div className="flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-red-500" />
                            <p className="text-sm">
                              {msg.error_message || "エラーが発生しました"}
                            </p>
                          </div>
                        ) : (
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">
                            {msg.content}
                          </p>
                        )}
                      </div>

                      {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && msg.status === "completed" && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {msg.sources.map((ref, i) => (
                            <Badge key={i} variant="secondary" size="sm">
                              <FileText className="w-3 h-3" />
                              {ref}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {msg.role === "assistant" && msg.id && msg.status === "completed" && (
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
              {/* チャットモード切替 */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setChatMode("rag")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all ${
                      chatMode === "rag"
                        ? "bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 font-medium"
                        : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <Search className="w-3.5 h-3.5" />
                    RAG検索
                  </button>
                  <button
                    onClick={() => setChatMode("fulltext")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all ${
                      chatMode === "fulltext"
                        ? "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 font-medium"
                        : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    全文参照
                  </button>
                  <button
                    onClick={() => setChatMode("free")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all ${
                      chatMode === "free"
                        ? "bg-accent-100 dark:bg-accent-900/50 text-accent-700 dark:text-accent-300 font-medium"
                        : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700"
                    }`}
                  >
                    <MessageCircle className="w-3.5 h-3.5" />
                    自由入力
                  </button>
                </div>
                {(chatMode === "rag" || chatMode === "fulltext") && sources.length === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <FileUp className="w-3.5 h-3.5" />
                    このモードにはソースが必要です
                  </p>
                )}
                {(chatMode === "rag" || chatMode === "fulltext") && sources.length > 0 && selectedSourceIds.size === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <Square className="w-3.5 h-3.5" />
                    ソースを選択してください
                  </p>
                )}
                {(chatMode === "rag" || chatMode === "fulltext") && selectedSourceIds.size > 0 && (
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
                      chatMode === "rag"
                        ? "ドキュメントについて質問してください...（Shift+Enterで改行）"
                        : chatMode === "fulltext"
                        ? "ドキュメント全文を参照して質問してください...（Shift+Enterで改行）"
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
                {chatMode === "rag"
                  ? "RAG検索モード：アップロードしたドキュメントから関連情報を検索して回答します"
                  : chatMode === "fulltext"
                  ? "全文参照モード：ドキュメント全文を参照して詳細に回答します"
                  : "自由入力モード：ドキュメントを参照せず、AIと直接対話します"
                }
                {currentSessionId && " | 会話履歴は自動的に引き継がれます"}
                {currentSessionId && (
                  <span className="ml-2">
                    |
                    <ExportButton
                      type="chat"
                      id={notebookId}
                      sessionId={currentSessionId}
                      className="ml-2 inline-flex"
                      variant="ghost"
                      size="sm"
                    />
                  </span>
                )}
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

      {/* Clear All Sessions Modal */}
      <Modal
        isOpen={showClearAllModal}
        onClose={() => setShowClearAllModal(false)}
        title="すべての会話を削除"
        description="このノートブックのすべての会話履歴が完全に削除されます。この操作は取り消せません。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setShowClearAllModal(false)} disabled={clearingAll}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleClearAllSessions}
            leftIcon={clearingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            disabled={clearingAll}
          >
            {clearingAll ? "削除中..." : "すべて削除"}
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

      {/* Delete Minute Modal */}
      <Modal
        isOpen={!!deleteMinuteId}
        onClose={() => setDeleteMinuteId(null)}
        title="議事録を削除"
        description="議事録と関連するデータが完全に削除されます。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteMinuteId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteMinuteConfirm}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Create/Edit Minute Modal */}
      <Modal
        isOpen={showMinuteModal}
        onClose={handleCloseMinuteModal}
        title={editingMinute ? "議事録を編集" : "新しい議事録を作成"}
        description="議事録をテキストで入力し、関連する資料を選択できます"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              タイトル <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={minuteTitle}
              onChange={(e) => setMinuteTitle(e.target.value)}
              placeholder="例: 第3回プロジェクト定例会議"
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              本文 <span className="text-red-500">*</span>
              <span className="text-xs text-surface-400 ml-2">
                ({minuteContent.length.toLocaleString()} / 50,000文字)
              </span>
            </label>
            <textarea
              value={minuteContent}
              onChange={(e) => setMinuteContent(e.target.value.slice(0, 50000))}
              placeholder={`例:
【日時】2024/12/05 14:00-15:00
【参加者】田中、鈴木、佐藤

【議題1】進捗報告
田中: 設計フェーズ完了、来週から実装開始
鈴木: テスト環境構築中

【決定事項】
- 次回会議は来週金曜日に設定`}
              rows={10}
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
            />
          </div>

          {sources.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
                関連資料（任意）
              </label>
              <div className="max-h-40 overflow-y-auto border border-surface-200 dark:border-surface-700 rounded-xl p-2 space-y-1">
                {sources.map((source) => (
                  <label
                    key={source.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-surface-50 dark:hover:bg-surface-800 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={minuteDocumentIds.includes(source.id)}
                      onChange={() => handleToggleMinuteDocument(source.id)}
                      className="rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                    />
                    <FileText className={`w-4 h-4 ${getFileColor(source.file_type)}`} />
                    <span className="text-sm text-surface-700 dark:text-surface-200 truncate">
                      {source.title}
                    </span>
                    <span className="text-xs text-surface-400 dark:text-surface-500 ml-auto">
                      {source.file_type?.toUpperCase() || ""}
                    </span>
                  </label>
                ))}
              </div>
              {minuteDocumentIds.length > 0 && (
                <p className="text-xs text-surface-500 mt-1">
                  {minuteDocumentIds.length}件の資料を選択中
                </p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={handleCloseMinuteModal}>
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveMinute}
              isLoading={savingMinute}
              disabled={!minuteTitle.trim() || !minuteContent.trim()}
              leftIcon={<ClipboardList className="w-4 h-4" />}
            >
              {editingMinute ? "更新" : "作成"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Source Detail Modal */}
      <Modal
        isOpen={showSourceDetailModal}
        onClose={handleCloseSourceDetail}
        title={sourceDetail?.title || "資料の詳細"}
        description={`ファイル形式: ${sourceDetail?.file_type?.toUpperCase() || ""}`}
        size="full"
      >
        {sourceDetailLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin mb-4" />
            <p className="text-sm text-surface-500">読み込み中...</p>
          </div>
        ) : sourceDetail ? (
          <div className="space-y-5 max-h-[70vh] overflow-y-auto">
            {/* Header with Status and Edit Toggle */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-surface-600 dark:text-surface-400">処理状態:</span>
                {sourceDetail.processing_status === "completed" ? (
                  <Badge variant="success" size="sm">完了</Badge>
                ) : sourceDetail.processing_status === "processing" ? (
                  <Badge variant="warning" size="sm">処理中</Badge>
                ) : sourceDetail.processing_status === "failed" ? (
                  <Badge variant="danger" size="sm">失敗</Badge>
                ) : (
                  <Badge variant="secondary" size="sm">待機中</Badge>
                )}
              </div>
              <Button
                variant={isEditingSourceDetail ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setIsEditingSourceDetail(!isEditingSourceDetail)}
                leftIcon={<Edit2 className="w-4 h-4" />}
              >
                {isEditingSourceDetail ? "編集中" : "編集"}
              </Button>
            </div>

            {/* Error Message */}
            {sourceDetail.processing_error && (
              <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-700 dark:text-red-300">処理エラー</p>
                  <p className="text-sm text-red-600 dark:text-red-400 mt-1">{sourceDetail.processing_error}</p>
                </div>
              </div>
            )}

            {/* Two-column layout for formatted text and summary */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Formatted Text */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-800 dark:text-surface-200">
                    整形されたテキスト
                  </h3>
                  <span className="text-xs text-surface-400">
                    {(sourceDetail.formatted_text?.length || 0).toLocaleString()}文字
                  </span>
                </div>
                {isEditingSourceDetail ? (
                  <textarea
                    value={editingFormattedText}
                    onChange={(e) => setEditingFormattedText(e.target.value)}
                    rows={14}
                    className="w-full px-4 py-3 text-sm bg-white dark:bg-surface-800 border border-primary-300 dark:border-primary-700 rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    placeholder="整形されたテキストがありません"
                  />
                ) : (
                  <div className="w-full px-4 py-3 text-sm bg-surface-50 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-xl min-h-[320px] max-h-[500px] overflow-y-auto">
                    <p className="text-surface-700 dark:text-surface-300 whitespace-pre-line leading-relaxed">
                      {cleanupText(sourceDetail.formatted_text) || "(整形されたテキストがありません)"}
                    </p>
                  </div>
                )}
              </div>

              {/* Summary */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-800 dark:text-surface-200">
                    要約
                  </h3>
                  <span className="text-xs text-surface-400">
                    {(sourceDetail.summary?.length || 0).toLocaleString()}文字
                  </span>
                </div>
                {isEditingSourceDetail ? (
                  <textarea
                    value={editingSummary}
                    onChange={(e) => setEditingSummary(e.target.value)}
                    rows={14}
                    className="w-full px-4 py-3 text-sm bg-white dark:bg-surface-800 border border-primary-300 dark:border-primary-700 rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    placeholder="要約がありません"
                  />
                ) : (
                  <div className="w-full px-4 py-3 text-sm bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-xl min-h-[320px] max-h-[500px] overflow-y-auto">
                    <p className="text-surface-700 dark:text-surface-300 whitespace-pre-line leading-relaxed">
                      {cleanupText(sourceDetail.summary) || "(要約がありません)"}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Original Text (Collapsible) */}
            <details className="group">
              <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-surface-600 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200 transition-colors">
                <FileText className="w-4 h-4" />
                抽出された元テキストを表示
                <span className="text-xs text-surface-400 ml-1">
                  ({(sourceDetail.full_text?.length || 0).toLocaleString()}文字)
                </span>
              </summary>
              <div className="mt-3 w-full px-4 py-3 text-sm bg-surface-100 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl max-h-60 overflow-y-auto">
                <p className="text-surface-600 dark:text-surface-400 whitespace-pre-wrap">
                  {sourceDetail.full_text || "(テキストなし)"}
                </p>
              </div>
            </details>

            {/* Footer Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-surface-200 dark:border-surface-700">
              <div>
                {sourceDetailElapsedTime !== null && (
                  <span className="text-xs text-surface-500">
                    処理時間: {sourceDetailElapsedTime.toFixed(1)}秒
                  </span>
                )}
              </div>
              <div className="flex gap-3">
                <Button variant="ghost" onClick={handleCloseSourceDetail}>
                  閉じる
                </Button>
                {isEditingSourceDetail && (
                  <Button
                    variant="primary"
                    onClick={handleSaveSourceDetail}
                    isLoading={savingSourceDetail}
                    leftIcon={<Save className="w-4 h-4" />}
                  >
                    保存
                  </Button>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </Modal>

      {/* Minute Detail Modal */}
      <Modal
        isOpen={showMinuteDetailModal}
        onClose={handleCloseMinuteDetail}
        title={minuteDetail?.title || "議事録の詳細"}
        description={minuteDetail ? `関連資料: ${minuteDetail.document_ids?.length || 0}件` : ""}
        size="full"
      >
        {minuteDetailLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin mb-4" />
            <p className="text-sm text-surface-500">読み込み中...</p>
          </div>
        ) : minuteDetail ? (
          <div className="space-y-5 max-h-[70vh] overflow-y-auto">
            {/* Header with Status and Edit Toggle */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-surface-600 dark:text-surface-400">処理状態:</span>
                {minuteDetail.processing_status === "completed" ? (
                  <Badge variant="success" size="sm">完了</Badge>
                ) : minuteDetail.processing_status === "processing" ? (
                  <Badge variant="warning" size="sm">処理中</Badge>
                ) : minuteDetail.processing_status === "failed" ? (
                  <Badge variant="danger" size="sm">失敗</Badge>
                ) : (
                  <Badge variant="secondary" size="sm">待機中</Badge>
                )}
              </div>
              <Button
                variant={isEditingMinuteDetail ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setIsEditingMinuteDetail(!isEditingMinuteDetail)}
                leftIcon={<Edit2 className="w-4 h-4" />}
              >
                {isEditingMinuteDetail ? "編集中" : "編集"}
              </Button>
            </div>

            {/* Error Message */}
            {minuteDetail.processing_error && (
              <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-700 dark:text-red-300">処理エラー</p>
                  <p className="text-sm text-red-600 dark:text-red-400 mt-1">{minuteDetail.processing_error}</p>
                </div>
              </div>
            )}

            {/* Two-column layout for formatted content and summary */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Formatted Content */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-800 dark:text-surface-200">
                    整形されたコンテンツ
                  </h3>
                  <span className="text-xs text-surface-400">
                    {(minuteDetail.formatted_content?.length || 0).toLocaleString()}文字
                  </span>
                </div>
                {isEditingMinuteDetail ? (
                  <textarea
                    value={editingMinuteFormattedContent}
                    onChange={(e) => setEditingMinuteFormattedContent(e.target.value)}
                    rows={14}
                    className="w-full px-4 py-3 text-sm bg-white dark:bg-surface-800 border border-primary-300 dark:border-primary-700 rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    placeholder="整形されたコンテンツがありません"
                  />
                ) : (
                  <div className="w-full px-4 py-3 text-sm bg-surface-50 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-xl min-h-[320px] max-h-[500px] overflow-y-auto">
                    <p className="text-surface-700 dark:text-surface-300 whitespace-pre-line leading-relaxed">
                      {cleanupText(minuteDetail.formatted_content) || "(整形されたコンテンツがありません)"}
                    </p>
                  </div>
                )}
              </div>

              {/* Summary */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-800 dark:text-surface-200">
                    要約
                  </h3>
                  <span className="text-xs text-surface-400">
                    {(minuteDetail.summary?.length || 0).toLocaleString()}文字
                  </span>
                </div>
                {isEditingMinuteDetail ? (
                  <textarea
                    value={editingMinuteSummary}
                    onChange={(e) => setEditingMinuteSummary(e.target.value)}
                    rows={14}
                    className="w-full px-4 py-3 text-sm bg-white dark:bg-surface-800 border border-primary-300 dark:border-primary-700 rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    placeholder="要約がありません"
                  />
                ) : (
                  <div className="w-full px-4 py-3 text-sm bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl min-h-[320px] max-h-[500px] overflow-y-auto">
                    <p className="text-surface-700 dark:text-surface-300 whitespace-pre-line leading-relaxed">
                      {cleanupText(minuteDetail.summary) || "(要約がありません)"}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Original Content (Collapsible) */}
            <details className="group">
              <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-surface-600 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200 transition-colors">
                <ClipboardList className="w-4 h-4" />
                元のコンテンツを表示
                <span className="text-xs text-surface-400 ml-1">
                  ({(minuteDetail.content?.length || 0).toLocaleString()}文字)
                </span>
              </summary>
              <div className="mt-3 w-full px-4 py-3 text-sm bg-surface-100 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl max-h-60 overflow-y-auto">
                <p className="text-surface-600 dark:text-surface-400 whitespace-pre-wrap">
                  {minuteDetail.content || "(コンテンツなし)"}
                </p>
              </div>
            </details>

            {/* Footer Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-surface-200 dark:border-surface-700">
              <div>
                {minuteDetailElapsedTime !== null && (
                  <span className="text-xs text-surface-500">
                    処理時間: {minuteDetailElapsedTime.toFixed(1)}秒
                  </span>
                )}
              </div>
              <div className="flex gap-3">
                <Button variant="ghost" onClick={handleCloseMinuteDetail}>
                  閉じる
                </Button>
                {isEditingMinuteDetail && (
                  <Button
                    variant="primary"
                    onClick={handleSaveMinuteDetail}
                    isLoading={savingMinuteDetail}
                    leftIcon={<Save className="w-4 h-4" />}
                  >
                    保存
                  </Button>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </Modal>

      {/* Notebook Settings Modal */}
      <Modal
        isOpen={showNotebookSettingsModal}
        onClose={() => setShowNotebookSettingsModal(false)}
        title="ノートブック設定"
        description="タイトル、説明、公開設定を変更できます"
      >
        <div className="space-y-4">
          {/* Title Input */}
          <Input
            label="タイトル"
            placeholder="ノートブックのタイトル"
            value={editNotebookTitle}
            onChange={(e) => setEditNotebookTitle(e.target.value)}
          />

          {/* Description Textarea */}
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              説明（任意）
            </label>
            <textarea
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="このノートブックの目的を入力してください"
              value={editNotebookDesc}
              onChange={(e) => setEditNotebookDesc(e.target.value)}
            />
          </div>

          {/* Public/Private Toggle */}
          <div className="flex items-center justify-between p-4 bg-surface-50 dark:bg-surface-800/50 rounded-xl">
            <div className="flex items-center gap-3">
              {notebook?.is_public ? (
                <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <Globe className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-lg bg-surface-100 dark:bg-surface-700 flex items-center justify-center">
                  <Lock className="w-5 h-5 text-surface-500" />
                </div>
              )}
              <div>
                <p className="text-sm font-medium text-surface-900 dark:text-surface-100">
                  {notebook?.is_public ? "公開ノートブック" : "個人用ノートブック"}
                </p>
                <p className="text-xs text-surface-500 dark:text-surface-400">
                  {notebook?.is_public
                    ? "全ユーザーがアクセス・編集可能"
                    : "自分だけがアクセス可能"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleToggleNotebookPublic}
              disabled={savingNotebookSettings}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                notebook?.is_public ? "bg-green-500" : "bg-surface-300 dark:bg-surface-600"
              } ${savingNotebookSettings ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  notebook?.is_public ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          <div className="text-xs text-surface-500 dark:text-surface-400 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <p className="font-medium text-amber-700 dark:text-amber-300 mb-1">公開設定について</p>
            <p>公開に変更すると、全ユーザーがこのノートブックにアクセスし、資料の追加・編集・削除が可能になります。</p>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => setShowNotebookSettingsModal(false)}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveNotebookSettings}
              isLoading={savingNotebookSettings}
              disabled={!editNotebookTitle.trim()}
              leftIcon={<Save className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Folder Modal */}
      <Modal
        isOpen={showCreateFolderModal}
        onClose={() => {
          setShowCreateFolderModal(false);
          setNewFolderName("");
        }}
        title="フォルダを作成"
        description="ソースを整理するためのフォルダを作成します"
      >
        <div className="space-y-4">
          <Input
            label="フォルダ名"
            placeholder="フォルダ名を入力"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleCreateFolder();
              }
            }}
            autoFocus
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setShowCreateFolderModal(false);
                setNewFolderName("");
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreateFolder}
              isLoading={creatingFolder}
              disabled={!newFolderName.trim()}
              leftIcon={<FolderPlus className="w-4 h-4" />}
            >
              作成
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Folder Confirmation Modal */}
      <Modal
        isOpen={deleteFolderId !== null}
        onClose={() => setDeleteFolderId(null)}
        title="フォルダを削除"
        description="この操作は取り消せません"
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-300">
                  フォルダ内のすべてのソースも削除されます
                </p>
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                  この操作は元に戻せません。続行しますか？
                </p>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setDeleteFolderId(null)}>
              キャンセル
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteFolder}
              leftIcon={<Trash2 className="w-4 h-4" />}
            >
              削除
            </Button>
          </div>
        </div>
      </Modal>

      {/* Move Source Modal */}
      <Modal
        isOpen={showMoveModal}
        onClose={() => {
          setShowMoveModal(false);
          setMovingSourceId(null);
        }}
        title="ソースを移動"
        description="移動先のフォルダを選択してください"
      >
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {/* No folder option */}
          <button
            onClick={() => handleMoveSource(null)}
            className="w-full flex items-center gap-3 p-3 rounded-lg bg-surface-50 dark:bg-surface-800 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors text-left"
          >
            <FileText className="w-5 h-5 text-surface-400" />
            <div>
              <p className="text-sm font-medium text-surface-700 dark:text-surface-200">
                未整理（フォルダなし）
              </p>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                フォルダから取り出します
              </p>
            </div>
          </button>
          {/* Folder options */}
          {folders.map((folder) => {
            const currentSource = sources.find((s) => s.id === movingSourceId);
            const isCurrentFolder = currentSource?.folder_id === folder.id;
            return (
              <button
                key={folder.id}
                onClick={() => handleMoveSource(folder.id)}
                disabled={isCurrentFolder}
                className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors text-left ${
                  isCurrentFolder
                    ? "bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800 cursor-not-allowed"
                    : "bg-surface-50 dark:bg-surface-800 hover:bg-surface-100 dark:hover:bg-surface-700"
                }`}
              >
                <Folder className="w-5 h-5 text-amber-500" />
                <div>
                  <p className={`text-sm font-medium ${
                    isCurrentFolder
                      ? "text-primary-700 dark:text-primary-300"
                      : "text-surface-700 dark:text-surface-200"
                  }`}>
                    {folder.name}
                    {isCurrentFolder && (
                      <span className="ml-2 text-xs text-primary-500">現在のフォルダ</span>
                    )}
                  </p>
                  <p className="text-xs text-surface-500 dark:text-surface-400">
                    {folder.source_count}件のソース
                  </p>
                </div>
              </button>
            );
          })}
        </div>
        <div className="flex justify-end gap-3 pt-4 mt-4 border-t border-surface-200 dark:border-surface-700">
          <Button
            variant="ghost"
            onClick={() => {
              setShowMoveModal(false);
              setMovingSourceId(null);
            }}
          >
            キャンセル
          </Button>
        </div>
      </Modal>
    </div>
  );
}
