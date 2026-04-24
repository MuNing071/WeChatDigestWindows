import os
import sys
import traceback

from PySide6.QtCore import QDate, QObject, QRunnable, QThreadPool, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import backend


APP_STYLESHEET = """
QMainWindow {
    background: #f5f7fb;
}
QWidget {
    color: #162033;
    font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei";
    font-size: 13px;
}
QFrame#Sidebar {
    background: #eef2f8;
    border-right: 1px solid #d9e1ee;
}
QFrame#ContentRoot {
    background: #f5f7fb;
}
QFrame#HeaderBar {
    background: #f8faff;
    border-bottom: 1px solid #dbe3ef;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #dde5f0;
    border-radius: 8px;
}
QFrame#HeroCard {
    background: #ffffff;
    border: 1px solid #d7dfed;
    border-radius: 8px;
}
QFrame#InlineNotice {
    background: #f7f9fd;
    border: 1px solid #d9e3f0;
    border-radius: 8px;
}
QLabel#BrandTitle {
    font-size: 18px;
    font-weight: 700;
}
QLabel#SidebarCaption {
    color: #5d6b82;
    font-size: 12px;
}
QLabel#PageTitle {
    font-size: 22px;
    font-weight: 700;
}
QLabel#PageSubtitle {
    color: #617086;
    font-size: 12px;
}
QLabel#SectionTitle {
    font-size: 15px;
    font-weight: 700;
}
QLabel#SectionSubtitle {
    color: #617086;
    font-size: 12px;
}
QLabel#FieldHelp {
    color: #738198;
    font-size: 12px;
}
QLabel#MutedText {
    color: #76859c;
}
QLabel#StatusBadge {
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}
QLabel[badgeKind="neutral"] {
    color: #415067;
    background: #e9eef6;
}
QLabel[badgeKind="success"] {
    color: #15603b;
    background: #dff5e9;
}
QLabel[badgeKind="warning"] {
    color: #8a5b00;
    background: #fff1cf;
}
QLabel[badgeKind="danger"] {
    color: #8d2432;
    background: #fde5e8;
}
QLabel[badgeKind="info"] {
    color: #1857ad;
    background: #e4efff;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d5dfed;
    border-radius: 8px;
    padding: 7px 14px;
}
QPushButton:hover {
    background: #f5f8fd;
}
QPushButton:pressed {
    background: #ecf2fb;
}
QPushButton[variant="primary"] {
    background: #2f6fed;
    color: #ffffff;
    border: 1px solid #2f6fed;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover {
    background: #245fd2;
}
QPushButton[variant="ghost"] {
    background: transparent;
}
QPushButton[segment="true"] {
    border-radius: 8px;
    padding: 6px 12px;
}
QPushButton[segment="true"][active="true"] {
    background: #e7f0ff;
    border: 1px solid #8fb3ef;
    color: #1b54b1;
    font-weight: 600;
}
QLineEdit, QComboBox, QDateEdit, QPlainTextEdit, QTextEdit, QListWidget, QTabWidget::pane {
    background: #ffffff;
    border: 1px solid #d7e0ec;
    border-radius: 8px;
}
QLineEdit, QComboBox, QDateEdit {
    padding: 7px 10px;
    min-height: 18px;
}
QPlainTextEdit, QTextEdit {
    padding: 8px;
}
QListWidget {
    padding: 6px;
}
QListWidget::item {
    border-radius: 8px;
    padding: 8px;
    margin: 2px 0px;
}
QListWidget::item:selected {
    background: #e8f0ff;
    color: #183f7a;
}
QTabBar::tab {
    padding: 8px 12px;
    border: none;
    margin-right: 8px;
    color: #637287;
}
QTabBar::tab:selected {
    color: #1d4fab;
    border-bottom: 2px solid #2f6fed;
    font-weight: 600;
}
QScrollArea {
    border: none;
    background: transparent;
}
"""


