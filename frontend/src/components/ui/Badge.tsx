"use client";

import { HTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "secondary" | "accent" | "success" | "warning" | "danger";
  size?: "sm" | "md";
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    const variants = {
      primary:
        "bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300",
      secondary:
        "bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400",
      accent:
        "bg-accent-100 dark:bg-accent-900/50 text-accent-700 dark:text-accent-300",
      success:
        "bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300",
      warning:
        "bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300",
      danger:
        "bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300",
    };

    const sizes = {
      sm: "px-2 py-0.5 text-[10px]",
      md: "px-2.5 py-1 text-xs",
    };

    return (
      <span
        ref={ref}
        className={clsx(
          "inline-flex items-center gap-1 font-medium rounded-full",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";

export { Badge };
