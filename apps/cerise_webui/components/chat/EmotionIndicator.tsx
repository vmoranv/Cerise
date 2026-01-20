'use client';

import { motion } from 'framer-motion';
import { useChatStore, Emotion } from '@/stores';
import { Heart, Zap, CloudRain, Flame, Sparkles, Brain, Star, Smile } from 'lucide-react';

// 情感到图标的映射
const emotionIcons: Record<Emotion, typeof Heart> = {
  [Emotion.NEUTRAL]: Smile,
  [Emotion.HAPPY]: Heart,
  [Emotion.SAD]: CloudRain,
  [Emotion.ANGRY]: Flame,
  [Emotion.SURPRISED]: Zap,
  [Emotion.FEAR]: Zap,
  [Emotion.DISGUST]: Flame,
  [Emotion.THINKING]: Brain,
  [Emotion.EXCITED]: Star,
  [Emotion.CONFIDENT]: Sparkles,
  [Emotion.SHY]: Heart,
  [Emotion.PLAYFUL]: Star,
};

// 情感到中文名称的映射
const emotionLabels: Record<Emotion, string> = {
  [Emotion.NEUTRAL]: '平静',
  [Emotion.HAPPY]: '开心',
  [Emotion.SAD]: '伤心',
  [Emotion.ANGRY]: '生气',
  [Emotion.SURPRISED]: '惊讶',
  [Emotion.FEAR]: '害怕',
  [Emotion.DISGUST]: '厌恶',
  [Emotion.THINKING]: '思考',
  [Emotion.EXCITED]: '兴奋',
  [Emotion.CONFIDENT]: '自信',
  [Emotion.SHY]: '害羞',
  [Emotion.PLAYFUL]: '调皮',
};

// 情感到颜色的映射
const emotionColors: Record<Emotion, string> = {
  [Emotion.NEUTRAL]: '#9ca3af',
  [Emotion.HAPPY]: '#fbbf24',
  [Emotion.SAD]: '#60a5fa',
  [Emotion.ANGRY]: '#ef4444',
  [Emotion.SURPRISED]: '#a78bfa',
  [Emotion.FEAR]: '#6366f1',
  [Emotion.DISGUST]: '#10b981',
  [Emotion.THINKING]: '#14b8a6',
  [Emotion.EXCITED]: '#ec4899',
  [Emotion.CONFIDENT]: '#f97316',
  [Emotion.SHY]: '#fb7185',
  [Emotion.PLAYFUL]: '#d946ef',
};

export function EmotionIndicator() {
  const { currentEmotion, emotionIntensity } = useChatStore();
  const Icon = emotionIcons[currentEmotion];
  const color = emotionColors[currentEmotion];
  const label = emotionLabels[currentEmotion];

  return (
    <motion.div
      className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gradient-soft border border-border"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* 情感图标 */}
      <motion.div
        className="relative flex items-center justify-center w-12 h-12 rounded-full"
        style={{
          background: `linear-gradient(135deg, ${color}22 0%, ${color}44 100%)`,
        }}
        animate={{
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          repeatType: 'reverse',
        }}
      >
        <Icon className="w-6 h-6" style={{ color }} />

        {/* 脉冲效果 */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle, ${color}33 0%, transparent 70%)`,
          }}
          animate={{
            scale: [1, 1.5],
            opacity: [0.5, 0],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
          }}
        />
      </motion.div>

      {/* 情感信息 */}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-foreground">{label}</span>
          <span className="text-xs text-foreground-tertiary">
            {Math.round(emotionIntensity * 100)}%
          </span>
        </div>

        {/* 强度条 */}
        <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, ${color}88 0%, ${color} 100%)`,
            }}
            initial={{ width: 0 }}
            animate={{ width: `${emotionIntensity * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
