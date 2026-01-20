// API类型定义 - 对应后端接口

export interface ChatRequest {
  message: string;
  session_id?: string;
  provider?: string;
  model?: string;
  temperature?: number;
  stream?: boolean;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  emotion?: Emotion;
  emotion_intensity?: number;
}

export interface SessionCreate {
  user_id?: string;
  personality?: PersonalityTraits;
}

export interface SessionResponse {
  session_id: string;
  user_id: string;
  message_count: number;
  created_at?: string;
}

export interface EmotionUpdate {
  emotion: Emotion;
  intensity: number;
}

export interface Live2DParameter {
  id: string;
  value: number;
  weight?: number;
}

export interface Live2DParametersUpdate {
  parameters: Live2DParameter[];
  smoothing?: number;
}

export interface Live2DEmotionUpdate {
  valence: number; // -1 到 1 (负面到正面)
  arousal: number; // 0 到 1 (平静到激动)
  intensity: number; // 0 到 1
  smoothing?: number;
}

// Provider 配置
export interface ProviderConfig {
  id: string;
  name: string;
  type: string;
  api_key?: string;
  base_url?: string;
  default_model?: string;
  enabled: boolean;
  models?: string[];
}

export interface ProviderTestResponse {
  success: boolean;
  message: string;
  latency?: number;
}

// 角色配置
export interface PersonalityTraits {
  openness: number; // 开放性
  conscientiousness: number; // 尽责性
  extraversion: number; // 外向性
  agreeableness: number; // 宜人性
  neuroticism: number; // 神经质
  playfulness?: number; // 玩心
  curiosity?: number; // 好奇心
  shyness?: number; // 害羞
}

export interface CharacterConfig {
  name: string;
  language: string;
  voice_character?: string;
  personality: PersonalityTraits;
  system_prompt_template?: string;
}

// 插件
export interface InstalledPlugin {
  name: string;
  version: string;
  description?: string;
  author?: string;
  enabled: boolean;
  config?: Record<string, unknown>;
}

export interface PluginInstallRequest {
  source: 'github' | 'upload';
  url?: string; // GitHub URL
  file?: File; // 上传的文件
}

// 应用配置
export interface AppConfig {
  server: {
    host: string;
    port: number;
    workers: number;
  };
  ai: {
    default_provider: string;
    default_model: string;
    temperature?: number;
    providers: ProviderConfig[];
  };
  character: CharacterConfig;
  plugins: {
    enabled: boolean;
    auto_start: boolean;
    plugins_dir: string;
    installed: InstalledPlugin[];
  };
  tts: {
    server_url: string;
    default_character: string;
    sample_rate: number;
  };
  logging: {
    level: string;
    file: string;
  };
}

// 情感类型
export enum Emotion {
  NEUTRAL = 'neutral',
  HAPPY = 'happy',
  SAD = 'sad',
  ANGRY = 'angry',
  SURPRISED = 'surprised',
  FEAR = 'fear',
  DISGUST = 'disgust',
  THINKING = 'thinking',
  EXCITED = 'excited',
  CONFIDENT = 'confident',
  SHY = 'shy',
  PLAYFUL = 'playful',
}

// WebSocket 消息类型
export interface WSChatMessage {
  type: 'chat' | 'emotion' | 'l2d_params' | 'error' | 'ping' | 'pong';
  data: unknown;
  session_id?: string;
}

// TTS 相关
export interface TTSRequest {
  text: string;
  character?: string;
  speed?: number;
  format?: 'wav' | 'mp3' | 'ogg';
  stream?: boolean;
}

export interface ASRRequest {
  audio_base64: string;
  sample_rate?: number;
  language?: string;
  format?: string;
}

export interface ASRResponse {
  text: string;
  confidence?: number;
}
