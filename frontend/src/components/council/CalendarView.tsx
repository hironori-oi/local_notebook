"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Calendar, ListOrdered } from "lucide-react";
import { CalendarMeeting } from "../../lib/councilApi";

interface CalendarViewProps {
  meetings: CalendarMeeting[];
  view: "week" | "month";
  onViewChange: (view: "week" | "month") => void;
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onMeetingClick: (meetingId: string) => void;
}

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

// Helper function to get local date key (YYYY-MM-DD) without timezone issues
const toLocaleDateKey = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export function CalendarView({
  meetings,
  view,
  onViewChange,
  currentDate,
  onDateChange,
  onMeetingClick,
}: CalendarViewProps) {
  // Get the start and end of the current view
  const { startDate, endDate, days } = useMemo(() => {
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
    const map = new Map<string, CalendarMeeting[]>();
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
      <div className={`grid grid-cols-7 ${view === "month" ? "min-h-[480px]" : "min-h-[200px]"}`}>
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
              } ${view === "week" ? "min-h-[160px]" : "min-h-[100px]"}`}
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
              </div>

              {/* Meetings */}
              <div className="space-y-1">
                {dayMeetings.map((meeting) => (
                  <button
                    key={meeting.id}
                    onClick={() => onMeetingClick(meeting.id)}
                    className="w-full text-left px-2 py-1 rounded-md bg-primary-50 dark:bg-primary-900/30 hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors group"
                  >
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-primary-500 flex-shrink-0" />
                      <span className="text-xs font-medium text-primary-700 dark:text-primary-300 truncate">
                        第{meeting.meeting_number}回
                      </span>
                    </div>
                    {meeting.title && (
                      <p className="text-xs text-surface-500 dark:text-surface-400 truncate mt-0.5">
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
