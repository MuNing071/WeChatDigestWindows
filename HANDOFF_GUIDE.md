# wechat-digest 项目部署与运行指南（接手者文档）

> **编写日期**: 2026-04-16  
> **项目状态**: ✅ 核心链路已跑通（微信解密 → 消息提取 → 豆包LLM摘要）  
> **适用环境**: Windows 11 + 微信 4.1.7.59 + Python 3.12  

---

## 一、项目是什么

wechat-digest 是一个微信群聊每日摘要自动化工具。它从微信本地加密数据库中提取聊天记录，调用 LLM（大语言模型）生成结构化日报，输出 Markdown 格式的聊天记录原文 + 摘要报告。

**已验证的完整链路**:  
`微信 SQLCipher4 加密数据库` → `SQLCipher 解密 + WAL 合并` → `消息提取去重排序` → `豆包 API (doubao-seed-2-0-lite)` → `结构化摘要 Markdown`

---

## 二、环境要求

| 组件 | 版本/规格 | 说明 |
|---|---|---|
| 操作系统 | Windows 11 | PowerShell 作为主 Shell |
| Python | 3.12.8 | 核心解密/提取逻辑全部用 Python |
| 微信版本 | 4.1.7.59 | 进程名 **Weixin.exe**（注意不是 WeChat.exe） |
| pip | 25.0.1 | |

### Python 依赖

```
pycryptodome >= 3.19    # SQLCipher 4 AES-256-CBC 解密
zstandard >= 0.22       # zstd 消息体解压
requests                # HTTP 请求（调用豆包API）
```

安装命令:
```bash
pip install pycryptodome zstandard requests
```

可选依赖（当前未使用但项目支持）:
```
playwright >= 1.40      # 公众号文章抓取
pilk >= 0.2             # SILK 语音编解码
websocket-client >= 1.6 # 讯飞语音转写
```

---

## 三、核心踩坑记录（⚠️ 最重要部分）

### 踩坑 #1：微信有两个数据目录（致命问题）

微信在 Windows 上可能存在 **两个数据目录**，Wetrace 和自动检测脚本可能指向旧的那个：

