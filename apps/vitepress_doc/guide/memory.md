# 记忆系统

记忆系统负责把对话沉淀为长期结构化信息，并在后续对话中参与召回与上下文拼装。

## 快速上手

1. 复制示例配置到本地数据目录并按需调整。
2. 打开或关闭 L1/L2/L4 分层，并设置容量与存储后端。
3. 根据部署规模调整 vector / sparse / kg / recall / rerank / association。
4. 启动 Core 服务，记忆管线会在对话事件写入后自动抽取并分流到各层。
5. 对话后检查存储或订阅事件，确认记忆已落库。

示例配置文件：apps/core/config/examples/memory.yaml
默认加载路径：~/.cerise/memory.yaml

## 分层结构

- L1 核心画像：AI persona 与用户画像
- L2 语义事实：实体、属性、值的可覆盖事实
- L4 程序习惯：任务类型与行为习惯

## 配置总览

### store

- backend：sqlite | state | memory
- sqlite_path：SQLite 文件路径（空值使用默认路径）
- state_path：StateStore 路径（空值使用默认路径）
- ttl_seconds：对话记忆的过期时间
- max_records_per_session：单会话最大记录数

### l1_core / l2_semantic / l4_procedural

- enabled：是否启用该层
- backend：sqlite | state | memory
- sqlite_path / state_path：存储路径（空值使用默认路径）
- max_records：该层最多保留的记录数

### vector

- enabled：向量检索开关
- provider：faiss | chroma | numpy
- embedding_backend：hash | provider
- embedding_dim：向量维度
- embedding_provider / embedding_model：外部向量模型配置
- top_k：向量召回数量
- persist_path：向量持久化路径

### sparse

- enabled：稀疏检索开关
- top_k：稀疏召回数量

### kg

- enabled：知识图谱开关
- top_k：图谱召回数量
- auto_extract：是否自动抽取实体关系

### compression

- enabled：压缩开关
- threshold：触发压缩的条数阈值
- window：压缩窗口大小
- max_chars：摘要最大长度

### recall

- enabled：召回开关
- top_k：最终召回数量
- min_score：最低分阈值
- rrf_k：RRF 融合参数

### rerank

- enabled：重排开关
- top_k：重排保留数量
- weight：重排权重
- provider_id / model：重排模型配置

### association

- enabled：联想召回开关
- max_hops：联想跳数
- top_k：联想召回数量
- max_entities：最大实体扩展数
- include_facts：是否携带事实
- expand_from_query / expand_from_results：联想扩展来源
- min_score：联想最低分阈值

## L1/L2/L4 配置示例

```yaml
l1_core:
  enabled: true
  backend: sqlite
  sqlite_path: ""
  state_path: ""
  max_records: 200

l2_semantic:
  enabled: true
  backend: sqlite
  sqlite_path: ""
  state_path: ""
  max_records: 200

l4_procedural:
  enabled: true
  backend: sqlite
  sqlite_path: ""
  state_path: ""
  max_records: 200
```

## 事件输出

记忆管线会在抽取完成后发布以下事件，供其它模块订阅：

- memory.core.updated
- memory.fact.upserted
- memory.habit.recorded
