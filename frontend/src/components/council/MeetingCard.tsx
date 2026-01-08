"use client";

import { Calendar, ListOrdered, StickyNote, ChevronRight } from "lucide-react";
import { CouncilMeetingListItem } from "../../lib/councilApi";

interface MeetingCardProps {
  meeting: CouncilMeetingListItem;
  onClick: () => void;
}

export function MeetingCard({ meeting, onClick }: MeetingCardProps) {
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

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-lg transition-all p-4 group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Meeting number and title */}
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-sm font-medium">
              <Calendar className="w-3.5 h-3.5" />
              第{meeting.meeting_number}回
            </span>
          </div>

          {meeting.title && (
            <h4 className="font-medium text-surface-900 dark:text-surface-100 mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {meeting.title}
            </h4>
          )}

          {/* Date and time */}
          <p className="text-sm text-surface-500 dark:text-surface-400 mb-3">
            {formatDate(meeting.scheduled_at)} {formatTime(meeting.scheduled_at)}
          </p>

          {/* Counts badges */}
          <div className="flex flex-wrap gap-2">
            {/* Agenda count */}
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
              <ListOrdered className="w-3 h-3" />
              議題: {meeting.agenda_count}件
            </span>

            {/* Note count */}
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400">
              <StickyNote className="w-3 h-3" />
              メモ: {meeting.note_count}件
            </span>
          </div>
        </div>

        {/* Arrow */}
        <ChevronRight className="w-5 h-5 text-surface-400 group-hover:text-primary-500 group-hover:translate-x-1 transition-all flex-shrink-0 ml-4" />
      </div>
    </button>
  );
}
