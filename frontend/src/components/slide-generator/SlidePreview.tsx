"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Edit3, Presentation } from "lucide-react";
import { Slide, SLIDE_TYPE_LABELS } from "../../lib/slideGeneratorApi";

interface SlidePreviewProps {
  slides: Slide[];
  onSlideClick?: (slide: Slide) => void;
}

export function SlidePreview({ slides, onSlideClick }: SlidePreviewProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [viewMode, setViewMode] = useState<"single" | "grid">("single");

  if (slides.length === 0) {
    return (
      <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-soft border border-surface-200 dark:border-surface-700 p-8 text-center">
        <Presentation className="w-12 h-12 mx-auto text-surface-300 mb-4" />
        <p className="text-surface-500">スライドがありません</p>
      </div>
    );
  }

  const currentSlide = slides[currentIndex];

  const goToPrevious = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => Math.min(slides.length - 1, prev + 1));
  };

  return (
    <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-soft border border-surface-200 dark:border-surface-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-200 dark:border-surface-700">
        <h3 className="font-medium text-surface-900 dark:text-surface-100">
          スライドプレビュー
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("single")}
            className={`px-3 py-1 rounded-lg text-sm transition-colors ${
              viewMode === "single"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400"
                : "text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-700"
            }`}
          >
            単一表示
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={`px-3 py-1 rounded-lg text-sm transition-colors ${
              viewMode === "grid"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400"
                : "text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-700"
            }`}
          >
            一覧表示
          </button>
        </div>
      </div>

      {viewMode === "single" ? (
        <>
          {/* Single slide view */}
          <div className="p-6">
            <div
              className="aspect-[16/9] bg-gradient-to-br from-surface-50 to-surface-100
                          dark:from-surface-700 dark:to-surface-750 rounded-xl p-8 relative
                          border border-surface-200 dark:border-surface-600 cursor-pointer
                          hover:border-primary-400 transition-colors group"
              onClick={() => onSlideClick?.(currentSlide)}
            >
              {/* Edit indicator */}
              <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="flex items-center gap-1 px-2 py-1 bg-primary-500 text-white rounded-lg text-xs">
                  <Edit3 className="w-3 h-3" />
                  編集
                </div>
              </div>

              {/* Slide type badge */}
              <div className="absolute top-3 left-3">
                <span className="px-2 py-1 bg-surface-200 dark:bg-surface-600 rounded text-xs text-surface-600 dark:text-surface-300">
                  {SLIDE_TYPE_LABELS[currentSlide.slide_type] || currentSlide.slide_type}
                </span>
              </div>

              {/* Slide content */}
              <div className="h-full flex flex-col justify-center">
                <h4 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-4 text-center">
                  {currentSlide.title}
                </h4>

                {currentSlide.content.subtitle && (
                  <p className="text-lg text-surface-600 dark:text-surface-300 text-center mb-4">
                    {currentSlide.content.subtitle}
                  </p>
                )}

                {currentSlide.content.bullets && currentSlide.content.bullets.length > 0 && (
                  <ul className="space-y-2 max-w-2xl mx-auto">
                    {currentSlide.content.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-start gap-2 text-surface-700 dark:text-surface-200">
                        <span className="text-primary-500 mt-1">•</span>
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {currentSlide.content.details && (
                  <p className="text-sm text-surface-500 mt-4 text-center">
                    {currentSlide.content.details}
                  </p>
                )}
              </div>
            </div>

            {/* Speaker notes */}
            {currentSlide.speaker_notes && (
              <div className="mt-4 p-4 bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl shadow-soft-sm">
                <p className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-2">スピーカーノート</p>
                <p className="text-sm text-surface-700 dark:text-surface-300 whitespace-pre-wrap leading-relaxed">
                  {currentSlide.speaker_notes}
                </p>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between p-4 border-t border-surface-200 dark:border-surface-700">
            <button
              onClick={goToPrevious}
              disabled={currentIndex === 0}
              className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700
                         disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-5 h-5 text-surface-600 dark:text-surface-300" />
            </button>

            <div className="flex items-center gap-2">
              {slides.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentIndex(i)}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    i === currentIndex
                      ? "bg-primary-500"
                      : "bg-surface-300 dark:bg-surface-600 hover:bg-surface-400"
                  }`}
                />
              ))}
            </div>

            <button
              onClick={goToNext}
              disabled={currentIndex === slides.length - 1}
              className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700
                         disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-5 h-5 text-surface-600 dark:text-surface-300" />
            </button>
          </div>

          {/* Slide counter */}
          <div className="text-center pb-4 text-sm text-surface-500">
            {currentIndex + 1} / {slides.length}
          </div>
        </>
      ) : (
        /* Grid view */
        <div className="p-4 grid grid-cols-2 md:grid-cols-3 gap-4">
          {slides.map((slide, index) => (
            <div
              key={slide.id}
              className={`aspect-[16/9] bg-gradient-to-br from-surface-50 to-surface-100
                          dark:from-surface-700 dark:to-surface-750 rounded-lg p-4 relative
                          border cursor-pointer transition-all group ${
                            index === currentIndex
                              ? "border-primary-400 ring-2 ring-primary-200 dark:ring-primary-800"
                              : "border-surface-200 dark:border-surface-600 hover:border-primary-300"
                          }`}
              onClick={() => {
                setCurrentIndex(index);
                onSlideClick?.(slide);
              }}
            >
              {/* Slide number */}
              <div className="absolute top-2 left-2">
                <span className="px-1.5 py-0.5 bg-surface-200 dark:bg-surface-600 rounded text-xs">
                  {index + 1}
                </span>
              </div>

              {/* Edit indicator */}
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Edit3 className="w-3 h-3 text-primary-500" />
              </div>

              {/* Slide title */}
              <div className="h-full flex flex-col justify-center">
                <p className="text-sm font-medium text-surface-900 dark:text-surface-100 text-center line-clamp-2">
                  {slide.title}
                </p>
                {slide.content.bullets && slide.content.bullets.length > 0 && (
                  <p className="text-xs text-surface-500 text-center mt-1">
                    {slide.content.bullets.length}項目
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
