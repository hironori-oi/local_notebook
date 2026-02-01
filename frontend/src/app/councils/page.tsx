"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Building2,
  Calendar,
  Trash2,
  Search,
  FolderOpen,
  Clock,
  User as UserIcon,
  Edit2,
  Save,
  ExternalLink,
  LayoutGrid,
} from "lucide-react";
import {
  isAuthenticated,
  getUser,
  logout,
  User,
} from "../../lib/apiClient";
import {
  Council,
  CouncilFilterType,
  fetchCouncils,
  createCouncil,
  deleteCouncil,
  updateCouncil,
  getGlobalCalendar,
  GlobalCalendarMeeting,
} from "../../lib/councilApi";
import { Header } from "../../components/layout/Header";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Card } from "../../components/ui/Card";
import { LoadingScreen, Skeleton } from "../../components/ui/Spinner";
import { Modal } from "../../components/ui/Modal";
import { GlobalCalendarView } from "../../components/council";

type ViewMode = "list" | "calendar";

export default function CouncilsPage() {
  const router = useRouter();
  const [councils, setCouncils] = useState<Council[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [organization, setOrganization] = useState("");
  const [officialUrl, setOfficialUrl] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<CouncilFilterType>("all");
  const [editCouncil, setEditCouncil] = useState<Council | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editOrganization, setEditOrganization] = useState("");
  const [editOfficialUrl, setEditOfficialUrl] = useState("");
  const [savingCouncil, setSavingCouncil] = useState(false);

  // Calendar view state
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [calendarView, setCalendarView] = useState<"week" | "month">("month");
  const [calendarDate, setCalendarDate] = useState(new Date());
  const [calendarMeetings, setCalendarMeetings] = useState<GlobalCalendarMeeting[]>([]);
  const [calendarCouncilCount, setCalendarCouncilCount] = useState(0);
  const [calendarLoading, setCalendarLoading] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Load councils after auth check or when filter changes
  useEffect(() => {
    if (!authChecked) return;

    (async () => {
      setLoading(true);
      try {
        const data = await fetchCouncils(filterType);
        setCouncils(data);
      } catch (e) {
        console.error(e);
        if (e instanceof Error && e.message.includes("401")) {
          logout();
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [authChecked, router, filterType]);

  // Load calendar data
  const loadCalendarData = useCallback(async () => {
    if (!authChecked) return;
    setCalendarLoading(true);
    try {
      const dateStr = calendarDate.toISOString().split("T")[0];
      const data = await getGlobalCalendar(calendarView, dateStr, filterType);
      setCalendarMeetings(data.meetings);
      setCalendarCouncilCount(data.council_count);
    } catch (e) {
      console.error(e);
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      }
    } finally {
      setCalendarLoading(false);
    }
  }, [authChecked, calendarView, calendarDate, filterType, router]);

  // Load calendar data when in calendar view
  useEffect(() => {
    if (viewMode === "calendar") {
      loadCalendarData();
    }
  }, [viewMode, loadCalendarData]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setCreating(true);

    try {
      const council = await createCouncil({
        title,
        description: desc || undefined,
        organization: organization || undefined,
        official_url: officialUrl || undefined,
      });
      setCouncils((prev) => [council, ...prev]);
      resetCreateForm();
      setIsModalOpen(false);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("審議会の作成に失敗しました");
      }
    } finally {
      setCreating(false);
    }
  };

  const resetCreateForm = () => {
    setTitle("");
    setDesc("");
    setOrganization("");
    setOfficialUrl("");
  };

  const handleDelete = async (councilId: string) => {
    try {
      await deleteCouncil(councilId);
      setCouncils((prev) => prev.filter((c) => c.id !== councilId));
      setDeleteId(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("削除に失敗しました");
      }
    }
  };

  const handleOpenEdit = (council: Council) => {
    setEditCouncil(council);
    setEditTitle(council.title);
    setEditDesc(council.description || "");
    setEditOrganization(council.organization || "");
    setEditOfficialUrl(council.official_url || "");
  };

  const handleSaveCouncil = async () => {
    if (!editCouncil || !editTitle.trim()) return;
    setSavingCouncil(true);

    try {
      const updated = await updateCouncil(editCouncil.id, {
        title: editTitle,
        description: editDesc || undefined,
        organization: editOrganization || undefined,
        official_url: editOfficialUrl || undefined,
      });
      setCouncils((prev) =>
        prev.map((c) =>
          c.id === editCouncil.id
            ? {
                ...c,
                title: updated.title,
                description: updated.description,
                organization: updated.organization,
                official_url: updated.official_url,
              }
            : c
        )
      );
      setEditCouncil(null);
    } catch (e) {
      if (e instanceof Error && e.message.includes("401")) {
        logout();
        router.push("/login");
      } else {
        alert("保存に失敗しました");
      }
    } finally {
      setSavingCouncil(false);
    }
  };

  const filteredCouncils = councils.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.organization?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isOwner = (council: Council) => user?.id === council.owner_id;

  const handleCalendarMeetingClick = (councilId: string, meetingId: string) => {
    router.push(`/councils/${councilId}/meetings/${meetingId}`);
  };

  // 審議会は常に公開なのでフィルタータブは「すべて」のみ
  // 後方互換性のためfilterTypeは保持するが、UIは非表示

  const viewModeOptions: { mode: ViewMode; label: string; icon: React.ReactNode }[] = [
    { mode: "list", label: "リスト", icon: <LayoutGrid className="w-4 h-4" /> },
    { mode: "calendar", label: "カレンダー", icon: <Calendar className="w-4 h-4" /> },
  ];

  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
      <Header user={user} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Hero Section */}
        <div className="relative mb-8 overflow-hidden">
          <div className="relative z-10">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div>
                <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                  審議会管理
                </h1>
                <p className="text-surface-500 dark:text-surface-400">
                  {councils.length === 0
                    ? "最初の審議会を登録しましょう"
                    : `${councils.length} 件の審議会`}
                </p>
              </div>
              <Button
                variant="primary"
                size="lg"
                leftIcon={<Plus className="w-5 h-5" />}
                onClick={() => setIsModalOpen(true)}
              >
                新規登録
              </Button>
            </div>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="mb-6 flex flex-wrap items-center justify-end gap-4">
          {/* 審議会は常に公開なのでフィルタータブは不要 */}
          <div className="flex bg-surface-100 dark:bg-surface-800 rounded-xl p-1">
            {viewModeOptions.map((option) => (
              <button
                key={option.mode}
                onClick={() => setViewMode(option.mode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  viewMode === option.mode
                    ? "bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 shadow-sm"
                    : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
                }`}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Calendar View */}
        {viewMode === "calendar" ? (
          <div className="mb-6">
            {calendarLoading ? (
              <Card variant="default" padding="lg" className="text-center py-16">
                <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p className="text-surface-500 dark:text-surface-400">カレンダーを読み込み中...</p>
              </Card>
            ) : (
              <GlobalCalendarView
                meetings={calendarMeetings}
                view={calendarView}
                onViewChange={setCalendarView}
                currentDate={calendarDate}
                onDateChange={setCalendarDate}
                onMeetingClick={handleCalendarMeetingClick}
                councilCount={calendarCouncilCount}
              />
            )}
          </div>
        ) : (
          <>
            {/* Search */}
            {councils.length > 0 && (
              <div className="mb-6">
                <Input
                  placeholder="審議会を検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  leftIcon={<Search className="w-4 h-4" />}
                  className="max-w-md"
                />
              </div>
            )}

            {/* Councils Grid */}
            {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="default" padding="none">
                <div className="p-5">
                  <Skeleton className="h-6 w-3/4 mb-3" />
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
                <div className="px-5 py-3 border-t border-surface-100 dark:border-surface-700">
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : filteredCouncils.length === 0 ? (
          <Card variant="default" padding="lg" className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-primary-100 to-accent-100 dark:from-primary-900/50 dark:to-accent-900/50 flex items-center justify-center">
              {searchQuery ? (
                <Search className="w-10 h-10 text-primary-500" />
              ) : (
                <Building2 className="w-10 h-10 text-primary-500" />
              )}
            </div>
            <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
              {searchQuery ? "審議会が見つかりません" : "審議会がありません"}
            </h3>
            <p className="text-surface-500 dark:text-surface-400 mb-6 max-w-md mx-auto">
              {searchQuery
                ? "別のキーワードで検索してください"
                : "最初の審議会を登録して、議事録や資料の管理を始めましょう"}
            </p>
            {!searchQuery && (
              <Button
                variant="primary"
                leftIcon={<Plus className="w-4 h-4" />}
                onClick={() => setIsModalOpen(true)}
              >
                審議会を登録
              </Button>
            )}
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCouncils.map((council, index) => (
              <Card
                key={council.id}
                variant="hover"
                padding="none"
                className="group animate-fade-in-up"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <Link href={`/councils/${council.id}`} className="block">
                  <div className="p-5">
                    {/* Header with icon */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 dark:from-primary-500/20 dark:to-accent-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Building2 className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                      </div>
                      {/* 審議会は常に公開なのでバッジは不要 */}
                    </div>

                    {/* Title */}
                    <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                      {council.title}
                    </h3>

                    {/* Organization */}
                    {council.organization && (
                      <div className="flex flex-wrap gap-2 mb-2">
                        <span className="text-xs px-2 py-1 rounded-lg bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400">
                          {council.organization}
                        </span>
                      </div>
                    )}

                    {/* Description */}
                    {council.description && (
                      <p className="text-sm text-surface-500 dark:text-surface-400 line-clamp-2">
                        {council.description}
                      </p>
                    )}
                  </div>

                  {/* Footer */}
                  <div className="px-5 py-3 border-t border-surface-100 dark:border-surface-700/50 bg-surface-50/50 dark:bg-surface-800/30 flex items-center justify-between">
                    <div className="flex items-center gap-4 text-xs text-surface-400 dark:text-surface-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {council.meeting_count || 0} 回
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {council.created_at
                          ? new Date(council.created_at).toLocaleDateString("ja-JP")
                          : "最近"}
                      </span>
                    </div>
                    {!isOwner(council) && (
                      <span className="flex items-center gap-1 text-xs text-surface-400 dark:text-surface-500">
                        <UserIcon className="w-3.5 h-3.5" />
                        {council.owner_display_name}
                      </span>
                    )}
                  </div>
                </Link>

                {/* Action buttons (only for owner) */}
                {isOwner(council) && (
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-all duration-200 rounded-2xl pointer-events-none" />
                )}
                {isOwner(council) && (
                  <div className="absolute bottom-16 right-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleOpenEdit(council);
                      }}
                      className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-primary-50 dark:hover:bg-primary-900/30 text-surface-500 hover:text-primary-500 shadow-md transition-all"
                      title="編集"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setDeleteId(council.id);
                      }}
                      className="p-2 rounded-lg bg-white/90 dark:bg-surface-800/90 hover:bg-red-50 dark:hover:bg-red-900/30 text-surface-500 hover:text-red-500 shadow-md transition-all"
                      title="削除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </Card>
            ))}
            </div>
          )}
          </>
        )}
      </main>

      {/* Create Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          resetCreateForm();
        }}
        title="新しい審議会を登録"
        description="審議会の基本情報を入力してください"
        size="lg"
      >
        <div className="space-y-4">
          <Input
            label="審議会名"
            placeholder="例：総合資源エネルギー調査会"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            leftIcon={<Building2 className="w-4 h-4" />}
            required
          />

          <Input
            label="所管省庁"
            placeholder="例：経済産業省"
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
          />

          <Input
            label="公式ページURL"
            placeholder="https://www.meti.go.jp/..."
            value={officialUrl}
            onChange={(e) => setOfficialUrl(e.target.value)}
            leftIcon={<ExternalLink className="w-4 h-4" />}
          />

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              説明（任意）
            </label>
            <textarea
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="この審議会の概要を入力してください"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
          </div>

          {/* 審議会は常に公開なので公開/非公開トグルは不要 */}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="ghost"
              onClick={() => {
                setIsModalOpen(false);
                resetCreateForm();
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              isLoading={creating}
              disabled={!title.trim()}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              登録
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="審議会を削除"
        description="この操作は取り消せません。すべての開催回、メモ、チャット履歴が完全に削除されます。"
        size="sm"
      >
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => setDeleteId(null)}>
            キャンセル
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteId && handleDelete(deleteId)}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            削除
          </Button>
        </div>
      </Modal>

      {/* Edit Council Modal */}
      <Modal
        isOpen={!!editCouncil}
        onClose={() => setEditCouncil(null)}
        title="審議会を編集"
        description="審議会の情報を変更できます"
        size="lg"
      >
        <div className="space-y-4">
          <Input
            label="審議会名"
            placeholder="例：総合資源エネルギー調査会"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            leftIcon={<Building2 className="w-4 h-4" />}
            required
          />

          <Input
            label="所管省庁"
            placeholder="例：経済産業省"
            value={editOrganization}
            onChange={(e) => setEditOrganization(e.target.value)}
          />

          <Input
            label="公式ページURL"
            placeholder="https://www.meti.go.jp/..."
            value={editOfficialUrl}
            onChange={(e) => setEditOfficialUrl(e.target.value)}
            leftIcon={<ExternalLink className="w-4 h-4" />}
          />

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5">
              説明（任意）
            </label>
            <textarea
              className="w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl transition-all duration-200 placeholder:text-surface-400 dark:placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="この審議会の概要を入力してください"
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
            />
          </div>

          {/* 審議会は常に公開なので公開/非公開トグルは不要 */}

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setEditCouncil(null)}>
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveCouncil}
              isLoading={savingCouncil}
              disabled={!editTitle.trim()}
              leftIcon={<Save className="w-4 h-4" />}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
