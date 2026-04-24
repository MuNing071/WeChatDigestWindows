import os
import sys
import traceback

from PySide6.QtCore import QDate, QObject, QRunnable, QThreadPool, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import backend


TRANSLATIONS = {
    "zh": {
        "window_title": "WeChatDigestWindows",
        "toolbar_main": "主工具栏",
        "refresh_sessions": "刷新会话",
        "open_output_folder": "打开输出目录",
        "tab_setup": "设置",
        "tab_workbench": "工作台",
        "language": "Language / 语言",
        "quick_start": "快速上手",
        "quick_start_body": (
            "1. 先点“自动检测”定位微信数据库目录。\n"
            "2. 选择模型供应商，填入 API Key；模型名和 Base URL 可以先用默认值。\n"
            "3. 点“保存设置”后，再测试 API 或执行数据库解密。\n"
            "4. 去工作台选择群聊或单聊，可按单日或多日范围生成摘要。"
        ),
        "privacy_tip": (
            "隐私提醒：本工具会读取你的本地微信数据库。API Key、解密目录、输出文件都属于敏感信息，"
            "不要把 output、.env、.wechat-digest、解密后的数据库或生成报告上传到公开仓库。"
        ),
        "environment": "环境与模型",
        "db_directory": "微信数据库目录",
        "auto_detect": "自动检测",
        "decrypted_dir": "解密输出目录",
        "output_dir": "摘要输出目录",
        "provider": "模型供应商",
        "provider_help": "内置 Doubao、GLM、DeepSeek、OpenAI、OpenRouter、SiliconFlow、Ollama 和 Custom。",
        "model": "模型名称",
        "base_url": "Base URL",
        "api_key": "API Key",
        "batch_endpoint": "批量推理端点",
        "batch_api_key": "批量推理 Key",
        "save_settings": "保存设置",
        "test_api": "测试 API",
        "decrypt_databases": "解密数据库",
        "mode_groups": "群聊",
        "mode_dms": "单聊",
        "search_sessions": "搜索会话",
        "summary_run": "摘要任务",
        "target": "目标会话",
        "date_mode": "时间范围",
        "single_day": "单日",
        "date_range": "多日范围",
        "date": "日期",
        "start_date": "开始日期",
        "end_date": "结束日期",
        "since": "起始时刻",
        "since_placeholder": "可选，格式 HH:MM，仅单日模式生效",
        "segment": "按时间段分段摘要",
        "full": "使用完整消息，不做压缩",
        "batch": "使用批量推理",
        "report_full": "在报告中附带聊天详情",
        "output": "输出位置",
        "generate_summary": "生成摘要",
        "choose_output": "选择单日输出文件",
        "generated_report": "摘要与结果",
        "run_log": "运行日志",
        "status_log": "状态日志",
        "no_session_selected": "尚未选择会话",
        "settings_saved": "设置已保存。",
        "api_test_finished": "API 测试完成。",
        "task_failed": "任务失败",
        "detected_db_directory": "已检测到数据库目录：{value}",
        "no_db_detected": "未检测到数据库目录。",
        "decrypt_finished": "解密完成：{payload}",
        "summary_written": "摘要已写入：{path}",
        "range_done": "已生成 {count} 天摘要，输出目录：{path}",
        "choose_summary_output": "选择摘要输出文件",
        "markdown_filter": "Markdown 文件 (*.md)",
        "no_session_title": "未选择会话",
        "no_session_body": "请先在左侧选择一个群聊或单聊。",
        "loaded_config": "已加载配置，包含 {count} 个已知映射。",
        "session_count": "共 {count} 个会话",
        "range_output_hint": "多日模式会按每天一个文件输出到该目录。",
    },
    "en": {
        "window_title": "WeChatDigestWindows",
        "toolbar_main": "Main Toolbar",
        "refresh_sessions": "Refresh Sessions",
        "open_output_folder": "Open Output Folder",
        "tab_setup": "Setup",
        "tab_workbench": "Workbench",
        "language": "Language",
        "quick_start": "Quick Start",
        "quick_start_body": (
            "1. Use Auto Detect to locate the WeChat data directory.\n"
            "2. Pick a provider and enter your API key; default model values are fine to start.\n"
            "3. Save settings before testing the API or decrypting databases.\n"
            "4. In Workbench, choose a group or DM and generate a single-day or multi-day summary."
        ),
        "privacy_tip": (
            "Privacy: this app reads your local WeChat database. Keep API keys, decrypted paths, "
            "databases, and generated outputs private. Do not publish output, .env, or .wechat-digest data."
        ),
        "environment": "Environment and Model",
        "db_directory": "WeChat DB Directory",
        "auto_detect": "Auto Detect",
        "decrypted_dir": "Decrypted Output Dir",
        "output_dir": "Summary Output Dir",
        "provider": "Model Provider",
        "provider_help": "Built-in presets include Doubao, GLM, DeepSeek, OpenAI, OpenRouter, SiliconFlow, Ollama, and Custom.",
        "model": "Model",
        "base_url": "Base URL",
        "api_key": "API Key",
        "batch_endpoint": "Batch Endpoint",
        "batch_api_key": "Batch API Key",
        "save_settings": "Save Settings",
        "test_api": "Test API",
        "decrypt_databases": "Decrypt Databases",
        "mode_groups": "Groups",
        "mode_dms": "Direct Messages",
        "search_sessions": "Search sessions",
        "summary_run": "Summary Run",
        "target": "Target",
        "date_mode": "Time Scope",
        "single_day": "Single Day",
        "date_range": "Date Range",
        "date": "Date",
        "start_date": "Start Date",
        "end_date": "End Date",
        "since": "Since",
        "since_placeholder": "Optional HH:MM, single-day mode only",
        "segment": "Segment by time window",
        "full": "Use full messages",
        "batch": "Use batch inference",
        "report_full": "Append chat details to report",
        "output": "Output",
        "generate_summary": "Generate Summary",
        "choose_output": "Choose Single-Day Output",
        "generated_report": "Summary and Result",
        "run_log": "Run Log",
        "status_log": "Status Log",
        "no_session_selected": "No session selected",
        "settings_saved": "Settings saved.",
        "api_test_finished": "API test finished.",
        "task_failed": "Task Failed",
        "detected_db_directory": "Detected DB directory: {value}",
        "no_db_detected": "No DB directory detected.",
        "decrypt_finished": "Decrypt finished: {payload}",
        "summary_written": "Summary written to: {path}",
        "range_done": "Generated {count} daily summaries. Output folder: {path}",
        "choose_summary_output": "Choose Summary Output",
        "markdown_filter": "Markdown (*.md)",
        "no_session_title": "No Session",
        "no_session_body": "Select a session from the left first.",
        "loaded_config": "Loaded config with {count} known mappings.",
        "session_count": "{count} sessions",
        "range_output_hint": "Range mode writes one file per day into this folder.",
    },
}


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
        self.sessions_cache = []
        self.current_mode_dm = False
        self.language = "zh"
        self.current_output_override = ""
        self.provider_presets = backend.list_provider_presets()
        self.provider_map = {item["key"]: item for item in self.provider_presets}
        self.setup_labels: dict[str, QLabel] = {}
        self.run_labels: dict[str, QLabel] = {}
        self._build_ui()
        if auto_bootstrap:
            self._load_state()
            self.refresh_sessions()
        self._apply_language()

    def t(self, key: str, **kwargs) -> str:
        text = TRANSLATIONS[self.language].get(key, key)
        return text.format(**kwargs) if kwargs else text

    def _build_ui(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.refresh_action = QAction(self)
        self.refresh_action.triggered.connect(self.refresh_sessions)
        self.toolbar.addAction(self.refresh_action)

        self.open_output_action = QAction(self)
        self.open_output_action.triggered.connect(self.open_output_folder)
        self.toolbar.addAction(self.open_output_action)

        self.tabs = QTabWidget()
        self.setup_tab = self._build_setup_tab()
        self.workbench_tab = self._build_workbench_tab()
        self.tabs.addTab(self.setup_tab, "")
        self.tabs.addTab(self.workbench_tab, "")
        self.setCentralWidget(self.tabs)
        self.resize(1280, 860)

    def _add_form_row(self, form: QFormLayout, label_store: dict[str, QLabel], key: str, widget: QWidget):
        label = QLabel()
        label_store[key] = label
        form.addRow(label, widget)

    def _build_setup_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.language_box = QGroupBox()
        lang_form = QFormLayout(self.language_box)
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", "zh")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        lang_form.addRow(self.language_label, self.language_combo)
        layout.addWidget(self.language_box)

        self.quick_start_box = QGroupBox()
        quick_layout = QVBoxLayout(self.quick_start_box)
        self.quick_start_label = QLabel()
        self.quick_start_label.setWordWrap(True)
        quick_layout.addWidget(self.quick_start_label)
        self.privacy_label = QLabel()
        self.privacy_label.setWordWrap(True)
        quick_layout.addWidget(self.privacy_label)
        layout.addWidget(self.quick_start_box)

        self.form_box = QGroupBox()
        form = QFormLayout(self.form_box)

        self.db_dir_edit = QLineEdit()
        self.detect_btn = QPushButton()
        self.detect_btn.clicked.connect(self.detect_db_dir)
        db_row = QWidget()
        db_row_layout = QHBoxLayout(db_row)
        db_row_layout.setContentsMargins(0, 0, 0, 0)
        db_row_layout.addWidget(self.db_dir_edit)
        db_row_layout.addWidget(self.detect_btn)
        self._add_form_row(form, self.setup_labels, "db_directory", db_row)

        self.decrypted_dir_edit = QLineEdit()
        self._add_form_row(form, self.setup_labels, "decrypted_dir", self.decrypted_dir_edit)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.textChanged.connect(self.update_output_preview)
        self._add_form_row(form, self.setup_labels, "output_dir", self.output_dir_edit)

        self.provider_combo = QComboBox()
        for item in self.provider_presets:
            self.provider_combo.addItem(item["label"], item["key"])
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)
        self._add_form_row(form, self.setup_labels, "provider", self.provider_combo)

        self.provider_help_label = QLabel()
        self.provider_help_label.setWordWrap(True)
        self._add_form_row(form, self.setup_labels, "provider_help", self.provider_help_label)

        self.model_edit = QLineEdit()
        self._add_form_row(form, self.setup_labels, "model", self.model_edit)

        self.base_url_edit = QLineEdit()
        self._add_form_row(form, self.setup_labels, "base_url", self.base_url_edit)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self._add_form_row(form, self.setup_labels, "api_key", self.api_key_edit)

        self.batch_endpoint_edit = QLineEdit()
        self._add_form_row(form, self.setup_labels, "batch_endpoint", self.batch_endpoint_edit)

        self.batch_api_key_edit = QLineEdit()
        self.batch_api_key_edit.setEchoMode(QLineEdit.Password)
        self._add_form_row(form, self.setup_labels, "batch_api_key", self.batch_api_key_edit)

        layout.addWidget(self.form_box)

        button_row = QHBoxLayout()
        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self.save_state)
        button_row.addWidget(self.save_btn)

        self.test_btn = QPushButton()
        self.test_btn.clicked.connect(self.test_api)
        button_row.addWidget(self.test_btn)

        self.decrypt_btn = QPushButton()
        self.decrypt_btn.clicked.connect(self.decrypt_databases)
        button_row.addWidget(self.decrypt_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_box = QGroupBox()
        status_layout = QVBoxLayout(self.status_box)
        self.status_log = QPlainTextEdit()
        self.status_log.setReadOnly(True)
        status_layout.addWidget(self.status_log)
        layout.addWidget(self.status_box, 1)
        return widget

    def _build_workbench_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        mode_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._filter_sessions)
        mode_row.addWidget(self.search_edit, 1)
        left_layout.addLayout(mode_row)

        self.session_count_label = QLabel()
        left_layout.addWidget(self.session_count_label)

        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(self._session_changed)
        left_layout.addWidget(self.session_list, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.run_box = QGroupBox()
        run_form = QFormLayout(self.run_box)

        self.target_name_label = QLabel()
        self.target_name_label.setWordWrap(True)
        self._add_form_row(run_form, self.run_labels, "target", self.target_name_label)

        self.single_day_radio = QRadioButton()
        self.range_day_radio = QRadioButton()
        self.single_day_radio.toggled.connect(self._date_mode_changed)
        self.range_day_radio.toggled.connect(self._date_mode_changed)
        date_mode_row = QWidget()
        date_mode_layout = QHBoxLayout(date_mode_row)
        date_mode_layout.setContentsMargins(0, 0, 0, 0)
        date_mode_layout.addWidget(self.single_day_radio)
        date_mode_layout.addWidget(self.range_day_radio)
        date_mode_layout.addStretch(1)
        self._add_form_row(run_form, self.run_labels, "date_mode", date_mode_row)

        default_date = QDate.fromString(backend.default_summary_date(), "yyyy-MM-dd")
        if not default_date.isValid():
            default_date = QDate.currentDate().addDays(-1)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(default_date)
        self.date_edit.dateChanged.connect(self._single_date_changed)
        self._add_form_row(run_form, self.run_labels, "date", self.date_edit)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(default_date)
        self.start_date_edit.dateChanged.connect(self.update_output_preview)
        self._add_form_row(run_form, self.run_labels, "start_date", self.start_date_edit)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(default_date)
        self.end_date_edit.dateChanged.connect(self.update_output_preview)
        self._add_form_row(run_form, self.run_labels, "end_date", self.end_date_edit)

        self.since_edit = QLineEdit()
        self.since_edit.textChanged.connect(self.update_output_preview)
        self._add_form_row(run_form, self.run_labels, "since", self.since_edit)

        self.segment_check = QCheckBox()
        self._add_form_row(run_form, self.run_labels, "segment", self.segment_check)

        self.full_check = QCheckBox()
        self._add_form_row(run_form, self.run_labels, "full", self.full_check)

        self.batch_check = QCheckBox()
        self._add_form_row(run_form, self.run_labels, "batch", self.batch_check)

        self.report_full_check = QCheckBox()
        self._add_form_row(run_form, self.run_labels, "report_full", self.report_full_check)

        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self._add_form_row(run_form, self.run_labels, "output", self.output_edit)

        self.range_hint_label = QLabel()
        self.range_hint_label.setWordWrap(True)
        self._add_form_row(run_form, self.run_labels, "range_hint", self.range_hint_label)

        button_row = QHBoxLayout()
        self.generate_btn = QPushButton()
        self.generate_btn.clicked.connect(self.run_summary)
        button_row.addWidget(self.generate_btn)
        self.choose_output_btn = QPushButton()
        self.choose_output_btn.clicked.connect(self.choose_output_file)
        button_row.addWidget(self.choose_output_btn)
        button_row.addStretch(1)
        button_wrap = QWidget()
        button_wrap.setLayout(button_row)
        run_form.addRow(QLabel(""), button_wrap)
        right_layout.addWidget(self.run_box)

        self.report_box = QGroupBox()
        report_layout = QVBoxLayout(self.report_box)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        report_layout.addWidget(self.report_view)
        right_layout.addWidget(self.report_box, 3)

        self.run_log_box = QGroupBox()
        run_log_layout = QVBoxLayout(self.run_log_box)
        self.run_log = QPlainTextEdit()
        self.run_log.setReadOnly(True)
        run_log_layout.addWidget(self.run_log)
        right_layout.addWidget(self.run_log_box, 2)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.single_day_radio.setChecked(True)
        return widget

    def _apply_language(self):
        self.setWindowTitle(self.t("window_title"))
        self.toolbar.setWindowTitle(self.t("toolbar_main"))
        self.refresh_action.setText(self.t("refresh_sessions"))
        self.open_output_action.setText(self.t("open_output_folder"))
        self.tabs.setTabText(0, self.t("tab_setup"))
        self.tabs.setTabText(1, self.t("tab_workbench"))

        self.language_box.setTitle(self.t("language"))
        self.language_label.setText(self.t("language"))

        self.quick_start_box.setTitle(self.t("quick_start"))
        self.quick_start_label.setText(self.t("quick_start_body"))
        self.privacy_label.setText(self.t("privacy_tip"))

        self.form_box.setTitle(self.t("environment"))
        self.setup_labels["db_directory"].setText(self.t("db_directory"))
        self.setup_labels["decrypted_dir"].setText(self.t("decrypted_dir"))
        self.setup_labels["output_dir"].setText(self.t("output_dir"))
        self.setup_labels["provider"].setText(self.t("provider"))
        self.setup_labels["provider_help"].setText("")
        self.setup_labels["model"].setText(self.t("model"))
        self.setup_labels["base_url"].setText(self.t("base_url"))
        self.setup_labels["api_key"].setText(self.t("api_key"))
        self.setup_labels["batch_endpoint"].setText(self.t("batch_endpoint"))
        self.setup_labels["batch_api_key"].setText(self.t("batch_api_key"))
        self.provider_help_label.setText(self.t("provider_help"))
        self.detect_btn.setText(self.t("auto_detect"))
        self.save_btn.setText(self.t("save_settings"))
        self.test_btn.setText(self.t("test_api"))
        self.decrypt_btn.setText(self.t("decrypt_databases"))
        self.status_box.setTitle(self.t("status_log"))

        self.mode_combo.blockSignals(True)
        current_mode = self.mode_combo.currentData()
        self.mode_combo.clear()
        self.mode_combo.addItem(self.t("mode_groups"), False)
        self.mode_combo.addItem(self.t("mode_dms"), True)
        target_index = self.mode_combo.findData(current_mode if current_mode is not None else self.current_mode_dm)
        self.mode_combo.setCurrentIndex(0 if target_index < 0 else target_index)
        self.mode_combo.blockSignals(False)
        self.search_edit.setPlaceholderText(self.t("search_sessions"))
        self.session_count_label.setText(self.t("session_count", count=self.session_list.count()))

        self.run_box.setTitle(self.t("summary_run"))
        self.run_labels["target"].setText(self.t("target"))
        self.run_labels["date_mode"].setText(self.t("date_mode"))
        self.run_labels["date"].setText(self.t("date"))
        self.run_labels["start_date"].setText(self.t("start_date"))
        self.run_labels["end_date"].setText(self.t("end_date"))
        self.run_labels["since"].setText(self.t("since"))
        self.run_labels["segment"].setText("")
        self.run_labels["full"].setText("")
        self.run_labels["batch"].setText("")
        self.run_labels["report_full"].setText("")
        self.run_labels["output"].setText(self.t("output"))
        self.run_labels["range_hint"].setText("")
        self.single_day_radio.setText(self.t("single_day"))
        self.range_day_radio.setText(self.t("date_range"))
        self.since_edit.setPlaceholderText(self.t("since_placeholder"))
        self.segment_check.setText(self.t("segment"))
        self.full_check.setText(self.t("full"))
        self.batch_check.setText(self.t("batch"))
        self.report_full_check.setText(self.t("report_full"))
        self.generate_btn.setText(self.t("generate_summary"))
        self.choose_output_btn.setText(self.t("choose_output"))
        self.range_hint_label.setText(self.t("range_output_hint"))
        self.report_box.setTitle(self.t("generated_report"))
        self.run_log_box.setTitle(self.t("run_log"))

        if not self.session_list.currentItem():
            self.target_name_label.setText(self.t("no_session_selected"))
        self._date_mode_changed()

    def _language_changed(self):
        self.language = self.language_combo.currentData() or "zh"
        self._apply_language()

    def _provider_changed(self):
        preset = self.provider_map[self.provider_combo.currentData()]
        model_values = {item["model"] for item in self.provider_presets if item["model"]}
        url_values = {item["base_url"] for item in self.provider_presets if item["base_url"]}
        if not self.model_edit.text().strip() or self.model_edit.text().strip() in model_values:
            self.model_edit.setText(preset["model"])
        if not self.base_url_edit.text().strip() or self.base_url_edit.text().strip() in url_values:
            self.base_url_edit.setText(preset["base_url"])

    def _load_state(self):
        state = backend.load_app_state()
        self.language = state.get("language", "zh")
        self.language_combo.setCurrentIndex(0 if self.language == "zh" else 1)
        self.db_dir_edit.setText(state["db_dir"])
        self.decrypted_dir_edit.setText(state["decrypted_dir"])
        self.output_dir_edit.setText(state["output_dir"])
        provider = state["provider"]
        provider_key = provider if provider in self.provider_map else "custom"
        provider_index = self.provider_combo.findData(provider_key)
        self.provider_combo.setCurrentIndex(0 if provider_index < 0 else provider_index)
        self.model_edit.setText(state["model"])
        self.base_url_edit.setText(state["base_url"])
        self.api_key_edit.setText(state["api_key"])
        self.batch_endpoint_edit.setText(state["batch_endpoint"])
        self.batch_api_key_edit.setText(state["batch_api_key"])
        self.status_log.appendPlainText(self.t("loaded_config", count=state["known_count"]))
        self._apply_language()

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
        QMessageBox.critical(self, self.t("task_failed"), message)
        self.status_log.appendPlainText(message)

    def detect_db_dir(self):
        self._submit(backend.detect_db_dir, self._db_detected)

    def _db_detected(self, value):
        if value:
            self.db_dir_edit.setText(value)
            self.status_log.appendPlainText(self.t("detected_db_directory", value=value))
        else:
            self.status_log.appendPlainText(self.t("no_db_detected"))

    def save_state(self):
        backend.save_app_state(self._collect_state())
        self.status_log.appendPlainText(self.t("settings_saved"))
        self.current_output_override = ""
        self.update_output_preview()

    def test_api(self):
        self.save_state()
        self._submit(backend.test_api, self._api_test_done)

    def _api_test_done(self, log_text):
        self.status_log.appendPlainText(log_text.strip() or self.t("api_test_finished"))

    def decrypt_databases(self):
        self.save_state()
        self._submit(backend.decrypt_databases, self._decrypt_done)

    def _decrypt_done(self, result):
        payload, log_text = result
        if log_text.strip():
            self.status_log.appendPlainText(log_text.strip())
        self.status_log.appendPlainText(self.t("decrypt_finished", payload=payload))

    def _on_mode_changed(self, _index):
        self.current_mode_dm = bool(self.mode_combo.currentData())
        self.refresh_sessions()

    def refresh_sessions(self):
        self._submit(backend.list_sessions, self._sessions_loaded, self.current_mode_dm)

    def _session_label(self, session: dict) -> str:
        name = session.get("name") or session.get("username") or ""
        username = session.get("username") or ""
        label = name
        if username and name != username:
            label = f"{name}  <{username}>"
        if session.get("last_time"):
            label = f"{label}  [{session['last_time']}]"
        return label

    def _sessions_loaded(self, result):
        sessions, log_text = result
        self.sessions_cache = sessions
        self.session_list.clear()
        for session in sessions:
            item = QListWidgetItem(self._session_label(session))
            item.setData(Qt.UserRole, session)
            self.session_list.addItem(item)
        self.session_count_label.setText(self.t("session_count", count=self.session_list.count()))
        if sessions:
            self.session_list.setCurrentRow(0)
        else:
            self.target_name_label.setText(self.t("no_session_selected"))
        self.run_log.setPlainText(log_text.strip())
        self._filter_sessions()

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
        self.session_count_label.setText(self.t("session_count", count=visible))

    def _session_changed(self, current, _previous):
        if not current:
            self.target_name_label.setText(self.t("no_session_selected"))
            return
        session = current.data(Qt.UserRole)
        name = session.get("name") or session.get("username") or ""
        username = session.get("username") or ""
        self.target_name_label.setText(name if not username or name == username else f"{name} ({username})")
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

    def _date_mode_changed(self):
        if not hasattr(self, "start_date_edit"):
            return
        is_range = self.range_day_radio.isChecked()
        self.start_date_edit.setEnabled(is_range)
        self.end_date_edit.setEnabled(is_range)
        self.date_edit.setEnabled(not is_range)
        self.since_edit.setEnabled(not is_range)
        self.output_edit.setReadOnly(True)
        self.choose_output_btn.setEnabled(not is_range)
        self.range_hint_label.setVisible(is_range)
        self.update_output_preview()

    def update_output_preview(self):
        group_name = self._selected_session_name()
        if not group_name:
            self.output_edit.clear()
            return
        if self.range_day_radio.isChecked():
            output_root = self.output_dir_edit.text().strip() or os.path.join(os.getcwd(), "output")
            self.output_edit.setText(output_root)
            return
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        if self.current_output_override:
            self.output_edit.setText(self.current_output_override)
            return
        try:
            path = backend.preview_output_path(group_name, date_str, self.since_edit.text())
        except Exception:
            path = ""
        self.output_edit.setText(path)

    def choose_output_file(self):
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        start_dir = self.output_dir_edit.text().strip() or os.getcwd()
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
        self.report_view.clear()
        self.run_log.clear()
        common = {
            "segment": self.segment_check.isChecked(),
            "full": self.full_check.isChecked(),
            "batch_mode": self.batch_check.isChecked(),
            "report_full": self.report_full_check.isChecked(),
        }
        if self.range_day_radio.isChecked():
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
        self.run_log.setPlainText(payload["log"].strip())
        if payload["mode"] == "range":
            self.report_view.setPlainText(payload["summary"])
            self.output_edit.setText(payload["output_path"])
            self.status_log.appendPlainText(
                self.t("range_done", count=len(payload["generated_files"]), path=payload["output_path"])
            )
            return
        self.output_edit.setText(payload["output_path"])
        self.report_view.setPlainText(payload["report"] or payload["summary"])
        self.status_log.appendPlainText(self.t("summary_written", path=payload["output_path"]))

    def open_output_folder(self):
        target = self.output_edit.text().strip() or self.output_dir_edit.text().strip()
        if not target:
            return
        path = target if os.path.isdir(target) else os.path.dirname(target)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def launch(smoke_test: bool = False):
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(auto_bootstrap=not smoke_test)
    window.show()
    if smoke_test:
        QTimer.singleShot(300, app.quit)
    return app.exec()
