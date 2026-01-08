"use client";

import { useMemo } from "react";
import { ChevronLeft, ChevronRight, Calendar, ListOrdered, Building2 } from "lucide-react";
import { GlobalCalendarMeeting } from "../../lib/councilApi";

interface GlobalCalendarViewProps {
  meetings: GlobalCalendarMeeting[];
  view: "week" | "month";
  onViewChange: (view: "week" | "month") => void;
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onMeetingClick: (councilId: string, meetingId: string) => void;
  councilCount: number;
}

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

// Helper function to get local date key (YYYY-MM-DD) without timezone issues
const toLocaleDateKey = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

// Generate consistent colors for councils based on their ID
function getCouncilColor(councilId: string): string {
  const colors = [
    "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800",
    "bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800",
    "bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800",
    "bg-orange-50 dark:bg-orange-900/30 border-orange-200 dark:border-orange-800",
    "bg-pink-50 dark:bg-pink-900/30 border-pink-200 dark:border-pink-800",
    "bg-teal-50 dark:bg-teal-900/30 border-teal-200 dark:border-teal-800",
    "bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-800",
    "bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800",
  ];
  // Simple hash of the council ID to get a consistent color
  let hash = 0;
  for (let i = 0; i < councilId.length; i++) {
    hash = councilId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function getCouncilTextColor(councilId: string): string {
  const colors = [
    "text-blue-700 dark:text-blue-300",
    "text-green-700 dark:text-green-300",
    "text-purple-700 dark:text-purple-300",
    "text-orange-700 dark:text-orange-300",
    "text-pink-700 dark:text-pink-300",
    "text-teal-700 dark:text-teal-300",
    "text-indigo-700 dark:text-indigo-300",
    "text-yellow-700 dark:text-yellow-300",
  ];
  let hash = 0;
  for (let i = 0; i < councilId.length; i++) {
    hash = councilId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

export function GlobalCalendarView({
  meetings,
  view,
  onViewChange,
  currentDate,
  onDateChange,
  onMeetingClick,
  councilCount,
}: GlobalCalendarViewProps) {
  // Get the start and end of the current view
  const { days } = useMemo(() => {
    if (view === "week") {
      const start = new Date(currentDate);
      const dayOfWeek = start.getDay();
      start.setDate(start.getDate() - dayOfWeek);
      start.setHours(0, 0, 0, 0);

      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      end.setHours(23, 59, 59, 999);

      const daysArray: Date[] = [];
      for (let i = 0; i < 7; i++) {
        const day = new Date(start);
        day.setDate(day.getDate() + i);
        daysArray.push(day);
      }

      return { startDate: start, endDate: end, days: daysArray };
    } else {
      // Month view
      const start = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
      const end = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);

      // Pad to start of week
      const startPadding = start.getDay();
      const actualStart = new Date(start);
      actualStart.setDate(actualStart.getDate() - startPadding);

      // Pad to end of week
      const endPadding = 6 - end.getDay();
      const actualEnd = new Date(end);
      actualEnd.setDate(actualEnd.getDate() + endPadding);

      const daysArray: Date[] = [];
      const cursor = new Date(actualStart);
      while (cursor <= actualEnd) {
        daysArray.push(new Date(cursor));
        cursor.setDate(cursor.getDate() + 1);
      }

      return { startDate: actualStart, endDate: actualEnd, days: daysArray };
    }
  }, [currentDate, view]);

  // Group meetings by date (using local timezone)
  const meetingsByDate = useMemo(() => {
    const map = new Map<string, GlobalCalendarMeeting[]>();
    meetings.forEach((meeting) => {
      const date = new Date(meeting.scheduled_at);
      const key = toLocaleDateKey(date);
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(meeting);
    });
    return map;
  }, [meetings]);

  const navigatePrev = () => {
    const newDate = new Date(currentDate);
    if (view === "week") {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setMonth(newDate.getMonth() - 1);
    }
    onDateChange(newDate);
  };

  const navigateNext = () => {
    const newDate = new Date(currentDate);
    if (view === "week") {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setMonth(newDate.getMonth() + 1);
    }
    onDateChange(newDate);
  };

  const goToToday = () => {
    onDateChange(new Date());
  };

  const formatHeader = () => {
    if (view === "week") {
      const weekStart = days[0];
      const weekEnd = days[6];
      const startMonth = weekStart.getMonth() + 1;
      const endMonth = weekEnd.getMonth() + 1;
      if (startMonth === endMonth) {
        return `${weekStart.getFullYear()}年${startMonth}月 ${weekStart.getDate()}日 - ${weekEnd.getDate()}日`;
      }
      return `${weekStart.getFullYear()}年${startMonth}月${weekStart.getDate()}日 - ${endMonth}月${weekEnd.getDate()}日`;
    }
    return `${currentDate.getFullYear()}年${currentDate.getMonth() + 1}月`;
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === currentDate.getMonth();
  };

  return (
    <div className="bg-white dark:bg-surface-800 rounded-2xl border border-surface-200 dark:border-surface-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-surface-200 dark:border-surface-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              {formatHeader()}
            </h2>
            <span className="px-2 py-1 text-xs font-medium bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400 rounded-md">
              {councilCount}件の審議会
            </span>
            <button
              onClick={goToToday}
              className="px-3 py-1 text-sm font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
            >
              今日
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* View toggle */}
            <div className="flex bg-surface-100 dark:bg-surface-700 rounded-lg p-1">
              <button
                onClick={() => onViewChange("week")}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  view === "week"
                    ? "bg-white dark:bg-surface-600 text-surface-900 dark:text-surface-100 shadow-sm"
                    : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
                }`}
              >
                週
              </button>
              <button
                onClick={() => onViewChange("month")}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  view === "month"
                    ? "bg-white dark:bg-surface-600 text-surface-900 dark:text-surface-100 shadow-sm"
                    : "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
                }`}
              >
                月
              </button>
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-1">
              <button
                onClick={navigatePrev}
                className="p-2 rounded-lg text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-700 transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={navigateNext}
                className="p-2 rounded-lg text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:text-surface-400 dark:hover:text-surface-200 dark:hover:bg-surface-700 transition-colors"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b border-surface-200 dark:border-surface-700">
        {WEEKDAYS.map((day, i) => (
          <div
            key={day}
            className={`py-2 text-center text-sm font-medium ${
              i === 0
                ? "text-red-500"
                : i === 6
                ? "text-blue-500"
                : "text-surface-500 dark:text-surface-400"
            }`}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className={`grid grid-cols-7 ${view === "month" ? "min-h-[520px]" : "min-h-[240px]"}`}>
        {days.map((date, index) => {
          const dateKey = toLocaleDateKey(date);
          const dayMeetings = meetingsByDate.get(dateKey) || [];
          const dayOfWeek = date.getDay();

          return (
            <div
              key={index}
              className={`border-b border-r border-surface-100 dark:border-surface-700/50 p-2 ${
                view === "month" && !isCurrentMonth(date)
                  ? "bg-surface-50 dark:bg-surface-900/50"
                  : ""
              } ${view === "week" ? "min-h-[200px]" : "min-h-[120px]"}`}
            >
              {/* Date number */}
              <div className="flex items-center justify-between mb-1">
                <span
                  className={`text-sm font-medium ${
                    isToday(date)
                      ? "w-7 h-7 flex items-center justify-center bg-primary-500 text-white rounded-full"
                      : dayOfWeek === 0
                      ? "text-red-500"
                      : dayOfWeek === 6
                      ? "text-blue-500"
                      : view === "month" && !isCurrentMonth(date)
                      ? "text-surface-400 dark:text-surface-600"
                      : "text-surface-700 dark:text-surface-300"
                  }`}
                >
                  {date.getDate()}
                </span>
                {dayMeetings.length > 0 && (
                  <span className="text-xs text-surface-400 dark:text-surface-500">
                    {dayMeetings.length}件
                  </span>
                )}
              </div>

              {/* Meetings */}
              <div className="space-y-1 overflow-y-auto max-h-[100px]">
                {dayMeetings.map((meeting) => (
                  <button
                    key={meeting.id}
                    onClick={() => onMeetingClick(meeting.council_id, meeting.id)}
                    className={`w-full text-left px-2 py-1.5 rounded-md border hover:opacity-80 transition-all group ${getCouncilColor(meeting.council_id)}`}
                  >
                    {/* Council name */}
                    <div className="flex items-center gap-1 mb-0.5">
                      <Building2 className={`w-3 h-3 flex-shrink-0 ${getCouncilTextColor(meeting.council_id)}`} />
                      <span className={`text-[10px] font-medium truncate ${getCouncilTextColor(meeting.council_id)}`}>
                        {meeting.council_title}
                      </span>
                    </div>
                    {/* Meeting number */}
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-surface-500 flex-shrink-0" />
                      <span className="text-xs font-medium text-surface-700 dark:text-surface-300 truncate">
                        第{meeting.meeting_number}回
                      </span>
                    </div>
                    {meeting.title && (
                      <p className="text-[10px] text-surface-500 dark:text-surface-400 truncate mt-0.5">
                        {meeting.title}
                      </p>
                    )}
                    {/* Agenda count */}
                    {meeting.agenda_count > 0 && (
                      <div className="flex items-center gap-1 mt-1">
                        <span className="inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                          <ListOrdered className="w-2.5 h-2.5" />
                          {meeting.agenda_count}
                        </span>
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
