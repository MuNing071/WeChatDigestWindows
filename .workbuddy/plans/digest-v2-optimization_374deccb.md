---
name: digest-v2-optimization
overview: 对 digest.py CLI 进行五大优化：消息智能压缩、Prompt模板可配置化、联系人映射导出、健壮性增强、架构/Agent Harness优化
todos:
  - id: opt-structure
    content: 重构 digest.py 内部架构：提取 ChatMessage 数据类、CompactOptions 配置类、拆分 cmd_xxx 核心逻辑为独立内部函数（消除 argparse.Namespace hack）
    status: completed
  - id: opt-contacts
    content: 新增 contacts 子命令：从 contact.db 读取映射、输出 JSON、缓存到 contacts_cache.json（TTL 24h）
    status: completed
    dependencies:
      - opt-structure
  - id: opt-compress
    content: 实现消息智能压缩：ID→昵称替换（默认启用）+ --compact 模式（过滤噪声/合并短消息/精简时间戳和sender）
    status: completed
    dependencies:
      - opt-contacts
  - id: opt-prompt
    content: Prompt 模板配置化：_load_prompt_template 加载外部文件（--prompt > ~/.wechat-digest/ > 项目默认 > 内置），变量替换 {{GROUP_NAME}}/{{TARGET_DATE}}/{{TOTAL}}
    status: completed
    dependencies:
      - opt-structure
  - id: opt-error
    content: 健壮性增强：全局 try-except + JSON 结构化错误 + LLM 重试（3次指数退避，区分可重试/不可重试错误）+ token 估算预警
    status: completed
    dependencies:
      - opt-structure
  - id: opt-cache-pipeline
    content: 缓存机制（extract 结果缓存到 cache/ 目录，TTL 1h，--no-cache 跳过）+ extract JSON 输出结构化（messages 对象数组 + messages_text 兼容字段）+ 更新 config.json 和文档
    status: completed
    dependencies:
      - opt-compress
      - opt-prompt
---

## 用户需求

对已完成基础功能的 digest.py CLI 工具进行深度优化，涵盖5个方向：

1. **消息智能压缩**：对过多消息内容做压缩——去除冗余时间戳、语气词、无意义发言，合并连续短消息，sender id 转昵称映射，节约 LLM token
2. **Prompt 模板可配置**：从外部文件加载 prompt 模板 + 变量替换，支持自定义模板路径，方便调整摘要风格
3. **群名/联系人 ID 映射 JSON**：新增 contacts 子命令，导出 username→昵称的映射表，供 agent 和其他工具使用
4. **健壮性增强**：统一 try-except 机制、结构化错误输出（JSON 模式下）、LLM 调用重试、graceful degradation
5. **架构/Agent/Harness 优化**：extract 结构化输出（非纯文本行）、token 估算、缓存机制、流水线模式改进

## 核心功能

- extract 子命令增加 `--compact` 压缩模式，输出压缩后的消息文本，预估可减少 40-60% token
- summarize 子命令从外部 prompt-template.txt 加载模板，支持 `--prompt` 指定自定义模板
- 新增 contacts 子命令，从 contact.db 读取 username→昵称映射并输出 JSON
- 全局错误处理统一化，JSON 模式下所有错误输出 `{"error": "..."}` 格式
- extract 返回结构化消息对象（非纯文本行），压缩层在 summarize 调用时按需启用
- token 估算功能，summarize 前预估输入 token 数并提示是否超限
- LLM 调用增加重试（3次，指数退避）

## 视觉效果

CLI 输出更结构化：JSON 模式输出完整元数据（token 估算、压缩率、缓存命中），文本模式增加进度提示和统计信息

## Tech Stack

- 纯 Python 3.12，无新依赖
- 已有依赖：pycryptodome, zstandard
- LLM：火山引擎豆包 API（已验证）
- 配置存储：`~/.wechat-digest/config.json`

## Implementation Approach

### 核心策略：在 digest.py 内部增加压缩层 + 配置化 + 结构化，不改 wechat-digest/ 模块

所有优化都在 `digest.py` 内实现，不改 wechat-digest/ 子目录的文件（除 prompt-template.txt 的变量对齐）。这保持了之前的 blast radius 控制策略。

### 消息压缩方案

分3层压缩，按需启用：

1. **ID→昵称替换**（默认启用）：从 contact.db 读取 wxid→昵称映射，将 `wxid_i68dsaz6jb2s11` 替换为可读昵称。这本身就是 token 节约（长 ID → 短昵称），也提升 LLM 理解质量
2. **冗余消息过滤**（`--compact` 启用）：

- 过滤纯表情/纯标点消息（如"哈"、"👍"、"[动画表情]"）
- 过滤系统通知（入群、退群、改名等 local_type 10000）
- 合并同一人连续短消息（2分钟内同一 sender 的多条 ≤10 字消息合并为一条）

3. **时间戳精简**（`--compact` 启用）：

- 同一分钟内的消息不重复显示时间，只显示一次 `[14:30]`
- 同一 sender 连续发言不重复显示 sender 名

预估效果：495 条消息原始约 25K token，压缩后约 10-15K token，节省 40-60%。

### Prompt 模板配置化

当前 `prompt-template.txt` 已有 `{{GROUP_NAME}}`、`{{TARGET_DATE}}`、`{{TOTAL}}` 变量，但 digest.py 的 `_call_llm()` 没有使用它。改造：

