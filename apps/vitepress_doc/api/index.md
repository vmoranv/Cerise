# API 概览

Cerise 提供 REST API 和 WebSocket 接口用于与核心服务交互。

## 基础信息

- **基础 URL**: `http://localhost:8000`
- **API 版本**: v1

## 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/chat` | 发送对话消息 |
| GET | `/api/character` | 获取当前角色信息 |
| GET | `/api/plugins` | 获取插件列表 |
| GET | `/api/health` | 健康检查 |

详细信息请参考:
- [REST API](./rest.md)
- [WebSocket](./websocket.md)
