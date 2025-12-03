"use client";

import { HTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";
import { User } from "lucide-react";

export interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  name?: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  variant?: "circle" | "rounded";
}

const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, src, alt, name, size = "md", variant = "circle", ...props }, ref) => {
    const sizes = {
      xs: "w-6 h-6 text-xs",
      sm: "w-8 h-8 text-sm",
      md: "w-10 h-10 text-base",
      lg: "w-12 h-12 text-lg",
      xl: "w-16 h-16 text-xl",
    };

    const iconSizes = {
      xs: "w-3 h-3",
      sm: "w-4 h-4",
      md: "w-5 h-5",
      lg: "w-6 h-6",
      xl: "w-8 h-8",
    };

    const variants = {
      circle: "rounded-full",
      rounded: "rounded-xl",
    };

    const getInitials = (name: string) => {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    };

    const getGradient = (name?: string) => {
      const gradients = [
        "from-primary-400 to-primary-600",
        "from-accent-400 to-accent-600",
        "from-emerald-400 to-emerald-600",
        "from-amber-400 to-amber-600",
        "from-rose-400 to-rose-600",
        "from-violet-400 to-violet-600",
        "from-cyan-400 to-cyan-600",
      ];
      if (!name) return gradients[0];
      const index = name.charCodeAt(0) % gradients.length;
      return gradients[index];
    };

    return (
      <div
        ref={ref}
        className={clsx(
          "relative flex items-center justify-center overflow-hidden",
          sizes[size],
          variants[variant],
          !src && `bg-gradient-to-br ${getGradient(name)} text-white font-medium`,
          className
        )}
        {...props}
      >
        {src ? (
          <img
            src={src}
            alt={alt || name || "Avatar"}
            className="w-full h-full object-cover"
          />
        ) : name ? (
          <span>{getInitials(name)}</span>
        ) : (
          <User className={iconSizes[size]} />
        )}
      </div>
    );
  }
);

Avatar.displayName = "Avatar";

export { Avatar };