| 目录 | 状态 | 特征 |
|---|---|---|
| `E:\Documents\WeChatFiles\xwechat_files\<wxid>\db_storage\` | **旧/停用** | 文件修改时间停在很久以前 |
| `E:\文档\WeChatFiles\xwechat_files\<wxid>\db_storage\` | **活跃/正在写入** | 文件今天还在更新 |

**如何确认哪个是活跃目录**:
```powershell
# 检查 message_0.db 的最后修改时间
Get-ChildItem "E:\Documents\WeChatFiles\xwechat_files\<wxid>\db_storage\message\message_0.db" | Select-Object LastWriteTime
Get-ChildItem "E:\文档\WeChatFiles\xwechat_files\<wxid>\db_storage\message\message_0.db" | Select-Object LastWriteTime
# 修改时间更近的那个就是活跃目录
```

**根因**: 微信更新或重新登录后可能切换数据路径。ini 配置文件 (`%APPDATA%/Tencent/xwechat/config/*.ini`) 中存的是实际路径，但 Wetrace 可能缓存了旧路径。

### 踩坑 #2：Wetrace 解密不合并 WAL 文件

**现象**: 活跃目录的 `.db` 文件今天还在更新，但 Wetrace 解密出来的数据只到几周前。

**原因**: SQLite 使用 WAL（Write-Ahead Logging）模式，新写入的数据先存在 `-wal` 和 `-shm` 文件中，没有立即合并到主 `.db` 文件。Wetrace 的解密流程**不处理 WAL 文件**，导致最新数据丢失。

**解决方案**: 使用 **wechat-digest 自带的 crypto/decrypt.py** 模块，它基于 pycryptodome 实现 SQLCipher 4 解密，并且会正确读取 WAL 文件中的数据。

参考脚本: `e:\微信群聊总结\decrypt_active.py`（已验证可用）

### 踩坑 #3：豆包 API Key 格式

用户从火山引擎控制台获取的 API Key 长这样：
```
api-key-20260313171836
66e9a0b0-837c-4f0f-a1f4-ee44413c04f9
```

**正确的 Bearer Token 是纯 UUID 部分**：
```
66e9a0b0-837c-4f0f-a1f4-ee44413c04f9
```
不要带 `api-key-` 前缀，也不要把两行拼起来。

### 踩坑 #4：群名不在数据库明文字段中

微信的群聊名称存储在 protobuf 序列化的 `ext_buffer` 字段中，**不能通过简单的 SQL 查询获取群名**。

**解决方案**: 
1. 从消息内容反推——看哪个群的聊天话题匹配目标群名
2. 建立并维护 `known_groups` 字典：`{"群显示名": "username@chatroom"}`
3. 已知映射: `"AI实践"` → `"49710605556@chatroom"`

### 踩坑 #5：PowerShell 编码问题

Python 脚本输出中文时 PowerShell 终端可能显示乱码。解决方案：
```python
# 在 Python 脚本头部加入
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
```

PowerShell 调用时重定向到文件再读取:
```powershell
python script.py > output.txt 2>&1; Get-Content output.txt -Encoding UTF8
```

---

## 四、密钥获取

### 方法一：通过 Wetrace Hook（推荐）

Wetrace 工具可以在运行时从 Weixin.exe 进程内存中提取 SQLCipher 密钥：

1. 启动 Wetrace: `cd wetrace-bin && go run .`
2. 打开浏览器访问 `http://127.0.0.1:5200`
3. 在 Settings 中配置正确的微信数据路径（**注意用活跃目录**）
4. 点击 Decrypt，密钥会自动提取并保存

密钥格式（64位十六进制字符串）:
```
49f459a35b3046b39007edcc6c35be772ae49b44a3294c04b0749ad96d311994
```

### 方法二：通过 wechat-digest 自带的 scanner_windows.py

```bash
# 需要管理员权限
python wechat-digest/init-keys.py
```

这会扫描 Weixin.exe 进程内存，找到 SQLCipher 密钥保存到 `~/.wechat-digest/all_keys.json`。

**前提条件**:
- 微信必须正在运行
- 需要**管理员权限**（OpenProcess 需要 PROCESS_VM_READ 权限）
- 扫描期间微信不能重启（内存中的密钥会失效）

---

## 五、一键运行：digest.py CLI

### 新版入口（推荐）

`digest.py` 是统一的 CLI 工具，替代旧的5个独立脚本。敏感信息通过环境变量传入，不硬编码。

```powershell
# 设置环境变量
$env:WECHAT_LLM_API_KEY = "your-api-key"

# 列出群
python digest.py groups

# 提取消息
python digest.py extract "AI实践" 2026-04-13

# 生成摘要
python digest.py summarize "AI实践" 2026-04-13 -o output/summary.md

# 一键全流程
python digest.py run "AI实践" 2026-04-13

# 测试 LLM 连接
python digest.py test-api
```

所有子命令支持 `--json` 参数输出结构化数据（agent 友好）。

### 配置文件

- 主配置: `~/.wechat-digest/config.json`（db_dir, decrypted_dir, known 群映射）
- LLM 配置: 环境变量 或 `~/.wechat-digest/llm_config.json`
- 密钥文件: `~/.wechat-digest/all_keys.json`

### 旧版脚本（保留为参考）

以下脚本已被 digest.py 替代，保留供参考：
- `run_doubao.py` → `digest.py run`
- `decrypt_active.py` → `digest.py decrypt`
- `find_ai_practice.py` → `digest.py groups`
- `extract_apr15.py` → `digest.py extract`
- `test_doubao.py` → `digest.py test-api`
DB_KEY = '49f459a35b3046b39007edcc6c35be772ae49b44a3294c04b0749ad96d311994'
```

### 运行命令

```powershell
python e:\微信群聊总结\run_doubao.py
```

### 输出文件

| 文件 | 内容 |
|---|---|
| `output/YYYY-MM-DD-ai_practice-chat.md` | 原始聊天记录，每条消息一行 `[HH:MM] sender: content` |
| `output/YYYY-MM-DD-ai_practice-summary.md` | 豆包 LLM 生成的结构化摘要报告（5个维度） |

---

## 六、项目文件索引

```
e:/微信群聊总结/
│
├── digest.py                     # ⭐ 统一CLI入口（9个子命令）
├── README.md                     # 工作区总览（快速开始指南）
├── HANDOFF_GUIDE.md              # 本文件（完整接手者文档）
│
├── wechat-digest/                # ⭐ 核心模块库（Git Clone）
│   ├── crypto/                   # 解密核心
│   │   ├── decrypt.py            # ⭐ SQLCipher 4 解密（WAL合并）
│   │   ├── config.py             # 配置加载+数据目录自动检测
│   │   └── keys/                 # 密钥扫描器
│   ├── extract-messages.py       # 消息提取命令行工具
│   ├── extract_decrypted.py      # 从已解密DB提取（Wetrace兼容）
│   ├── llm_summarize.py          # LLM 摘要
│   ├── init-keys.py              # 密钥提取入口
│   └── prompt-template.txt       # LLM Prompt 模板
│
├── wetrace-bin/                  # Wetrace 编译产物 + 已解密数据
│   └── wetrace/data/             # 已解密数据库
│       ├── message_active/       # ⭐ 含最新WAL数据的消息DB
│       ├── message/              # 消息DB
│       ├── session/              # 会话列表DB
│       └── contact/              # 联系人DB
│
├── scripts/                      # 工具脚本
│   ├── daily_stats.py           # 每日统计
│   ├── debug/list_groups.py      # 诊断：列出群组
│   └── inspect/                  # 数据库检查工具
│       ├── inspect_db.py         # DB概览
│       ├── inspect_sessions.py   # 会话表检查
│       ├── inspect_msg_schema.py # 消息表schema
│       └── db-*.txt              # 诊断输出
│
├── scripts/archive/              # ⚠️ 归档（旧版本/参考代码）
│   ├── run_doubao.py            # [旧版] 一键脚本（已被 digest.py 替代）
│   ├── decrypt_active.py        # [旧版] 解密脚本
│   ├── find_ai_practice.py      # [旧版] 群搜索
│   ├── extract_apr15.py         # [旧版] 消息提取
│   ├── test_doubao.py           # [旧版] API测试
│   ├── wechat-decrypt-full/     # 第三方解密库完整版（参考）
│   └── wetrace/                 # Wetrace 源码（参考）
│
├── utils/                        # 扩展工具目录（预留）
├── output/                       # 最终产出目录
│
└── .workbuddy/memory/            # 工作记忆
    ├── MEMORY.md                 # 跨 session 长期记忆
    └── YYYY-MM-DD.md             # 每日工作日志
```

---

## 七、已知的群名→表名映射

以下是通过消息内容反推出的群映射（截至 2026-04-15）:

| 显示名称 | 数据库表名 (username@chatroom) | 备注 |
|---|---|---|
| AI实践 | `49710605556@chatroom` | 最活跃群，日均1000+条消息 |

**如何发现新群的映射**:
1. 运行 `find_ai_practice.py` 查看所有有消息的群及其消息数量
2. 对每个群提取几条样本消息: `SELECT talker, content FROM "<table>" WHERE create_time >= ? AND create_time < ? LIMIT 5`
3. 根据消息内容判断属于哪个群
4. 将映射添加到 known_groups 字典

---

## 八、扩展与改进方向

### 高优先级

1. **解密全部 DB 文件**
   - 当前只解密了 `message_0.db`，活跃目录可能有 `message_0.db` ~ `message_N.db`
   - 修改 `decrypt_active.py` 循环解密所有 message_*.db

2. **群名映射持久化**
   - 将 known_groups 字典保存为 JSON 文件
   - 每次发现新群时自动追加
   - 支持模糊搜索群名

3. **通用化 run_doubao.py**
   - 接受命令行参数: `python run_doubao.py "群名" "2026-04-16"`
   - 自动根据群名查找表名
   - 自动检测日期范围

4. **增量解密**
   - 记录上次解密的时间点
   - 只解密新增的 WAL 数据
   - 避免每次全量解密 26 个数据库

### 中优先级

5. **PDF 输出**
   - 安装 pandoc + Chrome
   - 将 Markdown 摘要转为排版精美的 PDF

6. **语音消息转文字**
   - 安装 pilk（SILK 编解码）
   - 配置讯飞或其他语音转写 API

7. **多群批量处理**
   - 一次运行处理多个群的同日消息
   - 生成汇总报告

8. **定时任务**
   - 设置 Windows Task Scheduler 每天自动运行
   - 自动发送摘要到邮件/企业微信/飞书

---

## 九、故障排查速查

| 症状 | 常见原因 | 解决方法 |
|---|---|---|
| 解密数据只有旧数据 | 指向了非活跃数据目录 | 检查两个数据目录的文件修改时间，切换到活跃目录 |
| 解密数据仍然缺最近几天 | WAL 未合并 | 用 wechat-digest crypto 模块而非 Wetrace 解密 |
| 豆包 API 返回 401 | Key 格式错误 | 使用纯 UUID，不带 api-key- 前缀 |
| 找不到目标群 | 群名在 protobuf 中 | 通过消息内容反推，建立映射字典 |
| 中文乱码 | PowerShell GBK 编码 | 脚本头加 utf-8 stdout wrapper |
| 密钥提取失败 | 非管理员权限 / 微信未运行 | 以管理员身份运行 PowerShell，确保微信在线 |
| `file is not a database` | 加密数据库用了错误的 key | 重新从进程内存提取密钥 |

---

## 十、完整执行过程回顾（供接手者了解来龙去脉）

### 第一阶段：环境搭建与项目克隆
1. 克隆 wechat-digest 仓库到 `e:/微信群聊总结/`
2. 安装 Python 依赖（pycryptodome, zstandard, requests 等）
3. 启动 Wetrace（Go 项目），通过 Web UI 管理

### 第二阶段：密钥提取
1. 以管理员权限运行 Wetrace 的 Hook 功能
2. 扫描 Weixin.exe（PID 277516）进程内存
3. 成功提取 SQLCipher 密钥: `49f459a3...311994`
4. 密钥保存到 Wetrace 配置中

### 第三阶段：数据发现（最曲折的阶段）
1. **初次解密成功但数据旧**: Wetrace 报告 26 个 DB 全部解密成功
2. **检查发现数据只到 2026-03-13**: 但我们需要 4月15日的数据
3. **反复排查原因**: 
   - 检查源数据库 → 源文件也停在 3月13日
   - 重新触发 Wetrace 解密 → 仍然一样
4. **关键突破**: 发现微信有**两个数据目录**
   - `E:\Documents\WeChatFiles\...` (旧的，3月后停用)
   - `E:\文档\WeChatFiles\...` (活跃的，今天还在写入！)
5. **更新 Wetrace 路径 + 重新解密** → 数据仍然只到 3月13日
6. **最终根因定位**: Wetrace 不合并 WAL 文件，而 SQLite 新数据全在 WAL 里
7. **终极方案**: 使用 wechat-digest 自带的 crypto/decrypt.py（pycryptodome 实现，支持 WAL 合并）
8. **成功!** 解密后数据范围变为 3月13日 ~ 今天(4月16日) 18:38，4月15日共 2164 条消息

### 第四阶段：定位目标群
1. 4月15日有消息的群共 30 个
2. 最活跃群 `49710605556@chatroom` 有 1242 条消息
3. 提取样本消息 → 内容全是 AI 代码生成、Claude Code、大模型讨论 → **确认为 AI 实践群**

### 第五阶段：LLM 摘要生成
1. 提取 AI 实践群 4月15日全部消息共 **1123 条**
2. 测试豆包 API Key 格式：
   - `api-key-xxx...` (带前缀) → 失败
   - 纯 UUID `66e9a0b0-...` → ✅ 成功
3. 构造 prompt（包含消息上下文 + 结构化摘要要求）
4. 豆包 doubao-seed-2-0-lite-260215 生成高质量 5 维度摘要报告
5. 输出到 `output/` 目录

### 经验教训总结
- **永远先确认数据源的时效性** — 不要假设"刚解密的就包含最新数据"
- **Windows 上微信可能有多个数据目录** — 必须通过文件修改时间确认活跃的那个
- **WAL 文件是新数据的藏身之所** — SQLite WAL 模式下，`.db` 文件可能很久没变
- **API Key 格式要实测** — 文档不一定准确，写个最小测试脚本验证最快
- **群名需要间接推断** — 不要花太多时间尝试直接从数据库读群名

---

## 十一、联系方式与上下文

- **项目所有者**: 杰宇（Jerry/Jieyu），AI 产品经理
- **使用场景**: 每日自动总结微信群聊（特别是 AI 实践群）讨论要点
- **当前 LLM**: 火山引擎豆包 doubao-seed-2-0-lite-260215
- **关键决策记录**: 详见 `.workbuddy/memory/MEMORY.md`

---

> 本文档由 AI 助手小沐根据实际部署过程整理，最后更新于 2026-04-16。
