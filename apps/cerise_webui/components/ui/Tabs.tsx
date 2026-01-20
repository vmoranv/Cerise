'use client';

import * as React from 'react';
import { motion } from 'framer-motion';

// Context for managing tab state
interface TabsContextType {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextType | undefined>(undefined);

interface TabsProps {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({
  defaultValue,
  value,
  onValueChange,
  children,
  className = '',
}: TabsProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue);

  const activeValue = value !== undefined ? value : internalValue;
  const handleValueChange = onValueChange || setInternalValue;

  return (
    <TabsContext.Provider
      value={{ value: activeValue, onValueChange: handleValueChange }}
    >
      <div className={`w-full ${className}`}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`
        inline-flex items-center justify-center rounded-xl bg-zinc-100 dark:bg-zinc-800/50 p-1.5
        border border-black/5 dark:border-white/5
        ${className}
      `}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  className = '',
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error('TabsTrigger must be used within Tabs');

  const isActive = context.value === value;

  return (
    <button
      className={`
        relative flex items-center justify-center px-5 py-2.5 text-sm font-medium transition-all duration-200 z-10
        rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-cerise-primary/50
        ${isActive ? 'text-foreground' : 'text-foreground-secondary hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5'}
        ${className}
      `}
      onClick={() => context.onValueChange(value)}
    >
      {isActive && (
        <motion.div
          layoutId="activeTab"
          className="absolute inset-0 bg-white dark:bg-zinc-700 shadow-sm rounded-lg -z-10"
          initial={false}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
        />
      )}
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  children,
  className = '',
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error('TabsContent must be used within Tabs');

  if (context.value !== value) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
