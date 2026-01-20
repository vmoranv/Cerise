'use client';

import { motion } from 'framer-motion';

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Switch({
  checked,
  onCheckedChange,
  disabled = false,
}: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onCheckedChange(!checked)}
      className={`
        relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cerise-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background
        ${checked ? 'bg-cerise-primary' : 'bg-zinc-200 dark:bg-zinc-700'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
      disabled={disabled}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className={`
          pointer-events-none block h-5 w-5 rounded-full bg-white shadow-lg ring-0
          ${checked ? 'translate-x-5' : 'translate-x-0'}
        `}
      />
    </button>
  );
}
