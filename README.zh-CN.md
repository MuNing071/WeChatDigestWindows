# WeChatDigestWindows

[English README](./README.md) | [公开仓库范围](./PUBLIC_REPO_SCOPE.md) | [架构说明](./ARCHITECTURE.md) | [安全说明](./SECURITY.md) | [构建说明](./BUILD.md)

这是一个面向 Windows 的本地工具，用来把微信聊天记录整理成结构化 Markdown 摘要，既可以走命令行，也可以直接用桌面界面。

## 仓库里应该有什么

- `digest.py`：主流程和 CLI
- `run_gui.py`：桌面应用入口
- `src/wechat_digest_app/backend.py`：GUI 到 CLI 的薄适配层
- `src/wechat_digest_app/gui.py`：PySide6 桌面界面
- `tests/`：基础回归和冒烟测试
- `examples/`：脱敏后的示例输出
- 文档：README、架构、安全、构建、发布检查清单
- `src/wechat_digest_app/vendor/wechat_digest/`：保留署名的 vendored 第三方辅助代码

## 仓库里不应该有什么

- 解密后的数据库
- 真实聊天摘要或聊天截图
- 任何 `.env` 真值文件
- `%USERPROFILE%\\.wechat-digest\\*.json`
- 本机路径、密钥、群 ID、数据库 key
- `build/`、`dist/`、`output/` 之类运行产物
- 本地诊断导出文件，例如数据库表结构和会话快照

公开发布前请先看一遍 [SECURITY.md](./SECURITY.md)。

## 快速开始

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 个人运行配置放在仓库外

程序会把本地配置保存在：

- `%USERPROFILE%\\.wechat-digest\\config.json`
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\output\\`

这些文件不要拷进仓库。

### 3. 启动桌面界面

```powershell
python run_gui.py
```

### 4. 或者使用命令行

```powershell
python digest.py groups
python digest.py groups --dm
python digest.py summarize "示例群聊" 2026-04-16
python digest.py summarize "示例群聊" today --since 14:00
python digest.py batch "示例群聊" --last-n 7
```

## 当前 GUI 覆盖的流程

- 配置本地数据库和输出目录
- 配置模型供应商、模型名和 API Key
- 浏览群聊和单聊会话
- 运行单日或多日摘要
- 查看历史报告和运行日志

## 测试

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

GUI 冒烟测试：

```powershell
$env:QT_QPA_PLATFORM="offscreen"
python run_gui.py --smoke-test
```

## 打包

```powershell
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

更多说明见 [BUILD.md](./BUILD.md)。

## 说明

- 当前优先支持 Windows。
- GUI 故意保持很薄，核心流程仍然复用 `digest.py`。
- `scripts/archive/` 里是历史实验和参考代码，不建议当作主产品入口继续扩展。
