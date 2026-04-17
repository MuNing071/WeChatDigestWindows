# AI实践 群聊摘要 - 2026-04-15

> 消息总数：951 条 | 最活跃时段：15:00 - 23:00

### 核心讨论
1. **Claude最新封禁政策与替代方案讨论**
   - Anthropic近期加大对中国用户的封锁力度，要求全球所有用户完成身份验证，香港IP也被纳入封禁范围，Max账号被封概率远高于Pro和免费账号
   - 目前跳板机+AWS源是相对稳定的使用方案，多家国内大厂通过中转、人肉带卡的方式继续使用，第三方中转平台存在套利空间
   - 国内替代方案方面，GLM 5.1体验已接近Claude Sonnet 4.6，智谱、Kimi预计6月推出对标Opus 4.6的新版本。

2. **主流Coding Agent工具体验对比**
   - 闭源工具中多数群友认可Claude Code(CC)体验最优：流程透明可回溯，支持自动调用子代理，配合Plan模式先对齐需求再编码可避免过度开发，和Obsidian打通后长上下文管理更清晰
   - 龙虾(OpenCLaW)被反馈不稳定、记忆差、配置爬坡期长，属于半成品，体验远不如CC；Hermes整体提升有限，和龙虾差异不大
   - 开源工具中Gemini CLI相对稳定靠谱，整体开源Agent体验仍不及闭源CC。

3. **AI场景办公笔记本选型讨论**
   - AI开发、本地运行大模型场景优先推荐苹果M系列芯片Mac：核心优势包括统一内存架构可动态分配内存充当显存，低成本就能运行30B级本地大模型；类Unix底层生态对AI工具链兼容性更好，极少出现依赖报错；Apple Silicon专属MLX框架优化到位，系统级AI整合体验好；续航优势突出，出差一周不用带充电器
   - 不习惯macOS的Windows用户推荐机械革命星耀14，续航已能满足日常需求。

4. **AI对工作模式的改变**
   - 已有大量团队90%以上代码由AI生成，非研发岗位也可借助AI跨岗位完成开发工作，仅需人工做最终审核，AI降低了开发门槛，一人团队创业成为可能
   - AI普及后多数人习惯同时开多个AI任务并行，人类大脑上下文窗口有限，多数群友建议同时运行任务不超过3个，避免大脑过载。

### 实用信息
- **Claude Opus长时间运行停止解决**：可通过GitHub hooks配置实现持续运行，大任务建议拆分多步执行，先使用Plan模式对齐需求再编码，避免一次性给出过大需求导致上下文过载
- **GPT 5.4输出啰嗦优化**：可添加prompt指令`文本风格参考 Gemini 3.1 Pro`优化输出风格，解决不说人话的问题
- **WorkBuddy大任务卡顿解决**：拆分需求，控制每个步骤的输入输出，避免添加过多专家角色占用上下文，卡住后可终止让AI复盘原因
- **Obsidian+Claude Code联动方案**：使用Obsidian官方Claude Code Skill，可直接生成符合Obsidian格式的Markdown内容，支持双链、白板，方便长记忆知识分层整理
- **Claude节点风险检测**：可通过专用工具检测节点是否干净，降低被封禁概率
- **Windows使用AI开发环境注意事项**：建议使用WSL运行AI工具，可减少编码和权限问题，避免误删硬盘文件。

### 资源分享
| 资源 | 概要 | 备注 |
| --- | --- | --- |
| [SEO machine](https://github.com/TheCraigHewitt/seomachine) | SEO方向开源工具 | |
| [AgentRecall](https://github.com/Goldentrii/AgentRecall) | AI Agent长期记忆开源项目 | |
| [wechat-cli](https://github.com/huohuoer/wechat-cli/) | 微信命令行开发工具 | 原仓库已删除，有群友备份 |
| [Claude IP风险检测](https://ip.net.coffee/claude/) | 检测Claude使用节点的安全性，降低封禁风险 | 群友评价实用 |
| [ppti 商分职业性格测试](https://ryanliangwh.github.io/ppti/) | 面向战略/咨询/商分从业者的性格测试工具 | 群友原创Vibe Coding项目 |
| [meshy 1美元新用户活动](http://meshy.ai/s/k5nc4j) | AI 3D建模平台新用户优惠邀请 | |
| [Claude Imprint](https://github.com/Qizhan7/claude-imprint) | 带长期记忆的跨平台Claude私人AI管家 | 群友原创开源项目 |
| [WeChat-ClaudeCode-MCP](https://github.com/SsssssSynqa/WeChat-ClaudeCode-MCP) | 实现Claude连接微信，支持查询历史记录、监听新消息 | 群友原创开源项目 |
| [Clawd 桌宠](https://github.com/rullerzhou-afk/clawd-on-desk) | 支持Win/Mac的Claude主题电脑桌宠 | 群友原创开源项目 |


*报告生成时间: 2026-04-16 22:25:53*
*消息数: 951 | 压缩: 是*