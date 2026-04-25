# WeChatDigestWindows 交接说明

最后更新：2026-04-25

这份文档面向下一位维护者，目标是让公开仓库、桌面界面和核心流程都保持稳定、可发布、可继续迭代。

## 1. 当前项目状态

这个仓库现在是一套面向 Windows 的本地微信摘要工具，包含两种入口：

- CLI：`digest.py`
- GUI：`run_gui.py`

当前结构遵循以下边界：

- `digest.py`：真实业务流程和兼容入口
- `src/wechat_digest_app/backend.py`：供 GUI 调用的薄适配层
- `src/wechat_digest_app/gui.py`：PySide6 桌面界面
- `src/wechat_digest_app/vendor/wechat_digest/`：vendored 的辅助能力，如数据库自动探测、解密和 key 扫描

不要把业务逻辑重新塞回 GUI。

## 2. 公开仓库规则

公开仓库应该保留：

- 源代码
- 测试
- 脱敏示例
- 架构、构建、安全、发布文档
- vendored 第三方代码及其署名

公开仓库不应该包含：

- 解密后的数据库
- 真实聊天导出和摘要
- `.env` 真值文件
- `%USERPROFILE%\\.wechat-digest\\*.json`
- 本机路径、群 ID、数据库 key
- 本地诊断产物
- `build/`、`dist/`、`output/` 等运行产物

如果需要写文档示例，请统一用：

- `示例群聊`
- `Example Group`
- `%USERPROFILE%`
- `<your-path>`

不要在文档里留真实样本。

## 3. 这轮已经修过的重点

- README 改成中英双入口，并新增 `README.zh-CN.md`
- `HANDOFF_GUIDE.md` 改成公开可用的脱敏版本
- `RELEASE_CHECKLIST.md` 去掉了历史示例和乱码内容
- `.gitignore` 收紧，补上了本地诊断文件和代理 handoff 文件
- 删除了被跟踪的 `scripts/inspect/*.txt` 诊断输出，改为说明文档
- `app.spec` 改为相对仓库路径解析，避免依赖当前工作目录
- GUI 做了一轮导航和列表层级优化，补了图标与空状态文案

## 4. 下一步建议

优先级最高：

1. 继续完善 README 截图，但必须使用脱敏数据
2. 给桌面应用补正式图标和版本元数据
3. 增强报表页的筛选和搜索
4. 把更长耗时任务的进度反馈做得更细

如果要继续做 UI：

- 先改 `backend.py` 和 `gui.py`
- 每次改完都跑 GUI 冒烟测试
- 不要为了视觉修改而破坏 `digest.py` 的兼容入口

## 5. 最低验证要求

```powershell
python -m unittest discover -s tests -p "test_*.py"
$env:QT_QPA_PLATFORM='offscreen'
python run_gui.py --smoke-test
Remove-Item Env:QT_QPA_PLATFORM
pyinstaller --noconfirm app.spec
$env:QT_QPA_PLATFORM='offscreen'
& .\dist\WeChatDigestWindows\WeChatDigestWindows.exe --smoke-test
Remove-Item Env:QT_QPA_PLATFORM
```

如果改动影响了流程，也要补跑：

```powershell
python digest.py groups --json
python digest.py groups --dm --json
python digest.py test-api
```

## 6. 一句总原则

保持这个仓库“随时可公开”，同时让 GUI 继续做薄封装，而不是第二套业务实现。
当前默认运行态目录：

- `%USERPROFILE%\\.wechat-digest\\`
- 其中摘要输出默认写入 `%USERPROFILE%\\.wechat-digest\\output\\`
