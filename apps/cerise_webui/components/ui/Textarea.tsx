'use client';

import { type TextareaHTMLAttributes, forwardRef } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = '', error, ...props }, ref) => {
    return (
      <div className="w-full">
        <textarea
          ref={ref}
          className={`
            w-full rounded-lg border px-4 py-2.5
            bg-white dark:bg-zinc-900
            border-border dark:border-zinc-700
            text-foreground placeholder:text-foreground-tertiary
            focus:outline-none focus:ring-2 focus:ring-cerise-light focus:border-transparent
            transition-all duration-200
            resize-none
            ${error ? 'border-red-500 focus:ring-red-500' : ''}
            ${className}
          `}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
