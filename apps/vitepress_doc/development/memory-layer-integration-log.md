# 记忆层迁移开发日志

本日志用于记录从外部项目吸收记忆层设计要点并落地到 Cerise 的过程。

参考文档：`docs/project/memory-layer-research.md`

## 目标

- 将五层记忆、异步归档、摘要压缩、记忆衰减与强化等机制落地为可配置、可测试的模块。
- 不引入外部框架或 Web UI。

## 里程碑

- [ ] Phase 0：概念与契约
- [ ] Phase 1：存储基础（L1/L2/L4）
- [ ] Phase 2：检索与评分
- [ ] Phase 3：情景记忆 + 情绪
- [ ] Phase 4：异步归档 + 压缩 + 梦境任务
- [ ] Phase 5：配置与测试

## 开发记录

### 2026-01-20

- 完成调研与可迁移点拆解（TimeWeave / MemoryChain / AIRI）。
- 产出任务清单与许可证约束说明。

下一步：
- Phase 0 数据模型与事件契约落地。

### 2026-01-20（Phase 0 启动）

- 对齐阶段边界与优先级，补充 AIRI 记忆衰减与情绪要点。
- 开始 Phase 0：数据模型 + 事件契约实现。
- 记忆层调研与开发日志纳入文档站。

下一步：
- 完成 Phase 0 剩余 ports 合约草案。
- 进入 Phase 1 存储基础实现。

### 待办明细（按 Phase）

#### Phase 0：概念与契约
- [ ] 定义 MemoryLayer 枚举
- [ ] MemoryRecord 元数据对齐（layer + emotion）
- [ ] 新增事件契约草案（memory.core.updated 等）
- [ ] L1/L2/L4 ports 合约草案

#### Phase 1：存储基础（L1/L2/L4）
- [ ] CoreProfileStore 设计与实现
- [ ] SemanticFactsStore + upsert 冲突策略
- [ ] ProceduralHabitsStore
- [ ] tags/category 字段支持

#### Phase 2：检索与评分
- [ ] MemoryContextBuilder 与多层融合权重
- [ ] 记忆分数与遗忘曲线（half-life/decay）
- [ ] recall 更新 last_accessed / access_count
- [ ] 情绪分数参与 rerank/加权

#### Phase 3：情景记忆 + 情绪
- [ ] 情绪快照写入与检索加权
- [ ] 情绪过滤/加权策略
- [ ] trigger / random recall 机制

#### Phase 4：异步归档 + 压缩 + 梦境任务
- [ ] LLM 抽取 pipeline
- [ ] 阈值压缩与摘要入库
- [ ] Dreaming/后台 agent 重评分与清理

#### Phase 5：配置与测试
- [ ] MemoryConfig 扩展
- [ ] 单元测试覆盖（upsert/压缩/拼接/评分）