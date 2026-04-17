# 长期记忆

## 项目架构

### 项目已重构（2026-04-17）
- 引入Git版本控制，基线提交bf320d8，可通过`git reset --hard HEAD~1`回退
- 归档scripts/archive/：5个旧脚本+wechat-decrypt-full/+wetrace/源码
- 精简scripts/：保留诊断工具（list_groups.py、inspect_*.py）
- 更新README.md和HANDOFF_GUIDE.md

### digest.py CLI V3（当前主力入口）
- 统一CLI工具，9个子命令：groups/contacts/extract/summarize/run/batch/decrypt/test-api/config
- **V3功能（2026-04-17）**：
  - `--since HH:MM`：增量摘要，只处理指定时间后消息，--since 模式下自动追加到已有文件
  - `--segment`：分段摘要，按4小时间隔切分，每段独立调用LLM，合并输出
  - `--quiet / -q`：静默模式，只输出最终摘要
  - `batch` 子命令：支持日期范围（YYYY-MM-DD:YYYY-MM-DD）和 --last-n N 批量生成
  - `date` 参数默认 yesterday，支持 today/yesterday 字符串
  - 自动保存到 output/{群名}/{日期}.md（不传 --output 时）
  - 摘要缓存（TTL 12h）：~/.wechat-digest/cache/summary_*.json
- **V3 compact 模式（默认开启）**：
  - summarize/run/batch 默认 compact=True，用 `--full` 关闭压缩
  - extract 子命令保持 `--compact` 为可选（默认全量）
  - compact 保留 URL（不再省略，链接分享有价值信息）
  - 同发送者连续消息省略发送者名（节省token）
  - SEGMENT_GAP=60分钟（话题切换时显示时间标记）
  - 噪声过滤覆盖约27%（从1131→825条），包括拍一拍、扩展语气词、引用附和
  - `--report-full`：在报告中包含完整聊天详情（原 --full 功能）
- **V3上下文工程改进**：
  - 话题边界标记：`── [HH:MM] ──`
  - 系统消息过滤（撤回/加群/改名等，SYSTEM_MSG_PATTERNS）
  - ChatMessage 新增 ref_summary 字段（引用消息原文摘要，用于折叠显示）
- **V3代码质量改进**：
  - LLM_PROVIDERS 提取为模块级常量（消除两处重复定义）
  - 全局 --no-cache 已正确连通到子命令
  - cmd_run 智能跳过已解密状态（不再每次强制 decrypt）
  - 统一使用 logging 模块，log = logging.getLogger("wechat-digest")
  - _resolve_date()：today/yesterday/YYYY-MM-DD 统一解析
  - _safe_name()：群名路径安全化
  - _segment_messages()：按时间间隔切分消息段
- 摘要缓存key：`sum:{group}:{date}:{compact}:{since_min}:{segment}:{prompt_hash[:8]}`
- 摘要质量统计：stderr输出摘要字数/章节数
- 敏感信息通过环境变量读取：WECHAT_LLM_API_KEY、WECHAT_DB_KEY、LLM_PROVIDER
- 支持 --json 结构化输出（agent友好），compact 为默认模式
- 配置文件：~/.wechat-digest/config.json（db_dir, decrypted_dir, known, output_dir）
- LLM配置：~/.wechat-digest/llm_config.json 或环境变量
- 豆包API Key：66e9a0b0-837c-4f0f-a1f4-ee44413c04f9（UUID格式）
- 压缩效果（04-15, 1131条）：compact过滤27%噪声（1131→825条），文本30287字符

### 关键路径
- 微信加密DB: E:\Documents\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage
- 活跃数据目录: E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage（注意两个目录！）
- 已解密目录: e:\微信群聊总结\wetrace-bin\wetrace\data（含session/message/message_active等子目录）
- 输出目录: e:\微信群聊总结\output

### 核心模块
- wechat-digest/crypto/decrypt.py — SQLCipher 4 解密+WAL合并（唯一正确处理WAL的实现）
- wechat-digest/crypto/config.py — 配置加载+数据目录自动检测
- wechat-digest/extract-messages.py — 消息提取（命令行工具，支持群名+日期+hour-offset）
- wechat-digest/llm_summarize.py — 多厂商LLM摘要

### 已知群映射
- AI实践群: 49710605556@chatroom
- 联系人缓存1037个条目（contact.db自动读取）

## 踩坑经验
- 微信4.1.x内存扫描方法失效，必须用Wetrace Hook方式获取密钥
- Wetrace解密不合并WAL，最新数据需要用crypto/decrypt.py重新解密
- 微信有两个数据目录，旧的在E:\Documents\，活跃的在E:\文档\
- 豆包API Key格式是纯UUID，不带api-key-前缀
- PowerShell默认GBK编码，需要UTF-8 wrapper处理中文
- decrypted_dir应指向data/根目录（包含session/message/message_active），不是message_active子目录
- config.json中known字段支持群名模糊匹配
- NOISE_PATTERNS正则中+1的+需要转义（\+1），否则是量词导致re.error
- PowerShell管道|会干扰JSON解析，验证JSON输出用临时文件或python -c内联
