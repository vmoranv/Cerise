'use client';

import { ReactNode, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [open]);

  // Use portal if possible, but for simplicity in this stack just render
  // Note: Portal is better for ensuring z-index, but requires document access.
  // We'll trust the z-index for now or use a Portal component if we had one.
  // Actually, let's use a simple portal check or just render inline if typically at root.
  // Given Next.js app directory, inline often works if placed high, but for a reusable component, Portal is best.
  // However, I'll stick to inline with high z-index for simplicity unless it fails.
  // Wait, existing SettingsDialog used inline fixed positioning. I'll do the same.

  return (
    <AnimatePresence>
      {open && (
        <div className="relative z-50">
          <motion.div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => onOpenChange(false)}
          />
          <div className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none">
            {children}
          </div>
        </div>
      )}
    </AnimatePresence>
  );
}

interface DialogContentProps {
  children: ReactNode;
  className?: string;
  title?: string;
  onClose?: () => void; // Optional closer if not using Context
}

export function DialogContent({
  children,
  className = '',
  title,
  onClose,
}: DialogContentProps) {
  return (
    <motion.div
      className={`
        bg-background rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden pointer-events-auto border border-border
        ${className}
      `}
      initial={{ opacity: 0, scale: 0.95, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: 20 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
    >
      {title && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-gradient-to-r from-cerise-light/10 to-cerise-primary/10">
          <h2 className="text-xl font-bold bg-gradient-to-r from-cerise-light to-cerise-primary bg-clip-text text-transparent">
            {title}
          </h2>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            >
              <X className="w-5 h-5 text-foreground-secondary" />
            </button>
          )}
        </div>
      )}
      <div className="p-6">{children}</div>
    </motion.div>
  );
}
