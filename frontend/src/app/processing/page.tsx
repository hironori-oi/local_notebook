"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Clock, Loader2, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { Header } from "../../components/layout/Header";
import { ProcessingItemCard } from "../../components/processing";
import { Button } from "../../components/ui/Button";
import {
  getProcessingDashboard,
  ProcessingDashboard,
  ProcessingItem,
  retryProcessing,
  STATUS_LABELS,
} from "../../lib/processingApi";
import { getUser, User, isAuthenticated } from "../../lib/apiClient";

interface StatCardProps {
  label: string;
  value: number;
  icon: React.ElementType;
  color: "surface" | "primary" | "green" | "red";
}

function StatCard({ label, value, icon: Icon, color }: StatCardProps) {
  const colorClasses = {
    surface: "bg-surface-100 dark:bg-surface-800 text-surface-500",
    primary: "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400",
    green: "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400",
    red: "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400",
  };

  return (
    <div className={`p-4 rounded-xl ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium opacity-80">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <Icon className={`w-8 h-8 opacity-50 ${color === "primary" ? "animate-spin" : ""}`} />
      </div>
    </div>
  );
}

export default function ProcessingPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [dashboard, setDashboard] = useState<ProcessingDashboard | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  // Check auth and get user
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }

    const storedUser = getUser();
    if (storedUser) {
      setUser(storedUser);
    } else {
      router.push("/login");
    }
  }, [router]);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await getProcessingDashboard(filter);
      setDashboard(data);
    } catch (error) {
      console.error("Failed to fetch processing dashboard:", error);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  // Initial fetch and polling
  useEffect(() => {
    if (!user) return;

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 10000); // Poll every 10 seconds
    return () => clearInterval(interval);
  }, [user, fetchDashboard]);

  const handleRetry = async (item: ProcessingItem) => {
    setRetryingId(item.id);
    try {
      await retryProcessing(item.type, item.id);
      // Refresh dashboard after retry
      await fetchDashboard();
    } catch (error) {
      console.error("Failed to retry processing:", error);
      alert("再試行に失敗しました");
    } finally {
      setRetryingId(null);
    }
  };

  const handleManualRefresh = async () => {
    setLoading(true);
    await fetchDashboard();
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-900 dark:to-surface-800">
      <Header user={user} title="処理状況" />

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Header with refresh button */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">
              処理状況ダッシュボード
            </h1>
            <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
              資料・議事録のバックグラウンド処理状況を確認できます
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleManualRefresh}
            disabled={loading}
            leftIcon={
              loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )
            }
          >
            更新
          </Button>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="待機中"
            value={dashboard?.stats.pending || 0}
            icon={Clock}
            color="surface"
          />
          <StatCard
            label="処理中"
            value={dashboard?.stats.processing || 0}
            icon={Loader2}
            color="primary"
          />
          <StatCard
            label="今日完了"
            value={dashboard?.stats.completed_today || 0}
            icon={CheckCircle}
            color="green"
          />
          <StatCard
            label="今日失敗"
            value={dashboard?.stats.failed_today || 0}
            icon={XCircle}
            color="red"
          />
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(STATUS_LABELS).map(([status, label]) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === status
                  ? "bg-primary-500 text-white shadow-soft"
                  : "bg-white dark:bg-surface-800 text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Processing Items List */}
        <div className="space-y-3">
          {loading && !dashboard ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
          ) : dashboard?.items.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-surface-800 rounded-xl">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 dark:bg-surface-700 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-surface-400" />
              </div>
              <p className="text-surface-600 dark:text-surface-300 font-medium">
                {filter === "all"
                  ? "現在処理中のアイテムはありません"
                  : `「${STATUS_LABELS[filter]}」のアイテムはありません`}
              </p>
              <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
                新しい資料や議事録を追加すると、ここに処理状況が表示されます
              </p>
            </div>
          ) : (
            dashboard?.items.map((item) => (
              <ProcessingItemCard
                key={`${item.type}-${item.id}`}
                item={item}
                onRetry={() => handleRetry(item)}
                isRetrying={retryingId === item.id}
              />
            ))
          )}
        </div>

        {/* Auto-refresh notice */}
        <p className="text-center text-xs text-surface-400 dark:text-surface-500 mt-8">
          10秒ごとに自動更新されます
        </p>
      </main>
    </div>
  );
}
