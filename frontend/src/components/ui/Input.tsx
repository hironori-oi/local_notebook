"use client";

import { forwardRef, InputHTMLAttributes, useId } from "react";
import { clsx } from "clsx";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const helperId = `${generatedId}-helper`;
    const hasHelper = error || helperText;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1.5"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 dark:text-surface-500" aria-hidden="true">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={hasHelper ? helperId : undefined}
            className={clsx(
              "w-full px-4 py-2.5 text-sm bg-white dark:bg-surface-800 border rounded-xl transition-all duration-200",
              "placeholder:text-surface-400 dark:placeholder:text-surface-500",
              "focus:outline-none focus:ring-2 focus:border-transparent",
              error
                ? "border-red-300 dark:border-red-700 focus:ring-red-500"
                : "border-surface-200 dark:border-surface-700 focus:ring-primary-500",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 dark:text-surface-500" aria-hidden="true">
              {rightIcon}
            </div>
          )}
        </div>
        {hasHelper && (
          <p
            id={helperId}
            role={error ? "alert" : undefined}
            className={clsx(
              "mt-1.5 text-xs",
              error
                ? "text-red-500 dark:text-red-400"
                : "text-surface-500 dark:text-surface-400"
            )}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };
