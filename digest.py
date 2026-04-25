#!/usr/bin/env python3
"""
wechat-digest CLI V2 — 微信群聊摘要工具

子命令：
  groups [--json]              列出活跃群
  contacts [--json]            导出联系人映射
  extract <群> <日期> [--compact] [--json]  提取消息
  summarize <群> <日期> [--compact]         LLM 摘要
  run <群> <日期> [--compact]               一键全流程
  decrypt                      解密数据库
  test-api                     测试 LLM 连接
  config [--show|--set K=V]    配置管理

V2 优化：
  --compact   压缩消息（精简时间戳/过滤噪声/合并短消息），省 30-50% token
  --prompt    自定义 Prompt 模板文件
  --no-cache  跳过缓存
  contacts    导出群名/联系人 ID→昵称映射 JSON
"""

import argparse, asyncio, collections, datetime, hashlib, io, json, logging, math, os, re
import sqlite3, sys, tempfile, time
import urllib.error, urllib.request
from dataclasses import dataclass, asdict
from typing import Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_SCRIPT_DIR, "src")
_VENDORED_DIGEST_DIR = os.path.join(_SRC_DIR, "wechat_digest_app", "vendor", "wechat_digest")
_LEGACY_DIGEST_DIR = os.path.join(_SCRIPT_DIR, "wechat-digest")

for candidate in (_SRC_DIR, _VENDORED_DIGEST_DIR, _LEGACY_DIGEST_DIR):
    if os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

# Fix Windows console encoding when stdio streams exist.
def _patch_stdio_encoding(stream_name: str) -> None:
    stream = getattr(sys, stream_name, None)
    if stream is None:
        return
    encoding = getattr(stream, "encoding", None)
    buffer = getattr(stream, "buffer", None)
    if not encoding or not buffer:
        return
    if encoding.lower() != "utf-8":
        setattr(sys, stream_name, io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))


_patch_stdio_encoding("stdout")
_patch_stdio_encoding("stderr")

try:
    import zstandard; HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

try:
    from crypto.decrypt import full_decrypt, decrypt_wal; HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# 火山方舟批量推理SDK（可选）
try:
    from volcenginesdkarkruntime import AsyncArk; HAS_ARK_BATCH = True
except ImportError:
    HAS_ARK_BATCH = False

# ============================================================
# 数据结构
# ============================================================

@dataclass
class ChatMessage:
    """结构化消息"""
    timestamp: int
    dt_str: str
    sender_id: str
    sender_name: str
    content: str
    msg_type: int  # 1=文本 34=语音 49=链接/引用
    url: str = ""
    ref_summary: str = ""  # type=49 引用消息的被引用原文摘要（用于折叠显示）

    def to_dict(self):
        return asdict(self)

    def format_line(self, compact: bool = False) -> str:
        sender = self.sender_name or self.sender_id
        if self.msg_type == 34:
            body = "[语音]"
        elif self.msg_type == 49:
            body = f"[链接] {self.content}"
        else:
            body = self.content
        if compact:
            ts = self.dt_str[11:16] if len(self.dt_str) >= 16 else self.dt_str
            line = f"[{ts}] {sender}: {body}"
        else:
            line = f"[{self.dt_str}] {sender}: {body}"
            if self.msg_type == 49 and self.url and self.url.startswith("http"):
                line += f"\n  URL: {self.url}"
        return line


# ============================================================
# 常量 & 配置
# ============================================================

STATE_DIR = os.path.expanduser("~/.wechat-digest")
CONFIG_FILE = os.path.join(STATE_DIR, "config.json")
KEYS_FILE = os.path.join(STATE_DIR, "all_keys.json")
LLM_CONFIG_FILE = os.path.join(STATE_DIR, "llm_config.json")
CACHE_DIR = os.path.join(STATE_DIR, "cache")
CONTACTS_CACHE = os.path.join(CACHE_DIR, "contacts_cache.json")
DEFAULT_OUTPUT_DIR = os.path.join(STATE_DIR, "output")
DEFAULT_DECRYPTED_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "decrypted")

# 日志（--quiet 时设 WARNING 级别）
log = logging.getLogger("wechat-digest")
logging.basicConfig(format="%(message)s", level=logging.INFO)

# 压缩模式下的噪声词（可配置）
NOISE_PATTERNS = [
    # 单字/双字语气词
    re.compile(r'^(嗯|哦|额|啊|哈|好|是|对|行|嗯嗯|呵呵|确实|可以|真的|对的|合理)$'),
    # 短笑声
    re.compile(r'^(哈哈|哈哈哈|哈哈哈哈|哈哈哈哈哈|哈哈哈哈哈哈|哈哈哈哈哈哈哈哈)$'),
    # 扩展笑声/网络用语
    re.compile(r'^(haha|haha哈|hhh|hhhh|hhhhh|xs|www|wwwww)$'),
    # 通用简短回应
    re.compile(r'^(收到|谢谢|感谢|加油|同意|不错|厉害|牛|棒|666|冲|赞|\+1|同问|太强了|nb|NB|好有道理|这么简单理解|好家伙)$'),
    re.compile(r'^(ok|OK|Ok|yyds|YYDS|lol|haha)$'),
    # 纯表情/emoji
    re.compile(r'^([\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF\U0001F018-\U0001F270]+)$'),
    # 微信表情（[文字] 格式）
    re.compile(r'^\[[\u4e00-\u9fff\w]+\]$'),
    # 纯标点/空白
    re.compile(r'^[\s\.\,\?\!\~\，\。\？\！\～\、\;\；\:\：]*$'),
    # 短感叹/语气词组合
    re.compile(r'^(笑死|震惊|绝了|6|好的|嗯呢|哦哦|啊啊|呕呕|天呐|救命|麻烦了|辛苦了|打扰了|懂了|好搞笑|我笑死|笑死了|我的天啊|卧槽|天塌了|瑟瑟发抖|离了个大谱|好地狱|我去|绷不住了|绀不住了)$'),
    # 微信"拍一拍"消息
    re.compile(r'拍了拍'),
]

# 引用消息中纯附和/回应（type=49，正文是这些时可折叠）
QUOTE_NOISE_PATTERNS = [
    re.compile(r'^(嗯|哦|额|啊|好|是|对|行|确实|同意|不错|厉害|牛|棒|6|冲|赞|笑死|震惊|绝了|ok|OK|可以的|确实可以|确实如此|有道理|确实有道理|没错|对对对|对的对的|哈哈哈哈+)$'),
    re.compile(r'^[\+\-]1$'),
    re.compile(r'^\[[\u4e00-\u9fff\w]+\]$'),
    re.compile(r'^([\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]+)$'),
    # 扩展引用附和
    re.compile(r'^(真的假的|太真实了|好搞笑|离了个大谱|好地狱|瑟瑟发抖|nb|NB|同问|太强了|天塌了|绀不住了|绷不住了|好家伙|我去|好有道理|懂了)$'),
]

# 微信群系统消息模式（type=1 文本中混入的系统提示，无讨论价值）
SYSTEM_MSG_PATTERNS = [
    re.compile(r'^"?.{1,20}"?撤回了一条消息$'),
    re.compile(r'^你撤回了一条消息'),
    re.compile(r'邀请.{1,20}加入了群聊'),
    re.compile(r'.{1,20}加入了群聊'),
    re.compile(r'.{1,20}通过扫描.{1,10}分享的二维码加入群聊'),
    re.compile(r'^群公告$'),
    re.compile(r'修改群名为'),
    re.compile(r'将群名改为'),
    re.compile(r'群名称已修改为'),
    re.compile(r'^以下为新消息$'),
    re.compile(r'发起了群接龙'),
    re.compile(r'红包'),      # 过滤"收到红包"/"发了一个红包"等
    re.compile(r'转账'),
]

LLM_PROVIDERS = {
    "doubao":   {"base_url": "https://ark.cn-beijing.volces.com/api/v3",          "models": ["doubao-1-5-pro-256k", "doubao-pro-32k"]},
    "glm":      {"base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "models": ["glm-4-plus", "glm-4-flash"]},
    "deepseek": {"base_url": "https://api.deepseek.com/v1",                        "models": ["deepseek-chat", "deepseek-reasoner"]},
    "openai":   {"base_url": "https://api.openai.com/v1",                          "models": ["gpt-4o", "gpt-4o-mini"]},
}

# 批量推理提供商配置（火山方舟）
BATCH_PROVIDERS = {
    "ark": {"name": "火山方舟批量推理", "sdk": "volcenginesdkarkruntime"},
}

DEFAULT_PROMPT_TEMPLATE = """你是一个专业的微信群聊总结助手。你的任务是对微信群聊记录生成简洁、信息密度高的每日摘要。

## 输入
微信群「{{GROUP_NAME}}」在 {{TARGET_DATE}} 的聊天记录，格式为 [时间] 发送者: 内容。

## 输出要求

# {{GROUP_NAME}} 群聊摘要 - {{TARGET_DATE}}

> 消息总数：{{TOTAL}} 条 | 最活跃时段：XX:XX - XX:XX（根据时间戳判断）

### 核心讨论
（提炼 3-5 个最重要的讨论话题。每个话题包含标题和要点。只保留有信息量的观点和技术讨论，去掉纯闲聊、水话、低价值内容。要点要具体，包含工具名、版本号、结论等关键信息。）

### 实用信息
（提取群友分享的可操作技巧、工具推荐、配置方案、踩坑经验等。每个条目用一行，格式：- **主题**：具体内容。只保留有明确操作价值的，不含泛泛的感受。）

### 资源分享
（用表格整理分享的链接和资源。三列：资源 | 概要 | 备注。
- 资源列：有 URL 的用 [标题](URL) 格式，无 URL 的用纯文本
- 概要列：一两句话概括核心内容（根据标题和上下文推断，不照抄聊天）
- 备注列：群友有评价的简要写出，无评价留空
没有资源分享时省略此节。）

## 写作规则
1. **去水原则**：只保留有信息量的内容。闲聊、纯表情、吐槽、重复观点一律剔除
2. **隐私保护**：绝对不要出现任何群友的 wxid、昵称或可识别身份信息。用"有群友"、"有人"、"据群友反馈"等替代
3. **优先级排序**：模型/大模型相关 > Coding Agent 工具 > AI 应用/产品 > 技术方案 > 非AI话题
4. **具体化**：提到工具要写明名称和版本，提到方案要写明关键步骤，避免泛泛而谈
5. **客观中立**：忠实原文，不添加个人判断。多个观点并存时客观呈现
6. **灵活省略**：某个分类没有相关内容时，直接省略该分类，不要硬凑
7. **紧凑排版**：控制总字数在 800-1500 字之间，信息密度优先"""


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    try:
        from crypto.config import load_config as _lc
        cfg, _ = _lc(); return cfg
    except Exception:
        pass
    return {}


def save_config(cfg):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE) as f:
            return json.load(f)
    return {}


def load_llm_config():
    config = {}
    if os.path.exists(LLM_CONFIG_FILE):
        with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        main_cfg = load_config()
        if "llm" in main_cfg:
            config = dict(main_cfg["llm"])
    env_map = {
        "provider": "LLM_PROVIDER", "api_key": "WECHAT_LLM_API_KEY",
        "base_url": "LLM_BASE_URL", "model": "LLM_MODEL",
        "temperature": "LLM_TEMPERATURE", "max_tokens": "LLM_MAX_TOKENS",
        # 批量推理专用配置
        "batch_provider": "LLM_BATCH_PROVIDER",      # 批量推理提供商，如 "ark"
        "batch_endpoint": "LLM_BATCH_ENDPOINT",      # 批量推理端点ID
        "batch_api_key": "ARK_API_KEY",              # 火山方舟专用Key
    }
    for key, env_var in env_map.items():
        val = os.environ.get(env_var)
        if val is not None:
            config[key] = val
    return config


def get_db_key():
    key = os.environ.get("WECHAT_DB_KEY", "")
    if key:
        return key
    return load_config().get("db_key", "")


# ============================================================
# 联系人映射
# ============================================================

def _read_contacts_from_db(dec_dir):
    """从 contact.db 读取联系人映射"""
    contacts = {}
    for candidate in [
        os.path.join(dec_dir, "contact", "contact.db"),
        os.path.join(dec_dir, "contact.db"),
    ]:
        if not os.path.exists(candidate):
            continue
        try:
            conn = sqlite3.connect(candidate)
            try:
                cols = [d[0] for d in conn.execute("SELECT * FROM contact LIMIT 1").description]
            except Exception:
                conn.close(); continue
            user_col = nick_col = None
            col_lower = [c.lower() for c in cols]
            # username 优先于 id（username 是 wxid 格式，id 是数字）
            for preferred in ["username", "usrname", "id"]:
                if preferred in col_lower:
                    user_col = cols[col_lower.index(preferred)]
                    break
            for preferred in ["nick_name", "nickname", "remark", "alias"]:
                if preferred in col_lower:
                    nick_col = cols[col_lower.index(preferred)]
                    break
            if user_col and nick_col:
                rows = conn.execute(
                    f'SELECT "{user_col}", "{nick_col}" FROM contact '
                    f'WHERE "{nick_col}" IS NOT NULL AND "{nick_col}" != ""'
                ).fetchall()
                for uid, nick in rows:
                    if uid and nick:
                        contacts[str(uid)] = str(nick)
            conn.close(); break
        except Exception:
            continue
    return contacts


def get_contacts(use_cache=True):
    """获取联系人映射（缓存优先，TTL 24h）"""
    if use_cache and os.path.exists(CONTACTS_CACHE):
        try:
            with open(CONTACTS_CACHE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if time.time() - cache.get("_cached_at", 0) < 86400:
                return cache.get("contacts", {})
        except Exception:
            pass

    cfg = load_config()
    dec_dir = cfg.get("decrypted_dir", "")
    contacts = {}
    if dec_dir and os.path.isdir(dec_dir):
        contacts = _read_contacts_from_db(dec_dir)

    # 合并 known 反向映射作为群名补充
    known_reverse = {v: k for k, v in cfg.get("known", {}).items()}
    for uid, name in known_reverse.items():
        if uid not in contacts:
            contacts[uid] = name

    if contacts:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CONTACTS_CACHE, "w", encoding="utf-8") as f:
            json.dump({"_cached_at": time.time(), "contacts": contacts}, f, ensure_ascii=False, indent=2)
    return contacts


# ============================================================
# 群名解析
# ============================================================

def _split_words(text):
    """将中文/英文混合文本拆分为关键词列表。
    中文按单字拆分（因为中文没有空格分词），英文按空格拆分。
    例：'AI实践群' -> ['ai', '实践', '群']  'practice ai 群' -> ['practice', 'ai', '群']
    """
    parts = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]', text.lower())
    return [p for p in parts if len(p) > 0]


def _token_overlap_score(query_words, target_words):
    """计算两组关键词的交叉包含得分。
    基于双向包含：query 关键词在 target 中的比例 + target 关键词在 query 中的比例。
    返回 0.0-1.0 的分数。
    """
    if not query_words or not target_words:
        return 0.0
    q_set, t_set = set(query_words), set(target_words)
    if not q_set or not t_set:
        return 0.0
    # query -> target 覆盖率
    q_in_t = len(q_set & t_set) / len(q_set)
    # target -> query 覆盖率（惩罚 target 过长但 query 很短的情况）
    t_in_q = len(q_set & t_set) / len(t_set)
    # 双向加权：query 侧权重大（用户输入通常更短更关键）
    return q_in_t * 0.7 + t_in_q * 0.3


def _get_active_groups(db_dir=None, include_dm=False):
    """从 session.db + contact.db 获取活跃会话列表，返回 [(username, name, last_ts), ...]。
    session.db 提供 last_timestamp（活跃度排序），contact.db 提供真实群名/联系人名。
    include_dm=True 时同时返回一对一聊天会话。
    缓存结果避免重复查询。
    """
    if not hasattr(_get_active_groups, '_cache'):
        _get_active_groups._cache = None
        _get_active_groups._cache_time = 0
        _get_active_groups._cache_dm = None
        _get_active_groups._cache_dm_time = 0

    cache_key = '_dm' if include_dm else '_groups'
    cache_val = getattr(_get_active_groups, cache_key, None)
    cache_time_attr = cache_key + '_time'
    cache_time = getattr(_get_active_groups, cache_time_attr, 0)

    # 缓存 5 分钟
    if cache_val and time.time() - cache_time < 300:
        return cache_val

    cfg = load_config()
    if db_dir is None:
        db_dir = cfg.get("decrypted_dir", "")
    if not db_dir or not os.path.isdir(db_dir):
        return []

    # 1. 从 contact.db 读取联系人名映射 username -> name（群和个人都读）
    contact_names = {}
    for c in [os.path.join(db_dir, "contact", "contact.db"), os.path.join(db_dir, "contact.db")]:
        if not os.path.exists(c):
            continue
        try:
            conn = sqlite3.connect(c)
            rows = conn.execute(
                'SELECT username, nick_name, remark, alias FROM contact WHERE delete_flag = 0'
            ).fetchall()
            conn.close()
            for username, nick, remark, alias in rows:
                name = (remark or alias or nick or "").strip()
                if name:
                    contact_names[username] = name
            break
        except Exception:
            continue

    # 2. 从 session.db 读取活跃会话（按 last_timestamp 排序）
    session_db = None
    for c in [os.path.join(db_dir, "session", "session.db"), os.path.join(db_dir, "session.db")]:
        if os.path.exists(c):
            session_db = c; break

    if not session_db:
        return []

    known_reverse = {v: k for k, v in cfg.get("known", {}).items()}
    groups = []
    try:
        conn = sqlite3.connect(session_db)
        if include_dm:
            # 一对一：排除系统账号和公众号
            rows = conn.execute(
                "SELECT username, last_timestamp FROM SessionTable "
                "WHERE username NOT LIKE '%@chatroom' "
                "AND username NOT IN ('filehelper','notifymessage','brandsessionholder','brandservicesessionholder','@placeholder_foldgroup') "
                "AND last_timestamp > 1700000000 "
                "ORDER BY last_timestamp DESC"
            ).fetchall()
        else:
            # 群聊
            rows = conn.execute(
                "SELECT username, last_timestamp FROM SessionTable "
                "WHERE username LIKE '%@chatroom' ORDER BY last_timestamp DESC"
            ).fetchall()
        conn.close()
        for username, last_ts in rows:
            # 优先级：known_reverse > contact.db 名字 > username
            name = known_reverse.get(username) or contact_names.get(username, username)
            groups.append((username, name, last_ts))
    except Exception:
        pass

    setattr(_get_active_groups, cache_key, groups)
    setattr(_get_active_groups, cache_key + '_time', time.time())
    return groups


def resolve_group(name, db_dir=None):
    """解析群名，返回 (chatroom_id, canonical_name) 元组。
    canonical_name 是从 known 映射或 session.db 获取的标准群名，
    用于输出目录归一化（避免同一群产生多个文件夹）。
    """
    if not name:
        return None, name
    cfg = load_config()
    known = cfg.get("known", {})
    known_reverse = {v: k for k, v in known.items()}
    # 空格归一化（"ai 实践" -> "ai实践"），提升模糊匹配鲁棒性）
    norm = lambda s: re.sub(r'\s+', '', s.lower())
    norm_name = norm(name)

    # 1. 精确匹配 known（归一化后）
    if norm_name in known:
        return known[norm_name], norm_name
    if name in known:
        return known[name], name

    # 2. 子串包含匹配 known
    for k, v in known.items():
        norm_k = norm(k)
        if norm_name in norm_k or norm_k in norm_name:
            return v, k

    # 3. @chatroom 直接返回
    if "@chatroom" in str(name).lower():
        canonical = known_reverse.get(name, name)
        return name, canonical

    # 4. 词级别模糊匹配（群聊 + 一对一聊天，最近活跃的优先）
    query_words = _split_words(name)
    if query_words:
        candidates = []
        # 先搜群聊（前50个）
        for username, group_name, last_ts in _get_active_groups(db_dir, include_dm=False)[:50]:
            target_words = _split_words(group_name)
            score = _token_overlap_score(query_words, target_words)
            if score >= 0.5:
                candidates.append((score, last_ts, username, group_name))
        # 再搜一对一聊天（前30个），阈值提高到 0.6（人名通常较短，避免误匹配）
        for username, dm_name, last_ts in _get_active_groups(db_dir, include_dm=True)[:30]:
            target_words = _split_words(dm_name)
            score = _token_overlap_score(query_words, target_words)
            if score >= 0.6:
                candidates.append((score, last_ts, username, dm_name))
        if candidates:
            candidates.sort(key=lambda x: (-x[0], -x[1]))
            best = candidates[0]
            log.debug(f"[resolve] 模糊匹配 '{name}' -> '{best[3]}' ({best[2]}, score={best[0]:.2f})")
            return best[2], best[3]

    # 5. wxid_ 开头直接返回（一对一聊天 ID）
    if str(name).startswith("wxid_") or str(name).startswith("gh_"):
        return name, name

    # 5. Fallback: 查 session.db（保留原始逻辑兼容）
    if db_dir:
        session_db = os.path.join(db_dir, "session", "session.db")
        if not os.path.exists(session_db):
            session_db = os.path.join(db_dir, "session.db")
        if os.path.exists(session_db):
            try:
                conn = sqlite3.connect(session_db)
                rows = conn.execute(
                    "SELECT username, summary FROM SessionTable WHERE username LIKE '%@chatroom'"
                ).fetchall()
                conn.close()
                for username, summary in rows:
                    if summary and norm_name in norm(str(summary)):
                        return username, summary or username
            except Exception:
                pass
    return name, name


# ============================================================
# 消息提取核心
# ============================================================

def _extract_raw_rows(group_username, target_date, hour_offset=0, dec_dir=None, cfg=None, since_min=0):
    """从数据库提取原始行数据，返回 list of tuples。
    since_min: 额外偏移分钟数（用于 --since HH:MM 增量提取）
    """
    if cfg is None:
        cfg = load_config()
    keys = load_keys()

    base = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    ts_start = int((base + datetime.timedelta(hours=hour_offset, minutes=since_min)).timestamp())
    ts_end = int((base + datetime.timedelta(days=1, hours=hour_offset)).timestamp())
    table_name = "Msg_" + hashlib.md5(group_username.encode()).hexdigest()
    dctx = zstandard.ZstdDecompressor() if HAS_ZSTD else None

    all_rows = []

    # 策略1: 从已解密目录读取
    if dec_dir and os.path.isdir(dec_dir):
        msg_dir = os.path.join(dec_dir, "message_active")
        if not os.path.isdir(msg_dir):
            msg_dir = os.path.join(dec_dir, "message")
        if not os.path.isdir(msg_dir):
            msg_dir = dec_dir

        msg_dbs = sorted([f for f in os.listdir(msg_dir) if re.match(r"message_\d+\.db$", f)])
        for db_file in msg_dbs:
            db_path = os.path.join(msg_dir, db_file)
            try:
                conn = sqlite3.connect(db_path)
                exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
                ).fetchone()
                if not exists:
                    conn.close(); continue
                db_rows = conn.execute(f'''
                    SELECT create_time, message_content, WCDB_CT_message_content, local_type
                    FROM "{table_name}" WHERE create_time >= ? AND create_time < ?
                    ORDER BY create_time
                ''', (ts_start, ts_end)).fetchall()
                if db_rows:
                    all_rows.extend(db_rows)
                conn.close()
            except Exception:
                pass

    # 策略2: 从加密数据库直接解密读取
    if not all_rows and HAS_CRYPTO and keys:
        db_dir = cfg.get("db_dir", "")
        if db_dir:
            for key_name, key_info in keys.items():
                if not re.match(r"^message/message_\d+\.db$", key_name) or "enc_key" not in key_info:
                    continue
                db_path = os.path.join(db_dir, key_name)
                if not os.path.exists(db_path):
                    continue
                cache = tempfile.mkdtemp(prefix="digest-")
                out = os.path.join(cache, "dec.db")
                try:
                    enc_key = bytes.fromhex(key_info["enc_key"])
                    full_decrypt(db_path, out, enc_key)
                    wal = db_path + "-wal"
                    if os.path.exists(wal):
                        decrypt_wal(wal, out, enc_key)
                    conn = sqlite3.connect(out)
                    exists = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
                    ).fetchone()
                    if exists:
                        db_rows = conn.execute(f'''
                            SELECT create_time, message_content, WCDB_CT_message_content, local_type
                            FROM "{table_name}" WHERE create_time >= ? AND create_time < ?
                            ORDER BY create_time
                        ''', (ts_start, ts_end)).fetchall()
                        all_rows.extend(db_rows)
                    conn.close()
                except Exception:
                    pass

    all_rows.sort(key=lambda r: r[0])
    return all_rows, dctx


def _parse_messages(raw_rows, dctx, contacts=None):
    """将原始行数据解析为 ChatMessage 列表"""
    if contacts is None:
        contacts = {}
    messages = []

    for row in raw_rows:
        ts_val, content, ct_val, lt_val = row[0], row[1], row[2] or 0, row[3] or 0
        if ts_val == 0 or not content:
            continue

        dt_str = datetime.datetime.fromtimestamp(ts_val).strftime("%Y-%m-%d %H:%M")
        real_type = lt_val & 0xFFFFFFFF

        # 解压
        try:
            if ct_val == 4 and dctx and isinstance(content, bytes):
                text = dctx.decompress(content).decode("utf-8", errors="replace")
            elif isinstance(content, bytes):
                text = content.decode("utf-8", errors="replace")
            else:
                text = str(content)
        except Exception:
            continue

        if real_type == 1:
            parts = text.split(":\n", 1)
            if len(parts) == 2:
                sender_id, msg = parts[0].strip(), parts[1].strip()
            else:
                parts2 = text.split("\n", 1)
                if len(parts2) == 2:
                    sender_id, msg = parts2[0].strip(), parts2[1].strip()
                else:
                    sender_id, msg = "unknown", text.strip()
            # 过滤系统消息（撤回/加群/改名等无讨论价值的提示）
            if any(p.search(msg) for p in SYSTEM_MSG_PATTERNS):
                continue
            messages.append(ChatMessage(
                timestamp=ts_val, dt_str=dt_str,
                sender_id=sender_id, sender_name=contacts.get(sender_id, sender_id),
                content=msg, msg_type=1,
            ))
        elif real_type == 34:
            sender_m = re.search(r'fromusername="(.*?)"', text)
            sender_id = sender_m.group(1) if sender_m else "unknown"
            messages.append(ChatMessage(
                timestamp=ts_val, dt_str=dt_str,
                sender_id=sender_id, sender_name=contacts.get(sender_id, sender_id),
                content="[语音]", msg_type=34,
            ))
        elif real_type == 49:
            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", text, re.DOTALL)
            if not title_m:
                title_m = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
            url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", text, re.DOTALL)
            if not url_m:
                url_m = re.search(r"<url>(.*?)</url>", text, re.DOTALL)
            title = title_m.group(1).strip() if title_m else ""
            url = url_m.group(1).strip().replace("&amp;", "&") if url_m else ""
            if not title:
                continue
            sender_m = re.search(r"<fromusername>(.*?)</fromusername>", text)
            sender_id = sender_m.group(1) if sender_m else "unknown"
            # 提取引用原文摘要（<referencedmessage> 下的 <title> 或 <content>）
            ref_summary = ""
            ref_block_m = re.search(r"<referencedmessage>(.*?)</referencedmessage>", text, re.DOTALL)
            if ref_block_m:
                ref_block = ref_block_m.group(1)
                ref_title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", ref_block, re.DOTALL)
                if not ref_title_m:
                    ref_title_m = re.search(r"<title>(.*?)</title>", ref_block, re.DOTALL)
                if ref_title_m:
                    ref_summary = ref_title_m.group(1).strip()[:50]
            messages.append(ChatMessage(
                timestamp=ts_val, dt_str=dt_str,
                sender_id=sender_id, sender_name=contacts.get(sender_id, sender_id),
                content=title, msg_type=49, url=url,
                ref_summary=ref_summary,
            ))
    return messages


