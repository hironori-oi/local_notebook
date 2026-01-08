"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Plus,
  Building2,
  Calendar,
  StickyNote,
  ExternalLink,
  Edit2,
  Trash2,
  ChevronDown,
  X,
  Save,
  Sparkles,
} from "lucide-react";
import {
  isAuthenticated,
  getUser,
  logout,
  User,
} from "../../../lib/apiClient";
import {
  Council,
  CouncilMeetingListItem,
  CalendarMeeting,
  CouncilNoteListItem,
  getCouncil,
  getCouncilCalendar,
  listCouncilMeetings,
  createCouncilMeeting,
  updateCouncilMeeting,
  deleteCouncilMeeting,
  listCouncilNotes,
  createCouncilNote,
  deleteCouncilNote,
} from "../../../lib/councilApi";
import { Header } from "../../../components/layout/Header";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Card } from "../../../components/ui/Card";
import { LoadingScreen, Skeleton } from "../../../components/ui/Spinner";
import { Modal } from "../../../components/ui/Modal";
import { CalendarView, MeetingCard, CouncilChat } from "../../../components/council";

export default function CouncilDetailPage() {
  const params = useParams();
  const router = useRouter();
  const councilId = params.id as string;

  const [council, setCouncil] = useState<Council | null>(null);
  const [meetings, setMeetings] = useState<CouncilMeetingListItem[]>([]);
  const [calendarMeetings, setCalendarMeetings] = useState<CalendarMeeting[]>([]);
  const [notes, setNotes] = useState<CouncilNoteListItem[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);

  // Calendar state
  const [calendarView, setCalendarView] = useState<"week" | "month">("month");
  const [currentDate, setCurrentDate] = useState(new Date());

  // Create meeting modal
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [meetingNumber, setMeetingNumber] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [creatingMeeting, setCreatingMeeting] = useState(false);

  // Edit meeting modal
  const [editMeeting, setEditMeeting] = useState<CouncilMeetingListItem | null>(null);
  const [editMeetingNumber, setEditMeetingNumber] = useState("");
  const [editMeetingTitle, setEditMeetingTitle] = useState("");
  const [editMeetingDate, setEditMeetingDate] = useState("");
  const [updatingMeeting, setUpdatingMeeting] = useState(false);

  // Create note modal
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [creatingNote, setCreatingNote] = useState(false);

  // Delete confirmation
  const [deleteMeetingId, setDeleteMeetingId] = useState<string | null>(null);
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);

  // View mode
  const [viewMode, setViewMode] = useState<"calendar" | "list">("calendar");

  // Sidebar tab
  const [sidebarTab, setSidebarTab] = useState<"notes" | "chat">("notes");

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
    if (!authChecked || !councilId) return;

    setLoading(true);
    try {
      const [councilData, meetingsData, notesData] = await Promise.all([
        getCouncil(councilId),
        listCouncilMeetings(councilId),
        listCouncilNotes(councilId, "council"),
      ]);
      setCouncil(councilData);
      setMeetings(meetingsData);
      setNotes(notesData);

      // Set default meeting number
      const maxNumber = meetingsData.reduce((max, m) => Math.max(max, m.meeting_number), 0);
      setMeetingNumber(String(maxNumber + 1));
    } catch (e) {
      console.error(e);
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [authChecked, councilId, router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load calendar data when date changes
  useEffect(() => {
    if (!authChecked || !councilId) return;

    const loadCalendar = async () => {
      try {
        const dateStr = currentDate.toISOString().split("T")[0];
        const calendarData = await getCouncilCalendar(councilId, calendarView, dateStr);
        setCalendarMeetings(calendarData.meetings);
      } catch (e) {
        console.error(e);
      }
    };

    loadCalendar();
  }, [authChecked, councilId, currentDate, calendarView]);

  const handleCreateMeeting = async () => {
    if (!meetingNumber || !meetingDate) return;
    setCreatingMeeting(true);

    try {
      // Use noon (12:00) to avoid timezone issues with date display
      const scheduledAt = new Date(`${meetingDate}T12:00:00`);
      const newMeeting = await createCouncilMeeting(councilId, {
        meeting_number: parseInt(meetingNumber, 10),
        title: meetingTitle || undefined,
        scheduled_at: scheduledAt.toISOString(),
      });
      // Add note_count for MeetingCard compatibility (new meetings have 0 notes)
      const meetingWithNoteCount: CouncilMeetingListItem = { ...newMeeting, note_count: 0 };
      setMeetings((prev) => [meetingWithNoteCount, ...prev].sort((a, b) => b.meeting_number - a.meeting_number));
      resetMeetingForm();
      setShowMeetingModal(false);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("開催回の作成に失敗しました");
      }
    } finally {
      setCreatingMeeting(false);
    }
  };

  const resetMeetingForm = () => {
    const maxNumber = meetings.reduce((max, m) => Math.max(max, m.meeting_number), 0);
    setMeetingNumber(String(maxNumber + 1));
    setMeetingTitle("");
    setMeetingDate("");
  };

  const handleDeleteMeeting = async (meetingId: string) => {
    try {
      await deleteCouncilMeeting(meetingId);
      setMeetings((prev) => prev.filter((m) => m.id !== meetingId));
      setDeleteMeetingId(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("削除に失敗しました");
      }
    }
  };

  const handleOpenEditMeeting = (meeting: CouncilMeetingListItem) => {
    setEditMeeting(meeting);
    setEditMeetingNumber(String(meeting.meeting_number));
    setEditMeetingTitle(meeting.title || "");
    const scheduledAt = new Date(meeting.scheduled_at);
    // Use local date format YYYY-MM-DD
    const year = scheduledAt.getFullYear();
    const month = String(scheduledAt.getMonth() + 1).padStart(2, "0");
    const day = String(scheduledAt.getDate()).padStart(2, "0");
    setEditMeetingDate(`${year}-${month}-${day}`);
  };

  const handleUpdateMeeting = async () => {
    if (!editMeeting || !editMeetingNumber || !editMeetingDate) return;
    setUpdatingMeeting(true);

    try {
      // Use noon (12:00) to avoid timezone issues with date display
      const scheduledAt = new Date(`${editMeetingDate}T12:00:00`);
      const updated = await updateCouncilMeeting(editMeeting.id, {
        meeting_number: parseInt(editMeetingNumber, 10),
        title: editMeetingTitle || undefined,
        scheduled_at: scheduledAt.toISOString(),
      });
      setMeetings((prev) =>
        prev
          .map((m) =>
            m.id === editMeeting.id
              ? { ...m, ...updated }
              : m
          )
          .sort((a, b) => b.meeting_number - a.meeting_number)
      );
      setEditMeeting(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("更新に失敗しました");
      }
    } finally {
      setUpdatingMeeting(false);
    }
  };

  const handleCreateNote = async () => {
    if (!noteTitle.trim() || !noteContent.trim()) return;
    setCreatingNote(true);

    try {
      await createCouncilNote({
        council_id: councilId,
        title: noteTitle,
        content: noteContent,
      });
      // Reload notes
      const notesData = await listCouncilNotes(councilId, "council");
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

  const handleMeetingClick = (meetingId: string) => {
    router.push(`/councils/${councilId}/meetings/${meetingId}`);
  };

  const isOwner = council && user?.id === council.owner_id;

  if (!authChecked || loading) {
    return <LoadingScreen message="読み込み中..." />;
  }

  if (!council) {
    return (
      <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
        <Header user={user} showBackButton backHref="/councils" backLabel="審議会一覧" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <Card variant="default" padding="lg" className="text-center py-16">
            <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
              審議会が見つかりません
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
        backHref="/councils"
        backLabel="審議会一覧"
        title={council.title}
        subtitle={council.organization || undefined}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Council info */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 dark:from-primary-500/20 dark:to-accent-500/20 flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                    {council.title}
                  </h1>
                  <div className="flex items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
                    {council.organization && <span>{council.organization}</span>}
                    {council.council_type && (
                      <>
                        <span>|</span>
                        <span>{council.council_type}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              {council.description && (
                <p className="text-surface-600 dark:text-surface-400 max-w-2xl">
                  {council.description}
                </p>
              )}
              {council.official_url && (
                <a
                  href={council.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 hover:underline mt-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  公式ページ
                </a>
              )}
            </div>

            <Button
              variant="primary"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setShowMeetingModal(true)}
            >
              開催回を追加
            </Button>
          </div>

          {/* Stats */}
          <div className="flex gap-6 text-sm text-surface-500 dark:text-surface-400">
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              {meetings.length} 回開催
            </span>
            <span className="flex items-center gap-1.5">
              <StickyNote className="w-4 h-4" />
              {notes.length} 件のメモ
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main content - Calendar/List */}
          <div className="lg:col-span-2">
            {/* View toggle */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                開催回一覧
              </h2>
              <div className="flex bg-surface-100 dark:bg-surface-800 rounded-lg p-1">
                <button
                  onClick={() => setViewMode("calendar")}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    viewMode === "calendar"
                      ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                      : "text-surface-500 dark:text-surface-400"
                  }`}
                >
                  カレンダー
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    viewMode === "list"
                      ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                      : "text-surface-500 dark:text-surface-400"
                  }`}
                >
                  リスト
                </button>
              </div>
            </div>

            {viewMode === "calendar" ? (
              <CalendarView
                meetings={calendarMeetings}
                view={calendarView}
                onViewChange={setCalendarView}
                currentDate={currentDate}
                onDateChange={setCurrentDate}
                onMeetingClick={handleMeetingClick}
              />
            ) : (
              <div className="space-y-3">
                {meetings.length === 0 ? (
                  <Card variant="default" padding="lg" className="text-center py-12">
                    <Calendar className="w-12 h-12 mx-auto mb-4 text-surface-400" />
                    <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
                      開催回がありません
                    </h3>
                    <p className="text-surface-500 dark:text-surface-400 mb-4">
                      最初の開催回を追加しましょう
                    </p>
                    <Button
                      variant="primary"
                      leftIcon={<Plus className="w-4 h-4" />}
                      onClick={() => setShowMeetingModal(true)}
                    >
                      開催回を追加
                    </Button>
                  </Card>
                ) : (
                  meetings.map((meeting) => (
                    <div key={meeting.id} className="relative group">
                      <MeetingCard
                        meeting={meeting}
                        onClick={() => handleMeetingClick(meeting.id)}
                      />
                      {isOwner && (
                        <div className="absolute top-4 right-12 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenEditMeeting(meeting);
                            }}
                            className="p-2 rounded-lg bg-white dark:bg-surface-700 text-surface-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/30 shadow-md"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteMeetingId(meeting.id);
                            }}
                            className="p-2 rounded-lg bg-white dark:bg-surface-700 text-surface-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 shadow-md"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Sidebar - Notes / AI Assistant tabs */}
          <div>
            {/* Tab switcher */}
            <div className="flex bg-surface-100 dark:bg-surface-800 rounded-lg p-1 mb-4">
              <button
                onClick={() => setSidebarTab("notes")}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  sidebarTab === "notes"
                    ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                    : "text-surface-500 dark:text-surface-400"
                }`}
              >
                <StickyNote className="w-4 h-4" />
                メモ
              </button>
              <button
                onClick={() => setSidebarTab("chat")}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  sidebarTab === "chat"
                    ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                    : "text-surface-500 dark:text-surface-400"
                }`}
              >
                <Sparkles className="w-4 h-4" />
                AIアシスタント
              </button>
            </div>

            {sidebarTab === "notes" ? (
              /* Notes tab content */
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                    審議会メモ
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

                <div className="space-y-3">
                  {notes.length === 0 ? (
                    <Card variant="default" padding="md" className="text-center py-8">
                      <StickyNote className="w-10 h-10 mx-auto mb-3 text-surface-400" />
                      <p className="text-sm text-surface-500 dark:text-surface-400">
                        メモがありません
                      </p>
                    </Card>
                  ) : (
                    notes.map((note) => (
                      <Card
                        key={note.id}
                        variant="hover"
                        padding="md"
                        className="group cursor-pointer"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-surface-900 dark:text-surface-100 mb-1 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                              {note.title}
                            </h4>
                            <p className="text-sm text-surface-500 dark:text-surface-400 line-clamp-2">
                              {note.content_preview}
                            </p>
                            <p className="text-xs text-surface-400 dark:text-surface-500 mt-2">
                              {new Date(note.created_at).toLocaleDateString("ja-JP")} - {note.user_display_name}
                            </p>
                          </div>
                          {(user?.id === note.user_id || isOwner) && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteNoteId(note.id);
                              }}
                              className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 text-surface-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              </>
            ) : (
              /* AI Assistant tab content */
              <div className="h-[500px]">
                <CouncilChat
                  councilId={councilId}
                  meetings={meetings}
                  mode="council"
                />
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Create Meeting Modal */}
      <Modal
        isOpen={showMeetingModal}
        onClose={() => {
          setShowMeetingModal(false);
          resetMeetingForm();
        }}
        title="開催回を追加"
        description="開催日時と資料URLを入力してください"
        size="lg"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="開催回"
              type="number"
              placeholder="1"
              value={meetingNumber}
              onChange={(e) => setMeetingNumber(e.target.value)}
              leftIcon={<span className="text-sm">第</span>}
              required
            />
            <Input
              label="タイトル（任意）"
              placeholder="例：臨時会合"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
            />
          </div>

          <Input
            label="開催日"
            type="date"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
            required
          />

          <p className="text-sm text-surface-500 dark:text-surface-400">
            資料や議事録は、開催回を作成後に議題として追加できます。
          </p>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setShowMeetingModal(false);
                resetMeetingForm();
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreateMeeting}
              isLoading={creatingMeeting}
              disabled={!meetingNumber || !meetingDate}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              追加
            </Button>
          </div>
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
        description="審議会に関するメモを作成します"
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

      {/* Edit Meeting Modal */}
      <Modal
        isOpen={!!editMeeting}
        onClose={() => setEditMeeting(null)}
        title="開催回を編集"
        description="開催日時や回数を変更できます"
        size="lg"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="開催回"
              type="number"
              placeholder="1"
              value={editMeetingNumber}
              onChange={(e) => setEditMeetingNumber(e.target.value)}
              leftIcon={<span className="text-sm">第</span>}
              required
            />
            <Input
              label="タイトル（任意）"
              placeholder="例：臨時会合"
              value={editMeetingTitle}
              onChange={(e) => setEditMeetingTitle(e.target.value)}
            />
          </div>

          <Input
            label="開催日"
            type="date"
            value={editMeetingDate}
            onChange={(e) => setEditMeetingDate(e.target.value)}
            required
          />

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => setEditMeeting(null)}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleUpdateMeeting}
              isLoading={updatingMeeting}
              disabled={!editMeetingNumber || !editMeetingDate}
              leftIcon={<Save className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Meeting Confirmation */}
      <Modal
        isOpen={!!deleteMeetingId}
        onClose={() => setDeleteMeetingId(null)}
        title="開催回を削除"
        description="この操作は取り消せません。開催回に関連するすべてのデータが削除されます。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteMeetingId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteMeetingId && handleDeleteMeeting(deleteMeetingId)}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
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
    </div>
  );
}
