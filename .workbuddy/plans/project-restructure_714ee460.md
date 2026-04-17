---
name: project-restructure
overview: 基于 HANDOFF_GUIDE.md 确认的生产文件定位，对微信群聊总结工作区进行根目录整理、目录规范化、README建立三件事。核心修正：run_doubao.py/decrypt_active.py/find_ai_practice.py/extract_apr15.py 是生产代码而非临时脚本。
todos:
  - id: create-readme
    content: 创建根级 README.md（工作区总览：项目定位、目录结构图、快速开始、子项目说明）
    status: completed
  - id: restructure-scripts
    content: 创建 scripts/ 目录结构并迁移17个调试脚本（archive/debug/inspect 三类归档）
    status: completed
  - id: cleanup-redundant
    content: 删除冗余文件（2个zip包、空壳wechat-decrypt/目录）、迁移debug产出物到scripts/inspect/
    status: completed
    dependencies:
      - restructure-scripts
  - id: update-handoff
    content: 更新 HANDOFF_GUIDE.md 第六节「项目文件索引」同步新目录结构
    status: completed
    dependencies:
      - restructure-scripts
      - cleanup-redundant
  - id: verify-integrity
    content: 使用 code-explorer 验证所有被移动脚本的路径依赖无断裂，确认run_doubao等5个生产脚本不受影响
    status: completed
---

## 产品概述

对「微信群聊总结」工作区进行全面的架构重组：将根目录从开发调试状态整理为可维护的生产项目结构，建立清晰的文档体系，清理冗余文件，为后续功能扩展奠定基础。

## 核心任务

1. **根目录重组**：将约22个散落的Python脚本按生产/调试分类归位，根目录只保留入口级生产脚本和文档
2. **创建根级 README.md**：作为工作区总览，说明各子项目职责、数据流关系、快速开始指南
3. **冗余清理**：删除zip压缩包、空壳目录、迭代版本脚本、调试产出物
4. **目录规范化**：统一产出物路径（output/data/），明确 scripts/ 的子目录结构
5. **更新 HANDOFF_GUIDE.md 同步新结构**：确保接手者文档与实际文件位置一致

## 关键约束（来自HANDOFF_GUIDE + MEMORY）

- **5个生产脚本不可移动或修改其内部逻辑**：run_doubao.py, decrypt_active.py, find_ai_practice.py, extract_apr15.py, test_doubao.py — 这些是已验证的核心工具
- **Wetrace 是密钥获取的唯一可行方案**（微信4.1.x内存扫描失效），wetrace/ 和 wetrace-bin/ 必须保留
- **wechat-digest/crypto 是唯一支持WAL合并的解密模块**，wechat-decrypt-full 作为参考保留即可
- **当前活跃数据源**：wetrace-bin/wetrace/data/message_active/（Wetrace解密输出+手工WAL合并）
- **output/** 已有3个产出文件，命名需保持一致

## Tech Stack

本项目为纯 Python 脚本工具链 + PowerShell 编排，无新增技术栈需求：

- **核心语言**: Python 3.12 + PowerShell (Windows 11)
- **关键依赖**: pycryptodome (SQLCipher4), zstandard (zstd解压)
- **LLM**: 火山引擎豆包 API (doubao-seed-2-0-lite)
- **辅助工具**: wetrace.exe (Go编译产物，密钥Hook)

## Implementation Approach

采用「归档式重组」策略——不删除任何可能有价值的代码，而是通过目录迁移实现分层：

**策略核心**：三层目录模型

- **根目录** = 生产入口（一键运行脚本）+ 项目文档（README, HANDOFF）
- **scripts/** = 所有开发调试脚本（按功能分子目录）
- **子项目目录保持不动** = wechat-digest/, wetrace/, wetrace-bin/, wechat-decrypt-full/

**关键决策**：

1. 5个生产脚本保留在根目录（run_doubao.py 是用户的主要入口，不应深埋）
2. 开发调试脚本移入 scripts/{archive, debug, inspect} 而非直接删除（保留调试能力）
3. find_group2~5.py（迭代版本）移入 scripts/archive/，仅保留最终版逻辑参考
4. 不修改任何生产脚本的内部代码或 import 路径（避免引入回归风险）
5. README.md 采用精简版（~100行），详细内容留在 HANDOFF_GUIDE.md

## Architecture Design

```
重组后目标结构:
e:/微信群聊总结/
├── README.md                    # [新建] 工作区总览（~100行精简版）
├── HANDOFF_GUIDE.md             # [已有] 完整接手者文档（不移动）
│
├── run_doubao.py                # [保留] ⭐ 一键运行入口
├── decrypt_active.py            # [保留] 解密工具
├── find_ai_practice.py          # [保留] 群搜索工具  
├── extract_apr15.py             # [保留] 消息提取工具
├── test_doubao.py              # [保留] API测试工具
│
├── wechat-digest/               # [不动] 核心摘要项目源码
├── wechat-decrypt-full/         # [不动] 第三方解密库（参考用）
├── wechat-decrypt/              # [清理] 仅保留tools/中的有用工具
├── wetrace/                     # [不动] Go可视化前端源码
├── wetrace-bin/                 # [不动] Wetrace编译产物+解密输出
│
├── scripts/                     # [新建] 开发调试脚本收纳
│   ├── archive/                 # 有参考价值的历史脚本
│   │   ├── find_group.py        # find_group系列最终版
│   │   ├── find_group2.py ~ find_group5.py  # 迭代历史
│   │   └── find_target.py       # 早期搜索尝试
│   ├── debug/                   # 检查验证类脚本
│   │   ├── check_all_0415.py
│   │   ├── check_all_dates.py
│   │   ├── check_decrypt_range.py
│   │   ├── check_fresh.py
│   │   ├── deep_check.py
│   │   ├── list_groups.py
│   │   └── try_pycryptodome.py
│   └── inspect/                 # DB/schema检查类脚本+产出
│       ├── inspect_db.py
│       ├── inspect_msg_schema.py
│       ├── inspect_sessions.py
│       ├── db-sessions.txt      # 从根目录迁入
│       └── db-structure.txt     # 从根目录迁入
│
├── output/                      # [保留] 最终摘要产出
│   ├── 2026-04-15_topgroup_raw.txt
│   ├── 2026-04-15-ai_practice-chat.md
│   └── 2026-04-15-ai_practice-summary.md
│
└── .workbuddy/memory/           # [不动] 工作记忆
```

## Implementation Notes

1. **路径安全**：所有操作仅为 mkdir + git mv（或手动移动），不涉及代码修改
2. **HANDOFF_GUIDE.md 更新**：第六节「项目文件索引」需要同步新的目录结构，否则接手者会按旧路径找文件找不到
3. **wechat-decrypt/tools/ 处理**：该目录下有 diagnose_patterns.py 和 extract_keys.py 两个有用的诊断工具，考虑移入 scripts/inspect/ 后删除空壳 wechat-decrypt/
4. **压缩包删除**：wechat-decrypt.zip 和 wetrace.zip 删除前确认解压完整（已确认完整）
5. **blast radius 控制**：不触碰 .workbuddy/、wetrace/、wetrace-bin/、wechat-digest/ 内部文件

本次任务不涉及UI创建或改造，属于纯文件系统重组+文档撰写任务。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 在创建计划后执行阶段，用于批量扫描待移动的22个脚本文件头部，确认每个文件的用途注释、import依赖和是否有跨文件引用（确保移动后不会破坏相对路径引用）
- Expected outcome: 输出一份「文件依赖检查报告」，标明哪些文件有硬编码的相对路径需要在移动时修正