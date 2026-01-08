"use client";

import { Plus, ListOrdered } from "lucide-react";
import { CouncilAgendaItem } from "../../lib/councilApi";
import { AgendaCard } from "./AgendaCard";

interface AgendaListProps {
  agendas: CouncilAgendaItem[];
  onAgendaClick?: (agenda: CouncilAgendaItem) => void;
  onAddClick?: () => void;
  onEditAgenda?: (agenda: CouncilAgendaItem) => void;
  onDeleteAgenda?: (agenda: CouncilAgendaItem) => void;
  showActions?: boolean;
  emptyMessage?: string;
}

export function AgendaList({
  agendas,
  onAgendaClick,
  onAddClick,
  onEditAgenda,
  onDeleteAgenda,
  showActions = false,
  emptyMessage = "議題がありません",
}: AgendaListProps) {
  return (
    <div className="space-y-4">
      {/* Header with add button */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 flex items-center gap-2">
          <ListOrdered className="w-5 h-5" />
          議題一覧
          {agendas.length > 0 && (
            <span className="text-sm font-normal text-surface-500 dark:text-surface-400">
              ({agendas.length}件)
            </span>
          )}
        </h3>
        {onAddClick && (
          <button
            onClick={onAddClick}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            議題を追加
          </button>
        )}
      </div>

      {/* Agenda cards */}
      {agendas.length > 0 ? (
        <div className="space-y-3">
          {agendas.map((agenda) => (
            <AgendaCard
              key={agenda.id}
              agenda={agenda}
              onClick={onAgendaClick ? () => onAgendaClick(agenda) : undefined}
              showActions={showActions}
              onEdit={() => onEditAgenda?.(agenda)}
              onDelete={() => onDeleteAgenda?.(agenda)}
            />
          ))}
        </div>
      ) : (
        <div className="bg-surface-50 dark:bg-surface-800/50 rounded-xl border border-dashed border-surface-300 dark:border-surface-600 p-8 text-center">
          <ListOrdered className="w-10 h-10 text-surface-400 mx-auto mb-3" />
          <p className="text-surface-500 dark:text-surface-400 mb-4">
            {emptyMessage}
          </p>
          {onAddClick && (
            <button
              onClick={onAddClick}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 border border-primary-300 dark:border-primary-700 hover:border-primary-400 dark:hover:border-primary-600 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              最初の議題を追加
            </button>
          )}
        </div>
      )}
    </div>
  );
}
