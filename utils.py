"""
utils.py – Tiện ích dùng chung cho toàn bot
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta

import discord
from config import cfg, DATA_DIR, WARNINGS_FILE, CASES_FILE


# ─── JSON helpers ────────────────────────────────────────────────────────────

def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path: str) -> dict:
    _ensure_data_dir()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    _ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Warning DB ──────────────────────────────────────────────────────────────

def get_warnings(user_id: int) -> list[dict]:
    db = load_json(WARNINGS_FILE)
    return db.get(str(user_id), [])


def add_warning(user_id: int, moderator_id: int, reason: str, guild_id: int) -> int:
    db = load_json(WARNINGS_FILE)
    key = str(user_id)
    if key not in db:
        db[key] = []
    entry = {
        "id":           len(db[key]) + 1,
        "reason":       reason,
        "moderator_id": moderator_id,
        "guild_id":     guild_id,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    }
    db[key].append(entry)
    save_json(WARNINGS_FILE, db)
    return len(db[key])


def clear_warnings(user_id: int) -> None:
    db = load_json(WARNINGS_FILE)
    db.pop(str(user_id), None)
    save_json(WARNINGS_FILE, db)


def remove_warning(user_id: int, warn_id: int) -> bool:
    db = load_json(WARNINGS_FILE)
    key = str(user_id)
    if key not in db:
        return False
    
    warnings = db[key]
    original_len = len(warnings)
    warnings = [w for w in warnings if w["id"] != warn_id]
    
    if len(warnings) == original_len:
        return False
        
    for i, w in enumerate(warnings):
        w["id"] = i + 1
        
    if not warnings:
        db.pop(key, None)
    else:
        db[key] = warnings
        
    save_json(WARNINGS_FILE, db)
    return True


# ─── Case DB ─────────────────────────────────────────────────────────────────

def log_case(action: str, target, moderator,
             reason: str, duration_min: int = 0) -> int:
    db = load_json(CASES_FILE)
    case_id = len(db) + 1
    db[str(case_id)] = {
        "id":           case_id,
        "action":       action,
        "target_id":    target.id,
        "target_tag":   str(target),
        "mod_id":       moderator.id,
        "mod_tag":      str(moderator),
        "reason":       reason,
        "duration_min": duration_min,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    }
    save_json(CASES_FILE, db)
    return case_id


def get_case(case_id: int) -> dict | None:
    db = load_json(CASES_FILE)
    return db.get(str(case_id))


# ─── Permission check ────────────────────────────────────────────────────────

def is_mod(member: discord.Member) -> bool:
    role_ids = {r.id for r in member.roles}
    return (cfg.mod_role_id in role_ids
            or cfg.admin_role_id in role_ids
            or member.guild_permissions.administrator)


def is_admin(member: discord.Member) -> bool:
    role_ids = {r.id for r in member.roles}
    return (cfg.admin_role_id in role_ids
            or member.guild_permissions.administrator)


# ─── Embed builders ──────────────────────────────────────────────────────────

def mod_embed(title: str, description: str, color: int,
              fields: list[tuple[str, str, bool]] | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text="Hệ thống Kiểm duyệt")
    return embed


def duration_str(minutes: int) -> str:
    if minutes == 0:
        return "Vĩnh viễn"
    if minutes < 60:
        return f"{minutes} phút"
    if minutes < 1440:
        h = minutes // 60
        m = minutes % 60
        return f"{h} giờ" + (f" {m} phút" if m else "")
    d = minutes // 1440
    return f"{d} ngày"


# ─── Staff Suspensions DB ───────────────────────────────────────────────────

SUSPENSIONS_FILE = os.path.join(DATA_DIR, "suspensions.json")

def load_suspensions() -> dict:
    return load_json(SUSPENSIONS_FILE)

def save_suspensions(data: dict) -> None:
    save_json(SUSPENSIONS_FILE, data)

def add_suspension(user_id: int, guild_id: int, role_id: int, duration_min: int, channel_id: int) -> None:
    data = load_suspensions()
    expire_at = (datetime.now(timezone.utc) + timedelta(minutes=duration_min)).isoformat()
    data[str(user_id)] = {
        "guild_id": guild_id,
        "role_id": role_id,
        "expire_at": expire_at,
        "channel_id": channel_id
    }
    save_suspensions(data)

def remove_suspension(user_id: int) -> dict | None:
    data = load_suspensions()
    val = data.pop(str(user_id), None)
    if val:
        save_suspensions(data)
    return val

def normalize_channel_name(name: str) -> str:
    import unicodedata
    name = name.lower().replace("-", " ").replace("_", " ").strip()
    normalized = unicodedata.normalize('NFKD', name)
    return "".join([c for c in normalized if not unicodedata.combining(c)])