TRANSLATIONS = {
    "zh": {
        "window_title": "WeChatDigestWindows",
        "brand_caption": "中文优先的微信摘要桌面工具",
        "header_subtitle": "本地数据库解密、聊天筛选、跨日期摘要与报告浏览",
        "nav_workbench": "工作台",
        "nav_setup": "数据源",
        "nav_reports": "历史输出",
        "nav_logs": "运行日志",
        "nav_settings": "设置",
        "page_workbench_title": "工作台",
        "page_workbench_subtitle": "选择聊天、配置时间范围，并在右侧直接查看摘要结果。",
        "page_setup_title": "数据源与模型",
        "page_setup_subtitle": "先完成本地数据目录和模型配置，再回到工作台生成摘要。",
        "page_reports_title": "历史输出",
        "page_reports_subtitle": "浏览已生成的 Markdown 报告，支持快速预览和打开目录。",
        "page_logs_title": "运行日志",
        "page_logs_subtitle": "查看应用状态流与最近一次技术日志，便于排查失败原因。",
        "page_settings_title": "设置",
        "page_settings_subtitle": "语言、界面规则和 PySide6 落地说明。",
        "header_status_ready": "准备就绪",
        "header_status_loading": "处理中",
        "header_status_success": "已完成",
        "header_status_error": "发生错误",
        "header_status_cached": "缓存命中",
        "refresh_sessions": "刷新会话",
        "open_output_folder": "打开输出目录",
        "workbench_sessions_title": "会话浏览",
        "workbench_sessions_subtitle": "左侧优先展示会话名，标识符作为辅助信息。",
        "workbench_groups": "群聊",
        "workbench_dms": "单聊",
        "search_sessions": "搜索群聊、单聊或最后一条消息",
        "session_count": "{count} 个会话",
        "no_sessions": "暂无可显示会话。请先完成数据源配置并刷新。",
        "job_config_title": "摘要任务",
        "job_config_subtitle": "单日与多日范围都放在主流程里，不需要再进高级模式。",
        "target_session": "目标会话",
        "no_session_selected": "尚未选择会话",
        "date_scope": "时间范围",
        "single_day": "单日",
        "date_range": "多日范围",
        "date": "日期",
        "start_date": "开始日期",
        "end_date": "结束日期",
        "since": "起始时刻",
        "since_placeholder": "可选，格式 HH:MM，仅单日模式生效",
        "output_path": "输出位置",
        "choose_output": "选择单日文件",
        "range_output_hint": "多日模式会按每天一个 Markdown 文件输出到当前摘要目录。",
        "segment": "按时间段分段摘要",
        "segment_help": "适合消息量大的会话，便于结构化阅读。",
        "full": "使用完整消息",
        "full_help": "关闭压缩去重，适合高保真回看。",
        "batch": "使用批量推理",
        "batch_help": "已配置批量端点时可降低成本。",
        "report_full": "附带聊天详情",
        "report_full_help": "把更多聊天原文拼进报告，输出体积会更大。",
        "generate_summary": "生成摘要",
        "summary_running": "正在生成摘要，请稍候…",
        "results_title": "摘要结果",
        "results_subtitle": "人类可读报告与技术日志分开展示。",
        "result_tab_report": "报告预览",
        "result_tab_log": "任务日志",
        "report_empty": "还没有摘要结果。选择会话后点击“生成摘要”，结果会显示在这里。",
        "reports_title": "报告列表",
        "reports_subtitle": "按最近修改时间排序。",
        "report_preview_title": "报告预览",
        "report_preview_subtitle": "适合挑选要导出或截图的版本。",
        "no_reports": "还没有找到任何 Markdown 报告。",
        "open_report_folder": "打开该报告所在目录",
        "setup_onboarding_title": "首次启动指引",
        "setup_onboarding_body": (
            "1. 先定位微信数据库目录。\n"
            "2. 再填写模型提供方、API Key 与输出目录。\n"
            "3. 保存后测试 API，必要时执行数据库解密。\n"
            "4. 回到工作台选择会话与日期范围。"
        ),
        "source_card_title": "微信数据源",
        "source_card_subtitle": "用于定位本地微信数据库，并确认解密后的数据存放位置。",
        "db_directory": "微信数据库目录",
        "db_help": "一般可以先点“自动检测”，再手动修正。",
        "auto_detect": "自动检测",
        "decrypted_dir": "解密输出目录",
        "decrypted_help": "数据库解密后的副本会写到这里，不建议公开分享。",
        "detect_decrypt": "解密数据库",
        "provider_card_title": "模型与接口",
        "provider_card_subtitle": "默认推荐豆包；其余 OpenAI 兼容接口也可直接切换。",
        "provider": "模型供应商",
        "provider_help": "推荐先用豆包默认配置，再按需要切换 OpenRouter、SiliconFlow、Ollama 等。",
        "model": "模型名称",
        "model_help": "可用默认值，也可以手动填写兼容模型名。",
        "base_url": "Base URL",
        "base_url_help": "Custom 或 OpenAI 兼容接口时按服务商说明填写。",
        "api_key": "API Key",
        "api_key_help": "只保存在本机 `%USERPROFILE%\\.wechat-digest\\llm_config.json`。",
        "batch_endpoint": "批量推理端点",
        "batch_endpoint_help": "可选配置；未填写时不会启用批量模式。",
        "batch_api_key": "批量推理 Key",
        "batch_api_key_help": "仅在批量推理服务需要独立密钥时填写。",
        "output_card_title": "输出与隐私",
        "output_card_subtitle": "把报告、截图、发布素材和隐私边界讲清楚。",
        "output_dir": "摘要输出目录",
        "output_help": "报告页会直接读取这个目录下的 Markdown 文件。",
        "privacy_notice_title": "隐私提醒",
        "privacy_notice_body": "不要把 output、解密后的数据库、.env、API Key 或任何真实聊天截图提交到公开仓库。",
        "save_settings": "保存设置",
        "test_api": "测试 API",
        "logs_state_title": "应用状态",
        "logs_state_subtitle": "保存设置、检测目录、摘要完成等高层状态会写在这里。",
        "logs_run_title": "技术日志",
        "logs_run_subtitle": "最近一次会话刷新、测试 API 或摘要任务的原始日志。",
        "settings_language_title": "语言与界面",
        "settings_language_subtitle": "默认中文；英文作为辅助语言选项保留。",
        "language": "界面语言",
        "language_help": "建议发布版默认中文，英文面向补充说明场景。",
        "settings_design_title": "设计落地说明",
        "settings_design_subtitle": "这次改版围绕 PySide6 桌面工具的实现边界。",
        "design_rule_1": "侧边栏 App Shell 对应 `QListWidget` 导航 + `QStackedWidget` 页面栈。",
        "design_rule_2": "卡片式信息分组用轻边框与低圆角，不引入营销页式大面积装饰。",
        "design_rule_3": "工作台保持三栏：会话列表、任务配置、报告/日志结果。",
        "choose_summary_output": "选择摘要输出文件",
        "markdown_filter": "Markdown 文件 (*.md)",
        "status_loaded_config": "已加载配置：{count} 个已知映射，已有 {reports} 份报告。",
        "status_settings_saved": "设置已保存。",
        "status_detected_db": "已检测到数据库目录：{value}",
        "status_no_db": "未检测到数据库目录，请手动选择。",
        "status_api_done": "API 测试完成。",
        "status_decrypt_done": "解密完成：{payload}",
        "status_summary_written": "摘要已写入：{path}",
        "status_range_done": "已生成 {count} 天摘要，输出目录：{path}",
        "status_reports_loaded": "已载入 {count} 份报告。",
        "status_reports_empty": "当前输出目录下还没有报告。",
        "status_refreshing_sessions": "正在刷新会话列表…",
        "status_testing_api": "正在测试 API…",
        "status_decrypting": "正在执行数据库解密…",
        "status_generating": "正在生成摘要…",
        "status_loading_reports": "正在读取历史报告…",
        "task_failed": "任务失败",
        "no_session_title": "未选择会话",
        "no_session_body": "请先在左侧选择一个群聊或单聊。",
        "report_read_error": "无法读取报告：{path}",
    },
    "en": {
        "window_title": "WeChatDigestWindows",
        "brand_caption": "Chinese-first desktop utility for WeChat summaries",
        "header_subtitle": "Local DB decrypt, chat filtering, cross-date summaries, and report browsing.",
        "nav_workbench": "Workbench",
        "nav_setup": "Data Source",
        "nav_reports": "Reports",
        "nav_logs": "Logs",
        "nav_settings": "Settings",
        "page_workbench_title": "Workbench",
        "page_workbench_subtitle": "Choose a chat, configure time scope, and inspect the generated report on the right.",
        "page_setup_title": "Data Source and Model",
        "page_setup_subtitle": "Finish local data and model setup here before running summaries.",
        "page_reports_title": "Reports",
        "page_reports_subtitle": "Browse generated Markdown reports and open their folders quickly.",
        "page_logs_title": "Run Logs",
        "page_logs_subtitle": "Review app-level state messages and the latest technical log output.",
        "page_settings_title": "Settings",
        "page_settings_subtitle": "Language, UI rules, and PySide6 implementation notes.",
        "header_status_ready": "Ready",
        "header_status_loading": "Working",
        "header_status_success": "Completed",
        "header_status_error": "Error",
        "header_status_cached": "Cache Hit",
        "refresh_sessions": "Refresh Sessions",
        "open_output_folder": "Open Output Folder",
        "workbench_sessions_title": "Session Browser",
        "workbench_sessions_subtitle": "Readable names first, identifiers only as supporting metadata.",
        "workbench_groups": "Groups",
        "workbench_dms": "Direct Messages",
        "search_sessions": "Search chat name, DM, or last message",
        "session_count": "{count} sessions",
        "no_sessions": "No sessions available yet. Finish setup and refresh first.",
        "job_config_title": "Summary Job",
        "job_config_subtitle": "Single-day and date-range modes are both first-class controls.",
        "target_session": "Target Session",
        "no_session_selected": "No session selected",
        "date_scope": "Time Scope",
        "single_day": "Single Day",
        "date_range": "Date Range",
        "date": "Date",
        "start_date": "Start Date",
        "end_date": "End Date",
        "since": "Since",
        "since_placeholder": "Optional HH:MM, single-day mode only",
        "output_path": "Output",
        "choose_output": "Choose Single-Day File",
        "range_output_hint": "Range mode writes one Markdown file per day into the active output directory.",
        "segment": "Segment by time window",
        "segment_help": "Useful for large chats and more structured reading.",
        "full": "Use full messages",
        "full_help": "Disables compression and dedupe for higher fidelity output.",
        "batch": "Use batch inference",
        "batch_help": "Available when a batch endpoint has been configured.",
        "report_full": "Include chat details",
        "report_full_help": "Appends more raw chat context into the final report.",
        "generate_summary": "Generate Summary",
        "summary_running": "Generating summary, please wait…",
        "results_title": "Summary Result",
        "results_subtitle": "Human-readable report and technical log are shown separately.",
        "result_tab_report": "Report Preview",
        "result_tab_log": "Task Log",
        "report_empty": "No summary result yet. Select a session and click Generate Summary.",
        "reports_title": "Report List",
        "reports_subtitle": "Sorted by most recent modified time.",
        "report_preview_title": "Report Preview",
        "report_preview_subtitle": "Useful for deciding which version to export or screenshot.",
        "no_reports": "No Markdown reports found yet.",
        "open_report_folder": "Open This Report Folder",
        "setup_onboarding_title": "First-Run Guide",
        "setup_onboarding_body": (
            "1. Locate the local WeChat database directory.\n"
            "2. Enter model provider settings, API key, and output path.\n"
            "3. Save settings, test API, and decrypt if needed.\n"
            "4. Return to Workbench and choose a chat plus date range."
        ),
        "source_card_title": "WeChat Data Source",
        "source_card_subtitle": "Locate the local database and choose where decrypted copies should live.",
        "db_directory": "WeChat DB Directory",
        "db_help": "Start with Auto Detect, then adjust manually if needed.",
        "auto_detect": "Auto Detect",
        "decrypted_dir": "Decrypted Output Dir",
        "decrypted_help": "This holds decrypted database copies and should not be published.",
        "detect_decrypt": "Decrypt Databases",
        "provider_card_title": "Model and Endpoint",
        "provider_card_subtitle": "Doubao is the recommended default; OpenAI-compatible services can be swapped in directly.",
        "provider": "Model Provider",
        "provider_help": "Start with Doubao defaults, then switch to OpenRouter, SiliconFlow, Ollama, or Custom if needed.",
        "model": "Model",
        "model_help": "Default values are fine to start; override only if your provider requires it.",
        "base_url": "Base URL",
        "base_url_help": "Fill this for Custom or other OpenAI-compatible providers.",
        "api_key": "API Key",
        "api_key_help": "Stored only in `%USERPROFILE%\\.wechat-digest\\llm_config.json` on this machine.",
        "batch_endpoint": "Batch Endpoint",
        "batch_endpoint_help": "Optional. Batch mode stays off when this is empty.",
        "batch_api_key": "Batch API Key",
        "batch_api_key_help": "Only needed when your batch service uses a separate credential.",
        "output_card_title": "Output and Privacy",
        "output_card_subtitle": "Keep report location, publishing assets, and privacy boundaries explicit.",
        "output_dir": "Summary Output Dir",
        "output_help": "The Reports page reads Markdown files from this directory.",
        "privacy_notice_title": "Privacy Notice",
        "privacy_notice_body": "Do not commit output, decrypted databases, .env files, API keys, or screenshots with real chat content.",
        "save_settings": "Save Settings",
        "test_api": "Test API",
        "logs_state_title": "Application State",
        "logs_state_subtitle": "High-level events like settings save, DB detection, and completed summaries appear here.",
        "logs_run_title": "Technical Log",
        "logs_run_subtitle": "Raw output from the latest refresh, API test, or summary run appears here.",
        "settings_language_title": "Language and UI",
        "settings_language_subtitle": "Chinese by default, English kept as a secondary option.",
        "language": "Language",
        "language_help": "Recommended release default is Chinese.",
        "settings_design_title": "Design Handoff Notes",
        "settings_design_subtitle": "This redesign stays within the current PySide6 desktop implementation boundary.",
        "design_rule_1": "Sidebar app shell maps to `QListWidget` navigation plus a `QStackedWidget` content stack.",
        "design_rule_2": "Cards use light borders and low-radius surfaces instead of marketing-style decoration.",
        "design_rule_3": "Workbench stays three-zone: sessions, job config, and report/log results.",
        "choose_summary_output": "Choose Summary Output",
        "markdown_filter": "Markdown (*.md)",
        "status_loaded_config": "Loaded config: {count} known mappings and {reports} reports.",
        "status_settings_saved": "Settings saved.",
        "status_detected_db": "Detected DB directory: {value}",
        "status_no_db": "No DB directory detected. Please choose it manually.",
        "status_api_done": "API test finished.",
        "status_decrypt_done": "Decrypt finished: {payload}",
        "status_summary_written": "Summary written to: {path}",
        "status_range_done": "Generated {count} daily summaries. Output folder: {path}",
        "status_reports_loaded": "Loaded {count} reports.",
        "status_reports_empty": "No reports found in the current output directory.",
        "status_refreshing_sessions": "Refreshing sessions…",
        "status_testing_api": "Testing API…",
        "status_decrypting": "Decrypting databases…",
        "status_generating": "Generating summary…",
        "status_loading_reports": "Loading reports…",
        "task_failed": "Task Failed",
        "no_session_title": "No Session",
        "no_session_body": "Select a group or DM from the left first.",
        "report_read_error": "Unable to read report: {path}",
    },
}


