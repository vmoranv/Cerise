'use client';

import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Button } from '../ui/Button';
import { Send, Paperclip } from 'lucide-react';
import { useUIStore } from '@/stores';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Message Cerise...',
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // const { voiceInputActive, setVoiceInputActive } = useUIStore(); // Unused for now

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'; // Reset height
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  return (
    <div className="w-full relative group">
      <div
        className={cn(
          'flex items-end gap-2 p-2 rounded-[1.5rem] border transition-all duration-300',
          'bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl',
          'border-black/5 dark:border-white/10',
          'focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/50',
          'shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.2)]',
          'hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)]',
        )}
      >
        {/* Attachment Button */}
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full h-10 w-10 text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
          title="Add attachment"
          disabled={disabled}
        >
          <Paperclip className="w-5 h-5" />
        </Button>

        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            'flex-1 bg-transparent border-0 focus:ring-0 p-2.5',
            'text-base text-foreground placeholder:text-muted-foreground/70',
            'resize-none min-h-[44px] max-h-[200px] overflow-y-auto w-full',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
          style={{ height: 'auto' }}
        />

        {/* Send Button */}
        <Button
          size="icon"
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className={cn(
            'rounded-full h-10 w-10 shrink-0 transition-all duration-300',
            message.trim()
              ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90'
              : 'bg-muted text-muted-foreground hover:bg-muted/80 shadow-none',
          )}
        >
          <Send className="w-5 h-5" />
        </Button>
      </div>

      {/* Decorative Glow */}
      <div className="absolute inset-0 -z-10 rounded-[1.5rem] bg-gradient-to-b from-primary/5 to-transparent blur-xl opacity-0 transition-opacity duration-500 group-focus-within:opacity-100" />
    </div>
  );
}
