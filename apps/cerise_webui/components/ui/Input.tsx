import { type InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  className?: string; // Additional classes for the input element
  wrapperClassName?: string; // Classes for the wrapper div
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', wrapperClassName = '', ...props }, ref) => {
    return (
      <div className={`space-y-1.5 ${wrapperClassName}`}>
        {label && (
          <label className="text-xs font-medium text-foreground-secondary ml-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            w-full px-4 py-2.5 text-sm bg-white dark:bg-zinc-900 
            border border-border rounded-lg shadow-sm
            outline-none transition-all duration-200
            placeholder:text-foreground-tertiary
            hover:border-foreground-secondary/50 
            focus:border-cerise-primary focus:ring-2 focus:ring-cerise-primary/20
            disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-zinc-50 dark:disabled:bg-zinc-800
            ${error ? 'border-error focus:border-error focus:ring-error/20' : ''}
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-xs text-error ml-1">{error}</p>}
      </div>
    );
  },
);

Input.displayName = 'Input';
