# Cerise Web UI

基于 Next.js 14+ 的 Cerise AI 智能助手前端界面。

## 🌸 特性

- **优雅设计**: 樱花粉主题色系，充满艺术感的现代化界面
- **实时对话**: WebSocket 支持的流式对话体验
- **情感系统**: 实时显示 AI 的情感状态
- **Live2D 集成**: 虚拟角色可视化展示
- **响应式布局**: 完美适配桌面端和移动端
- **暗色模式**: 自动适配系统主题
- **类型安全**: 完整的 TypeScript 支持

## 🚀 快速开始

### 前置要求

- Node.js 20+
- pnpm 8+
- 后端服务已启动 (Core API + TTS Server)

### 安装依赖

```bash
pnpm install
```

### 配置环境变量

复制环境变量模板:

```bash
cp .env.local.example .env.local
```

编辑 `.env.local` 配置后端地址:

```env
NEXT_PUBLIC_CORE_API_URL=http://localhost:8000
NEXT_PUBLIC_TTS_API_URL=http://localhost:8001
```

### 开发模式

```bash
pnpm dev
```

访问 [http://localhost:3000](http://localhost:3000)

### 生产构建

```bash
pnpm build
pnpm start
```

## 📁 项目结构

```
apps/cerise_webui/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # 根布局
│   ├── page.tsx           # 主页
│   └── globals.css        # 全局样式
├── components/            # React 组件
│   ├── ui/               # 基础 UI 组件
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   └── Textarea.tsx
│   ├── chat/             # 聊天相关组件
│   │   ├── MessageBubble.tsx
│   │   ├── MessageList.tsx
│   │   ├── ChatInput.tsx
│   │   └── EmotionIndicator.tsx
│   ├── live2d/           # Live2D 组件
│   │   └── Live2DView.tsx
│   └── ChatInterface.tsx  # 主聊天界面
├── lib/                   # 工具库
│   └── api.ts            # API 服务层
├── stores/               # 状态管理 (Zustand)
│   └── index.ts
├── types/                # TypeScript 类型定义
│   └── api.ts
├── hooks/                # 自定义 Hooks
└── public/               # 静态资源
```

## 🎨 技术栈

- **框架**: Next.js 16 (App Router)
- **UI 库**: React 19
- **样式**: Tailwind CSS 4
- **动画**: Framer Motion 12
- **状态管理**: Zustand 5
- **HTTP 客户端**: Axios
- **图标**: Lucide React
- **类型检查**: TypeScript 5

## 🌈 主题色彩

基于 "Cerise"（樱桃粉）的色彩方案:

- **主色**: `#de3163` (Cerise Primary)
- **浅色**: `#ff6b9d` (Cerise Light)
- **深色**: `#c72c5c` (Cerise Dark)
- **渐变**: 从樱花粉到玫瑰红的优雅渐变

## 🔌 API 对接

### Core API 端点

- `POST /sessions` - 创建会话
- `POST /chat` - 发送消息
- `GET /emotion` - 获取情感状态
- `POST /l2d/emotion` - 设置 Live2D 情感
- `WebSocket /ws/chat` - 流式聊天

### 管理 API 端点

- `GET /admin/config` - 获取配置
- `GET /admin/providers` - 列出 AI Providers
- `GET /admin/plugins` - 列出插件
- `POST /admin/providers/{id}/test` - 测试 Provider

### TTS API 端点

- `POST /api/v1/tts/synthesize/audio` - 语音合成
- `POST /api/v1/asr/transcribe` - 语音识别
- `WebSocket /ws/tts` - TTS 流式
- `WebSocket /ws/asr` - ASR 流式

## 📝 开发指南

### 添加新组件

1. 在 `components/` 下创建组件文件
2. 使用 TypeScript 和 Tailwind CSS
3. 遵循现有的命名和结构约定
4. 添加适当的动画效果

### 状态管理

使用 Zustand 管理全局状态:

```tsx
import { useChatStore } from '@/stores';

function MyComponent() {
  const { messages, addMessage } = useChatStore();
  // ...
}
```

### API 调用

使用封装的 API 服务:

```tsx
import { chatApi } from '@/lib/api';

const response = await chatApi.chat({
  message: 'Hello',
  session_id: sessionId,
});
```

## 🛠️ 配置选项

### Tailwind CSS

主题配置在 `globals.css` 中通过 CSS 变量定义，支持:

- 自定义颜色系统
- 暗色模式适配
- 动画和过渡效果
- 玻璃态效果

### TypeScript

`tsconfig.json` 配置了路径别名:

- `@/*` -> `./` (项目根目录)

## 🚧 TODO

- [ ] 集成实际的 Live2D SDK
- [ ] 完善 WebSocket 实时通信
- [ ] 实现语音输入功能
- [ ] 添加配置管理界面
- [ ] 支持多语言
- [ ] 添加消息历史记录
- [ ] 实现插件管理界面

## 📄 License

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!
