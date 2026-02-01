"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Calendar,
  StickyNote,
  Plus,
  Trash2,
  Loader2,
  Save,
  ArrowLeft,
  X,
  Sparkles,
  Edit2,
  Eye,
  BarChart3,
  Lightbulb,
  Target,
  Users,
  Shield,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Star,
} from "lucide-react";
import {
  isAuthenticated,
  getUser,
  logout,
  User,
} from "../../../../../lib/apiClient";
import {
  Council,
  CouncilMeetingDetail,
  CouncilMeetingListItem,
  CouncilNoteListItem,
  CouncilNote,
  CouncilAgendaItem,
  CouncilAgendaItemDetail,
  CouncilInfographic,
  CouncilInfographicListItem,
  getCouncil,
  getCouncilMeeting,
  listCouncilMeetings,
  listCouncilNotes,
  createCouncilNote,
  getCouncilNote,
  updateCouncilNote,
  deleteCouncilNote,
  getAgendaDetail,
  deleteAgenda,
  listCouncilInfographics,
  createCouncilInfographic,
  getCouncilInfographic,
  deleteCouncilInfographic,
} from "../../../../../lib/councilApi";
import { Header } from "../../../../../components/layout/Header";
import { Button } from "../../../../../components/ui/Button";
import { Input } from "../../../../../components/ui/Input";
import { Card } from "../../../../../components/ui/Card";
import { LoadingScreen } from "../../../../../components/ui/Spinner";
import { Modal } from "../../../../../components/ui/Modal";
import {
  CouncilChat,
  AgendaList,
  AgendaDetail,
  AgendaFormModal,
} from "../../../../../components/council";

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const councilId = params.id as string;
  const meetingId = params.meetingId as string;

  const [council, setCouncil] = useState<Council | null>(null);
  const [meeting, setMeeting] = useState<CouncilMeetingDetail | null>(null);
  const [allMeetings, setAllMeetings] = useState<CouncilMeetingListItem[]>([]);
  const [notes, setNotes] = useState<CouncilNoteListItem[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);

  // Selected agenda detail view
  const [selectedAgendaId, setSelectedAgendaId] = useState<string | null>(null);
  const [selectedAgendaDetail, setSelectedAgendaDetail] = useState<CouncilAgendaItemDetail | null>(null);
  const [loadingAgendaDetail, setLoadingAgendaDetail] = useState(false);

  // Agenda form modal
  const [showAgendaModal, setShowAgendaModal] = useState(false);
  const [editingAgenda, setEditingAgenda] = useState<CouncilAgendaItem | null>(null);

  // Delete agenda confirmation
  const [deleteAgendaId, setDeleteAgendaId] = useState<string | null>(null);
  const [deletingAgenda, setDeletingAgenda] = useState(false);

  // Create note modal
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [creatingNote, setCreatingNote] = useState(false);

  // Delete note confirmation
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);

  // View/Edit note modal
  const [viewingNote, setViewingNote] = useState<CouncilNote | null>(null);
  const [loadingNoteDetail, setLoadingNoteDetail] = useState(false);
  const [isEditingNote, setIsEditingNote] = useState(false);
  const [editNoteTitle, setEditNoteTitle] = useState("");
  const [editNoteContent, setEditNoteContent] = useState("");
  const [savingNoteEdit, setSavingNoteEdit] = useState(false);

  // Sidebar tab
  const [sidebarTab, setSidebarTab] = useState<"notes" | "chat" | "infographic">("chat");

  // Infographic state
  const [infographics, setInfographics] = useState<CouncilInfographicListItem[]>([]);
  const [selectedInfographic, setSelectedInfographic] = useState<CouncilInfographic | null>(null);
  const [showInfographicModal, setShowInfographicModal] = useState(false);
  const [loadingInfographic, setLoadingInfographic] = useState(false);
  const [infographicTopic, setInfographicTopic] = useState("");
  const [selectedAgendaIdsForInfographic, setSelectedAgendaIdsForInfographic] = useState<string[]>([]);
  const [generatingInfographic, setGeneratingInfographic] = useState(false);
  const [deleteInfographicId, setDeleteInfographicId] = useState<string | null>(null);
  const [deletingInfographic, setDeletingInfographic] = useState(false);

  // Auth check
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load data
  const loadData = useCallback(async () => {
    if (!authChecked || !councilId || !meetingId) return;

    setLoading(true);
    try {
      const [councilData, meetingData, allMeetingsData, notesData] = await Promise.all([
        getCouncil(councilId),
        getCouncilMeeting(meetingId),
        listCouncilMeetings(councilId),
        listCouncilNotes(councilId, meetingId),
      ]);
      setCouncil(councilData);
      setMeeting(meetingData);
      setAllMeetings(allMeetingsData);
      setNotes(notesData);

      // Load infographics separately to not block essential data
      try {
        const infographicsData = await listCouncilInfographics(councilId, meetingId);
        setInfographics(infographicsData.infographics);
      } catch (infErr) {
        console.error("Failed to load infographics:", infErr);
        // Don't block page loading if infographics fail
      }
    } catch (e) {
      console.error(e);
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [authChecked, councilId, meetingId, router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Helper to check if agenda has completed materials
  const hasCompletedMaterials = (agenda: CouncilAgendaItem) => {
    // Check aggregated status
    if (agenda.materials_processing_status === "completed") return true;
    // Check individual materials if available
    if (agenda.materials?.some(m => m.processing_status === "completed")) return true;
    return false;
  };

  // Helper to check if agenda is processing
  const isAgendaProcessing = (agenda: CouncilAgendaItem) => {
    if (agenda.materials_processing_status === "processing") return true;
    if (agenda.minutes_processing_status === "processing") return true;
    // Check individual materials if available
    if (agenda.materials?.some(m => m.processing_status === "processing")) return true;
    return false;
  };

  // Helper to check if agenda has searchable content
  const isAgendaSearchable = (agenda: CouncilAgendaItem) => {
    return hasCompletedMaterials(agenda) || agenda.minutes_processing_status === "completed";
  };

  // Polling for processing status (check if any agenda is processing)
  useEffect(() => {
    if (!meeting) return;

    const needsPolling = meeting.agendas.some(isAgendaProcessing);

    if (!needsPolling) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getCouncilMeeting(meetingId);
        setMeeting(updated);

        // Also update selected agenda detail if applicable
        if (selectedAgendaId) {
          const updatedAgendaDetail = await getAgendaDetail(selectedAgendaId);
          setSelectedAgendaDetail(updatedAgendaDetail);
        }
      } catch (e) {
        console.error("Polling failed:", e);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [meeting, meetingId, selectedAgendaId]);

  // Load agenda detail when selected
  const handleAgendaClick = async (agenda: CouncilAgendaItem) => {
    setSelectedAgendaId(agenda.id);
    setLoadingAgendaDetail(true);
    try {
      const detail = await getAgendaDetail(agenda.id);
      setSelectedAgendaDetail(detail);
    } catch (e) {
      console.error("Failed to load agenda detail:", e);
    } finally {
      setLoadingAgendaDetail(false);
    }
  };

  const handleAgendaFormSuccess = async () => {
    // Reload meeting data to get updated agendas list
    try {
      const updated = await getCouncilMeeting(meetingId);
      setMeeting(updated);
      setEditingAgenda(null);
    } catch (e) {
      console.error("Failed to reload meeting:", e);
    }
  };

  const handleDeleteAgenda = async () => {
    if (!deleteAgendaId) return;
    setDeletingAgenda(true);
    try {
      await deleteAgenda(deleteAgendaId);
      // Reload meeting data
      const updated = await getCouncilMeeting(meetingId);
      setMeeting(updated);
      // Clear selection if we deleted the selected agenda
      if (selectedAgendaId === deleteAgendaId) {
        setSelectedAgendaId(null);
        setSelectedAgendaDetail(null);
      }
      setDeleteAgendaId(null);
    } catch (e) {
      console.error("Failed to delete agenda:", e);
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("議題の削除に失敗しました");
      }
    } finally {
      setDeletingAgenda(false);
    }
  };

  const handleRefreshAgendaDetail = async () => {
    if (!selectedAgendaId) return;
    try {
      const detail = await getAgendaDetail(selectedAgendaId);
      setSelectedAgendaDetail(detail);
      // Also reload meeting to update the list
      const updated = await getCouncilMeeting(meetingId);
      setMeeting(updated);
    } catch (e) {
      console.error("Failed to refresh agenda detail:", e);
    }
  };

  const handleCreateNote = async () => {
    if (!noteTitle.trim() || !noteContent.trim()) return;
    setCreatingNote(true);

    try {
      await createCouncilNote({
        council_id: councilId,
        meeting_id: meetingId,
        title: noteTitle,
        content: noteContent,
      });
      const notesData = await listCouncilNotes(councilId, meetingId);
      setNotes(notesData);
      setNoteTitle("");
      setNoteContent("");
      setShowNoteModal(false);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("メモの作成に失敗しました");
      }
    } finally {
      setCreatingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      await deleteCouncilNote(noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
      setDeleteNoteId(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("削除に失敗しました");
      }
    }
  };

  const handleViewNote = async (noteId: string) => {
    setLoadingNoteDetail(true);
    setIsEditingNote(false);
    try {
      const note = await getCouncilNote(noteId);
      setViewingNote(note);
      setEditNoteTitle(note.title);
      setEditNoteContent(note.content);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("メモの取得に失敗しました");
      }
    } finally {
      setLoadingNoteDetail(false);
    }
  };

  const handleStartEditNote = () => {
    if (!viewingNote) return;
    setEditNoteTitle(viewingNote.title);
    setEditNoteContent(viewingNote.content);
    setIsEditingNote(true);
  };

  const handleSaveNoteEdit = async () => {
    if (!viewingNote || !editNoteTitle.trim() || !editNoteContent.trim()) return;
    setSavingNoteEdit(true);
    try {
      const updated = await updateCouncilNote(viewingNote.id, {
        title: editNoteTitle,
        content: editNoteContent,
      });
      setViewingNote(updated);
      // Update the list
      const notesData = await listCouncilNotes(councilId, meetingId);
      setNotes(notesData);
      setIsEditingNote(false);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("メモの更新に失敗しました");
      }
    } finally {
      setSavingNoteEdit(false);
    }
  };

  const handleCloseNoteModal = () => {
    setViewingNote(null);
    setIsEditingNote(false);
    setEditNoteTitle("");
    setEditNoteContent("");
  };

  // Infographic handlers
  const handleGenerateInfographic = async () => {
    if (!infographicTopic.trim()) return;
    setGeneratingInfographic(true);
    try {
      const infographic = await createCouncilInfographic(councilId, meetingId, {
        topic: infographicTopic,
        agenda_ids: selectedAgendaIdsForInfographic.length > 0 ? selectedAgendaIdsForInfographic : undefined,
      });
      setSelectedInfographic(infographic);
      setShowInfographicModal(true);
      setInfographicTopic("");
      setSelectedAgendaIdsForInfographic([]);
      // Reload infographics list
      const infographicsData = await listCouncilInfographics(councilId, meetingId);
      setInfographics(infographicsData.infographics);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert(e instanceof Error ? e.message : "インフォグラフィックの生成に失敗しました");
      }
    } finally {
      setGeneratingInfographic(false);
    }
  };

  const handleSelectInfographic = async (infographicId: string) => {
    setLoadingInfographic(true);
    setShowInfographicModal(true);
    try {
      const infographic = await getCouncilInfographic(infographicId);
      setSelectedInfographic(infographic);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("インフォグラフィックの取得に失敗しました");
        setShowInfographicModal(false);
      }
    } finally {
      setLoadingInfographic(false);
    }
  };

  const handleCloseInfographicModal = () => {
    setShowInfographicModal(false);
  };

  const handleDeleteInfographic = async () => {
    if (!deleteInfographicId) return;
    setDeletingInfographic(true);
    try {
      await deleteCouncilInfographic(deleteInfographicId);
      // Clear selection if we deleted the selected one
      if (selectedInfographic?.id === deleteInfographicId) {
        setSelectedInfographic(null);
      }
      // Reload list
      const infographicsData = await listCouncilInfographics(councilId, meetingId);
      setInfographics(infographicsData.infographics);
      setDeleteInfographicId(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("インフォグラフィックの削除に失敗しました");
      }
    } finally {
      setDeletingInfographic(false);
    }
  };

  const toggleAgendaForInfographic = (agendaId: string) => {
    setSelectedAgendaIdsForInfographic((prev) =>
      prev.includes(agendaId)
        ? prev.filter((id) => id !== agendaId)
        : [...prev, agendaId]
    );
  };

  const selectAllAgendasForInfographic = () => {
    if (!meeting) return;
    const processedAgendaIds = meeting.agendas
      .filter(isAgendaSearchable)
      .map((a) => a.id);
    setSelectedAgendaIdsForInfographic(processedAgendaIds);
  };

  const deselectAllAgendasForInfographic = () => {
    setSelectedAgendaIdsForInfographic([]);
  };

  // Icon mapping for infographic sections
  const getIconComponent = (iconHint?: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      lightbulb: <Lightbulb className="w-5 h-5" />,
      chart: <BarChart3 className="w-5 h-5" />,
      target: <Target className="w-5 h-5" />,
      users: <Users className="w-5 h-5" />,
      shield: <Shield className="w-5 h-5" />,
      clock: <Clock className="w-5 h-5" />,
      warning: <AlertTriangle className="w-5 h-5" />,
      check: <CheckCircle2 className="w-5 h-5" />,
      arrow: <ArrowRight className="w-5 h-5" />,
      star: <Star className="w-5 h-5" />,
    };
    return iconMap[iconHint || ""] || <Lightbulb className="w-5 h-5" />;
  };

  // Color mapping for infographic sections
  const getColorClasses = (colorHint?: string) => {
    const colorMap: Record<string, { bg: string; text: string; border: string }> = {
      primary: { bg: "bg-blue-50 dark:bg-blue-900/30", text: "text-blue-600 dark:text-blue-400", border: "border-blue-200 dark:border-blue-800" },
      secondary: { bg: "bg-gray-50 dark:bg-gray-800/50", text: "text-gray-600 dark:text-gray-400", border: "border-gray-200 dark:border-gray-700" },
      accent: { bg: "bg-purple-50 dark:bg-purple-900/30", text: "text-purple-600 dark:text-purple-400", border: "border-purple-200 dark:border-purple-800" },
      success: { bg: "bg-green-50 dark:bg-green-900/30", text: "text-green-600 dark:text-green-400", border: "border-green-200 dark:border-green-800" },
      warning: { bg: "bg-amber-50 dark:bg-amber-900/30", text: "text-amber-600 dark:text-amber-400", border: "border-amber-200 dark:border-amber-800" },
      danger: { bg: "bg-red-50 dark:bg-red-900/30", text: "text-red-600 dark:text-red-400", border: "border-red-200 dark:border-red-800" },
    };
    return colorMap[colorHint || ""] || colorMap.primary;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "short",
    });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString("ja-JP", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const isOwner = council && user?.id === council.owner_id;
  const nextAgendaNumber = meeting ? Math.max(0, ...meeting.agendas.map((a) => a.agenda_number)) + 1 : 1;

  if (!authChecked || loading) {
    return <LoadingScreen message="読み込み中..." />;
  }

  if (!council || !meeting) {
    return (
      <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
        <Header user={user} showBackButton backHref={`/councils/${councilId}`} backLabel="審議会に戻る" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <Card variant="default" padding="lg" className="text-center py-16">
            <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
              開催回が見つかりません
            </h3>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
      <Header
        user={user}
        showBackButton
        backHref={`/councils/${councilId}`}
        backLabel={council.title}
        title={`第${meeting.meeting_number}回`}
        subtitle={meeting.title || undefined}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Meeting info header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium">
              <Calendar className="w-4 h-4" />
              第{meeting.meeting_number}回
            </span>
            {meeting.title && (
              <h1 className="text-xl font-bold text-surface-900 dark:text-surface-100">
                {meeting.title}
              </h1>
            )}
          </div>
          <p className="text-surface-500 dark:text-surface-400">
            {formatDate(meeting.scheduled_at)} {formatTime(meeting.scheduled_at)}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Agenda section */}
            {selectedAgendaDetail ? (
              // Show selected agenda detail
              <Card variant="default" padding="lg">
                <div className="mb-4 pb-4 border-b border-surface-200 dark:border-surface-700">
                  <button
                    onClick={() => {
                      setSelectedAgendaId(null);
                      setSelectedAgendaDetail(null);
                    }}
                    className="inline-flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-300 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    議題一覧に戻る
                  </button>
                </div>
                {loadingAgendaDetail ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
                  </div>
                ) : (
                  <AgendaDetail
                    agenda={selectedAgendaDetail}
                    onRefresh={handleRefreshAgendaDetail}
                  />
                )}
              </Card>
            ) : (
              // Show agenda list
              <Card variant="default" padding="lg">
                <AgendaList
                  agendas={meeting.agendas}
                  onAgendaClick={handleAgendaClick}
                  onAddClick={() => {
                    setEditingAgenda(null);
                    setShowAgendaModal(true);
                  }}
                  onEditAgenda={(agenda) => {
                    setEditingAgenda(agenda);
                    setShowAgendaModal(true);
                  }}
                  onDeleteAgenda={(agenda) => setDeleteAgendaId(agenda.id)}
                  showActions={true}
                />
              </Card>
            )}

          </div>

          {/* Sidebar - Notes / AI Assistant tabs */}
          <div className="lg:col-span-1">
            <div className="sticky top-24">
              {/* Tab switcher */}
              <div className="flex bg-surface-100 dark:bg-surface-800 rounded-lg p-1 mb-4">
                <button
                  onClick={() => setSidebarTab("notes")}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    sidebarTab === "notes"
                      ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                      : "text-surface-500 dark:text-surface-400"
                  }`}
                >
                  <StickyNote className="w-3.5 h-3.5" />
                  メモ
                </button>
                <button
                  onClick={() => setSidebarTab("chat")}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    sidebarTab === "chat"
                      ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                      : "text-surface-500 dark:text-surface-400"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  AI
                </button>
                <button
                  onClick={() => setSidebarTab("infographic")}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    sidebarTab === "infographic"
                      ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                      : "text-surface-500 dark:text-surface-400"
                  }`}
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  図解
                </button>
              </div>

              {sidebarTab === "notes" ? (
                /* Notes tab content */
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                      この開催回のメモ
                    </h2>
                    <Button
                      variant="ghost"
                      size="sm"
                      leftIcon={<Plus className="w-4 h-4" />}
                      onClick={() => setShowNoteModal(true)}
                    >
                      追加
                    </Button>
                  </div>

                  {notes.length === 0 ? (
                    <Card variant="default" padding="md" className="text-center py-8">
                      <StickyNote className="w-10 h-10 mx-auto mb-3 text-surface-400" />
                      <p className="text-sm text-surface-500 dark:text-surface-400">
                        メモがありません
                      </p>
                    </Card>
                  ) : (
                    <div className="space-y-3">
                      {notes.map((note) => (
                        <Card
                          key={note.id}
                          variant="hover"
                          padding="md"
                          className="group cursor-pointer"
                          onClick={() => handleViewNote(note.id)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-surface-900 dark:text-surface-100 mb-1">
                                {note.title}
                              </h4>
                              <p className="text-sm text-surface-500 dark:text-surface-400 line-clamp-2">
                                {note.content_preview}
                              </p>
                              <p className="text-xs text-surface-400 dark:text-surface-500 mt-2">
                                {new Date(note.created_at).toLocaleDateString("ja-JP")} - {note.user_display_name}
                              </p>
                            </div>
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={() => handleViewNote(note.id)}
                                className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 text-surface-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-all"
                                title="表示"
                              >
                                <Eye className="w-4 h-4" />
                              </button>
                              {(user?.id === note.user_id || isOwner) && (
                                <button
                                  onClick={() => setDeleteNoteId(note.id)}
                                  className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 text-surface-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all"
                                  title="削除"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  )}
                </>
              ) : sidebarTab === "chat" ? (
                /* AI Assistant tab content */
                <div className="h-[600px]">
                  <CouncilChat
                    councilId={councilId}
                    meetings={allMeetings}
                    mode="meeting"
                    currentMeetingId={meetingId}
                    agendas={meeting.agendas}
                  />
                </div>
              ) : (
                /* Infographic tab content */
                <div className="space-y-4">
                  {/* Generation form */}
                  <Card variant="default" padding="md">
                    <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100 mb-3">
                      インフォグラフィック生成
                    </h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-surface-600 dark:text-surface-400 mb-1">
                          トピック
                        </label>
                        <textarea
                          className="w-full px-3 py-2 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg transition-all placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                          rows={2}
                          placeholder="図解したいテーマを入力"
                          value={infographicTopic}
                          onChange={(e) => setInfographicTopic(e.target.value)}
                          disabled={generatingInfographic}
                        />
                      </div>

                      {/* Agenda selection */}
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-xs font-medium text-surface-600 dark:text-surface-400">
                            対象議題
                          </label>
                          <div className="flex gap-1">
                            <button
                              onClick={selectAllAgendasForInfographic}
                              className="text-xs text-primary-500 hover:text-primary-600"
                              disabled={generatingInfographic}
                            >
                              全選択
                            </button>
                            <span className="text-surface-300">|</span>
                            <button
                              onClick={deselectAllAgendasForInfographic}
                              className="text-xs text-surface-500 hover:text-surface-600"
                              disabled={generatingInfographic}
                            >
                              解除
                            </button>
                          </div>
                        </div>
                        <div className="max-h-32 overflow-y-auto space-y-1 p-2 bg-surface-50 dark:bg-surface-800 rounded-lg">
                          {meeting.agendas.filter(isAgendaSearchable).length === 0 ? (
                            <p className="text-xs text-surface-400 text-center py-2">処理済みの議題がありません</p>
                          ) : (
                            meeting.agendas
                              .filter(isAgendaSearchable)
                              .map((agenda) => (
                                <label
                                  key={agenda.id}
                                  className="flex items-center gap-2 p-1.5 rounded hover:bg-surface-100 dark:hover:bg-surface-700 cursor-pointer"
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedAgendaIdsForInfographic.includes(agenda.id)}
                                    onChange={() => toggleAgendaForInfographic(agenda.id)}
                                    disabled={generatingInfographic}
                                    className="rounded border-surface-300 text-primary-500 focus:ring-primary-500"
                                  />
                                  <span className="text-xs text-surface-700 dark:text-surface-300 truncate">
                                    議題{agenda.agenda_number}
                                    {agenda.title && `: ${agenda.title}`}
                                  </span>
                                </label>
                              ))
                          )}
                        </div>
                        <p className="text-xs text-surface-400 mt-1">
                          未選択時は全ての処理済み議題を使用
                        </p>
                      </div>

                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleGenerateInfographic}
                        disabled={!infographicTopic.trim() || generatingInfographic}
                        isLoading={generatingInfographic}
                        leftIcon={<BarChart3 className="w-4 h-4" />}
                        className="w-full"
                      >
                        {generatingInfographic ? "生成中..." : "生成"}
                      </Button>
                    </div>
                  </Card>

                  {/* History list */}
                  <Card variant="default" padding="md">
                    <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100 mb-3">
                      生成履歴 ({infographics.length})
                    </h3>
                    {infographics.length === 0 ? (
                      <div className="text-center py-6">
                        <BarChart3 className="w-10 h-10 mx-auto mb-3 text-surface-300" />
                        <p className="text-sm text-surface-500">
                          トピックを入力して図解を生成してください
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {infographics.map((inf) => (
                          <div
                            key={inf.id}
                            className="group p-2 rounded-lg cursor-pointer transition-colors hover:bg-surface-50 dark:hover:bg-surface-800"
                            onClick={() => handleSelectInfographic(inf.id)}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-surface-900 dark:text-surface-100 truncate">
                                  {inf.title}
                                </p>
                                <p className="text-xs text-surface-400 truncate">
                                  {inf.topic}
                                </p>
                                <p className="text-xs text-surface-400 mt-1">
                                  {new Date(inf.created_at).toLocaleDateString("ja-JP")}
                                </p>
                              </div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDeleteInfographicId(inf.id);
                                }}
                                className="p-1 rounded opacity-0 group-hover:opacity-100 text-surface-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all"
                                title="削除"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Agenda Form Modal */}
      <AgendaFormModal
        isOpen={showAgendaModal}
        onClose={() => {
          setShowAgendaModal(false);
          setEditingAgenda(null);
        }}
        onSuccess={handleAgendaFormSuccess}
        meetingId={meetingId}
        agenda={editingAgenda || undefined}
        nextAgendaNumber={nextAgendaNumber}
      />

      {/* Delete Agenda Confirmation */}
      <Modal
        isOpen={!!deleteAgendaId}
        onClose={() => setDeleteAgendaId(null)}
        title="議題を削除"
        description="この議題に関連する全てのデータ（要約、チャンク等）が削除されます。この操作は取り消せません。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteAgendaId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteAgenda}
            isLoading={deletingAgenda}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Create Note Modal */}
      <Modal
        isOpen={showNoteModal}
        onClose={() => {
          setShowNoteModal(false);
          setNoteTitle("");
          setNoteContent("");
        }}
        title="メモを追加"
        description="この開催回に関するメモを作成します"
      >
        <div className="space-y-4">
          <Input
            label="タイトル"
            placeholder="メモのタイトル"
            value={noteTitle}
            onChange={(e) => setNoteTitle(e.target.value)}
            required
          />

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              内容
            </label>
            <textarea
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={6}
              placeholder="メモの内容を入力してください"
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setShowNoteModal(false);
                setNoteTitle("");
                setNoteContent("");
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreateNote}
              isLoading={creatingNote}
              disabled={!noteTitle.trim() || !noteContent.trim()}
              leftIcon={<Save className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Note Confirmation */}
      <Modal
        isOpen={!!deleteNoteId}
        onClose={() => setDeleteNoteId(null)}
        title="メモを削除"
        description="この操作は取り消せません。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteNoteId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteNoteId && handleDeleteNote(deleteNoteId)}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* View/Edit Note Modal */}
      <Modal
        isOpen={!!viewingNote || loadingNoteDetail}
        onClose={handleCloseNoteModal}
        title={isEditingNote ? "メモを編集" : "メモの詳細"}
        size="lg"
      >
        {loadingNoteDetail ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          </div>
        ) : viewingNote ? (
          <div className="space-y-4">
            {isEditingNote ? (
              // Edit mode
              <>
                <Input
                  label="タイトル"
                  value={editNoteTitle}
                  onChange={(e) => setEditNoteTitle(e.target.value)}
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
                    内容
                  </label>
                  <textarea
                    className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y"
                    rows={12}
                    value={editNoteContent}
                    onChange={(e) => setEditNoteContent(e.target.value)}
                  />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <Button
                    variant="ghost"
                    onClick={() => setIsEditingNote(false)}
                    disabled={savingNoteEdit}
                  >
                    キャンセル
                  </Button>
                  <Button
                    variant="primary"
                    onClick={handleSaveNoteEdit}
                    isLoading={savingNoteEdit}
                    disabled={!editNoteTitle.trim() || !editNoteContent.trim()}
                    leftIcon={<Save className="w-4 h-4" />}
                  >
                    保存
                  </Button>
                </div>
              </>
            ) : (
              // View mode
              <>
                <div>
                  <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
                    {viewingNote.title}
                  </h3>
                  <p className="text-xs text-surface-400 dark:text-surface-500">
                    作成日: {new Date(viewingNote.created_at).toLocaleString("ja-JP")}
                    {viewingNote.updated_at !== viewingNote.created_at && (
                      <> | 更新日: {new Date(viewingNote.updated_at).toLocaleString("ja-JP")}</>
                    )}
                  </p>
                </div>
                <div className="bg-surface-50 dark:bg-surface-800 rounded-xl p-4 max-h-96 overflow-y-auto">
                  <p className="text-sm text-surface-700 dark:text-surface-200 whitespace-pre-wrap">
                    {viewingNote.content}
                  </p>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <Button variant="ghost" onClick={handleCloseNoteModal}>
                    閉じる
                  </Button>
                  {(user?.id === viewingNote.user_id || isOwner) && (
                    <Button
                      variant="primary"
                      onClick={handleStartEditNote}
                      leftIcon={<Edit2 className="w-4 h-4" />}
                    >
                      編集
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        ) : null}
      </Modal>

      {/* Delete Infographic Confirmation */}
      <Modal
        isOpen={!!deleteInfographicId}
        onClose={() => setDeleteInfographicId(null)}
        title="インフォグラフィックを削除"
        description="この操作は取り消せません。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteInfographicId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteInfographic}
            isLoading={deletingInfographic}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Infographic Display Modal (Full Size) */}
      <Modal
        isOpen={showInfographicModal}
        onClose={handleCloseInfographicModal}
        title={selectedInfographic?.structure.title || "インフォグラフィック"}
        description={selectedInfographic?.structure.subtitle || undefined}
        size="full"
      >
        {loadingInfographic ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            <p className="ml-3 text-surface-500">読み込み中...</p>
          </div>
        ) : selectedInfographic ? (
          <div className="max-w-5xl mx-auto">
            {/* Sections Grid - 2 columns on larger screens */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {selectedInfographic.structure.sections.map((section) => {
                const colors = getColorClasses(section.color_hint);
                return (
                  <div
                    key={section.id}
                    className={`p-5 rounded-xl border-2 ${colors.bg} ${colors.border}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${colors.text} bg-white dark:bg-surface-900`}>
                        {getIconComponent(section.icon_hint)}
                      </div>
                      <div className="flex-1">
                        <h3 className={`text-lg font-semibold mb-3 ${colors.text}`}>
                          {section.heading}
                        </h3>
                        <ul className="space-y-2">
                          {section.key_points.map((point, idx) => (
                            <li
                              key={idx}
                              className="flex items-start gap-2 text-sm text-surface-700 dark:text-surface-300"
                            >
                              <ArrowRight className="w-4 h-4 flex-shrink-0 mt-0.5 text-surface-400" />
                              <span>{point}</span>
                            </li>
                          ))}
                        </ul>
                        {section.detail && (
                          <p className="mt-3 text-xs text-surface-500 dark:text-surface-400 italic border-t border-surface-200 dark:border-surface-700 pt-2">
                            {section.detail}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer Note */}
            {selectedInfographic.structure.footer_note && (
              <div className="mt-8 text-center">
                <p className="text-sm text-surface-500 dark:text-surface-400 italic">
                  {selectedInfographic.structure.footer_note}
                </p>
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
