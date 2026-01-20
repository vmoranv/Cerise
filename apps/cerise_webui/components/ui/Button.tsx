'use client';

import { type ReactNode } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cerise-primary dark:focus:ring-offset-background';

  const variants = {
    // Minimal primary: solid distinct color, no heavy gradients
    primary:
      'bg-cerise-primary text-white hover:bg-violet-700 shadow-sm hover:shadow-glow',
    // Secondary: clean white/dark gray
    secondary:
      'bg-white dark:bg-zinc-800 text-foreground border border-border hover:bg-zinc-50 dark:hover:bg-zinc-700 shadow-sm',
    // Ghost: subtle
    ghost:
      'text-foreground-secondary hover:text-foreground hover:bg-zinc-100 dark:hover:bg-zinc-800',
    // Danger: subtle red
    danger:
      'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
    icon: 'h-10 w-10 min-w-[2.5rem] p-0',
  };

  return (
    <motion.button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      {...(props as any)}
    >
      {isLoading ? (
        <svg
          className="mr-2 h-4 w-4 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : null}
      {children}
    </motion.button>
  );
}
