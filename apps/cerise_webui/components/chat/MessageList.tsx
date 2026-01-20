'use client';

import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { useChatStore } from '@/stores';
import { Loader2, MessageCircle } from 'lucide-react';

export function MessageList() {
  const { messages, isLoading } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-cerise-light to-cerise-primary opacity-20 mb-4 flex items-center justify-center">
            <MessageCircle className="w-12 h-12 text-cerise-primary" />
          </div>
          <h3 className="text-xl font-semibold text-foreground mb-2">开始对话</h3>
          <p className="text-foreground-secondary max-w-md">
            你好！我是 Cerise，很高兴认识你。有什么我可以帮助你的吗？
          </p>
        </div>
      ) : (
        <>
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="flex items-center gap-2 text-foreground-secondary">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Cerise 正在思考...</span>
            </div>
          )}
        </>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
