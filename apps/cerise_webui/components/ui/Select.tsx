'use client';

import { useState, useRef, useEffect, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check } from 'lucide-react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value?: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
}

export function Select({
  value,
  onValueChange,
  options,
  placeholder = 'Select...',
  disabled = false,
}: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div className="relative w-full z-20" ref={containerRef}>
      <button
        type="button"
        className={`
          w-full flex items-center justify-between px-4 py-2.5 text-sm bg-white dark:bg-zinc-900 
          border border-border rounded-lg shadow-sm transition-all duration-200
          hover:border-foreground-secondary/50 focus:outline-none focus:ring-2 focus:ring-cerise-primary/20 focus:border-cerise-primary
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${isOpen ? 'border-cerise-primary ring-2 ring-cerise-primary/20' : ''}
        `}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        <span
          className={`${!selectedOption ? 'text-foreground-tertiary' : 'text-foreground'} truncate`}
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-foreground-tertiary transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -5, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -5, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 right-0 mt-1.5 p-1 bg-white dark:bg-zinc-900 border border-border rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto"
          >
            {options.length === 0 ? (
              <div className="px-4 py-2 text-sm text-foreground-tertiary text-center">
                No options
              </div>
            ) : (
              options.map((option) => (
                <button
                  key={option.value}
                  className={`
                    w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors text-left
                    ${value === option.value ? 'bg-cerise-primary/10 text-cerise-primary font-medium' : 'text-foreground hover:bg-zinc-100 dark:hover:bg-zinc-800'}
                    `}
                  onClick={() => {
                    onValueChange(option.value);
                    setIsOpen(false);
                  }}
                >
                  <span className="truncate">{option.label}</span>
                  {value === option.value && <Check className="w-3.5 h-3.5" />}
                </button>
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
