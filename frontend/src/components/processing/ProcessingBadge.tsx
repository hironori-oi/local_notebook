"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { getProcessingStats, ProcessingStats } from "../../lib/processingApi";
import { isAuthenticated } from "../../lib/apiClient";

export function ProcessingBadge() {
  const [stats, setStats] = useState<ProcessingStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Only fetch if authenticated
    if (!isAuthenticated()) {
      setIsLoading(false);
      return;
    }

    const fetchStats = async () => {
      try {
        const data = await getProcessingStats();
        setStats(data);
      } catch (error) {
        console.error("Failed to fetch processing stats:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();

    // Poll every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  // Don't render anything while loading or if not authenticated
  if (isLoading || !stats) return null;

  const activeCount = stats.pending + stats.processing;

  // Don't show badge if no active processing
  if (activeCount === 0) return null;

  return (
    <Link
      href="/processing"
      className="relative p-2 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-800 transition-all"
      title={`処理状況: ${stats.pending}件待機中, ${stats.processing}件処理中`}
    >
      <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
      <span className="absolute -top-0.5 -right-0.5 w-4 h-4 flex items-center justify-center text-[10px] font-bold text-white bg-primary-500 rounded-full">
        {activeCount > 9 ? "9+" : activeCount}
      </span>
    </Link>
  );
}
