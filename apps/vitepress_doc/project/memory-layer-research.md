# 记忆层调研与迁移方案

本文档记录对 TimeWeave Memoria、AstrBot MemoryChain、AIRI 的调研结论，并拆解可迁移点到 Cerise 的具体实现任务。

## 调研范围

- 目标：评估外部项目是否可作为 Cerise 记忆层基础，并提炼可迁移设计/机制。
- 排除：不引入外部 Web UI；仅吸收记忆层逻辑与流程设计。

## 调研对象

| 项目 | 仓库 | 本地镜像 | 结论 |
| --- | --- | --- | --- |
| TimeWeave Memoria | https://github.com/DITF16/time-weave-memoria | `.tmp/time-weave-memoria` | 设计可借鉴，代码不可直接复用（强耦合 + 许可证限制） |
| AstrBot MemoryChain | https://github.com/Li-shi-ling/astrbot_plugin_memorychain | `.tmp/astrbot_plugin_memorychain` | 流程可借鉴，代码强依赖 AstrBot 且 AGPL 约束 |
| AIRI | https://github.com/moeru-ai/airi | `.tmp/airi` | 记忆层 WIP，但文档与 schema 可借鉴，MIT 许可 |

## 关键设计提炼

### TimeWeave Memoria

- 五层记忆模型：L1 核心画像、L2 语义事实、L3 情景向量、L4 习惯/程序性、L5 情绪标签。
- 读写分离：对话路径快速检索 + 生成；后台异步抽取/归档。
- 维护机制：摘要压缩、旧记忆清理、矢量库膨胀控制。
- 混合检索：向量模糊召回 + SQL 精确事实 + 核心画像拼装。

代码参考：
- Pipeline：`.tmp/time-weave-memoria/app/core/pipeline.py`
- 向量库：`.tmp/time-weave-memoria/app/storage/vector_db.py`
- 语义/习惯：`.tmp/time-weave-memoria/app/storage/sql_db.py`

### AstrBot MemoryChain

- 会话滚动窗口 + 阈值触发压缩。
- 摘要入向量库，检索后拼入系统提示。
- 多会话隔离（群聊/私聊按 kb 命名区分）。

代码参考：
- 插件主逻辑：`.tmp/astrbot_plugin_memorychain/main.py`

### AIRI

- 模块化记忆驱动：MemoryDriver 位于 DB Driver 与 Core 之间，支持更换存储实现（Memory Alaya、memory-pgvector）。
- 记忆类型分层：working/short-term/long-term/muscle，强调不同检索与保留策略。
- 记忆分数与半衰期：记忆分数随时间衰减，可通过强化机制提升。
- 情绪记忆：存储情绪分数，回忆受情绪影响；支持情绪触发与随机闪回。
- 梦境/潜意识后台任务：异步处理与重新评分，类似 background pipeline。
- 数据模型启发：memory_fragments 包含 importance、emotional_impact、last_accessed、access_count，支持 tags 与 episodic table，多维向量索引（1536/1024/768）。

文档/代码参考：
- `.tmp/airi/docs/README.zh-CN.md`
- `.tmp/airi/docs/content/zh-Hans/blog/DevLog-2025.04.14/index.md`
- `.tmp/airi/services/telegram-bot/src/db/schema.ts`

## 迁移可行性结论

- 不适合直接引入代码：TimeWeave/AstrBot 强绑定各自框架；AIRI 记忆层尚在建设中。
- 适合迁移设计思想：五层记忆、读写分离、摘要压缩、混合检索、记忆衰减与强化、情绪影响、后台 pipeline。

## 迁移任务清单（面向 Cerise）

> 目标：在现有 `apps/core/ai/memory` 基础上吸收三者设计，不引入外部框架依赖。

### Phase 0：概念与契约（进行中）

- [ ] 定义 MemoryLayer 枚举（core/semantic/episodic/procedural/emotional）。
- [ ] MemoryRecord 元数据对齐：layer + emotion snapshot（为后续 score/importance 字段预留）。
- [ ] 新增事件契约草案：memory.core.updated / memory.fact.upserted / memory.habit.recorded / memory.emotional_snapshot.attached。
- [ ] 定义 L1/L2/L4 的 ports 合约草案（接口签名）。

### Phase 1：存储基础（L1/L2/L4）

- [ ] CoreProfileStore（JSON 或 SQLite），存储 AI persona 与用户画像。
- [ ] SemanticFactsStore（SQLite），实现 upsert 冲突解决（entity+attribute 主键）。
- [ ] ProceduralHabitsStore（SQLite），记录 task_type + instruction。
- [ ] 支持 tags / category 字段（AIRI schema 启发）。

### Phase 2：检索与评分

- [ ] MemoryContextBuilder：按层级权重拼接上下文。
- [ ] 记忆评分与遗忘曲线（half-life / decay），支持强化机制。
- [ ] recall 更新 last_accessed / access_count，作为权重因子。
- [ ] 情绪分数参与 rerank/加权。

### Phase 3：情景记忆 + 情绪

- [ ] Episodic 记录带情绪快照字段（来自 emotion pipeline）。
- [ ] 情绪过滤/加权策略。
- [ ] 可选：trigger / random recall 机制。

### Phase 4：异步归档 + 压缩 + 梦境任务

- [ ] MemoryPipeline：LLM 抽取事实/习惯/核心画像 -> 分流存储。
- [ ] 压缩阈值 + 摘要入库策略（参考 memorychain）。
- [ ] Dreaming/后台 agent：重评分、强化、清理策略。

### Phase 5：配置与测试

- [ ] 更新 MemoryConfig 增加 L1/L2/L4 配置段。
- [ ] 加入压缩阈值、摘要模型、任务类型映射等配置。
- [ ] 新增单元测试覆盖：upsert 冲突、压缩触发、上下文拼接、评分衰减。

## 许可证提示

- TimeWeave Memoria 为自定义许可证，要求修改开源，商用闭源需授权。
- AstrBot MemoryChain 使用 AGPL-3.0。
- AIRI 使用 MIT 许可证。
- 因此仅迁移设计理念，不直接复用代码。