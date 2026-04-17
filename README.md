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
| `contacts [--json]` | 导出联系人映射 |
| `extract <群名> <日期> [--json] [-o file]` | 提取消息 |
| `summarize <群名> <日期> [-o file]` | LLM 生成摘要 |
| `run <群名> <日期>` | 一键全流程（解密+提取+摘要） |
| `batch <群名> --last-n N` | 批量生成多天摘要 |
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
├── digest.py                    # ⭐ 统一CLI入口
├── README.md                    # 本文件
├── HANDOFF_GUIDE.md             # 完整接手者文档（踩坑记录+详细配置）
│
├── wechat-digest/               # ⭐ 核心模块库
│   ├── crypto/                  # SQLCipher 4 解密核心（支持WAL合并）
│   │   ├── decrypt.py           # 解密+WAL合并实现
│   │   ├── config.py            # 配置加载+数据目录自动检测
│   │   └── keys/                # 密钥扫描器（Windows/Mac/Linux）
│   ├── extract-messages.py      # 消息提取（命令行工具）
│   ├── extract_decrypted.py     # 从已解密DB提取（Wetrace兼容）
│   ├── llm_summarize.py         # LLM 摘要（多厂商支持）
│   ├── init-keys.py             # 密钥提取入口
│   ├── voice_to_text.py         # 语音转文字（可选）
│   ├── biz-articles.py          # 公众号文章抓取（可选）
│   └── prompt-template.txt       # Prompt 模板
│
├── wetrace-bin/                 # Wetrace 编译产物 + 密钥Hook工具 + 已解密数据
│   └── wetrace/data/            # 已解密数据库（session/message/contact）
│
├── utils/                       # 扩展工具目录
├── scripts/                     # 工具脚本
│   ├── daily_stats.py           # 每日统计
│   ├── debug/list_groups.py     # 诊断：列出群组
│   └── inspect/                 # 数据库检查工具
│
├── scripts/archive/             # 归档（旧版本/参考代码，不影响主流程）
│   ├── run_doubao.py           # 旧版一键脚本（已被digest.py替代）
│   ├── decrypt_active.py        # 旧版解密脚本
│   ├── find_ai_practice.py     # 旧版群搜索
│   ├── extract_apr15.py        # 旧版消息提取
│   ├── test_doubao.py          # 旧版API测试
│   ├── wechat-decrypt-full/    # 第三方解密库（参考）
│   └── wetrace/                # Wetrace 源码（参考）
│
└── output/                      # 最终产出（摘要Markdown）
```

## 版本控制

项目使用 Git 管理，出错时可回退：

```powershell
# 查看提交历史
git log --oneline

# 回退到基线版本（重构前）
git reset --hard HEAD~1

# 查看当前状态
git status
```

## Agent 友好设计

`digest.py` 专为 AI agent 交互优化：

- **分步操作**: 每个子命令独立可调用，agent 可以先 groups 查看列表，再选择群提取
- **JSON 输出**: `--json` 参数让所有命令返回结构化数据，方便程序解析
- **错误信息**: 明确的错误提示，不使用 bare except
- **无交互**: 所有命令非交互式，不会因为 stdin 不可用而卡住
- **敏感信息外置**: API Key 和密码从环境变量/配置文件读取，不硬编码

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
