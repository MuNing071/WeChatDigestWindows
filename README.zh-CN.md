# WeChatDigestWindows

[English README](./README.md) | [安全说明](./SECURITY.md)

这是一个面向 Windows 的本地工具，用来把微信聊天记录整理成结构化 Markdown 摘要，既可以走命令行，也可以直接用桌面界面。

## 仓库保留什么

- `digest.py`：主流程和 CLI
- `run_gui.py`：桌面应用入口
- `src/wechat_digest_app/backend.py`：GUI 到 CLI 的薄适配层
- `src/wechat_digest_app/gui.py`：PySide6 桌面界面
- `src/wechat_digest_app/vendor/wechat_digest/`：vendored 的辅助代码
- `tests/`：基础回归和冒烟测试

## 仓库不保留什么

- 解密后的数据库
- 真实聊天导出和真实摘要
- `.env` 真值文件
- `%USERPROFILE%\\.wechat-digest\\*.json`
- 本机路径、群 ID、数据库 key
- `build/`、`dist/` 这类构建产物
- `output/`、`wetrace-bin/` 这类本地运行目录
- 只对单台机器有意义的历史归档和调试快照

## 快速开始

安装依赖：

```powershell
pip install -r requirements.txt
```

启动桌面界面：

```powershell
python run_gui.py
```

使用命令行：

```powershell
python digest.py groups
python digest.py groups --dm
python digest.py summarize "示例群聊" 2026-04-16
```

## 本地运行态

个人运行配置和输出都放在仓库外：

- `%USERPROFILE%\\.wechat-digest\\config.json`
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\output\\`

这台机器对应的本地目录是：

- `E:\\微信群聊总结.local-state`

## 验证

```powershell
python -m unittest discover -s tests -p "test_*.py"
$env:QT_QPA_PLATFORM="offscreen"
python run_gui.py --smoke-test
```

## 打包

```powershell
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

公开发布前请先看 [SECURITY.md](./SECURITY.md)。