# ============================================================
# 消息压缩
# ============================================================

def compress_messages(messages, compact=False):
    """
    压缩消息列表，减少 token 用量。
    compact=True 时执行以下压缩策略：
    1. 过滤纯噪声（语气词、纯emoji、短笑声等）
    2. 过滤引用消息(type=49)中的纯附和回复
    3. 合并同一发送者的连续短消息（≤25字，180s内）
    4. 截断超长消息（>800字截断到前800+省略标记）
    5. 去重：完全相同内容的连续消息只保留首条
    """
    if not compact:
        return messages

    # 常量
    MERGE_MAX_LEN = 25       # 可合并的消息最大字数
    MERGE_WINDOW = 180       # 合并时间窗口（秒）
    TRUNCATE_AT = 800        # 长消息截断阈值
    MAX_CONSEC_DUPE = 2      # 连续相同消息最多保留条数

    result = []
    prev = None
    merge_buffer = []
    consec_dupe_count = 0
    last_content = None

    def flush_merge():
        nonlocal merge_buffer
        if not merge_buffer:
            return
        if len(merge_buffer) == 1:
            result.append(merge_buffer[0])
        else:
            first = merge_buffer[0]
            combined = " | ".join(m.content for m in merge_buffer)
            merged = ChatMessage(
                timestamp=first.timestamp, dt_str=first.dt_str,
                sender_id=first.sender_id, sender_name=first.sender_name,
                content=combined, msg_type=first.msg_type,
            )
            result.append(merged)
        merge_buffer = []

    def is_noise_msg(msg):
        """判断是否为噪声消息"""
        if msg.msg_type == 1:
            stripped = msg.content.strip()
            return any(p.match(stripped) for p in NOISE_PATTERNS)
        return False

    def is_quote_noise(msg):
        """判断引用消息(type=49)是否为纯附和，或可折叠为引用摘要前缀"""
        if msg.msg_type == 49:
            stripped = msg.content.strip()
            # 引用消息本身无正文，只有被引用内容 -> 噪声
            if not stripped:
                return True
            # 正文是纯附和/同意
            if any(p.match(stripped) for p in QUOTE_NOISE_PATTERNS):
                return True
        return False

    def truncate_content(content):
        """截断超长消息"""
        if len(content) > TRUNCATE_AT:
            return content[:TRUNCATE_AT] + "\n...（已截断，原文%d字）" % len(content)
        return content

    for msg in messages:
        # 1. 过滤 type=49 引用消息中的纯附和
        if is_quote_noise(msg):
            continue

        # 2. 过滤纯噪声
        if is_noise_msg(msg):
            continue

        # 3. 连续相同内容去重（跨发送者）
        content = msg.content.strip()
        if content == last_content:
            consec_dupe_count += 1
            if consec_dupe_count >= MAX_CONSEC_DUPE:
                continue  # 跳过第3条及之后的重复
        else:
            consec_dupe_count = 0
            last_content = content

        # 4. 截断超长消息
        if msg.msg_type == 1 and len(msg.content) > TRUNCATE_AT:
            msg = ChatMessage(
                timestamp=msg.timestamp, dt_str=msg.dt_str,
                sender_id=msg.sender_id, sender_name=msg.sender_name,
                content=truncate_content(msg.content), msg_type=msg.msg_type,
                url=msg.url,
            )

        # 5. 合并同一发送者的连续短消息
        if (msg.msg_type == 1 and prev and
            msg.sender_id == prev.sender_id and
            len(msg.content) <= MERGE_MAX_LEN and
            len(prev.content) <= MERGE_MAX_LEN and
            msg.timestamp - prev.timestamp < MERGE_WINDOW):
            merge_buffer.append(msg)
        else:
            flush_merge()
            merge_buffer.append(msg)

        prev = msg

    flush_merge()
    return result


def messages_to_text(messages, compact=False):
    """将消息列表转为文本。"""
    def _sender(msg):
        return msg.sender_name or msg.sender_id

    if not compact:
        lines = []
        for m in messages:
            sender = _sender(m)
            if m.msg_type == 34:
                body = "[语音]"
            elif m.msg_type == 49:
                body = f"[链接] {m.content}"
                if m.url and m.url.startswith("http"):
                    body += f"\n  URL: {m.url}"
            else:
                body = m.content
            lines.append(f"[{m.dt_str}] {sender}: {body}")
        return "\n".join(lines)

    # compact 模式：分段标记时间（只在话题切换时显示时间戳）
    lines = []
    prev_min = None
    SEGMENT_GAP = 60  # 分钟，超过此间隔显示时间标记
    prev_sender_id = None

    for msg in messages:
        ts = msg.dt_str[11:16] if len(msg.dt_str) >= 16 else msg.dt_str
        sender = _sender(msg)
        if msg.msg_type == 34:
            body = "[语音]"
        elif msg.msg_type == 49:
            # compact 模式保留 URL（链接分享有价值信息）
            ref_part = f"[→{msg.ref_summary[:15]}…]" if msg.ref_summary else ""
            body = f"[链接] {msg.content}" + (f" {ref_part}" if ref_part else "")
            if msg.url and msg.url.startswith("http"):
                body += f"\n  {msg.url}"
        else:
            body = msg.content

        # 计算时间分段
        show_ts = False
        try:
            h, m = ts.split(":")
            cur_min = int(h) * 60 + int(m)
            if prev_min is None or abs(cur_min - prev_min) >= SEGMENT_GAP:
                show_ts = True
            prev_min = cur_min
        except (ValueError, IndexError):
            show_ts = True

        # 同一发送者连续消息省略发送者名（话题切换时恢复）
        same_sender = (not show_ts and msg.sender_id == prev_sender_id)

        if show_ts:
            lines.append(f"── [{ts}] ──")
            lines.append(f"{sender}: {body}")
        elif same_sender:
            lines.append(body)
        else:
            lines.append(f"{sender}: {body}")

        prev_sender_id = msg.sender_id

    return "\n".join(lines)


def estimate_tokens(text):
    """粗略估算 token 数（中文约 1.5 token/字，英文约 0.25 token/word）"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.25)


# ============================================================
# Prompt 模板
# ============================================================

def load_prompt_template(prompt_path=None):
    """
    加载 Prompt 模板。优先级：
    1. --prompt 指定路径
    2. ~/.wechat-digest/prompt-template.txt
    3. wechat-digest/prompt-template.txt（项目自带）
    4. 内置默认模板
    """
    candidates = [prompt_path] if prompt_path else []
    candidates.extend([
        os.path.join(STATE_DIR, "prompt-template.txt"),
        os.path.join(_VENDORED_DIGEST_DIR, "prompt-template.txt"),
        os.path.join(_LEGACY_DIGEST_DIR, "prompt-template.txt"),
    ])
    for path in candidates:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
    return DEFAULT_PROMPT_TEMPLATE


def render_prompt(template, group_name, date_str, total_msgs):
    """渲染 Prompt 模板，替换变量"""
    return template.replace("{{GROUP_NAME}}", group_name).replace("{{TARGET_DATE}}", date_str).replace("{{TOTAL}}", str(total_msgs))


# ============================================================
# 缓存
# ============================================================

def _cache_key(group_username, date, compact=False):
    raw = f"{group_username}:{date}:{'c' if compact else 'f'}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"extract_{key}.json")


def load_extract_cache(group_username, date, compact=False, max_age=3600):
    """加载提取缓存（TTL 1h）"""
    key = _cache_key(group_username, date, compact)
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        if time.time() - os.path.getmtime(path) > max_age:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_extract_cache(group_username, date, compact, data):
    """保存提取缓存"""
    key = _cache_key(group_username, date, compact)
    path = _cache_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


# ============================================================
# 摘要缓存（TTL 12h）
# ============================================================

def _summary_cache_key(group_username, date, compact=False, since_min=0, segment=False, prompt_hash=""):
    raw = f"sum:{group_username}:{date}:{'c' if compact else 'f'}:{since_min}:{'seg' if segment else 'full'}:{prompt_hash[:8]}"
    return hashlib.md5(raw.encode()).hexdigest()[:14]


def _summary_cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"summary_{key}.json")


def load_summary_cache(group_username, date, compact=False, since_min=0, segment=False, prompt_hash="", max_age=43200):
    """加载摘要缓存（TTL 12h）"""
    key = _summary_cache_key(group_username, date, compact, since_min, segment, prompt_hash)
    path = _summary_cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        if time.time() - os.path.getmtime(path) > max_age:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_summary_cache(group_username, date, compact, since_min, segment, prompt_hash, summary_text):
    """保存摘要缓存"""
    key = _summary_cache_key(group_username, date, compact, since_min, segment, prompt_hash)
    path = _summary_cache_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary_text, "cached_at": time.time()}, f, ensure_ascii=False)
    except Exception:
        pass


def _safe_name(name):
    """将群名/路径不安全字符替换为下划线，用于自动保存目录名"""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip('_') or "unknown_group"


def _segment_messages(messages, gap_hours=4):
    """
    将消息列表按时间间隔切分为多段。
    gap_hours: 相邻消息超过此小时间隔则开启新段（默认 4 小时）
    返回: list of (label, messages_in_segment)
      label 示例: "上午 (08:00-11:45)"
    """
    if not messages:
        return []

    gap_secs = gap_hours * 3600
    segments = []
    current_seg = [messages[0]]

    for msg in messages[1:]:
        if msg.timestamp - current_seg[-1].timestamp >= gap_secs:
            segments.append(current_seg)
            current_seg = [msg]
        else:
            current_seg.append(msg)
    if current_seg:
        segments.append(current_seg)

    def _ts_label(ts):
        return datetime.datetime.fromtimestamp(ts).strftime("%H:%M")

    result = []
    for seg in segments:
        if not seg:
            continue
        t_start = _ts_label(seg[0].timestamp)
        t_end = _ts_label(seg[-1].timestamp)
        label = f"{t_start}-{t_end} [{len(seg)}条]"
        result.append((label, seg))
    return result




# ============================================================
# decrypt 子命令
# ============================================================

def cmd_decrypt(args):
    if not HAS_CRYPTO:
        print("ERROR: pycryptodome 未安装", file=sys.stderr); sys.exit(1)
    cfg = load_config(); keys = load_keys()
    db_dir = cfg.get("db_dir", "")
    out_dir = cfg.get("decrypted_dir", DEFAULT_DECRYPTED_DIR)
    if not db_dir or not os.path.isdir(db_dir):
        print("ERROR: db_dir 未配置或不存在", file=sys.stderr); sys.exit(1)
    if not keys:
        print("ERROR: 未找到密钥文件", file=sys.stderr); sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    total_pages = total_wal = 0
    for key_name, key_info in keys.items():
        if "enc_key" not in key_info:
            continue
        db_path = os.path.join(db_dir, key_name)
        if not os.path.exists(db_path):
            continue
        rel_out = os.path.join(out_dir, key_name)
        enc_key = bytes.fromhex(key_info["enc_key"])
        try:
            pages = full_decrypt(db_path, rel_out, enc_key)
            total_pages += pages
            wal_path = db_path + "-wal"
            if os.path.exists(wal_path):
                patched = decrypt_wal(wal_path, rel_out, enc_key)
                total_wal += patched
                print(f"  {key_name}: {pages}页 + {patched}WAL", file=sys.stderr)
            else:
                print(f"  {key_name}: {pages}页", file=sys.stderr)
        except Exception as e:
            print(f"  {key_name}: 失败 ({e})", file=sys.stderr)
    print(f"\n完成: {total_pages}页, {total_wal}WAL帧", file=sys.stderr)
    return {"total_pages": total_pages, "total_wal": total_wal}


# ============================================================
# groups 子命令
# ============================================================

def cmd_groups(args):
    cfg = load_config(); keys = load_keys()
    dec_dir = cfg.get("decrypted_dir", "")
    session_db = None

    if dec_dir and os.path.isdir(dec_dir):
        for c in [os.path.join(dec_dir, "session", "session.db"), os.path.join(dec_dir, "session.db")]:
            if os.path.exists(c):
                session_db = c; break

    if not session_db and HAS_CRYPTO and keys:
        db_dir = cfg.get("db_dir", "")
        if db_dir:
            session_src = os.path.join(db_dir, "session", "session.db")
            if os.path.exists(session_src) and "session/session.db" in keys:
                try:
                    enc_key = bytes.fromhex(keys["session/session.db"]["enc_key"])
                    cache = tempfile.mkdtemp(prefix="digest-session-")
                    session_db = os.path.join(cache, "session_dec.db")
                    full_decrypt(session_src, session_db, enc_key)
                    wal = session_src + "-wal"
                    if os.path.exists(wal):
                        decrypt_wal(wal, session_db, enc_key)
                except Exception:
                    session_db = None

    if not session_db:
        _error_exit("无法获取群列表，请先运行 decrypt", args.json)

    is_dm = getattr(args, 'dm', False)

    if is_dm:
        sql = (
            "SELECT username, summary, last_timestamp FROM SessionTable "
            "WHERE username NOT LIKE '%@chatroom' "
            "AND username NOT IN ('filehelper','notifymessage','brandsessionholder','brandservicesessionholder','@placeholder_foldgroup') "
            "AND last_timestamp > 1700000000 "
            "ORDER BY last_timestamp DESC"
        )
        contact_filter = ""  # 不限制 @chatroom
    else:
        sql = (
            "SELECT username, summary, last_timestamp FROM SessionTable "
            "WHERE username LIKE '%@chatroom' ORDER BY last_timestamp DESC"
        )
        contact_filter = "WHERE username LIKE '%@chatroom' AND"

    conn = sqlite3.connect(session_db)
    rows = conn.execute(sql).fetchall()
    conn.close()

    # 从 contact.db 读取联系人名（群和个人都读）
    contact_names = {}
    if dec_dir and os.path.isdir(dec_dir):
        for c in [os.path.join(dec_dir, "contact", "contact.db"), os.path.join(dec_dir, "contact.db")]:
            if not os.path.exists(c):
                continue
            try:
                cconn = sqlite3.connect(c)
                crows = cconn.execute(
                    'SELECT username, nick_name, remark, alias FROM contact '
                    f"{contact_filter} delete_flag = 0"
                ).fetchall()
                cconn.close()
                for username, nick, remark, alias in crows:
                    name = (remark or alias or nick or "").strip()
                    if name:
                        contact_names[username] = name
                break
            except Exception:
                continue

    try:
        for uid, name in get_contacts(use_cache=True).items():
            if uid and name and uid not in contact_names:
                contact_names[uid] = name
    except Exception:
        pass

    known_reverse = {v: k for k, v in cfg.get("known", {}).items()}
    results = []
    for username, summary, last_ts in rows:
        name = known_reverse.get(username) or contact_names.get(username)
        if not name and summary:
            summary_text = str(summary).strip()
            if summary_text and not summary_text.startswith("gh_") and len(summary_text) <= 40:
                name = summary_text
        if not name:
            name = username
        results.append({
            "username": username,
            "name": name,
            "last_msg": (summary or "")[:80],
            "last_ts": last_ts,
            "last_time": datetime.datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d %H:%M") if last_ts > 1e9 else "",
        })

    label = "一对一聊天" if is_dm else "群聊"
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== 共 {len(results)} 个{label} ===\n")
        for r in results:
            print(f"  {r['username']}")
            if r['name'] != r['username']:
                name_label = "联系人" if is_dm else "群名"
                print(f"    {name_label}: {r['name']}")
            if r['last_msg']:
                print(f"    最近: {r['last_msg']}")
            if r['last_time']:
                print(f"    活跃: {r['last_time']}")
            print()
    return results


# ============================================================
# contacts 子命令
# ============================================================

def cmd_contacts(args):
    """导出联系人 ID→昵称映射"""
    contacts = get_contacts(use_cache=not getattr(args, 'no_cache', False))
    if args.json:
        print(json.dumps(contacts, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== 共 {len(contacts)} 个联系人 ===\n")
        for uid, name in sorted(contacts.items(), key=lambda x: x[1]):
            print(f"  {uid}: {name}")
    return contacts


# ============================================================
# extract 子命令
# ============================================================

def _do_extract(group_name, target_date, hour_offset=0, compact=False, no_cache=False, json_mode=False, since_min=0):
    """提取消息的核心逻辑，返回 (messages_list, group_username, canonical_name)。
    since_min: 从当天第 since_min 分钟开始提取（用于 --since HH:MM）
    """
    cfg = load_config()
    dec_dir = cfg.get("decrypted_dir", "")
    group_username, canonical_name = resolve_group(group_name, db_dir=dec_dir)

    # 检查缓存（since_min != 0 时不使用缓存，因为增量范围可变）
    cached = None if no_cache or since_min else load_extract_cache(group_username, target_date, compact)
    if cached:
        messages = [ChatMessage(**m) for m in cached.get("messages", [])]
        log.info(f"[cache] 命中缓存: {len(messages)} 条消息")
        return messages, group_username, canonical_name

    contacts = get_contacts(use_cache=not no_cache)
    raw_rows, dctx = _extract_raw_rows(group_username, target_date, hour_offset, dec_dir, cfg, since_min=since_min)
    messages = _parse_messages(raw_rows, dctx, contacts)

    if compact:
        before = len(messages)
        messages = compress_messages(messages, compact=True)
        log.info(f"[compact] {before} → {len(messages)} 条（压缩 {before - len(messages)} 条）")

    # 保存缓存（only when since_min == 0，增量查询不缓存）
    if not since_min:
        cache_data = {
            "group": group_name, "username": group_username, "date": target_date,
            "message_count": len(messages), "compact": compact,
            "messages": [m.to_dict() for m in messages],
        }
        save_extract_cache(group_username, target_date, compact, cache_data)

    return messages, group_username, canonical_name


def cmd_extract(args):
    group_name = args.group
    target_date = args.date
    hour_offset = args.hour_offset or 0
    compact = getattr(args, 'compact', False)
    no_cache = getattr(args, 'no_cache', False)

    messages, group_username, canonical_name = _do_extract(group_name, target_date, hour_offset, compact, no_cache)
    print(f"群: {group_name} -> {canonical_name} ({group_username})", file=sys.stderr)
    print(f"消息数: {len(messages)}", file=sys.stderr)

    if args.json:
        result = {
            "group": group_name, "username": group_username, "date": target_date,
            "message_count": len(messages), "compact": compact,
            "messages": [m.to_dict() for m in messages],
            "messages_text": messages_to_text(messages, compact),
        }
        json_text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_text)
            print(f"已保存到 {args.output}", file=sys.stderr)
        else:
            print(json_text)
    elif args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(messages_to_text(messages, compact))
        print(f"已保存到 {args.output}", file=sys.stderr)
    else:
        print(messages_to_text(messages, compact))

    return messages


# ============================================================
# summarize 子命令
# ============================================================

def _resolve_date(date_str):
    """解析日期字符串，支持 today/yesterday/YYYY-MM-DD。"""
    if not date_str or date_str == "yesterday":
        return (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if date_str == "today":
        return datetime.date.today().strftime("%Y-%m-%d")
    return date_str  # 直接当 YYYY-MM-DD 使用


def _call_llm(messages_text, group_name, date_str, config, prompt_template=None, total_msgs=0, batch_mode=False):
    """调用 LLM API，支持重试
    
    Args:
        batch_mode: 是否使用批量推理（成本更低，适合定时任务）
    """
    # 批量推理模式
    if batch_mode:
        return _call_llm_batch(messages_text, group_name, date_str, config, prompt_template, total_msgs)
    
    # 实时推理模式（原逻辑）
    provider = config.get("provider", "glm")
    api_key = config.get("api_key", "")
    base_url = config.get("base_url")
    model = config.get("model")
    temperature = float(config.get("temperature", "0.7"))
    max_tokens = int(config.get("max_tokens", "4096"))

    if provider in LLM_PROVIDERS:
        prov = LLM_PROVIDERS[provider]
        if not base_url:
            base_url = prov["base_url"]
        if not model:
            model = prov["models"][0]

    if not api_key:
        return None, "API Key 未配置"

    # 渲染 prompt
    template = prompt_template or DEFAULT_PROMPT_TEMPLATE
    system_prompt = render_prompt(template, group_name, date_str, total_msgs)
    user_content = f"以下是「{group_name}」在 {date_str} 的聊天记录:\n\n{messages_text}"

    # Token 估算预警
    est_tokens = estimate_tokens(system_prompt + user_content)
    print(f"[LLM] provider={provider}, model={model}, 估算token≈{est_tokens}", file=sys.stderr)
    if est_tokens > 100000:
        print(f"[WARN] 估算token超10万，可能超限。建议使用 --compact 压缩。", file=sys.stderr)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = json.dumps(payload).encode("utf-8")

    # 重试逻辑：3次，指数退避，只重试可重试错误
    max_retries = 3
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=300)
            result = json.loads(resp.read())
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"], None
            elif "result" in result:
                return result["result"], None
            else:
                return f"# API 返回异常\n\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```", None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            retryable = e.code in (429, 500, 502, 503, 504)
            if retryable and attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[LLM] HTTP {e.code}, {wait}s后重试 ({attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            return f"# API 错误 ({e.code})\n\n```\n{body[:500]}\n```", f"HTTP {e.code}"
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[LLM] 网络错误, {wait}s后重试 ({attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            return f"# 请求失败\n\n错误: {e}", "网络错误"
        except Exception as e:
            return f"# 请求失败\n\n错误: {e}", str(e)

    return "# 重试耗尽", "重试耗尽"


def _call_llm_batch(messages_text, group_name, date_str, config, prompt_template=None, total_msgs=0):
    """调用火山方舟批量推理API（成本更低，适合定时任务）
    
    要求：
    - 已安装 volcenginesdkarkruntime: pip install "volcengine-python-sdk[ark]"
    - 已配置 ARK_API_KEY 环境变量或 batch_api_key
    - 已配置 batch_endpoint（批量推理端点ID）
    """
    batch_provider = config.get("batch_provider", "ark")
    batch_endpoint = config.get("batch_endpoint", "")
    api_key = config.get("batch_api_key", "") or config.get("api_key", "")
    
    if not HAS_ARK_BATCH:
        return None, "未安装火山方舟SDK，请运行: pip install 'volcengine-python-sdk[ark]'"
    
    if not api_key:
        return None, "批量推理 API Key 未配置（设置 ARK_API_KEY 环境变量）"
    
    if not batch_endpoint:
        return None, "批量推理端点ID未配置（设置 LLM_BATCH_ENDPOINT 环境变量或 batch_endpoint 配置）"
    
    # 渲染 prompt
    template = prompt_template or DEFAULT_PROMPT_TEMPLATE
    system_prompt = render_prompt(template, group_name, date_str, total_msgs)
    user_content = f"以下是「{group_name}」在 {date_str} 的聊天记录:\n\n{messages_text}"
    
    # Token 估算
    est_tokens = estimate_tokens(system_prompt + user_content)
    print(f"[LLM-Batch] provider={batch_provider}, endpoint={batch_endpoint[:20]}..., 估算token≈{est_tokens}", file=sys.stderr)
    
    # 使用 asyncio 运行异步批量推理
    try:
        result = asyncio.run(_async_batch_chat(api_key, batch_endpoint, system_prompt, user_content))
        if result:
            return result, None
        return None, "批量推理返回空结果"
    except Exception as e:
        return None, f"批量推理调用失败: {e}"


async def _async_batch_chat(api_key, endpoint, system_prompt, user_content):
    """异步批量推理调用"""
    client = AsyncArk(
        api_key=api_key,
        timeout=24 * 3600,  # 24小时超时（批量推理可能需要较长时间）
    )
    
    completion = await client.batch.chat.completions.create(
        model=endpoint,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    )
    
    # 解析响应
    if completion.choices and len(completion.choices) > 0:
        return completion.choices[0].message.content
    return None


def _parse_since(since_str):
    """解析 HH:MM 格式为分钟数偏移，失败返回 0"""
    if not since_str:
        return 0
    try:
        parts = since_str.strip().split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except Exception:
        return 0


def _auto_output_path(group_name, date_str, since_min=0):
    """自动生成输出路径：<output_dir>/{safe_group}/{date}.md
    group_name: 优先使用 canonical_name（标准群名），保证同一群不会产生多个目录。
    """
    cfg = load_config()
    out_root = cfg.get("output_dir", DEFAULT_OUTPUT_DIR)
    safe_group = _safe_name(group_name)
    fname = f"{date_str}.md"
    return os.path.join(out_root, safe_group, fname)


def cmd_summarize(args):
    group_name = args.group
    target_date = args.date
    hour_offset = args.hour_offset or 0
    compact = not getattr(args, 'full', False)  # compact 默认 True，--full 关闭
    no_cache = getattr(args, 'no_cache', False)
    prompt_path = getattr(args, 'prompt', None)
    since_str = getattr(args, 'since', None)
    since_min = _parse_since(since_str)
    do_segment = getattr(args, 'segment', False)
    batch_mode = getattr(args, 'batch_mode', False)

    messages, group_username, canonical_name = _do_extract(
        group_name, target_date, hour_offset, compact, no_cache, since_min=since_min
    )
    if not messages:
        _error_exit(f"{target_date} 没有消息可摘要", getattr(args, 'json', False))

    log.info(f"\n共 {len(messages)} 条消息，开始生成摘要...")
    if batch_mode:
        log.info("[模式] 批量推理（成本优化）")
    est = estimate_tokens(messages_to_text(messages, compact))
    log.info(f"消息文本估算 ≈{est} tokens")

    config = load_llm_config()
    # 批量模式检查 batch_api_key，实时模式检查 api_key
    if batch_mode:
        if not config.get("batch_api_key") and not config.get("api_key"):
            _error_exit("未配置批量推理 API Key。设置: ARK_API_KEY 环境变量", getattr(args, 'json', False))
        if not config.get("batch_endpoint"):
            _error_exit("未配置批量推理端点ID。设置: LLM_BATCH_ENDPOINT 环境变量", getattr(args, 'json', False))
    else:
        if not config.get("api_key"):
            _error_exit("未配置 LLM API Key。设置: WECHAT_LLM_API_KEY 环境变量", getattr(args, 'json', False))

    prompt_template = load_prompt_template(prompt_path)
    prompt_hash = hashlib.md5(prompt_template.encode()).hexdigest()

    # 确定输出路径（用 canonical_name 保证同一群不会产生多个目录）
    output_path = getattr(args, 'output', None)
    if not output_path:
        output_path = _auto_output_path(canonical_name, target_date, since_min)

    if do_segment:
        # ---- 分段摘要模式 ----
        segments = _segment_messages(messages, gap_hours=4)
        if not segments:
            _error_exit(f"{target_date} 切段后无消息", getattr(args, 'json', False))
        log.info(f"[segment] 切分为 {len(segments)} 段，每段独立调用 LLM")

        all_summaries = []
        for seg_label, seg_msgs in segments:
            seg_text = messages_to_text(seg_msgs, compact)
            seg_tokens = estimate_tokens(seg_text)
            log.info(f"  段 [{seg_label}] {len(seg_msgs)}条 ≈{seg_tokens}tokens")

            # 段级摘要缓存
            seg_cache_key = f"{seg_label}_{prompt_hash[:8]}"
            seg_ph = hashlib.md5(seg_cache_key.encode()).hexdigest()
            seg_summary = None
            if not no_cache:
                cached_seg = load_summary_cache(group_username, target_date, compact, since_min, True, seg_ph)
                if cached_seg:
                    seg_summary = cached_seg.get("summary", "")
                    log.info(f"  [cache] 命中段缓存: {seg_label}")

            if seg_summary is None:
                seg_summary, err = _call_llm(seg_text, group_name, target_date, config, prompt_template, len(seg_msgs), batch_mode=batch_mode)
                if err:
                    log.warning(f"  段 [{seg_label}] LLM 失败: {err}")
                    seg_summary = f"*（该时间段摘要生成失败: {err}）*"
                else:
                    save_summary_cache(group_username, target_date, compact, since_min, True, seg_ph, seg_summary)

            all_summaries.append((seg_label, seg_summary))

        # 合并分段输出
        merged_lines = [f"# {group_name} 群聊摘要 - {target_date}", ""]
        for seg_label, seg_sum in all_summaries:
            merged_lines.append(f"## 时段 {seg_label}")
            merged_lines.append("")
            merged_lines.append(seg_sum)
            merged_lines.append("")
        summary = "\n".join(merged_lines)

    else:
        # ---- 普通（全天）摘要模式 ----
        messages_text = messages_to_text(messages, compact)

        summary = None
        if not no_cache:
            cached_sum = load_summary_cache(group_username, target_date, compact, since_min, False, prompt_hash)
            if cached_sum:
                summary = cached_sum.get("summary", "")
                log.info(f"[cache] 命中摘要缓存")

        if summary is None:
            summary, error = _call_llm(messages_text, group_name, target_date, config, prompt_template, len(messages), batch_mode=batch_mode)
            if error:
                log.warning(f"ERROR: LLM 调用失败 - {error}")
            if summary is None:
                _error_exit("API Key 未配置", getattr(args, 'json', False))
            save_summary_cache(group_username, target_date, compact, since_min, False, prompt_hash, summary)

    # 摘要质量统计
    summary_chars = len(summary)
    summary_sections = len(re.findall(r'^#{1,3} ', summary, re.MULTILINE))
    log.info(f"[摘要] {summary_chars}字 / {summary_sections}个章节")

    # 写文件（--since 模式追加，否则覆盖）
    report_full = getattr(args, 'report_full', False)
    report = _build_report(messages, summary, group_name, target_date, compact, full=report_full, since_str=since_str)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if since_min and os.path.exists(output_path):
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n")
            f.write(report)
        log.info(f"摘要已追加: {output_path}")
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        log.info(f"报告已保存: {output_path}")

    print(summary)
    return summary


def _build_report(messages, summary_text, group_name, date_str, compact=False, full=False, since_str=None):
    lines = [summary_text, ""]
    if full:
        lines.extend(["---", "", "## 聊天详情", ""])
        lines.extend(m.format_line(compact=compact) for m in messages)
    lines.append("")
    lines.append(f"*报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    since_note = f" | 起始时间: {since_str}" if since_str else ""
    lines.append(f"*消息数: {len(messages)} | 压缩: {'是' if compact else '否'}{since_note}*")
    return "\n".join(lines)


# ============================================================
# batch 子命令
# ============================================================

def cmd_batch(args):
    """批量生成多天摘要"""
    group_name = args.group
    # batch 子命令默认启用批量模式（如果用户显式传了 --batch-mode 或默认开启）
    batch_mode = getattr(args, 'batch_mode', True)  # batch 命令默认开启批量模式

    # 解析日期列表
    dates = []
    if getattr(args, 'last_n', None):
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                 for i in range(args.last_n, 0, -1)]
    elif getattr(args, 'date_range', None):
        try:
            start_s, end_s = args.date_range.split(":", 1)
            start = datetime.date.fromisoformat(start_s.strip())
            end = datetime.date.fromisoformat(end_s.strip())
            d = start
            while d <= end:
                dates.append(d.strftime("%Y-%m-%d"))
                d += datetime.timedelta(days=1)
        except Exception as e:
            _error_exit(f"日期范围格式错误，应为 YYYY-MM-DD:YYYY-MM-DD，错误: {e}")
    else:
        _error_exit("batch 需要日期范围 (DATE:DATE) 或 --last-n N")

    mode_str = "批量推理" if batch_mode else "实时推理"
    log.info(f"=== batch: {group_name} / {len(dates)} 天 / {mode_str} ===")
    success, fail = 0, 0

    for date_str in dates:
        log.info(f"\n--- {date_str} ---")
        # 构造一个模拟 args 对象
        sub_args = argparse.Namespace(
            group=group_name, date=date_str,
            hour_offset=getattr(args, 'hour_offset', 0),
            full=getattr(args, 'full', False),
            no_cache=getattr(args, 'no_cache', False),
            report_full=getattr(args, 'report_full', False),
            prompt=getattr(args, 'prompt', None),
            output=None, since=None, segment=False,
            json=False,
            batch_mode=batch_mode,
        )
        try:
            cmd_summarize(sub_args)
            success += 1
        except SystemExit:
            log.warning(f"  {date_str}: 无消息或失败，跳过")
            fail += 1
        except Exception as e:
            log.warning(f"  {date_str}: 错误 - {e}")
            fail += 1

    log.info(f"\n=== batch 完成: {success} 成功 / {fail} 失败 ===")


# ============================================================
# run 子命令
# ============================================================

def cmd_run(args):
    group_name = args.group
    target_date = args.date
    log.info(f"=== digest run: {group_name} / {target_date} ===\n")

    # 检查是否需要解密（decrypted_dir 有文件则跳过）
    cfg = load_config()
    dec_dir = cfg.get("decrypted_dir", "")
    needs_decrypt = True
    if dec_dir and os.path.isdir(dec_dir):
        # 检查 message_active 或 message 子目录中是否有 db 文件
        for subdir in ["message_active", "message"]:
            d = os.path.join(dec_dir, subdir)
            if os.path.isdir(d) and any(f.endswith(".db") for f in os.listdir(d)):
                needs_decrypt = False
                break

    if needs_decrypt:
        log.info("[1/2] 解密数据库...")
        cmd_decrypt(argparse.Namespace())
    else:
        log.info("[1/2] 已有解密数据，跳过解密")

    log.info("[2/2] 提取消息并生成摘要...")
    cmd_summarize(args)


# ============================================================
# test-api 子命令
# ============================================================

def cmd_test_api(args):
    config = load_llm_config()
    provider = config.get("provider", "未配置")
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")
    model = config.get("model", "")
    
    # 批量推理配置
    batch_provider = config.get("batch_provider", "未配置")
    batch_endpoint = config.get("batch_endpoint", "")
    batch_api_key = config.get("batch_api_key", "")

    print("=== 实时推理配置 ===", file=sys.stderr)
    print(f"  provider: {provider}", file=sys.stderr)
    print(f"  model:    {model}", file=sys.stderr)
    print(f"  base_url: {base_url}", file=sys.stderr)
    print(f"  api_key:  {api_key[:8]}..." if api_key else "  api_key:  (空)", file=sys.stderr)
    
    print("\n=== 批量推理配置 ===", file=sys.stderr)
    print(f"  provider:     {batch_provider}", file=sys.stderr)
    print(f"  endpoint:     {batch_endpoint[:30]}..." if batch_endpoint else "  endpoint:     (空)", file=sys.stderr)
    print(f"  api_key:      {batch_api_key[:8]}..." if batch_api_key else "  api_key:      (空)", file=sys.stderr)
    print(f"  SDK状态:      {'已安装' if HAS_ARK_BATCH else '未安装'}", file=sys.stderr)

    if not api_key:
        print("\nERROR: 实时推理 API Key 未配置", file=sys.stderr)
    else:
        # 测试实时推理
        if provider in LLM_PROVIDERS and not base_url:
            base_url = LLM_PROVIDERS[provider]["base_url"]

        payload = {"model": model, "messages": [{"role": "user", "content": "回复OK"}], "max_tokens": 10, "stream": False}
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        print(f"\n测试实时推理: {url}", file=sys.stderr)

        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            if "choices" in result:
                print(f"OK! 模型回复: {result['choices'][0]['message']['content']}", file=sys.stderr)
            else:
                print(f"WARN: 连接成功但返回格式异常", file=sys.stderr)
        except urllib.error.HTTPError as e:
            print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
    
    # 批量推理配置检查
    if batch_api_key and batch_endpoint:
        print(f"\n批量推理配置完整，可通过 --batch-mode 使用", file=sys.stderr)
    else:
        print(f"\n提示: 配置 ARK_API_KEY 和 LLM_BATCH_ENDPOINT 后可使用批量推理（成本更低）", file=sys.stderr)


# ============================================================
# config 子命令
# ============================================================

def cmd_config(args):
    cfg = load_config()
    if args.show or (not args.set and not args.init):
        safe = dict(cfg)
        if "db_key" in safe and safe["db_key"]:
            safe["db_key"] = safe["db_key"][:8] + "..."
        if "llm" in safe and "api_key" in safe["llm"] and safe["llm"]["api_key"]:
            safe["llm"]["api_key"] = safe["llm"]["api_key"][:8] + "..."
        print(json.dumps(safe, indent=2, ensure_ascii=False))
        return

    if args.init:
        print("=== 初始化配置 ===\n")
        try:
            from crypto.config import auto_detect_db_dir
            detected = auto_detect_db_dir()
            if detected:
                cfg["db_dir"] = detected
                print(f"  自动检测到: {detected}")
        except Exception:
            pass
        if not cfg.get("db_dir"):
            db_input = input("  请输入微信数据目录: ").strip()
            if db_input:
                cfg["db_dir"] = db_input
        cfg.setdefault("decrypted_dir", DEFAULT_DECRYPTED_DIR)
        cfg.setdefault("output_dir", DEFAULT_OUTPUT_DIR)
        cfg.setdefault("known", {})
        save_config(cfg)
        print(f"\n  配置已保存到: {CONFIG_FILE}")
        return

    if args.set:
        for pair in args.set:
            if "=" not in pair:
                print(f"ERROR: 格式应为 KEY=VALUE", file=sys.stderr); continue
            key, value = pair.split("=", 1)
            parts = key.split(".")
            target = cfg
            for p in parts[:-1]:
                target = target.setdefault(p, {})
            target[parts[-1]] = value
        save_config(cfg)
        print(f"配置已更新: {args.set}")


# ============================================================
# 错误处理工具
# ============================================================

def _error_exit(msg, json_mode=False):
    """统一错误退出"""
    if json_mode:
        print(json.dumps({"error": msg}, ensure_ascii=False))
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="微信群聊摘要工具 V2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python digest.py groups --json                    # 列出群（JSON）
  python digest.py contacts --json                  # 导出联系人映射
  python digest.py extract "AI实践"                 # 提取昨天消息（默认）
  python digest.py extract "AI实践" 2026-04-13 --compact --json  # 压缩模式
  python digest.py summarize "AI实践"               # 昨天摘要，自动保存
  python digest.py summarize "AI实践" today         # 今天摘要
  python digest.py summarize "AI实践" today --since 14:00       # 今天14点后增量
  python digest.py summarize "AI实践" --segment           # 分时段摘要（默认 compact）
  python digest.py summarize "AI实践" --full              # 关闭压缩，完整消息文本
  python digest.py summarize "AI实践" --batch-mode        # 批量推理（省成本）
  python digest.py batch "AI实践" --last-n 7              # 最近7天批量（默认 compact + 批量推理）
  python digest.py batch "AI实践" 2026-04-10:2026-04-16         # 日期范围批量
  python digest.py run "AI实践"                     # 一键全流程（昨天）
  python digest.py run "AI实践" --batch-mode        # 一键全流程（批量推理）
  python digest.py --quiet summarize "AI实践"       # 静默模式

环境变量配置：
  实时推理: WECHAT_LLM_API_KEY, LLM_PROVIDER, LLM_MODEL
  批量推理: ARK_API_KEY, LLM_BATCH_ENDPOINT
        """,
    )

    # 全局参数
    parser.add_argument("--no-cache", action="store_true", help="跳过缓存，强制重新提取")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式，只输出最终结果")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # groups
    p = subparsers.add_parser("groups", help="列出活跃群聊")
    p.add_argument("--date", help="筛选指定日期活跃的群")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")
    p.add_argument("--dm", "--dm", action="store_true", dest="dm", help="显示一对一聊天（而非群聊）")

    # contacts (V2新增)
    p = subparsers.add_parser("contacts", help="导出联系人ID→昵称映射")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")

    # extract
    p = subparsers.add_parser("extract", help="提取群聊消息")
    p.add_argument("group", help="群名称或 username")
    p.add_argument("date", nargs="?", default="yesterday", help="目标日期 YYYY-MM-DD / today / yesterday（默认昨天）")
    p.add_argument("--hour-offset", type=int, default=0, help="时间窗口偏移小时数")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")
    p.add_argument("--compact", action="store_true", help="压缩消息（省 30-50%% token）")
    p.add_argument("--output", "-o", help="输出文件路径")

    # summarize
    p = subparsers.add_parser("summarize", help="LLM 生成摘要")
    p.add_argument("group", help="群名称")
    p.add_argument("date", nargs="?", default="yesterday", help="目标日期 YYYY-MM-DD / today / yesterday（默认昨天）")
    p.add_argument("--hour-offset", type=int, default=0, help="时间窗口偏移小时数")
    p.add_argument("--full", action="store_true", help="关闭压缩模式，使用完整消息文本（默认 compact 压缩）")
    p.add_argument("--no-cache", action="store_true", help="跳过提取缓存")
    p.add_argument("--report-full", action="store_true", help="在报告中包含完整聊天详情")
    p.add_argument("--prompt", help="自定义 Prompt 模板文件路径")
    p.add_argument("--output", "-o", help="输出文件路径（默认自动保存到用户目录下的 output/群名/日期.md）")
    p.add_argument("--since", metavar="HH:MM", help="只处理该时间点之后的消息（增量模式）")
    p.add_argument("--segment", action="store_true", help="按时间段切分摘要（每段独立调用 LLM）")
    p.add_argument("--batch-mode", action="store_true", help="使用批量推理API（成本更低，适合定时任务）")

    # run
    p = subparsers.add_parser("run", help="一键全流程")
    p.add_argument("group", help="群名称")
    p.add_argument("date", nargs="?", default="yesterday", help="目标日期 YYYY-MM-DD / today / yesterday（默认昨天）")
    p.add_argument("--hour-offset", type=int, default=0)
    p.add_argument("--full", action="store_true", help="关闭压缩模式（默认 compact 压缩）")
    p.add_argument("--no-cache", action="store_true", help="跳过提取缓存")
    p.add_argument("--report-full", action="store_true", help="在报告中包含完整聊天详情")
    p.add_argument("--prompt", help="自定义 Prompt 模板文件路径")
    p.add_argument("--output", "-o", help="输出文件路径（默认自动保存到用户目录下的 output/群名/日期.md）")
    p.add_argument("--since", metavar="HH:MM", help="只处理该时间点之后的消息（增量模式）")
    p.add_argument("--segment", action="store_true", help="按时间段切分摘要（每段独立调用 LLM）")
    p.add_argument("--batch-mode", action="store_true", help="使用批量推理API（成本更低，适合定时任务）")

    # batch
    p = subparsers.add_parser("batch", help="批量生成多天摘要")
    p.add_argument("group", help="群名称")
    p.add_argument("date_range", nargs="?", metavar="START:END", help="日期范围，格式 YYYY-MM-DD:YYYY-MM-DD")
    p.add_argument("--last-n", type=int, dest="last_n", metavar="N", help="最近 N 天（不传 date_range 时使用）")
    p.add_argument("--hour-offset", type=int, default=0)
    p.add_argument("--full", action="store_true", help="关闭压缩模式（默认 compact 压缩）")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--report-full", action="store_true", help="在报告中包含完整聊天详情")
    p.add_argument("--prompt", help="自定义 Prompt 模板文件路径")
    p.add_argument("--batch-mode", action="store_true", help="使用批量推理API（成本更低，适合定时任务，默认开启）")

    # decrypt
    subparsers.add_parser("decrypt", help="解密所有微信数据库")

    # test-api
    subparsers.add_parser("test-api", help="测试 LLM API 连接")

    # config
    p = subparsers.add_parser("config", help="查看/修改配置")
    p.add_argument("--show", action="store_true", help="显示当前配置")
    p.add_argument("--set", nargs="+", metavar="KEY=VALUE", help="设置配置项")
    p.add_argument("--init", action="store_true", help="交互式初始化配置")

    args = parser.parse_args()
    if not args.command:
        parser.print_help(); sys.exit(0)

    # --quiet 静默模式
    if getattr(args, 'quiet', False):
        logging.getLogger("wechat-digest").setLevel(logging.WARNING)

    # 全局 --no-cache 连通到子命令
    if getattr(args, 'no_cache', False) is False:
        # 子命令自己的 --no-cache 已经在各子解析器中定义，全局的只补充没有子命令 --no-cache 的情况
        pass
    # 如果全局 no_cache=True 但子命令 args 里还没有该属性，补充
    global_no_cache = getattr(args, 'no_cache', False)
    if global_no_cache:
        args.no_cache = True

    # 解析 date 参数为标准 YYYY-MM-DD
    if hasattr(args, 'date') and args.date:
        args.date = _resolve_date(args.date)

    cmd_map = {
        "groups": cmd_groups, "contacts": cmd_contacts,
        "extract": cmd_extract, "summarize": cmd_summarize,
        "run": cmd_run, "batch": cmd_batch, "decrypt": cmd_decrypt,
        "test-api": cmd_test_api, "config": cmd_config,
    }

    handler = cmd_map.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n中断", file=sys.stderr); sys.exit(130)
        except Exception as e:
            json_mode = getattr(args, 'json', False)
            if json_mode:
                print(json.dumps({"error": str(e)}, ensure_ascii=False))
            else:
                print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
