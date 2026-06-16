"""
cogs/automod.py – Kiểm duyệt tự động theo nội quy server
Đọc cấu hình trực tiếp từ cfg (runtime) nên thay đổi /config có hiệu lực ngay.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

from config import cfg, COLOR_ERROR, COLOR_WARN
import utils

# Regex cố định (không thay đổi qua config)
_PHONE_RE = re.compile(r"(?<!\d)(0[3-9]\d{8}|\+84[3-9]\d{8})(?!\d)")
_SUSPICIOUS_RE_CACHE: tuple[list, re.Pattern | None] = ([], None)


def _get_suspicious_re() -> re.Pattern | None:
    """Tạo lại regex nếu danh sách domains thay đổi."""
    global _SUSPICIOUS_RE_CACHE
    domains = cfg.suspicious_domains
    if _SUSPICIOUS_RE_CACHE[0] == domains:
        return _SUSPICIOUS_RE_CACHE[1]
    if not domains:
        pat = None
    else:
        pat = re.compile("|".join(re.escape(d) for d in domains), re.IGNORECASE)
    _SUSPICIOUS_RE_CACHE = (list(domains), pat)
    return pat


_AD_RE_CACHE: tuple[list, re.Pattern | None] = ([], None)


def _get_ad_re() -> re.Pattern | None:
    global _AD_RE_CACHE
    patterns = cfg.ad_patterns
    if _AD_RE_CACHE[0] == patterns:
        return _AD_RE_CACHE[1]
    if not patterns:
        pat = None
    else:
        pat = re.compile("|".join(patterns), re.IGNORECASE)
    _AD_RE_CACHE = (list(patterns), pat)
    return pat


class AutoMod(commands.Cog):
    """Cog tự động kiểm duyệt tin nhắn theo nội quy."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._msg_cache: dict[int, deque] = defaultdict(lambda: deque(maxlen=20))

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        ch = guild.get_channel(cfg.mod_log_channel_id)
        if ch:
            await ch.send(embed=embed)

    async def _punish(self, message: discord.Message, violation: str,
                      reason: str, *, delete: bool = True, auto_warn: bool = True) -> None:
        member = message.author
        guild  = message.guild

        if delete:
            try:
                await message.delete()
            except discord.HTTPException:
                pass

        total = 0
        if auto_warn:
            total = utils.add_warning(member.id, self.bot.user.id, reason, guild.id)
            utils.log_case("AUTO-WARN", member, self.bot.user, reason)

            # Escalation dựa vào cfg.warn_punishments (đọc runtime)
            wp = cfg.warn_punishments
            punishment = wp.get(str(total), wp.get(str(max(int(k) for k in wp)), ["ban", 0]))
            action, duration = punishment

            if total >= 10:
                try:
                    from cogs.moderation import send_proposal
                    await send_proposal(guild, member, "ban", f"Tích lũy {total} cảnh cáo (Auto-mod: {violation})", self.bot.user.mention)
                except Exception:
                    pass

            if action == "mute" and duration > 0:
                try:
                    timeout_td = discord.utils.utcnow() + timedelta(minutes=duration)
                    await member.timeout(timeout_td, reason=f"[Auto-Mod] {reason}")
                    utils.log_case("AUTO-MUTE", member, self.bot.user, reason, duration)
                except discord.HTTPException:
                    pass
            elif action == "ban":
                try:
                    await guild.ban(member, reason=f"[Auto-Mod] {reason} (warn #{total})")
                    utils.log_case("AUTO-BAN", member, self.bot.user, reason)
                except discord.HTTPException:
                    pass

        # DM người vi phạm
        try:
            total_now = len(utils.get_warnings(member.id))
            dm_embed = discord.Embed(
                title=f"⚠️ Vi phạm: {violation}",
                description=(
                    f"Tin nhắn của bạn trong **{guild.name}** đã bị xóa.\n"
                    f"**Lý do:** {reason}\n\n"
                    f"Tổng cảnh cáo: **{total_now}**\n"
                    f"Nếu bạn cho đây là nhầm lẫn, dùng `/appeal` để kháng cáo."
                ),
                color=COLOR_WARN,
            )
            await member.send(embed=dm_embed)
        except discord.HTTPException:
            pass

        # Log
        log_embed = discord.Embed(
            title=f"🤖 Auto-Mod: {violation}",
            description=f"Vi phạm trong {message.channel.mention}",
            color=COLOR_ERROR,
        )
        log_embed.add_field(name="Người dùng", value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Vi phạm",    value=violation,                           inline=True)
        log_embed.add_field(name="Lý do",      value=reason,                              inline=False)
        log_embed.add_field(name="Nội dung",   value=f"```{message.content[:400]}```",    inline=False)
        await self._send_log(guild, log_embed)

    def _is_spam(self, user_id: int, content: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        cache = self._msg_cache[user_id]
        cache.append((now, content))
        window  = cfg.spam_window    # đọc runtime
        thresh  = cfg.spam_threshold # đọc runtime
        recent  = [c for t, c in cache if now - t <= window]
        same    = [c for c in recent if c == content]
        return len(same) >= thresh

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        if utils.is_mod(message.author):
            return

        content = message.content
        lower   = content.lower()
        member  = message.author

        # 1. Spam
        if self._is_spam(member.id, content):
            return await self._punish(message, "Spam", "Gửi tin nhắn lặp lại liên tục.")

        # 2. Link độc hại
        sus_re = _get_suspicious_re()
        if sus_re and sus_re.search(lower):
            return await self._punish(message, "Link đáng ngờ", "Chia sẻ link độc hại / IP grabber.")

        # 3. Quảng cáo
        ad_re = _get_ad_re()
        if ad_re and ad_re.search(lower):
            return await self._punish(message, "Quảng cáo", "Quảng cáo server/link không được phép.")

        # 4. Thù ghét (đọc runtime)
        for kw in cfg.hate_keywords:
            if kw in lower:
                return await self._punish(message, "Ngôn từ thù ghét",
                                          f"Sử dụng ngôn từ thù ghét: `{kw}`")

        # 5. Chính trị (đọc runtime)
        for kw in cfg.politics_keywords:
            if kw in lower:
                return await self._punish(message, "Nội dung chính trị",
                                          "Chia sẻ nội dung chính trị bị cấm.")

        # 6. Thông tin cá nhân
        if _PHONE_RE.search(content):
            return await self._punish(message, "Thông tin cá nhân",
                                      "Chia sẻ số điện thoại người khác.")

        # 7. Mention spam (đọc runtime)
        if len(message.mentions) > cfg.max_mentions:
            return await self._punish(message, "Mention spam",
                                      f"Mention quá nhiều người ({len(message.mentions)}).")

        # 8. Emoji spam (đọc runtime)
        emoji_count = len(re.findall(r"<a?:\w+:\d+>|[\U0001F300-\U0001FAFF]", content))
        if emoji_count > cfg.max_emoji:
            return await self._punish(message, "Emoji spam",
                                      f"Quá nhiều emoji ({emoji_count}).", auto_warn=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
