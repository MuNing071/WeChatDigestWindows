# 火山方舟批量推理配置指南

## 概述

digest.py 支持两种LLM调用模式：
- **实时推理**：响应快，适合即时需求
- **批量推理**：成本低（约5-7折），适合定时任务

## 快速开始

### 1. 安装火山方舟SDK

```bash
pip install --upgrade "volcengine-python-sdk[ark]"
```

### 2. 获取批量推理端点ID

1. 登录[火山方舟控制台](https://console.volcengine.com/ark/)
2. 进入「批量推理」页面
3. 创建批量推理端点，获取端点ID（如 `ep-bi-20260417113501-nbr5x`）

### 3. 配置环境变量

```powershell
# PowerShell
$env:ARK_API_KEY = "your-ark-api-key"
$env:LLM_BATCH_ENDPOINT = "ep-bi-20260417113501-nbr5x"
```

或永久配置到系统环境变量。

## 使用方式

### 命令行使用

```bash
# 单次摘要使用批量推理
python digest.py summarize "AI实践" --batch-mode

# 批量生成多天摘要（默认使用批量推理）
python digest.py batch "AI实践" --last-n 7 --compact

# 一键全流程使用批量推理
python digest.py run "AI实践" --batch-mode
```

### 定时任务配置

在 WorkBuddy 自动化任务中，使用 `--batch-mode` 参数：

```json
{
  "prompt": "python e:/微信群聊总结/digest.py run 'AI实践' --batch-mode --compact"
}
```

## 配置优先级

1. 环境变量（最高优先级）
   - `ARK_API_KEY` - 火山方舟API Key
   - `LLM_BATCH_ENDPOINT` - 批量推理端点ID
   - `LLM_BATCH_PROVIDER` - 批量推理提供商（默认 ark）

2. 配置文件（次优先级）
   - `~/.wechat-digest/llm_config.json`

```json
{
  "provider": "doubao",
  "api_key": "your-realtime-api-key",
  "model": "doubao-1-5-pro-256k",
  "batch_provider": "ark",
  "batch_endpoint": "ep-bi-20260417113501-nbr5x",
  "batch_api_key": "your-ark-api-key"
}
```

## 成本对比

| 模式 | 适用场景 | 成本 | 响应时间 |
|------|----------|------|----------|
| 实时推理 | 即时需求 | 标准价 | 秒级 |
| 批量推理 | 定时任务 | 约5-7折 | 分钟级 |

## 故障排查

### SDK未安装

```
未安装火山方舟SDK，请运行: pip install 'volcengine-python-sdk[ark]'
```

解决：`pip install --upgrade "volcengine-python-sdk[ark]"`

### 端点ID未配置

```
未配置批量推理端点ID。设置 LLM_BATCH_ENDPOINT 环境变量
```

解决：设置 `LLM_BATCH_ENDPOINT` 环境变量

### API Key无效

检查 `ARK_API_KEY` 是否正确，注意与实时推理的 Key 可能不同。

## 测试配置

```bash
python digest.py test-api
```

输出应显示：
- 实时推理配置：已配置
- 批量推理配置：provider / endpoint / api_key / SDK状态
