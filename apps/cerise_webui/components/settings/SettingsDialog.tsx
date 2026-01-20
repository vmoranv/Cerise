'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { motion, AnimatePresence } from 'framer-motion';

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsDialog({ isOpen, onClose }: SettingsDialogProps) {
  const [coreApiUrl, setCoreApiUrl] = useState(
    process.env.NEXT_PUBLIC_CORE_API_URL || 'http://localhost:8000'
  );
  const [ttsApiUrl, setTtsApiUrl] = useState(
    process.env.NEXT_PUBLIC_TTS_API_URL || 'http://localhost:8001'
  );
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');

  const handleSave = () => {
    // TODO: 保存配置到 localStorage 或后端
    localStorage.setItem('coreApiUrl', coreApiUrl);
    localStorage.setItem('ttsApiUrl', ttsApiUrl);
    localStorage.setItem('provider', provider);
    localStorage.setItem('model', model);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* 背景遮罩 */}
          <motion.div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* 对话框 */}
          <motion.div
            className="fixed inset-0 flex items-center justify-center z-50 p-4"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            <div className="bg-background rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
              {/* 头部 */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-gradient-to-r from-cerise-light/10 to-cerise-primary/10">
                <h2 className="text-2xl font-bold bg-gradient-to-r from-cerise-light to-cerise-primary bg-clip-text text-transparent">
                  设置
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  <X className="w-5 h-5 text-foreground-secondary" />
                </button>
              </div>

              {/* 内容 */}
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
                <div className="space-y-6">
                  {/* API 配置 */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-foreground">API 配置</h3>

                    <div>
                      <label className="block text-sm font-medium text-foreground-secondary mb-2">
                        Core API 地址
                      </label>
                      <Input
                        type="text"
                        value={coreApiUrl}
                        onChange={(e) => setCoreApiUrl(e.target.value)}
                        placeholder="http://localhost:8000"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground-secondary mb-2">
                        TTS Server 地址
                      </label>
                      <Input
                        type="text"
                        value={ttsApiUrl}
                        onChange={(e) => setTtsApiUrl(e.target.value)}
                        placeholder="http://localhost:8001"
                      />
                    </div>
                  </div>

                  {/* AI 模型配置 */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-foreground">AI 模型</h3>

                    <div>
                      <label className="block text-sm font-medium text-foreground-secondary mb-2">
                        提供商
                      </label>
                      <select
                        value={provider}
                        onChange={(e) => setProvider(e.target.value)}
                        className="w-full rounded-lg border px-4 py-2.5 bg-white dark:bg-zinc-900 border-border dark:border-zinc-700 text-foreground focus:outline-none focus:ring-2 focus:ring-cerise-light focus:border-transparent transition-all duration-200"
                      >
                        <option value="openai">OpenAI</option>
                        <option value="claude">Claude (Anthropic)</option>
                        <option value="gemini">Gemini (Google)</option>
                        <option value="deepseek">DeepSeek</option>
                        <option value="qwen">Qwen (阿里)</option>
                        <option value="glm">GLM (智谱)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground-secondary mb-2">
                        模型
                      </label>
                      <Input
                        type="text"
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        placeholder="gpt-4o"
                      />
                      <p className="mt-1 text-xs text-foreground-tertiary">
                        根据选择的提供商输入相应的模型名称
                      </p>
                    </div>
                  </div>

                  {/* 提示信息 */}
                  <div className="rounded-lg bg-cerise-light/10 border border-cerise-light/20 p-4">
                    <p className="text-sm text-foreground-secondary">
                      <span className="font-semibold text-cerise-primary">提示：</span>
                      配置更改将保存到本地存储，刷新页面后生效。
                      如需修改后端配置，请编辑 <code className="px-1.5 py-0.5 bg-zinc-200 dark:bg-zinc-800 rounded text-xs">apps/core/config.yaml</code>
                    </p>
                  </div>
                </div>
              </div>

              {/* 底部按钮 */}
              <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-background-secondary">
                <Button variant="ghost" onClick={onClose}>
                  取消
                </Button>
                <Button variant="primary" onClick={handleSave}>
                  保存设置
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
