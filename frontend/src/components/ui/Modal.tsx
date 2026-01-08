"use client";

import { HTMLAttributes, forwardRef, useEffect, useCallback, useId } from "react";
import { clsx } from "clsx";
import { X } from "lucide-react";

export interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl" | "5xl" | "full";
  showCloseButton?: boolean;
}

const Modal = forwardRef<HTMLDivElement, ModalProps>(
  (
    {
      className,
      isOpen,
      onClose,
      title,
      description,
      size = "md",
      showCloseButton = true,
      children,
      ...props
    },
    ref
  ) => {
    const sizes = {
      sm: "max-w-sm",
      md: "max-w-md",
      lg: "max-w-lg",
      xl: "max-w-xl",
      "2xl": "max-w-2xl",
      "3xl": "max-w-3xl",
      "4xl": "max-w-4xl",
      "5xl": "max-w-5xl",
      full: "max-w-[90vw] max-h-[90vh]",
    };

    const isFullSize = size === "full";

    const handleEscape = useCallback(
      (e: KeyboardEvent) => {
        if (e.key === "Escape") onClose();
      },
      [onClose]
    );

    useEffect(() => {
      if (isOpen) {
        document.addEventListener("keydown", handleEscape);
        document.body.style.overflow = "hidden";
      }
      return () => {
        document.removeEventListener("keydown", handleEscape);
        document.body.style.overflow = "";
      };
    }, [isOpen, handleEscape]);

    const titleId = useId();
    const descriptionId = useId();

    if (!isOpen) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-surface-900/60 dark:bg-surface-950/80 backdrop-blur-sm animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Modal */}
        <div
          ref={ref}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? titleId : undefined}
          aria-describedby={description ? descriptionId : undefined}
          className={clsx(
            "relative w-full bg-white dark:bg-surface-800 rounded-2xl shadow-soft-xl animate-scale-in",
            isFullSize && "flex flex-col",
            sizes[size],
            className
          )}
          onClick={(e) => e.stopPropagation()}
          {...props}
        >
          {/* Header */}
          {(title || showCloseButton) && (
            <div className={clsx(
              "flex items-start justify-between p-5 border-b border-surface-200 dark:border-surface-700",
              isFullSize && "flex-shrink-0"
            )}>
              <div>
                {title && (
                  <h2
                    id={titleId}
                    className="text-lg font-semibold text-surface-900 dark:text-surface-100"
                  >
                    {title}
                  </h2>
                )}
                {description && (
                  <p
                    id={descriptionId}
                    className="mt-1 text-sm text-surface-500 dark:text-surface-400"
                  >
                    {description}
                  </p>
                )}
              </div>
              {showCloseButton && (
                <button
                  onClick={onClose}
                  aria-label="閉じる"
                  className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                >
                  <X className="w-5 h-5" aria-hidden="true" />
                </button>
              )}
            </div>
          )}

          {/* Content */}
          <div className={clsx(
            "p-5",
            isFullSize && "flex-1 overflow-y-auto"
          )}>{children}</div>
        </div>
      </div>
    );
  }
);

Modal.displayName = "Modal";

export { Modal };
