'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { EmotionIndicator } from '@/components/chat/EmotionIndicator';
import { Live2DView } from '@/components/live2d/Live2DView';
import { useChatStore, type Message } from '@/stores';
import { chatApi } from '@/lib/api';
import { Settings, Menu, X, Sparkles, Zap, Brain, Mic } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils'; // Assuming you have a cn utility, if not I'll just use template literals or install it later.

export function ChatInterface() {
  const router = useRouter();
  const {
    session,
    setSession,
    messages,
    addMessage,
    setEmotion,
    setLoading,
    setError,
  } = useChatStore();

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // 初始化会话
  useEffect(() => {
    const initSession = async () => {
      try {
        const newSession = await chatApi.createSession({});
        setSession(newSession);
      } catch (error) {
        console.error('Failed to create session:', error);
        setError('无法创建会话');
      }
    };

    if (!session) {
      initSession();
    }
  }, [session, setSession, setError]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!session) {
        setError('Session not initialized');
        return;
      }
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: Date.now(),
      };
      addMessage(userMessage);
      setLoading(true);
      setError(null);

      try {
        const response = await chatApi.chat({
          message: content,
          session_id: session.session_id,
        });

        const assistantMessage: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: response.response,
          emotion: response.emotion,
          emotion_intensity: response.emotion_intensity,
          timestamp: Date.now(),
        };
        addMessage(assistantMessage);

        if (response.emotion)
          setEmotion(response.emotion, response.emotion_intensity ?? 0.5);
      } catch (error) {
        setError('Failed to send message');
      } finally {
        setLoading(false);
      }
    },
    [session, addMessage, setLoading, setError, setEmotion],
  );

  return (
    <div className="flex w-full h-screen bg-background text-foreground overflow-hidden font-sans">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[280px] flex-col border-r border-border bg-muted/10 h-full">
        <div className="h-14 flex items-center px-4 border-b border-border/50">
          <div className="flex items-center gap-2 font-semibold">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="tracking-tight">Cerise</span>
          </div>
        </div>

        <div className="flex-1 relative overflow-hidden">
          {/* Live2D Placeholder / View */}
          <div className="absolute inset-0">
            <Live2DView />
          </div>
        </div>

        <div className="p-4 border-t border-border/50 bg-background/50 backdrop-blur-sm">
          <EmotionIndicator />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full relative">
        {/* Mobile Header */}
        <header className="md:hidden h-14 flex items-center justify-between px-4 border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-50">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </Button>
          <span className="font-semibold">Cerise</span>
          <div className="w-9" /> {/* Spacer */}
        </header>

        {/* Mobile Sidebar Overlay */}
        <AnimatePresence>
          {isSidebarOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/50 z-50 md:hidden"
                onClick={() => setIsSidebarOpen(false)}
              />
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                className="fixed inset-y-0 left-0 w-[280px] bg-background z-50 md:hidden border-r shadow-xl flex flex-col"
              >
                <div className="p-4 flex justify-between items-center border-b">
                  <span className="font-bold">Menu</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsSidebarOpen(false)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex-1 relative">
                  <Live2DView />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* Scrollable Chat Area */}
        <div className="flex-1 overflow-y-auto w-full relative">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none -z-10" />

          <div className="max-w-4xl mx-auto w-full min-h-full flex flex-col">
            {messages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-12 select-none">
                <div className="text-center space-y-6 max-w-2xl">
                  <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-primary/10 text-primary mb-4 ring-1 ring-primary/20 shadow-[0_0_20px_-5px_var(--primary)]">
                    <Sparkles className="w-8 h-8" />
                  </div>
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground">
                    How can I help you today?
                  </h1>
                  <p className="text-xl text-muted-foreground leading-relaxed">
                    Cerise handles your complex tasks with multi-LLM routing,
                    voice interaction, and real-time intelligence.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
                  {[
                    {
                      title: 'Smart Routing',
                      icon: Brain,
                      desc: 'Auto-select best model',
                    },
                    {
                      title: 'Voice Mode',
                      icon: Mic,
                      desc: 'Hands-free interaction',
                    },
                    {
                      title: 'High Speed',
                      icon: Zap,
                      desc: 'Optimized inference',
                    },
                  ].map((item, i) => (
                    <button
                      key={i}
                      className="flex flex-col items-start p-6 rounded-2xl border border-border bg-card hover:bg-muted/50 transition-all text-left group"
                    >
                      <item.icon className="w-6 h-6 mb-3 text-muted-foreground group-hover:text-primary transition-colors" />
                      <span className="font-semibold text-foreground mb-1">
                        {item.title}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        {item.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex-1 p-4 pb-0">
                <MessageList />
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="w-full flex-none bg-gradient-to-t from-background via-background to-transparent pb-6 pt-10 px-4 z-20">
          <div className="max-w-3xl mx-auto relative">
            <ChatInput
              onSend={handleSendMessage}
              disabled={false}
              placeholder="Message Cerise..."
            />
            <div className="text-center mt-3">
              <span className="text-[10px] text-muted-foreground/60 font-mono uppercase tracking-wider">
                Powered by OpenAI • Anthropic • DeepMind
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
