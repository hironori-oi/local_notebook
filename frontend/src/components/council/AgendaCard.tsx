"use client";

import { FileText, ClipboardList, ExternalLink, ChevronRight, AlertCircle, ListOrdered } from "lucide-react";
import { CouncilAgendaItem, PROCESSING_STATUS_LABELS, PROCESSING_STATUS_COLORS } from "../../lib/councilApi";

interface AgendaCardProps {
  agenda: CouncilAgendaItem;
  onClick?: () => void;
  showActions?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

/**
 * Get aggregated materials status from the materials array
 */
function getMaterialsStatus(agenda: CouncilAgendaItem): { hasAny: boolean; status: string; label: string } {
  const hasMaterialsArray = agenda.materials && agenda.materials.length > 0;
  const hasLegacyUrl = !!agenda.materials_url;

  if (!hasMaterialsArray && !hasLegacyUrl) {
    return { hasAny: false, status: "none", label: "URL未設定" };
  }

  if (hasMaterialsArray) {
    // Aggregate status from materials array
    const statuses = agenda.materials.map((m) => m.processing_status);
    if (statuses.some((s) => s === "failed")) {
      return { hasAny: true, status: "failed", label: PROCESSING_STATUS_LABELS["failed"] || "失敗" };
    }
    if (statuses.some((s) => s === "processing")) {
      return { hasAny: true, status: "processing", label: PROCESSING_STATUS_LABELS["processing"] || "処理中" };
    }
    if (statuses.some((s) => s === "pending")) {
      return { hasAny: true, status: "pending", label: PROCESSING_STATUS_LABELS["pending"] || "待機中" };
    }
    if (statuses.every((s) => s === "completed")) {
      return { hasAny: true, status: "completed", label: `完了 (${agenda.materials.length}件)` };
    }
    // Mixed or unknown
    return { hasAny: true, status: "completed", label: `${agenda.materials.length}件` };
  }

  // Legacy materials_url
  return {
    hasAny: true,
    status: agenda.materials_processing_status,
    label: PROCESSING_STATUS_LABELS[agenda.materials_processing_status] || agenda.materials_processing_status,
  };
}

export function AgendaCard({ agenda, onClick, showActions, onEdit, onDelete }: AgendaCardProps) {
  const materialsStatus = getMaterialsStatus(agenda);

  const hasError =
    materialsStatus.status === "failed" ||
    agenda.minutes_processing_status === "failed";

  const hasAnyUrl = materialsStatus.hasAny || agenda.minutes_url;

  return (
    <div
      className={`bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-4 ${
        onClick ? "hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-lg transition-all cursor-pointer group" : ""
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Agenda number and title */}
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-sm font-medium">
              <ListOrdered className="w-3.5 h-3.5" />
              議題{agenda.agenda_number}
            </span>
            {hasError && (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs">
                <AlertCircle className="w-3 h-3" />
                エラー
              </span>
            )}
          </div>

          {agenda.title && (
            <h4 className={`font-medium text-surface-900 dark:text-surface-100 mb-2 ${
              onClick ? "group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" : ""
            }`}>
              {agenda.title}
            </h4>
          )}

          {/* Status badges */}
          <div className="flex flex-wrap gap-2">
            {/* Materials status */}
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs ${
                  materialsStatus.hasAny
                    ? PROCESSING_STATUS_COLORS[materialsStatus.status] || "bg-gray-100 text-gray-700"
                    : "bg-surface-100 dark:bg-surface-700 text-surface-500 dark:text-surface-400"
                }`}
              >
                <FileText className="w-3 h-3" />
                資料: {materialsStatus.label}
              </span>
              {agenda.materials_url && (
                <a
                  href={agenda.materials_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-surface-400 hover:text-primary-500 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            {/* Minutes status */}
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs ${
                  agenda.minutes_url
                    ? PROCESSING_STATUS_COLORS[agenda.minutes_processing_status] || "bg-gray-100 text-gray-700"
                    : "bg-surface-100 dark:bg-surface-700 text-surface-500 dark:text-surface-400"
                }`}
              >
                <ClipboardList className="w-3 h-3" />
                議事録: {agenda.minutes_url
                  ? PROCESSING_STATUS_LABELS[agenda.minutes_processing_status] || agenda.minutes_processing_status
                  : "URL未設定"}
              </span>
              {agenda.minutes_url && (
                <a
                  href={agenda.minutes_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-surface-400 hover:text-primary-500 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>

          {/* Action buttons */}
          {showActions && (
            <div className="flex gap-2 mt-3 pt-3 border-t border-surface-100 dark:border-surface-700">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit?.();
                }}
                className="px-3 py-1.5 text-xs font-medium text-surface-600 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
              >
                編集
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete?.();
                }}
                className="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                削除
              </button>
            </div>
          )}
        </div>

        {/* Arrow (only when clickable) */}
        {onClick && (
          <ChevronRight className="w-5 h-5 text-surface-400 group-hover:text-primary-500 group-hover:translate-x-1 transition-all flex-shrink-0 ml-4" />
        )}
      </div>
    </div>
  );
}
