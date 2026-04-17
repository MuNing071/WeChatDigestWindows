---
name: wechat-digest-arch-reorg
overview: 梳理并整合微信群聊总结项目的架构，将分散的解密、提取、LLM模块统一为清晰的目录结构，删除冗余代码和旧脚本。
todos:
  - id: analyze-and-cleanup
    content: 分析并确认可删除的根目录旧脚本（5个），更新README.md中的目录结构说明
    status: completed
  - id: archive-reference-library
    content: 将 wechat-decrypt-full/ 移动到 archive/wechat-decrypt-full/ 作为参考归档
    status: completed
  - id: consolidate-scripts
    content: 精简 scripts/ 目录，将有价值的脚本保留，无用的移到 archive/
    status: completed
  - id: extract-useful-utilities
    content: 从 wechat-digest/ 中提取有用工具（如 biz-articles.py、voice_to_text.py）到 utils/ 子目录
    status: completed
  - id: update-documentation
    content: 更新 README.md 和 HANDOFF_GUIDE.md，反映新的目录结构
    status: completed
  - id: create-dependency-diagram
    content: 创建简化的依赖关系图和快速开始指南
    status: completed
---

## 项目架构梳理

### 现状分析

**工作区包含5个功能交叉的项目内容：**

| 目录 | 文件数 | 用途 | 状态 |
| --- | --- | --- | --- |
| `digest.py` | 1 (1775行) | 统一CLI入口 | ✅ 核心，已验证 |
| `wechat-digest/` | 16个.py | 解密/提取/LLM库 | ✅ 核心依赖 |
| `wechat-decrypt-full/` | 16个.py | 第三方解密库完整版 | ⚠️ 参考库 |
| `wetrace/` + `wetrace-bin/` | 382+33个文件 | Go可视化工具+编译产物 | ⚠️ 密钥提取/数据源 |
| `根目录旧脚本×5` | 5个.py | 已废弃 | ❌ 可删除 |
| `scripts/` | 21个.py | 调试归档 | ⚠️ 部分可清理 |


### 核心数据流

```
微信加密DB (SQLCipher 4)
    ↓ [密钥提取: wetrace-bin/ 或 init-keys.py]
crypto/decrypt.py [解密 + WAL合并]
    ↓ [解密后DB]
digest.py [提取消息 → 压缩 → LLM摘要]
    ↓
output/ [Markdown摘要]
```

### 依赖关系

1. **digest.py** 依赖 **wechat-digest/crypto/** (解密) + LLM API
2. **digest.py** 可读写 **wetrace-bin/wetrace/data/** (已解密DB)
3. **wechat-decrypt-full/** 的crypto/是wechat-digest/的来源，仅作参考
4. **wetrace/** 是Go项目，用于密钥提取和数据可视化，与Python工作流松耦合

### 整合重构目标

1. 删除废弃代码，保留必要依赖
2. 建立清晰的三层架构：CLI入口 → 核心库 → 数据源
3. 文档和配置集中管理

## 技术架构：三层结构

```
┌─────────────────────────────────────────────────┐
│  Layer 1: CLI 入口层                              │
│  digest.py (1775行) - 统一命令接口                 │
│  - decrypt / extract / summarize / run / batch    │
└─────────────────────┬───────────────────────────┘
                      │ imports
┌─────────────────────▼───────────────────────────┐
│  Layer 2: 核心库 wechat-digest/                  │
│  ├── crypto/         SQLCipher 4 解密 (WAL合并)   │
│  ├── extract_*.py    消息提取 (已内嵌到digest.py) │
│  └── llm_summarize.py  LLM调用 (已内嵌到digest.py)│
└─────────────────────┬───────────────────────────┘
                      │ reads
┌─────────────────────▼───────────────────────────┐
│  Layer 3: 数据源层                                │
│  ├── 微信加密DB  →  需要密钥 + 解密               │
│  ├── wetrace-bin/  →  已解密DB (可直接用)        │
│  └── wechat-decrypt-full/  →  仅参考，无依赖      │
└─────────────────────────────────────────────────┘
```

## 目录重构方案

```
e:/微信群聊总结/
│
├── digest.py                    # ⭐ 统一CLI入口（保留）
├── README.md                    # 项目总览（保留）
├── HANDOFF_GUIDE.md             # 踩坑记录（保留）
│
├── wechat-digest/               # ⭐ 核心库（保留，瘦身）
│   ├── crypto/                  # 解密核心（必需）
│   │   ├── decrypt.py
│   │   ├── config.py
│   │   └── keys/
│   ├── extract.py               # 消息提取（可合并到digest.py）
│   ├── llm.py                   # LLM调用（可合并到digest.py）
│   └── __init__.py
│
├── wetrace-bin/                 # 数据源+密钥工具（保留）
│   ├── wetrace.exe              # 密钥提取工具
│   └── wetrace/data/            # 已解密DB
│
├── wechat-decrypt-full/         # 【归档】参考库（移动到archive/）
│
├── scripts/                     # 调试脚本（精简）
│   ├── daily_stats.py           # 有用，保留
│   └── [其他归档]
│
├── output/                      # 产出目录（保留）
│
├── __pycache__/                 # 可添加到.gitignore
│
└── [根目录旧脚本全部删除]
    ❌ run_doubao.py
    ❌ decrypt_active.py
    ❌ find_ai_practice.py
    ❌ extract_apr15.py
    ❌ test_doubao.py
```

## 依赖分析

| 组件 | 被依赖 | 依赖 |
| --- | --- | --- |
| digest.py | 0 | wechat-digest/crypto |
| wechat-digest/crypto | digest.py | pycryptodome |
| wechat-digest/* 其他 | 无 | - |
| wechat-decrypt-full/* | 无 | - |
| wetrace-bin/* | digest.py (读已解密DB) | - |


## 实现步骤