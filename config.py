"""
config.py – Cấu hình mặc định + Runtime config tải từ data/config.json
Mọi thứ có giá trị mặc định sẵn, admin có thể đổi qua lệnh /config
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

# ─── Bắt buộc điền vào .env ──────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "")

# ─── Đường dẫn data ──────────────────────────────────────────────────────────
DATA_DIR        = os.path.join(os.path.dirname(__file__), "data")
WARNINGS_FILE   = os.path.join(DATA_DIR, "warnings.json")
CASES_FILE      = os.path.join(DATA_DIR, "cases.json")
CONFIG_FILE     = os.path.join(DATA_DIR, "config.json")

# ─── Màu embed ───────────────────────────────────────────────────────────────
COLOR_ERROR   = 0xE74C3C
COLOR_WARN    = 0xF39C12
COLOR_SUCCESS = 0x2ECC71
COLOR_INFO    = 0x3498DB
COLOR_MOD     = 0x9B59B6

# ─── Giá trị mặc định (dùng khi chưa có config.json) ────────────────────────
DEFAULTS = {
    # Core
    "bot_prefix":    "!",
    "guild_id":      0,

    # Channels (0 = chưa cấu hình)
    "mod_log_channel_id": 0,
    "rules_channel_id":   0,
    "appeal_channel_id":  0,
    "staff_channel_id":   0,

    # Roles
    "mod_role_id":   0,
    "admin_role_id": 0,
    "muted_role_id": 0,

    # Auto-mod thresholds
    "spam_threshold": 5,   # số tin nhắn giống nhau
    "spam_window":    5,   # trong X giây
    "max_emoji":      15,  # emoji tối đa / tin nhắn
    "max_mentions":   5,   # @mention tối đa

    "warn_punishments": {
        "1": ["warn_only", 0],
        "2": ["warn_only", 0],
        "3": ["mute",      60],
        "4": ["mute",      120],
        "5": ["mute",      420],
        "6": ["mute",      840],
        "7": ["mute",      1680],
        "8": ["mute",      3360],
        "9": ["mute",      4320],
    },

    # Từ khóa
    "hate_keywords": [
        "đồ súc vật", "mày chết đi", "tao giết mày",
        "đéo mày", "địt mẹ", "đụ má",
    ],
    "politics_keywords": [
        "lật đổ chế độ", "phản động", "chính phủ lật đổ",
    ],

    # Link quảng cáo (regex pattern)
    "ad_patterns": [
        r"discord\.gg/",
        r"discord\.com/invite/",
        r"discordapp\.com/invite/",
        r"t\.me/",
    ],

    # Domain độc hại
    "suspicious_domains": [
        "grabify.link", "iplogger.org", "2no.co", "yip.su",
        "ipgrabber.ru", "blasze.tk",
        "discord-nitro.gift", "free-nitro.ru",
    ],
}


# ─── Runtime Config Manager ──────────────────────────────────────────────────

class _ConfigManager:
    """Quản lý cấu hình runtime – load/save từ JSON."""

    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Merge defaults + saved (saved thắng)
                self._data = {**DEFAULTS, **saved}
                return
            except Exception:
                pass
        self._data = dict(DEFAULTS)

    def save(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def reset(self, key: str) -> None:
        self._data[key] = DEFAULTS.get(key)
        self.save()

    def reset_all(self) -> None:
        self._data = dict(DEFAULTS)
        self.save()

    # ── List helpers ─────────────────────────────────────────────────────────

    def list_add(self, key: str, value: str) -> bool:
        lst = self._data.get(key, [])
        if value in lst:
            return False
        lst.append(value)
        self._data[key] = lst
        self.save()
        return True

    def list_remove(self, key: str, value: str) -> bool:
        lst = self._data.get(key, [])
        if value not in lst:
            return False
        lst.remove(value)
        self._data[key] = lst
        self.save()
        return True

    # ── Shortcuts ────────────────────────────────────────────────────────────

    @property
    def bot_prefix(self) -> str:        return self.get("bot_prefix")
    @property
    def guild_id(self) -> int:          return self.get("guild_id")
    @property
    def mod_log_channel_id(self) -> int: return self.get("mod_log_channel_id")
    @property
    def rules_channel_id(self) -> int:  return self.get("rules_channel_id")
    @property
    def appeal_channel_id(self) -> int: return self.get("appeal_channel_id")
    @property
    def staff_channel_id(self) -> int:  return self.get("staff_channel_id")
    @property
    def mod_role_id(self) -> int:       return self.get("mod_role_id")
    @property
    def admin_role_id(self) -> int:     return self.get("admin_role_id")
    @property
    def muted_role_id(self) -> int:     return self.get("muted_role_id")
    @property
    def spam_threshold(self) -> int:    return self.get("spam_threshold")
    @property
    def spam_window(self) -> int:       return self.get("spam_window")
    @property
    def max_emoji(self) -> int:         return self.get("max_emoji")
    @property
    def max_mentions(self) -> int:      return self.get("max_mentions")
    @property
    def hate_keywords(self) -> list:    return self.get("hate_keywords", [])
    @property
    def politics_keywords(self) -> list: return self.get("politics_keywords", [])
    @property
    def ad_patterns(self) -> list:      return self.get("ad_patterns", [])
    @property
    def suspicious_domains(self) -> list: return self.get("suspicious_domains", [])
    @property
    def warn_punishments(self) -> dict: return self.get("warn_punishments", {})


# Singleton – import và dùng trực tiếp: from config import cfg
cfg = _ConfigManager()
