# 微信群聊总结 (WeChat Group Digest)

从微信本地加密数据库提取群聊记录，调用 LLM 生成结构化每日摘要。

## 快速开始

```powershell
# 1. 配置环境变量（敏感信息不硬编码）
$env:WECHAT_LLM_API_KEY = "your-api-key"

# 2. 初始化配置
python digest.py config --init

# 3. 列出所有群
python digest.py groups

# 4. 提取消息
python digest.py extract "AI实践" 2026-04-13

# 5. 生成摘要
python digest.py summarize "AI实践" 2026-04-13 -o output/2026-04-13-summary.md

# 或者一键全流程
python digest.py run "AI实践" 2026-04-13
```

## CLI 子命令

| 命令 | 说明 |
|------|------|
| `groups [--json]` | 列出所有群聊，支持 JSON 输出 |
| `extract <群名> <日期> [--json] [-o file]` | 提取消息 |
| `summarize <群名> <日期> [-o file]` | LLM 生成摘要 |
| `run <群名> <日期>` | 一键全流程（解密+提取+摘要） |
| `decrypt` | 解密所有微信数据库 |
| `test-api` | 测试 LLM API 连接 |
| `config --show/--set KEY=VALUE/--init` | 查看/修改配置 |

## 配置

配置文件: `~/.wechat-digest/config.json`

敏感信息优先从环境变量读取，不硬编码在代码中：

| 环境变量 | 说明 |
|----------|------|
| `WECHAT_LLM_API_KEY` | LLM API 密钥 |
| `WECHAT_DB_KEY` | 数据库解密密钥 |
| `LLM_PROVIDER` | LLM 提供商 (doubao/glm/deepseek/openai) |
| `LLM_BASE_URL` | LLM API 地址 |
| `LLM_MODEL` | 模型名称 |

也支持 `~/.wechat-digest/llm_config.json` 单独配置 LLM。

## 数据流

```
微信加密数据库 (SQLCipher 4, WAL模式)
    → digest.py decrypt（解密+WAL合并）
    → digest.py groups（列出群聊，支持模糊搜索）
    → digest.py extract（提取消息，支持JSON输出）
    → digest.py summarize（LLM摘要生成）
    → output/ 摘要 Markdown
```

## 目录结构

```
e:/微信群聊总结/
├── digest.py                    # ⭐ 统一CLI入口（替代旧的5个独立脚本）
├── README.md                    # 本文件
├── HANDOFF_GUIDE.md             # 完整接手者文档（踩坑记录+详细配置）
│
├── run_doubao.py                # 旧版一键脚本（保留为参考，已被 digest.py 替代）
├── decrypt_active.py            # 旧版解密脚本（保留为参考）
├── find_ai_practice.py          # 旧版群搜索脚本（保留为参考）
├── extract_apr15.py             # 旧版消息提取脚本（保留为参考）
├── test_doubao.py              # 旧版API测试脚本（保留为参考）
│
├── wechat-digest/               # 核心模块（解密/提取/LLM）
│   ├── crypto/                  # SQLCipher 4 解密核心（支持WAL合并）
│   ├── extract-messages.py      # 群聊消息提取（支持命令行参数）
│   ├── extract_decrypted.py     # 从已解密DB提取（Wetrace兼容）
│   ├── llm_summarize.py         # LLM 摘要（多厂商支持）
│   └── prompt-template.txt      # Prompt 模板
│
├── wechat-decrypt-full/         # 第三方解密库（参考）
├── wetrace/                     # Wetrace 可视化工具源码
├── wetrace-bin/                 # Wetrace 编译产物 + 密钥Hook工具
│
├── scripts/                     # 开发调试脚本归档
│   ├── archive/                 # 历史版本脚本
│   ├── debug/                   # 检查验证类脚本
│   └── inspect/                 # DB/schema检查 + 调试产出
│
├── output/                      # 最终产出（摘要Markdown）
└── .workbuddy/memory/           # 工作记忆
```

## Agent 友好设计

`digest.py` 专为 AI agent 交互优化：

- **分步操作**: 每个子命令独立可调用，agent 可以先 groups 查看列表，再选择群提取
- **JSON 输出**: `--json` 参数让所有命令返回结构化数据，方便程序解析
- **错误信息**: 明确的错误提示，不使用 bare except
- **无交互**: 所有命令非交互式，不会因为 stdin 不可用而卡住
- **敏感信息外置**: API Key 和密码从环境变量/配置文件读取，不硬编码

## 核心配置要点

| 配置项 | 位置 | 说明 |
|--------|------|------|
| 微信数据目录 | `~/.wechat-digest/config.json` → `db_dir` | 加密数据库所在目录 |
| 已解密目录 | `~/.wechat-digest/config.json` → `decrypted_dir` | wetrace 解密输出目录 |
| 群名映射 | `~/.wechat-digest/config.json` → `known` | 群名到 username 的映射 |
| LLM 配置 | 环境变量 或 `llm_config.json` | API Key、模型、endpoint |
| 数据库密钥 | 环境变量 `WECHAT_DB_KEY` | 通过 Wetrace 从进程内存提取 |

已知群映射: `"AI实践"` → `49710605556@chatroom`

## 常见问题

- **解密数据只有旧数据?** → 检查是否用了正确的活跃数据目录（详见 HANDOFF 第四节）
- **WAL 未合并导致缺最新数据?** → 用 `digest.py decrypt` 或 wechat-digest/crypto/ 解密
- **LLM API 返回 401?** → 检查环境变量 `WECHAT_LLM_API_KEY` 是否正确
- **中文乱码?** → PowerShell 默认 GBK 编码，digest.py 已内置 UTF-8 处理
- **groups 列出群但名字是 username?** → 在 config.json 的 known 字段添加映射

完整踩坑记录和故障排查见 [HANDOFF_GUIDE.md](./HANDOFF_GUIDE.md)。

## 环境要求

- Windows 11 + Python 3.12 + 微信 4.1.x
- pip: pycryptodome, zstandard
- 微信进程名 **Weixin.exe**（非 WeChat.exe）