PAGE_KEYS = ["workbench", "setup", "reports", "logs", "settings"]


class TaskSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class TaskRunner(QRunnable):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = TaskSignals()

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception as exc:  # pragma: no cover
            self.signals.failed.emit(f"{exc}\n\n{traceback.format_exc()}")
            return
        self.signals.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self, auto_bootstrap: bool = True):
        super().__init__()
        self.pool = QThreadPool.globalInstance()
        self.language = "zh"
        self.current_page = "workbench"
        self.current_mode_dm = False
        self.current_output_override = ""
        self.current_report_path = ""
        self.reports_cache = []
        self.provider_presets = backend.list_provider_presets()
        self.provider_map = {item["key"]: item for item in self.provider_presets}
        self._build_ui()
        self._apply_styles()
        if auto_bootstrap:
            self._load_state()
            self.refresh_sessions()
            self.refresh_reports()
        self._apply_language()

    def t(self, key: str, **kwargs) -> str:
        text = TRANSLATIONS[self.language].get(key, key)
        return text.format(**kwargs) if kwargs else text

    def _build_ui(self):
        self.setWindowTitle("WeChatDigestWindows")
        self.resize(1440, 920)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        self.content_root = QFrame()
        self.content_root.setObjectName("ContentRoot")
        content_layout = QVBoxLayout(self.content_root)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        header = self._build_header()
        content_layout.addWidget(header)

        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(self._build_workbench_page())
        self.page_stack.addWidget(self._build_setup_page())
        self.page_stack.addWidget(self._build_reports_page())
        self.page_stack.addWidget(self._build_logs_page())
        self.page_stack.addWidget(self._build_settings_page())
        content_layout.addWidget(self.page_stack, 1)

        root_layout.addWidget(self.content_root, 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Sidebar")
        frame.setFixedWidth(236)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        brand = QLabel("WeChatDigestWindows")
        brand.setObjectName("BrandTitle")
        layout.addWidget(brand)

        caption = QLabel()
        caption.setObjectName("SidebarCaption")
        caption.setWordWrap(True)
        self.brand_caption_label = caption
        layout.addWidget(caption)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        self.nav_list.setSpacing(2)
        self.nav_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.nav_list.currentRowChanged.connect(self._nav_changed)
        for key in PAGE_KEYS:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, key)
            self.nav_list.addItem(item)
        layout.addWidget(self.nav_list, 1)

        footer = QLabel("PySide6  ·  Local-first  ·  Windows")
        footer.setObjectName("SidebarCaption")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        return frame

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("HeaderBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)

        title_wrap = QVBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(4)
        self.page_title_label = QLabel()
        self.page_title_label.setObjectName("PageTitle")
        self.page_subtitle_label = QLabel()
        self.page_subtitle_label.setObjectName("PageSubtitle")
        self.page_subtitle_label.setWordWrap(True)
        title_wrap.addWidget(self.page_title_label)
        title_wrap.addWidget(self.page_subtitle_label)
        layout.addLayout(title_wrap, 1)

        self.header_badge = QLabel()
        self.header_badge.setObjectName("StatusBadge")
        layout.addWidget(self.header_badge, 0, Qt.AlignTop)

        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self._refresh_active_page)
        layout.addWidget(self.refresh_btn, 0, Qt.AlignTop)

        self.open_output_btn = QPushButton()
        self.open_output_btn.clicked.connect(self.open_output_folder)
        layout.addWidget(self.open_output_btn, 0, Qt.AlignTop)
        return frame

    def _card(self, title_obj: QLabel | None = None, subtitle_obj: QLabel | None = None, hero: bool = False):
        frame = QFrame()
        frame.setObjectName("HeroCard" if hero else "Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        if title_obj is not None:
            title_obj.setObjectName("SectionTitle")
            layout.addWidget(title_obj)
        if subtitle_obj is not None:
            subtitle_obj.setObjectName("SectionSubtitle")
            subtitle_obj.setWordWrap(True)
            layout.addWidget(subtitle_obj)
        return frame, layout

    def _field_stack(self, widget: QWidget, help_label: QLabel | None = None) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(widget)
        if help_label is not None:
            help_label.setObjectName("FieldHelp")
            help_label.setWordWrap(True)
            layout.addWidget(help_label)
        return wrapper

    def _build_workbench_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_card, left_layout = self._card(QLabel(), QLabel())
        self.sessions_title_label = left_card.layout().itemAt(0).widget()
        self.sessions_subtitle_label = left_card.layout().itemAt(1).widget()
        left_layout.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.group_mode_btn = QPushButton()
        self.group_mode_btn.clicked.connect(lambda: self._set_session_mode(False))
        self.group_mode_btn.setProperty("segment", "true")
        mode_row.addWidget(self.group_mode_btn)
        self.dm_mode_btn = QPushButton()
        self.dm_mode_btn.clicked.connect(lambda: self._set_session_mode(True))
        self.dm_mode_btn.setProperty("segment", "true")
        mode_row.addWidget(self.dm_mode_btn)
        left_layout.addLayout(mode_row)

        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._filter_sessions)
        left_layout.addWidget(self.search_edit)

        self.session_count_label = QLabel()
        self.session_count_label.setObjectName("MutedText")
        left_layout.addWidget(self.session_count_label)

        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(self._session_changed)
        left_layout.addWidget(self.session_list, 1)

        self.sessions_empty_label = QLabel()
        self.sessions_empty_label.setWordWrap(True)
        self.sessions_empty_label.setObjectName("MutedText")
        left_layout.addWidget(self.sessions_empty_label)

        splitter.addWidget(left_card)

        center_card, center_layout = self._card(QLabel(), QLabel())
        self.job_title_label = center_card.layout().itemAt(0).widget()
        self.job_subtitle_label = center_card.layout().itemAt(1).widget()
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.target_name_label = QLabel()
        self.target_name_label.setWordWrap(True)
        self.target_name_label.setObjectName("SectionSubtitle")
        self.workbench_labels = {}

        def add_row(key: str, widget: QWidget):
            label = QLabel()
            self.workbench_labels[key] = label
            form.addRow(label, widget)

        add_row("target_session", self.target_name_label)

        scope_widget = QWidget()
        scope_layout = QHBoxLayout(scope_widget)
        scope_layout.setContentsMargins(0, 0, 0, 0)
        scope_layout.setSpacing(8)
        self.single_day_btn = QPushButton()
        self.single_day_btn.clicked.connect(lambda: self._set_date_mode(False))
        self.single_day_btn.setProperty("segment", "true")
        scope_layout.addWidget(self.single_day_btn)
        self.range_day_btn = QPushButton()
        self.range_day_btn.clicked.connect(lambda: self._set_date_mode(True))
        self.range_day_btn.setProperty("segment", "true")
        scope_layout.addWidget(self.range_day_btn)
        scope_layout.addStretch(1)
        add_row("date_scope", scope_widget)

        default_date = QDate.fromString(backend.default_summary_date(), "yyyy-MM-dd")
        if not default_date.isValid():
            default_date = QDate.currentDate().addDays(-1)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(default_date)
        self.date_edit.dateChanged.connect(self._single_date_changed)
        add_row("date", self.date_edit)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(default_date)
        self.start_date_edit.dateChanged.connect(self.update_output_preview)
        add_row("start_date", self.start_date_edit)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(default_date)
        self.end_date_edit.dateChanged.connect(self.update_output_preview)
        add_row("end_date", self.end_date_edit)

        self.since_help = QLabel()
        self.since_edit = QLineEdit()
        self.since_edit.textChanged.connect(self.update_output_preview)
        add_row("since", self._field_stack(self.since_edit, self.since_help))

        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(8)
        output_layout.addWidget(self.output_edit)
        self.range_hint_label = QLabel()
        self.range_hint_label.setObjectName("FieldHelp")
        self.range_hint_label.setWordWrap(True)
        output_layout.addWidget(self.range_hint_label)
        add_row("output_path", output_widget)

        self.segment_check = QCheckBox()
        self.segment_help = QLabel()
        add_row("segment", self._field_stack(self.segment_check, self.segment_help))

        self.full_check = QCheckBox()
        self.full_help = QLabel()
        add_row("full", self._field_stack(self.full_check, self.full_help))

        self.batch_check = QCheckBox()
        self.batch_help = QLabel()
        add_row("batch", self._field_stack(self.batch_check, self.batch_help))

        self.report_full_check = QCheckBox()
        self.report_full_help = QLabel()
        add_row("report_full", self._field_stack(self.report_full_check, self.report_full_help))

        center_layout.addLayout(form)

        button_row = QHBoxLayout()
        self.choose_output_btn = QPushButton()
        self.choose_output_btn.clicked.connect(self.choose_output_file)
        button_row.addWidget(self.choose_output_btn)
        self.generate_btn = QPushButton()
        self.generate_btn.setProperty("variant", "primary")
        self.generate_btn.clicked.connect(self.run_summary)
        button_row.addWidget(self.generate_btn)
        center_layout.addLayout(button_row)
        center_layout.addStretch(1)
        splitter.addWidget(center_card)

        right_card, right_layout = self._card(QLabel(), QLabel())
        self.results_title_label = right_card.layout().itemAt(0).widget()
        self.results_subtitle_label = right_card.layout().itemAt(1).widget()
        self.result_tabs = QTabWidget()
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.run_log = QPlainTextEdit()
        self.run_log.setReadOnly(True)
        self.result_tabs.addTab(self.report_view, "")
        self.result_tabs.addTab(self.run_log, "")
        right_layout.addWidget(self.result_tabs, 1)
        splitter.addWidget(right_card)

        splitter.setSizes([300, 420, 560])
        layout.addWidget(splitter, 1)

        self.current_mode_dm = False
        self.group_mode_btn.setProperty("active", "true")
        self.dm_mode_btn.setProperty("active", "false")
        self.single_day_btn.setProperty("active", "true")
        self.range_day_btn.setProperty("active", "false")
        return page

    def _build_setup_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(24, 24, 24, 24)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        onboarding_card, onboarding_layout = self._card(QLabel(), None, hero=True)
        self.setup_onboarding_title = onboarding_card.layout().itemAt(0).widget()
        self.setup_onboarding_body = QLabel()
        self.setup_onboarding_body.setWordWrap(True)
        onboarding_layout.addWidget(self.setup_onboarding_body)
        layout.addWidget(onboarding_card)

        source_card, source_layout = self._card(QLabel(), QLabel())
        self.source_title = source_card.layout().itemAt(0).widget()
        self.source_subtitle = source_card.layout().itemAt(1).widget()
        source_form = QFormLayout()
        source_form.setSpacing(12)
        self.setup_labels = {}

        def add_setup_row(key: str, widget: QWidget):
            label = QLabel()
            self.setup_labels[key] = label
            source_form.addRow(label, widget)

        self.db_dir_edit = QLineEdit()
        self.db_help = QLabel()
        db_row = QWidget()
        db_layout = QVBoxLayout(db_row)
        db_layout.setContentsMargins(0, 0, 0, 0)
        db_layout.setSpacing(8)
        db_inline = QWidget()
        db_inline_layout = QHBoxLayout(db_inline)
        db_inline_layout.setContentsMargins(0, 0, 0, 0)
        db_inline_layout.setSpacing(8)
        db_inline_layout.addWidget(self.db_dir_edit, 1)
        self.detect_btn = QPushButton()
        self.detect_btn.clicked.connect(self.detect_db_dir)
        db_inline_layout.addWidget(self.detect_btn)
        db_layout.addWidget(db_inline)
        db_layout.addWidget(self.db_help)
        add_setup_row("db_directory", db_row)

        self.decrypted_dir_edit = QLineEdit()
        self.decrypted_help = QLabel()
        add_setup_row("decrypted_dir", self._field_stack(self.decrypted_dir_edit, self.decrypted_help))
        source_layout.addLayout(source_form)

        source_actions = QHBoxLayout()
        source_actions.addStretch(1)
        self.decrypt_btn = QPushButton()
        self.decrypt_btn.clicked.connect(self.decrypt_databases)
        source_actions.addWidget(self.decrypt_btn)
        source_layout.addLayout(source_actions)
        layout.addWidget(source_card)

        provider_card, provider_layout = self._card(QLabel(), QLabel())
        self.provider_title = provider_card.layout().itemAt(0).widget()
        self.provider_subtitle = provider_card.layout().itemAt(1).widget()
        provider_form = QFormLayout()
        provider_form.setSpacing(12)
        self.provider_labels = {}

        def add_provider_row(key: str, widget: QWidget):
            label = QLabel()
            self.provider_labels[key] = label
            provider_form.addRow(label, widget)

        self.provider_combo = QComboBox()
        for item in self.provider_presets:
            self.provider_combo.addItem(item["label"], item["key"])
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)
        self.provider_help_label = QLabel()
        add_provider_row("provider", self._field_stack(self.provider_combo, self.provider_help_label))

        self.model_edit = QLineEdit()
        self.model_help = QLabel()
        add_provider_row("model", self._field_stack(self.model_edit, self.model_help))

        self.base_url_edit = QLineEdit()
        self.base_url_help = QLabel()
        add_provider_row("base_url", self._field_stack(self.base_url_edit, self.base_url_help))

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_help = QLabel()
        add_provider_row("api_key", self._field_stack(self.api_key_edit, self.api_key_help))

        self.batch_endpoint_edit = QLineEdit()
        self.batch_endpoint_help = QLabel()
        add_provider_row("batch_endpoint", self._field_stack(self.batch_endpoint_edit, self.batch_endpoint_help))

        self.batch_api_key_edit = QLineEdit()
        self.batch_api_key_edit.setEchoMode(QLineEdit.Password)
        self.batch_api_key_help = QLabel()
        add_provider_row("batch_api_key", self._field_stack(self.batch_api_key_edit, self.batch_api_key_help))

        provider_layout.addLayout(provider_form)
        provider_actions = QHBoxLayout()
        provider_actions.addStretch(1)
        self.test_btn = QPushButton()
        self.test_btn.clicked.connect(self.test_api)
        provider_actions.addWidget(self.test_btn)
        provider_layout.addLayout(provider_actions)
        layout.addWidget(provider_card)

        output_card, output_layout = self._card(QLabel(), QLabel())
        self.output_title = output_card.layout().itemAt(0).widget()
        self.output_subtitle = output_card.layout().itemAt(1).widget()
        output_form = QFormLayout()
        output_form.setSpacing(12)
        self.output_labels = {}

        def add_output_row(key: str, widget: QWidget):
            label = QLabel()
            self.output_labels[key] = label
            output_form.addRow(label, widget)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.textChanged.connect(self.update_output_preview)
        self.output_help = QLabel()
        add_output_row("output_dir", self._field_stack(self.output_dir_edit, self.output_help))
        output_layout.addLayout(output_form)

        self.privacy_notice = QFrame()
        self.privacy_notice.setObjectName("InlineNotice")
        privacy_layout = QVBoxLayout(self.privacy_notice)
        privacy_layout.setContentsMargins(14, 14, 14, 14)
        privacy_layout.setSpacing(8)
        self.privacy_title = QLabel()
        self.privacy_title.setObjectName("SectionTitle")
        privacy_layout.addWidget(self.privacy_title)
        self.privacy_body = QLabel()
        self.privacy_body.setWordWrap(True)
        self.privacy_body.setObjectName("FieldHelp")
        privacy_layout.addWidget(self.privacy_body)
        output_layout.addWidget(self.privacy_notice)

        output_actions = QHBoxLayout()
        self.save_btn = QPushButton()
        self.save_btn.setProperty("variant", "primary")
        self.save_btn.clicked.connect(self.save_state)
        output_actions.addWidget(self.save_btn)
        output_actions.addStretch(1)
        output_layout.addLayout(output_actions)
        layout.addWidget(output_card)

        layout.addStretch(1)
        return page

    def _build_reports_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_card, left_layout = self._card(QLabel(), QLabel())
        self.reports_title_label = left_card.layout().itemAt(0).widget()
        self.reports_subtitle_label = left_card.layout().itemAt(1).widget()
        self.report_list = QListWidget()
        self.report_list.currentItemChanged.connect(self._report_changed)
        left_layout.addWidget(self.report_list, 1)
        self.reports_empty_label = QLabel()
        self.reports_empty_label.setWordWrap(True)
        self.reports_empty_label.setObjectName("MutedText")
        left_layout.addWidget(self.reports_empty_label)
        splitter.addWidget(left_card)

        right_card, right_layout = self._card(QLabel(), QLabel())
        self.report_preview_title = right_card.layout().itemAt(0).widget()
        self.report_preview_subtitle = right_card.layout().itemAt(1).widget()
        report_actions = QHBoxLayout()
        self.open_report_folder_btn = QPushButton()
        self.open_report_folder_btn.clicked.connect(self._open_selected_report_folder)
        report_actions.addWidget(self.open_report_folder_btn)
        report_actions.addStretch(1)
        right_layout.addLayout(report_actions)
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        right_layout.addWidget(self.report_preview, 1)
        splitter.addWidget(right_card)

        splitter.setSizes([340, 900])
        layout.addWidget(splitter, 1)
        return page

    def _build_logs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        state_card, state_layout = self._card(QLabel(), QLabel())
        self.logs_state_title = state_card.layout().itemAt(0).widget()
        self.logs_state_subtitle = state_card.layout().itemAt(1).widget()
        self.status_log = QPlainTextEdit()
        self.status_log.setReadOnly(True)
        state_layout.addWidget(self.status_log)
        layout.addWidget(state_card, 1)

        run_card, run_layout = self._card(QLabel(), QLabel())
        self.logs_run_title = run_card.layout().itemAt(0).widget()
        self.logs_run_subtitle = run_card.layout().itemAt(1).widget()
        self.global_run_log = QPlainTextEdit()
        self.global_run_log.setReadOnly(True)
        run_layout.addWidget(self.global_run_log)
        layout.addWidget(run_card, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        language_card, language_layout = self._card(QLabel(), QLabel())
        self.settings_language_title = language_card.layout().itemAt(0).widget()
        self.settings_language_subtitle = language_card.layout().itemAt(1).widget()
        language_form = QFormLayout()
        self.settings_labels = {}

        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", "zh")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.language_help = QLabel()
        self.language_help.setWordWrap(True)
        language_field = self._field_stack(self.language_combo, self.language_help)
        label = QLabel()
        self.settings_labels["language"] = label
        language_form.addRow(label, language_field)
        language_layout.addLayout(language_form)
        layout.addWidget(language_card)

        design_card, design_layout = self._card(QLabel(), QLabel())
        self.settings_design_title = design_card.layout().itemAt(0).widget()
        self.settings_design_subtitle = design_card.layout().itemAt(1).widget()
        self.design_rule_labels = []
        for _ in range(3):
            rule = QLabel()
            rule.setWordWrap(True)
            rule.setObjectName("FieldHelp")
            self.design_rule_labels.append(rule)
            design_layout.addWidget(rule)
        design_layout.addStretch(1)
        layout.addWidget(design_card)
        layout.addStretch(1)
        return page

    def _apply_styles(self):
        self.setStyleSheet(APP_STYLESHEET)

    def _apply_language(self):
        self.setWindowTitle(self.t("window_title"))
        self.brand_caption_label.setText(self.t("brand_caption"))
        self.refresh_btn.setText(self.t("refresh_sessions"))
        self.open_output_btn.setText(self.t("open_output_folder"))

        nav_map = {
            "workbench": "nav_workbench",
            "setup": "nav_setup",
            "reports": "nav_reports",
            "logs": "nav_logs",
            "settings": "nav_settings",
        }
        for idx in range(self.nav_list.count()):
            item = self.nav_list.item(idx)
            item.setText(self.t(nav_map[item.data(Qt.UserRole)]))

        self._apply_header_copy()

        self.sessions_title_label.setText(self.t("workbench_sessions_title"))
        self.sessions_subtitle_label.setText(self.t("workbench_sessions_subtitle"))
        self.group_mode_btn.setText(self.t("workbench_groups"))
        self.dm_mode_btn.setText(self.t("workbench_dms"))
        self.search_edit.setPlaceholderText(self.t("search_sessions"))
        self.sessions_empty_label.setText(self.t("no_sessions"))
        self.job_title_label.setText(self.t("job_config_title"))
        self.job_subtitle_label.setText(self.t("job_config_subtitle"))
        self.workbench_labels["target_session"].setText(self.t("target_session"))
        self.workbench_labels["date_scope"].setText(self.t("date_scope"))
        self.workbench_labels["date"].setText(self.t("date"))
        self.workbench_labels["start_date"].setText(self.t("start_date"))
        self.workbench_labels["end_date"].setText(self.t("end_date"))
        self.workbench_labels["since"].setText(self.t("since"))
        self.workbench_labels["output_path"].setText(self.t("output_path"))
        self.workbench_labels["segment"].setText("")
        self.workbench_labels["full"].setText("")
        self.workbench_labels["batch"].setText("")
        self.workbench_labels["report_full"].setText("")
        self.single_day_btn.setText(self.t("single_day"))
        self.range_day_btn.setText(self.t("date_range"))
        self.since_edit.setPlaceholderText(self.t("since_placeholder"))
        self.range_hint_label.setText(self.t("range_output_hint"))
        self.segment_check.setText(self.t("segment"))
        self.segment_help.setText(self.t("segment_help"))
        self.full_check.setText(self.t("full"))
        self.full_help.setText(self.t("full_help"))
        self.batch_check.setText(self.t("batch"))
        self.batch_help.setText(self.t("batch_help"))
        self.report_full_check.setText(self.t("report_full"))
        self.report_full_help.setText(self.t("report_full_help"))
        self.choose_output_btn.setText(self.t("choose_output"))
        self.generate_btn.setText(self.t("generate_summary"))
        self.results_title_label.setText(self.t("results_title"))
        self.results_subtitle_label.setText(self.t("results_subtitle"))
        self.result_tabs.setTabText(0, self.t("result_tab_report"))
        self.result_tabs.setTabText(1, self.t("result_tab_log"))
        if not self.report_view.toPlainText().strip():
            self.report_view.setPlainText(self.t("report_empty"))

        self.setup_onboarding_title.setText(self.t("setup_onboarding_title"))
        self.setup_onboarding_body.setText(self.t("setup_onboarding_body"))
        self.source_title.setText(self.t("source_card_title"))
        self.source_subtitle.setText(self.t("source_card_subtitle"))
        self.setup_labels["db_directory"].setText(self.t("db_directory"))
        self.db_help.setText(self.t("db_help"))
        self.detect_btn.setText(self.t("auto_detect"))
        self.setup_labels["decrypted_dir"].setText(self.t("decrypted_dir"))
        self.decrypted_help.setText(self.t("decrypted_help"))
        self.decrypt_btn.setText(self.t("detect_decrypt"))

        self.provider_title.setText(self.t("provider_card_title"))
        self.provider_subtitle.setText(self.t("provider_card_subtitle"))
        self.provider_labels["provider"].setText(self.t("provider"))
        self.provider_help_label.setText(self.t("provider_help"))
        self.provider_labels["model"].setText(self.t("model"))
        self.model_help.setText(self.t("model_help"))
        self.provider_labels["base_url"].setText(self.t("base_url"))
        self.base_url_help.setText(self.t("base_url_help"))
        self.provider_labels["api_key"].setText(self.t("api_key"))
        self.api_key_help.setText(self.t("api_key_help"))
        self.provider_labels["batch_endpoint"].setText(self.t("batch_endpoint"))
        self.batch_endpoint_help.setText(self.t("batch_endpoint_help"))
        self.provider_labels["batch_api_key"].setText(self.t("batch_api_key"))
        self.batch_api_key_help.setText(self.t("batch_api_key_help"))
        self.test_btn.setText(self.t("test_api"))

        self.output_title.setText(self.t("output_card_title"))
        self.output_subtitle.setText(self.t("output_card_subtitle"))
        self.output_labels["output_dir"].setText(self.t("output_dir"))
        self.output_help.setText(self.t("output_help"))
        self.privacy_title.setText(self.t("privacy_notice_title"))
        self.privacy_body.setText(self.t("privacy_notice_body"))
        self.save_btn.setText(self.t("save_settings"))

        self.reports_title_label.setText(self.t("reports_title"))
        self.reports_subtitle_label.setText(self.t("reports_subtitle"))
        self.reports_empty_label.setText(self.t("no_reports"))
        self.report_preview_title.setText(self.t("report_preview_title"))
        self.report_preview_subtitle.setText(self.t("report_preview_subtitle"))
        self.open_report_folder_btn.setText(self.t("open_report_folder"))
        if not self.report_preview.toPlainText().strip():
            self.report_preview.setPlainText(self.t("no_reports"))

        self.logs_state_title.setText(self.t("logs_state_title"))
        self.logs_state_subtitle.setText(self.t("logs_state_subtitle"))
        self.logs_run_title.setText(self.t("logs_run_title"))
        self.logs_run_subtitle.setText(self.t("logs_run_subtitle"))

        self.settings_language_title.setText(self.t("settings_language_title"))
        self.settings_language_subtitle.setText(self.t("settings_language_subtitle"))
        self.settings_labels["language"].setText(self.t("language"))
        self.language_help.setText(self.t("language_help"))
        self.settings_design_title.setText(self.t("settings_design_title"))
        self.settings_design_subtitle.setText(self.t("settings_design_subtitle"))
        self.design_rule_labels[0].setText(self.t("design_rule_1"))
        self.design_rule_labels[1].setText(self.t("design_rule_2"))
        self.design_rule_labels[2].setText(self.t("design_rule_3"))

        if not self.target_name_label.text().strip():
            self.target_name_label.setText(self.t("no_session_selected"))
        self._update_session_mode_buttons()
        self._update_date_mode_buttons()
        self._update_session_count()

    def _apply_header_copy(self):
        title_key = f"page_{self.current_page}_title"
        subtitle_key = f"page_{self.current_page}_subtitle"
        self.page_title_label.setText(self.t(title_key))
        self.page_subtitle_label.setText(self.t(subtitle_key))

    def _set_header_status(self, key: str, kind: str):
        self.header_badge.setText(self.t(key))
        self.header_badge.setProperty("badgeKind", kind)
        self.header_badge.style().unpolish(self.header_badge)
        self.header_badge.style().polish(self.header_badge)

    def _nav_changed(self, index: int):
        if index < 0:
            return
        key = self.nav_list.item(index).data(Qt.UserRole)
        self.current_page = key
        self.page_stack.setCurrentIndex(index)
        self._apply_header_copy()
        if key == "reports":
            self.refresh_reports()

    def _append_status(self, text: str):
        if hasattr(self, "status_log"):
            self.status_log.appendPlainText(text)

    def _set_latest_run_log(self, text: str):
        if hasattr(self, "run_log"):
            self.run_log.setPlainText(text)
        if hasattr(self, "global_run_log"):
            self.global_run_log.setPlainText(text)

    def _load_state(self):
        state = backend.load_app_state()
        self.language = state.get("language", "zh")
        self.language_combo.setCurrentIndex(0 if self.language == "zh" else 1)
        self.db_dir_edit.setText(state["db_dir"])
        self.decrypted_dir_edit.setText(state["decrypted_dir"])
        self.output_dir_edit.setText(state["output_dir"])
        provider_key = state["provider"] if state["provider"] in self.provider_map else "custom"
        provider_index = self.provider_combo.findData(provider_key)
        self.provider_combo.setCurrentIndex(0 if provider_index < 0 else provider_index)
        self.model_edit.setText(state["model"])
        self.base_url_edit.setText(state["base_url"])
        self.api_key_edit.setText(state["api_key"])
        self.batch_endpoint_edit.setText(state["batch_endpoint"])
        self.batch_api_key_edit.setText(state["batch_api_key"])
        self._append_status(self.t("status_loaded_config", count=state["known_count"], reports=state["report_count"]))
        self._set_header_status("header_status_ready", "neutral")
        self._apply_language()
        self.nav_list.setCurrentRow(0)

    def _collect_state(self):
        preset = self.provider_map[self.provider_combo.currentData()]
        return {
            "db_dir": self.db_dir_edit.text(),
            "decrypted_dir": self.decrypted_dir_edit.text(),
            "output_dir": self.output_dir_edit.text(),
            "provider": preset["provider"],
            "model": self.model_edit.text(),
            "base_url": self.base_url_edit.text(),
            "api_key": self.api_key_edit.text(),
            "batch_endpoint": self.batch_endpoint_edit.text(),
            "batch_api_key": self.batch_api_key_edit.text(),
            "language": self.language,
        }

    def _submit(self, func, on_done, *args, on_fail=None, **kwargs):
        task = TaskRunner(func, *args, **kwargs)
        task.signals.finished.connect(on_done)
        task.signals.failed.connect(on_fail or self._task_failed)
        self.pool.start(task)

    def _task_failed(self, message):
        self._set_header_status("header_status_error", "danger")
        self._append_status(message)
        QMessageBox.critical(self, self.t("task_failed"), message)

    def _refresh_active_page(self):
        if self.current_page == "reports":
            self.refresh_reports()
        elif self.current_page == "logs":
            self.refresh_sessions()
            self.refresh_reports()
        else:
            self.refresh_sessions()

    def _provider_changed(self):
        preset = self.provider_map[self.provider_combo.currentData()]
        model_values = {item["model"] for item in self.provider_presets if item["model"]}
        url_values = {item["base_url"] for item in self.provider_presets if item["base_url"]}
        if not self.model_edit.text().strip() or self.model_edit.text().strip() in model_values:
            self.model_edit.setText(preset["model"])
        if not self.base_url_edit.text().strip() or self.base_url_edit.text().strip() in url_values:
            self.base_url_edit.setText(preset["base_url"])

    def _language_changed(self):
        self.language = self.language_combo.currentData() or "zh"
        self._apply_language()

    def _set_session_mode(self, include_dm: bool, refresh: bool = True):
        self.current_mode_dm = include_dm
        self._update_session_mode_buttons()
        if refresh:
            self.refresh_sessions()

    def _update_session_mode_buttons(self):
        self.group_mode_btn.setProperty("active", "true" if not self.current_mode_dm else "false")
        self.dm_mode_btn.setProperty("active", "true" if self.current_mode_dm else "false")
        for button in (self.group_mode_btn, self.dm_mode_btn):
            button.style().unpolish(button)
            button.style().polish(button)

    def _set_date_mode(self, is_range: bool):
        self.range_day_btn.setProperty("active", "true" if is_range else "false")
        self.single_day_btn.setProperty("active", "false" if is_range else "true")
        self._update_date_mode_buttons()
        self.start_date_edit.setEnabled(is_range)
        self.end_date_edit.setEnabled(is_range)
        self.date_edit.setEnabled(not is_range)
        self.since_edit.setEnabled(not is_range)
        self.choose_output_btn.setEnabled(not is_range)
        self.range_hint_label.setVisible(is_range)
        self.current_output_override = "" if is_range else self.current_output_override
        if hasattr(self, "output_dir_edit"):
            self.update_output_preview()

    def _update_date_mode_buttons(self):
        for button in (self.single_day_btn, self.range_day_btn):
            button.style().unpolish(button)
            button.style().polish(button)

    def _is_range_mode(self) -> bool:
        return self.range_day_btn.property("active") == "true"

    def detect_db_dir(self):
        self._set_header_status("header_status_loading", "info")
        self._append_status(self.t("status_refreshing_sessions"))
        self._submit(backend.detect_db_dir, self._db_detected)

    def _db_detected(self, value: str):
        if value:
            self.db_dir_edit.setText(value)
            self._append_status(self.t("status_detected_db", value=value))
            self._set_header_status("header_status_success", "success")
        else:
            self._append_status(self.t("status_no_db"))
            self._set_header_status("header_status_error", "warning")

    def save_state(self):
        backend.save_app_state(self._collect_state())
        self.current_output_override = ""
        self.update_output_preview()
        self.refresh_reports()
        self._append_status(self.t("status_settings_saved"))
        self._set_header_status("header_status_success", "success")

    def test_api(self):
        self.save_state()
        self._set_header_status("header_status_loading", "info")
        self._append_status(self.t("status_testing_api"))
        self._submit(backend.test_api, self._api_test_done)

    def _api_test_done(self, log_text: str):
        text = log_text.strip() or self.t("status_api_done")
        self._append_status(text)
        self._set_latest_run_log(text)
        self._set_header_status("header_status_success", "success")

    def decrypt_databases(self):
        self.save_state()
        self._set_header_status("header_status_loading", "info")
        self._append_status(self.t("status_decrypting"))
        self._submit(backend.decrypt_databases, self._decrypt_done)

    def _decrypt_done(self, result):
        payload, log_text = result
        if log_text.strip():
            self._append_status(log_text.strip())
            self._set_latest_run_log(log_text.strip())
        self._append_status(self.t("status_decrypt_done", payload=payload))
        self._set_header_status("header_status_success", "success")

    def refresh_sessions(self):
        self._set_header_status("header_status_loading", "info")
        self._append_status(self.t("status_refreshing_sessions"))
        self._submit(backend.list_sessions, self._sessions_loaded, self.current_mode_dm)

    def _session_label(self, session: dict) -> str:
        name = session.get("name") or session.get("username") or ""
        username = session.get("username") or ""
        label = name
        if username and name != username:
            label = f"{name}  <{username}>"
        if session.get("last_time"):
            label = f"{label}\n{session['last_time']}"
        return label

    def _sessions_loaded(self, result):
        sessions, log_text = result
        self.session_list.clear()
        for session in sessions:
            item = QListWidgetItem(self._session_label(session))
            item.setData(Qt.UserRole, session)
            self.session_list.addItem(item)
        if sessions:
            self.session_list.setCurrentRow(0)
            self._set_header_status("header_status_ready", "neutral")
        else:
            self.target_name_label.setText(self.t("no_session_selected"))
            self._set_header_status("header_status_error", "warning")
        self._update_session_count()
        self._set_latest_run_log(log_text.strip())
        self._filter_sessions()

    def _update_session_count(self, count: int | None = None):
        value = self.session_list.count() if count is None else count
        self.session_count_label.setText(self.t("session_count", count=value))

    def _filter_sessions(self):
        needle = self.search_edit.text().strip().lower()
        visible = 0
        for idx in range(self.session_list.count()):
            item = self.session_list.item(idx)
            session = item.data(Qt.UserRole)
            haystack = f"{session.get('name', '')} {session.get('username', '')} {session.get('last_msg', '')}".lower()
            hidden = bool(needle) and needle not in haystack
            item.setHidden(hidden)
            if not hidden:
                visible += 1
        self._update_session_count(visible)

    def _session_changed(self, current, _previous):
        if not current:
            self.target_name_label.setText(self.t("no_session_selected"))
            self.update_output_preview()
            return
        session = current.data(Qt.UserRole)
        name = session.get("name") or session.get("username") or ""
        username = session.get("username") or ""
        if username and name != username:
            self.target_name_label.setText(f"{name}\n{username}")
        else:
            self.target_name_label.setText(name)
        self.current_output_override = ""
        self.update_output_preview()

    def _selected_session_name(self) -> str:
        item = self.session_list.currentItem()
        if not item:
            return ""
        session = item.data(Qt.UserRole)
        return session.get("name") or session.get("username") or ""

    def _single_date_changed(self):
        self.current_output_override = ""
        self.update_output_preview()

    def update_output_preview(self):
        group_name = self._selected_session_name()
        if not group_name:
            self.output_edit.clear()
            return
        if self._is_range_mode():
            output_root = self.output_dir_edit.text().strip() or os.path.join(os.getcwd(), "output")
            self.output_edit.setText(output_root)
            return
        if self.current_output_override:
            self.output_edit.setText(self.current_output_override)
            return
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        try:
            path = backend.preview_output_path(group_name, date_str, self.since_edit.text())
        except Exception:
            path = ""
        self.output_edit.setText(path)

    def choose_output_file(self):
        start_dir = self.output_dir_edit.text().strip() or os.getcwd()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        selected, _ = QFileDialog.getSaveFileName(
            self,
            self.t("choose_summary_output"),
            os.path.join(start_dir, f"{date_str}.md"),
            self.t("markdown_filter"),
        )
        if selected:
            self.current_output_override = selected
            self.output_edit.setText(selected)

    def run_summary(self):
        self.save_state()
        group_name = self._selected_session_name()
        if not group_name:
            QMessageBox.warning(self, self.t("no_session_title"), self.t("no_session_body"))
            return
        self.report_view.setPlainText(self.t("summary_running"))
        self._set_latest_run_log("")
        self._set_header_status("header_status_loading", "info")
        self._append_status(self.t("status_generating"))
        common = {
            "segment": self.segment_check.isChecked(),
            "full": self.full_check.isChecked(),
            "batch_mode": self.batch_check.isChecked(),
            "report_full": self.report_full_check.isChecked(),
        }
        if self._is_range_mode():
            self._submit(
                backend.summarize_range,
                self._summary_done,
                group_name,
                self.start_date_edit.date().toString("yyyy-MM-dd"),
                self.end_date_edit.date().toString("yyyy-MM-dd"),
                **common,
            )
            return
        self._submit(
            backend.summarize_single,
            self._summary_done,
            group_name,
            self.date_edit.date().toString("yyyy-MM-dd"),
            since_text=self.since_edit.text().strip(),
            output_path=self.output_edit.text().strip() or None,
            **common,
        )

    def _summary_done(self, payload):
        log_text = payload["log"].strip()
        self._set_latest_run_log(log_text)
        if payload["mode"] == "range":
            self.report_view.setPlainText(payload["summary"])
            self.output_edit.setText(payload["output_path"])
            self._append_status(self.t("status_range_done", count=len(payload["generated_files"]), path=payload["output_path"]))
        else:
            self.output_edit.setText(payload["output_path"])
            self.report_view.setPlainText(payload["report"] or payload["summary"])
            self._append_status(self.t("status_summary_written", path=payload["output_path"]))
        if "[cache]" in log_text:
            self._set_header_status("header_status_cached", "info")
        else:
            self._set_header_status("header_status_success", "success")
        self.refresh_reports()

    def refresh_reports(self):
        self._append_status(self.t("status_loading_reports"))
        self._submit(backend.list_reports, self._reports_loaded)

    def _reports_loaded(self, reports):
        self.reports_cache = reports
        self.report_list.clear()
        for report in reports:
            item = QListWidgetItem(f"{report['relative_path']}\n{report['modified']}")
            item.setData(Qt.UserRole, report)
            self.report_list.addItem(item)
        if reports:
            self.report_list.setCurrentRow(0)
            self._append_status(self.t("status_reports_loaded", count=len(reports)))
        else:
            self.report_preview.setPlainText(self.t("no_reports"))
            self._append_status(self.t("status_reports_empty"))

    def _report_changed(self, current, _previous):
        if not current:
            return
        record = current.data(Qt.UserRole)
        self.current_report_path = record["path"]
        try:
            self.report_preview.setPlainText(backend.read_report(record["path"]))
        except Exception:
            self.report_preview.setPlainText(self.t("report_read_error", path=record["path"]))

    def _open_selected_report_folder(self):
        if not self.current_report_path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.current_report_path)))

    def open_output_folder(self):
        target = self.output_edit.text().strip() or self.output_dir_edit.text().strip() or backend.output_root()
        path = target if os.path.isdir(target) else os.path.dirname(target)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def launch(smoke_test: bool = False):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(auto_bootstrap=not smoke_test)
    window.show()
    if smoke_test:
        QTimer.singleShot(400, app.quit)
    return app.exec()
