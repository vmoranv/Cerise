'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useChatStore, useUIStore } from '@/stores';
import { Eye, EyeOff, Sparkles } from 'lucide-react';

// Live2D 占位组件
// TODO: 集成实际的 Live2D SDK
export function Live2DView() {
  const { currentEmotion } = useChatStore();
  const { live2DVisible, toggleLive2D } = useUIStore();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // 模拟 Live2D 加载
    const timer = setTimeout(() => setIsReady(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  if (!live2DVisible) {
    return (
      <motion.div
        className="absolute top-4 right-4 z-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <button
          onClick={toggleLive2D}
          className="p-2 rounded-lg bg-white dark:bg-zinc-800 shadow-lg hover:shadow-xl transition-all"
          title="显示 Live2D"
        >
          <Eye className="w-5 h-5 text-foreground-secondary" />
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="relative w-full h-full flex items-center justify-center bg-gradient-soft rounded-2xl overflow-hidden"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden">
        {/* 樱花粉渐变背景 */}
        <div className="absolute inset-0 bg-gradient-to-br from-pink-50 via-rose-50 to-fuchsia-50 dark:from-zinc-900 dark:via-zinc-800 dark:to-zinc-900 opacity-60" />

        {/* 动态圆圈装饰 */}
        <motion.div
          className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-gradient-to-br from-cerise-light to-cerise-primary opacity-10"
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 90, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
        />
        <motion.div
          className="absolute -bottom-20 -left-20 w-64 h-64 rounded-full bg-gradient-to-br from-pink-400 to-rose-400 opacity-10"
          animate={{
            scale: [1.2, 1, 1.2],
            rotate: [90, 0, 90],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
        />
      </div>

      {/* Live2D 容器 */}
      <div className="relative z-10 w-full h-full flex flex-col items-center justify-center">
        {!isReady ? (
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-full border-4 border-cerise-light border-t-transparent animate-spin" />
            <p className="text-foreground-secondary">加载 Live2D 模型...</p>
          </div>
        ) : (
          <>
            {/* Live2D Canvas 占位 */}
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-32 h-32 mx-auto mb-4 rounded-full bg-gradient-to-br from-cerise-light to-cerise-primary opacity-20 flex items-center justify-center">
                  <Sparkles className="w-16 h-16 text-cerise-primary" />
                </div>
                <p className="text-lg font-medium text-foreground mb-2">Cerise</p>
                <p className="text-sm text-foreground-secondary">Live2D 模型占位</p>
                <p className="text-xs text-foreground-tertiary mt-2">
                  当前情感: {currentEmotion}
                </p>
              </div>
            </div>

            {/* 控制按钮 */}
            <div className="absolute top-4 right-4">
              <button
                onClick={toggleLive2D}
                className="p-2 rounded-lg bg-white dark:bg-zinc-800 shadow-lg hover:shadow-xl transition-all"
                title="隐藏 Live2D"
              >
                <EyeOff className="w-5 h-5 text-foreground-secondary" />
              </button>
            </div>
          </>
        )}
      </div>

      {/* Canvas 元素 - 用于实际的 Live2D 渲染 */}
      <canvas
        id="live2d-canvas"
        className="absolute inset-0 w-full h-full hidden"
        // TODO: 初始化 Live2D SDK
      />
    </motion.div>
  );
}
