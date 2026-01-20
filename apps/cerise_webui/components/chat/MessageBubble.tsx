'use client';

import { motion } from 'framer-motion';
import { type Message, Emotion } from '@/stores';
import { User, Sparkles } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

// 情感到颜色的映射
const emotionColors: Record<Emotion, string> = {
  [Emotion.NEUTRAL]: 'from-zinc-400 to-zinc-500',
  [Emotion.HAPPY]: 'from-yellow-400 to-amber-500',
  [Emotion.SAD]: 'from-blue-400 to-blue-600',
  [Emotion.ANGRY]: 'from-red-500 to-red-600',
  [Emotion.SURPRISED]: 'from-purple-400 to-purple-600',
  [Emotion.FEAR]: 'from-indigo-500 to-indigo-700',
  [Emotion.DISGUST]: 'from-green-500 to-green-700',
  [Emotion.THINKING]: 'from-teal-400 to-teal-600',
  [Emotion.EXCITED]: 'from-pink-400 to-pink-600',
  [Emotion.CONFIDENT]: 'from-orange-400 to-orange-600',
  [Emotion.SHY]: 'from-rose-300 to-rose-400',
  [Emotion.PLAYFUL]: 'from-fuchsia-400 to-fuchsia-600',
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const emotionColor = message.emotion ? emotionColors[message.emotion] : emotionColors[Emotion.NEUTRAL];

  return (
    <motion.div
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* 头像 */}
      <div
        className={`
          flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
          ${isUser ? 'bg-gradient-to-br from-zinc-600 to-zinc-700' : `bg-gradient-to-br ${emotionColor}`}
          shadow-md
        `}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Sparkles className="w-5 h-5 text-white" />
        )}
      </div>

      {/* 消息内容 */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[70%]`}>
        <div
          className={`
            px-4 py-3 rounded-2xl shadow-md
            ${
              isUser
                ? 'bg-gradient-to-br from-cerise-light to-cerise-primary text-white'
                : 'bg-white dark:bg-zinc-800 text-foreground border border-border'
            }
          `}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>

        {/* 时间戳 */}
        <div className="flex items-center gap-2 mt-1 px-2">
          <span className="text-xs text-foreground-tertiary">
            {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