1. `_call_llm()` 优先从 `--prompt` 参数指定的文件加载模板
2. 回退到 `~/.wechat-digest/prompt-template.txt`（用户可自定义）
3. 再回退到 `wechat-digest/prompt-template.txt`（项目默认）
4. 最后回退到内置硬编码（当前行为）
5. 模板变量替换：`{{GROUP_NAME}}`、`{{TARGET_DATE}}`、`{{TOTAL}}`、`{{COMPACT_MODE}}`

### 联系人映射

从 `decrypted_dir/contact/contact.db` 读取 username→nickname 映射：

- 新增 `contacts` 子命令，输出 JSON `{"wxid_xxx": "张三", ...}`
- 首次运行时缓存到 `~/.wechat-digest/contacts_cache.json`（带 TTL，默认 24h）
- extract 和 summarize 自动加载缓存用于 ID→昵称替换

### 健壮性增强

1. **全局异常处理**：main() 入口加 try-except，JSON 模式下输出 `{"error": "msg", "command": "xxx"}`
2. **LLM 重试**：3次重试，指数退避（1s/2s/4s），区分可重试错误（网络超时/429/500）和不可重试错误（401/403）
3. **Graceful degradation**：contact.db 不可用时跳过昵称替换；prompt 模板文件不存在时用内置模板

### 架构/Agent 优化

1. **结构化 extract 输出**：JSON 模式下，messages 从 `string[]` 改为 `[{ts, sender, sender_name, type, content}]` 对象数组，同时保留 `messages_text` 字段（纯文本，向后兼容）
2. **Token 估算**：summarize 前用 `len(text) // 2` 估算中文 token 数（粗估），超过模型 max_tokens 的 80% 时警告
3. **缓存机制**：extract 结果缓存到 `~/.wechat-digest/cache/{group}_{date}.json`，带 TTL（默认 1h），`--no-cache` 跳过
4. **Pipeline 模式改进**：`run` 子命令不再通过 argparse.Namespace hack 调用子函数，而是直接调用内部函数（提取 cmd_xxx 的核心逻辑为独立函数）

## Implementation Notes

1. **压缩不改变 extract 的默认行为**：不加 `--compact` 时输出和之前完全一样，避免破坏现有用法
2. **contacts_cache.json 的 TTL 用文件修改时间判断**：不引入额外依赖，`os.path.getmtime()` 即可
3. **token 估算用简单字符除法**：中文约 1.5 字/token，英文约 4 字/token，折中用 `len(text) // 2`，足够做预警
4. **LLM 重试只对 urllib.error.HTTPError 429/502/503/504 和 socket.timeout 生效**，401/403 立即失败
5. **prompt-template.txt 中的 {{TOTAL}} 变量**：当前模板有这个变量但 digest.py 的内置 prompt 没有，需要在模板加载时统一注入
6. **缓存 key 用 group_username + date 的 md5**：避免群名中的中文导致文件名问题

## Architecture Design

```mermaid
graph TD
    A[digest.py CLI] --> B[配置层]
    B --> B1[config.json]
    B --> B2[环境变量]
    B --> B3[contacts_cache.json]
    
    A --> C[extract 核心逻辑]
    C --> C1[_format_messages 原始格式化]
    C --> C2[_compact_messages 压缩格式化]
    C --> C3[_resolve_contacts ID→昵称]
    C --> C4[缓存层 cache/{hash}.json]
    
    A --> D[summarize 核心逻辑]
    D --> D1[_load_prompt_template 模板加载]
    D --> D2[_call_llm_with_retry 带重试LLM调用]
    D --> D3[_estimate_tokens token估算]
    
    A --> E[contacts 子命令]
    E --> F[contact.db]
    E --> G[contacts_cache.json]
    
    A --> H[全局错误处理]
    H --> H1[JSON模式: 结构化错误]
    H --> H2[文本模式: 友好提示]
```

## Directory Structure

```
e:/微信群聊总结/
├── digest.py                    # [MODIFY] 核心改造目标：增加压缩层、prompt配置化、contacts子命令、错误处理、结构化输出、缓存、token估算
├── wechat-digest/
│   └── prompt-template.txt      # [MODIFY] 对齐变量名，确保 {{GROUP_NAME}}/{{TARGET_DATE}}/{{TOTAL}} 与 digest.py 一致
└── C:/Users/Administrator/.wechat-digest/
    ├── config.json              # [MODIFY] 添加 prompt_template、cache_ttl、compact 默认配置
    ├── contacts_cache.json      # [NEW] 联系人映射缓存（自动生成）
    ├── prompt-template.txt      # [NEW] 用户自定义 prompt 模板（可选，优先于项目默认）
    └── cache/                   # [NEW] extract 结果缓存目录
        └── {hash}.json          # [NEW] 缓存文件（自动生成）
```

## Key Code Structures

```python
# 消息结构化对象（extract JSON 输出）
@dataclass
class ChatMessage:
    ts: int               # unix timestamp
    sender: str           # 原始 sender id
    sender_name: str      # 昵称（已解析），未解析时等于 sender
    msg_type: int         # local_type
    content: str          # 消息正文

# 压缩选项
@dataclass
class CompactOptions:
    filter_noise: bool = True      # 过滤纯表情/标点/系统通知
    merge_consecutive: bool = True  # 合并同一人连续短消息
    simplify_timestamp: bool = True # 同分钟不重复时间戳
    simplify_sender: bool = True   # 同人连续不重复 sender
```

## SubAgent

- **code-explorer**: 用于验证 contact.db 的表结构和字段名，确保联系人映射功能实现准确

## Skill

- **finance-data-retrieval**: 不适用本次任务