"use client";

import { HTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";

export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "white" | "surface";
}

const Spinner = forwardRef<HTMLDivElement, SpinnerProps>(
  ({ className, size = "md", variant = "primary", ...props }, ref) => {
    const sizes = {
      sm: "w-4 h-4 border-2",
      md: "w-6 h-6 border-2",
      lg: "w-8 h-8 border-3",
    };

    const variants = {
      primary: "border-surface-200 dark:border-surface-700 border-t-primary-500",
      white: "border-white/20 border-t-white",
      surface: "border-surface-300 dark:border-surface-600 border-t-surface-600 dark:border-t-surface-300",
    };

    return (
      <div
        ref={ref}
        className={clsx(
          "rounded-full animate-spin",
          sizes[size],
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);

Spinner.displayName = "Spinner";

// Full page loading spinner
const LoadingScreen = ({ message = "Loading..." }: { message?: string }) => {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center bg-surface-50 dark:bg-surface-950 z-50">
      <div className="relative">
        <div className="w-16 h-16 rounded-full border-4 border-primary-100 dark:border-primary-900/50"></div>
        <div className="absolute inset-0 w-16 h-16 rounded-full border-4 border-transparent border-t-primary-500 animate-spin"></div>
      </div>
      <p className="mt-4 text-sm text-surface-500 dark:text-surface-400 animate-pulse">
        {message}
      </p>
    </div>
  );
};

// Skeleton loader
const Skeleton = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { variant?: "text" | "circular" | "rectangular" }>(
  ({ className, variant = "text", ...props }, ref) => {
    const variants = {
      text: "h-4 rounded",
      circular: "rounded-full",
      rectangular: "rounded-xl",
    };

    return (
      <div
        ref={ref}
        className={clsx(
          "bg-gradient-to-r from-surface-200 via-surface-100 to-surface-200 dark:from-surface-700 dark:via-surface-800 dark:to-surface-700 bg-[length:200%_100%] animate-shimmer",
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);

Skeleton.displayName = "Skeleton";

export { Spinner, LoadingScreen, Skeleton };
