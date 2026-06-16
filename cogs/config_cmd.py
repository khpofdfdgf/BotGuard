"""
cogs/config_cmd.py – Lệnh /config cho Admin chỉnh cấu hình ngay trong Discord
"""
from __future__ import annotations

import re
import discord
from discord import app_commands
from discord.ext import commands

from config import cfg, DEFAULTS
import utils


# ─── Helpers ─────────────────────────────────────────────────────────────────

def is_admin(member: discord.Member) -> bool:
    role_ids = {r.id for r in member.roles}
    return (cfg.admin_role_id in role_ids
            or member.guild_permissions.administrator)


def duration_str(minutes: int) -> str:
    if minutes == 0:
        return "Vĩnh viễn"
    if minutes < 60:
        return f"{minutes} phút"
    if minutes < 1440:
        h, m = divmod(minutes, 60)
        return f"{h} giờ" + (f" {m} phút" if m else "")
    return f"{minutes // 1440} ngày"


# ─── Embeds ──────────────────────────────────────────────────────────────────

def _embed_overview() -> discord.Embed:
    e = discord.Embed(
        title="⚙️ Cấu Hình Bot",
        description="Chọn mục cần chỉnh sửa từ menu bên dưới.",
        color=0x5865F2,
    )
    e.add_field(name="Prefix",       value=f"`{cfg.bot_prefix}`",          inline=True)
    e.add_field(name="Guild ID",     value=f"`{cfg.guild_id or 'chưa đặt'}`", inline=True)
    e.add_field(name="\u200b",       value="\u200b",                        inline=True)

    # Channels
    def ch(id_): return f"<#{id_}>" if id_ else "`chưa đặt`"
    e.add_field(name="📺 Channels", value=(
        f"Mod Log: {ch(cfg.mod_log_channel_id)}\n"
        f"Rules:   {ch(cfg.rules_channel_id)}\n"
        f"Appeal:  {ch(cfg.appeal_channel_id)}\n"
        f"Staff:   {ch(cfg.staff_channel_id)}"
    ), inline=True)

    # Roles
    def ro(id_): return f"<@&{id_}>" if id_ else "`chưa đặt`"
    e.add_field(name="👤 Roles", value=(
        f"Mod:   {ro(cfg.mod_role_id)}\n"
        f"Admin: {ro(cfg.admin_role_id)}\n"
        f"Muted: {ro(cfg.muted_role_id)}"
    ), inline=True)

    e.add_field(name="\u200b", value="\u200b", inline=True)

    # Auto-mod
    e.add_field(name="🤖 Auto-Mod", value=(
        f"Spam: `{cfg.spam_threshold}` tin / `{cfg.spam_window}` giây\n"
        f"Max emoji: `{cfg.max_emoji}` | Max mention: `{cfg.max_mentions}`"
    ), inline=False)

    # Warn punishments
    wp = cfg.warn_punishments
    lines = []
    for k in sorted(wp.keys(), key=int):
        act, dur = wp[k]
        icon = "🔨" if act == "ban" else ("🔇" if act == "mute" else "⚠️")
        lines.append(f"Warn **{k}**: {icon} {act}" + (f" ({duration_str(dur)})" if dur else ""))
    e.add_field(name="⚖️ Hệ Thống Phạt", value="\n".join(lines), inline=False)

    # Keywords summary
    e.add_field(name="💬 Từ Khóa", value=(
        f"Thù ghét: `{len(cfg.hate_keywords)}` từ\n"
        f"Chính trị: `{len(cfg.politics_keywords)}` từ\n"
        f"Domain xấu: `{len(cfg.suspicious_domains)}` domain"
    ), inline=True)

    e.set_footer(text="Mọi thay đổi được lưu ngay lập tức.")
    return e


def _embed_thresholds() -> discord.Embed:
    e = discord.Embed(title="🤖 Ngưỡng Auto-Mod", color=0x3498DB)
    e.add_field(name="spam_threshold", value=f"`{cfg.spam_threshold}` tin nhắn giống nhau", inline=False)
    e.add_field(name="spam_window",    value=f"`{cfg.spam_window}` giây",                   inline=False)
    e.add_field(name="max_emoji",      value=f"`{cfg.max_emoji}` emoji / tin nhắn",          inline=False)
    e.add_field(name="max_mentions",   value=f"`{cfg.max_mentions}` @mention / tin nhắn",   inline=False)
    e.set_footer(text="Dùng /config set <key> <value> để thay đổi")
    return e


def _embed_punishments() -> discord.Embed:
    e = discord.Embed(title="⚖️ Hệ Thống Phạt", color=0xE74C3C)
    wp = cfg.warn_punishments
    for k in sorted(wp.keys(), key=int):
        act, dur = wp[k]
        icon = "🔨" if act == "ban" else ("🔇" if act == "mute" else "⚠️")
        e.add_field(
            name=f"Warn #{k}",
            value=f"{icon} **{act}**" + (f"\n⏱ {duration_str(dur)}" if dur else ""),
            inline=True,
        )
    e.set_footer(text="Dùng /config warn <số> <hành động> <phút>")
    return e


def _embed_keywords(title: str, keywords: list, key: str) -> discord.Embed:
    e = discord.Embed(title=title, color=0xF39C12)
    if keywords:
        chunks = [keywords[i:i+15] for i in range(0, len(keywords), 15)]
        for i, chunk in enumerate(chunks):
            e.add_field(
                name=f"Danh sách {f'(trang {i+1})' if i else ''}",
                value="\n".join(f"`{w}`" for w in chunk),
                inline=False,
            )
    else:
        e.description = "*Chưa có từ khóa nào.*"
    e.set_footer(text=f"Dùng /config addword {key} <từ> | /config removeword {key} <từ>")
    return e


# ─── Select Menu ─────────────────────────────────────────────────────────────

class ConfigSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📊 Tổng quan",          value="overview",    description="Xem toàn bộ cấu hình"),
            discord.SelectOption(label="🤖 Ngưỡng Auto-Mod",     value="thresholds",  description="Spam, emoji, mention"),
            discord.SelectOption(label="⚖️ Hệ thống phạt",       value="punishments", description="Warn 1-5 xử phạt gì"),
            discord.SelectOption(label="💬 Từ khóa thù ghét",    value="hate",        description="Danh sách từ bị cấm"),
            discord.SelectOption(label="🏛️ Từ khóa chính trị",   value="politics",    description="Nội dung chính trị bị cấm"),
            discord.SelectOption(label="🔗 Domain đáng ngờ",     value="domains",     description="Link độc hại / IP grabber"),
        ]
        super().__init__(placeholder="Chọn mục cần xem/chỉnh...", options=options)

    async def callback(self, interaction: discord.Interaction):
        v = self.values[0]
        if v == "overview":
            embed = _embed_overview()
        elif v == "thresholds":
            embed = _embed_thresholds()
        elif v == "punishments":
            embed = _embed_punishments()
        elif v == "hate":
            embed = _embed_keywords("💬 Từ Khóa Thù Ghét", cfg.hate_keywords, "hate")
        elif v == "politics":
            embed = _embed_keywords("🏛️ Từ Khóa Chính Trị", cfg.politics_keywords, "politics")
        elif v == "domains":
            embed = _embed_keywords("🔗 Domain Đáng Ngờ", cfg.suspicious_domains, "domain")
        else:
            embed = _embed_overview()
        await interaction.response.edit_message(embed=embed, view=self.view)


class ConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ConfigSelect())

    @discord.ui.button(label="🔄 Reset mặc định", style=discord.ButtonStyle.danger, row=1)
    async def reset_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Chỉ Admin mới có thể reset!", ephemeral=True)

        class ConfirmView(discord.ui.View):
            @discord.ui.button(label="✅ Xác nhận Reset", style=discord.ButtonStyle.danger)
            async def confirm(self, i: discord.Interaction, b: discord.ui.Button):
                cfg.reset_all()
                await i.response.edit_message(
                    content="✅ Đã reset toàn bộ cấu hình về mặc định!",
                    embed=_embed_overview(), view=None
                )
            @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
                await i.response.edit_message(content=None, view=None)

        await interaction.response.send_message(
            "⚠️ Bạn có chắc muốn reset **toàn bộ cấu hình** về mặc định?",
            view=ConfirmView(), ephemeral=True
        )


# ─── Cog ─────────────────────────────────────────────────────────────────────

class ConfigCommand(commands.Cog):
    """Lệnh /config để Admin chỉnh bot ngay trong Discord."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _check_admin(self, interaction: discord.Interaction) -> bool:
        return is_admin(interaction.user)

    # ═══════════════════════════════════════════════════════════════════════
    # Group /config
    # ═══════════════════════════════════════════════════════════════════════

    config_group = app_commands.Group(
        name="config",
        description="⚙️ Cấu hình bot (chỉ Admin)",
    )

    # ── /config view ────────────────────────────────────────────────────────

    @config_group.command(name="view", description="Xem toàn bộ cấu hình hiện tại")
    async def config_view(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=_embed_overview(),
            view=ConfigView(),
            ephemeral=True,
        )

    # ── /config set ─────────────────────────────────────────────────────────

    @config_group.command(name="set", description="Thay đổi một giá trị cấu hình")
    @app_commands.describe(
        key="Tên config (ví dụ: spam_threshold, max_emoji, bot_prefix, mod_log_channel_id...)",
        value="Giá trị mới"
    )
    @app_commands.choices(key=[
        app_commands.Choice(name="bot_prefix",           value="bot_prefix"),
        app_commands.Choice(name="guild_id",             value="guild_id"),
        app_commands.Choice(name="mod_log_channel_id",   value="mod_log_channel_id"),
        app_commands.Choice(name="rules_channel_id",     value="rules_channel_id"),
        app_commands.Choice(name="appeal_channel_id",    value="appeal_channel_id"),
        app_commands.Choice(name="mod_role_id",          value="mod_role_id"),
        app_commands.Choice(name="admin_role_id",        value="admin_role_id"),
        app_commands.Choice(name="muted_role_id",        value="muted_role_id"),
        app_commands.Choice(name="spam_threshold",       value="spam_threshold"),
        app_commands.Choice(name="spam_window",          value="spam_window"),
        app_commands.Choice(name="max_emoji",            value="max_emoji"),
        app_commands.Choice(name="max_mentions",         value="max_mentions"),
    ])
    async def config_set(self, interaction: discord.Interaction,
                         key: str, value: str):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        # Ép kiểu đúng
        int_keys = {
            "guild_id", "mod_log_channel_id", "rules_channel_id",
            "appeal_channel_id", "mod_role_id", "admin_role_id",
            "muted_role_id", "spam_threshold", "spam_window",
            "max_emoji", "max_mentions",
        }
        try:
            parsed = int(value) if key in int_keys else value
        except ValueError:
            return await interaction.response.send_message(
                f"❌ `{key}` cần giá trị số nguyên!", ephemeral=True
            )

        cfg.set(key, parsed)
        await interaction.response.send_message(
            embed=utils.mod_embed(
                "✅ Đã cập nhật",
                f"**{key}** → `{parsed}`",
                0x2ECC71,
            ),
            ephemeral=True,
        )

    # ── /config warn ────────────────────────────────────────────────────────

    @config_group.command(name="warn", description="Thay đổi hình phạt cho warn thứ N")
    @app_commands.describe(
        warn_number="Số warn (1-9)",
        action="Hành động: warn_only | mute | ban",
        duration_minutes="Thời gian mute (phút, để 0 nếu ban hoặc warn_only)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="⚠️ warn_only – Chỉ cảnh cáo",  value="warn_only"),
        app_commands.Choice(name="🔇 mute – Mute có thời hạn",    value="mute"),
        app_commands.Choice(name="🔨 ban – Ban vĩnh viễn",        value="ban"),
    ])
    async def config_warn(self, interaction: discord.Interaction,
                          warn_number: int, action: str, duration_minutes: int = 0):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        wp = cfg.warn_punishments
        wp[str(warn_number)] = [action, duration_minutes]
        cfg.set("warn_punishments", wp)

        dur_display = f" ({duration_str(duration_minutes)})" if duration_minutes else ""
        await interaction.response.send_message(
            embed=utils.mod_embed(
                "✅ Đã cập nhật hình phạt",
                f"Warn **#{warn_number}** → **{action}**{dur_display}",
                0x2ECC71,
                fields=[("Xem lại", "Dùng `/config view` → chọn Hệ thống phạt", False)],
            ),
            ephemeral=True,
        )

    # ── /config addword ─────────────────────────────────────────────────────

    @config_group.command(name="addword", description="Thêm từ khóa vào danh sách cấm")
    @app_commands.describe(
        category="Loại từ khóa",
        word="Từ hoặc cụm từ cần thêm",
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="💬 Thù ghét",      value="hate_keywords"),
        app_commands.Choice(name="🏛️ Chính trị",    value="politics_keywords"),
        app_commands.Choice(name="🔗 Domain xấu",    value="suspicious_domains"),
        app_commands.Choice(name="📢 Pattern quảng cáo", value="ad_patterns"),
    ])
    async def config_addword(self, interaction: discord.Interaction,
                             category: str, word: str):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        added = cfg.list_add(category, word.lower().strip())
        label = {"hate_keywords": "thù ghét", "politics_keywords": "chính trị",
                 "suspicious_domains": "domain xấu", "ad_patterns": "quảng cáo"}.get(category, category)

        if added:
            await interaction.response.send_message(
                embed=utils.mod_embed("✅ Đã thêm", f"`{word}` → danh sách **{label}**", 0x2ECC71),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"⚠️ `{word}` đã có trong danh sách **{label}** rồi.", ephemeral=True
            )

    # ── /config removeword ──────────────────────────────────────────────────

    @config_group.command(name="removeword", description="Xóa từ khóa khỏi danh sách cấm")
    @app_commands.describe(
        category="Loại từ khóa",
        word="Từ hoặc cụm từ cần xóa",
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="💬 Thù ghét",      value="hate_keywords"),
        app_commands.Choice(name="🏛️ Chính trị",    value="politics_keywords"),
        app_commands.Choice(name="🔗 Domain xấu",    value="suspicious_domains"),
        app_commands.Choice(name="📢 Pattern quảng cáo", value="ad_patterns"),
    ])
    async def config_removeword(self, interaction: discord.Interaction,
                                category: str, word: str):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        removed = cfg.list_remove(category, word.lower().strip())
        label = {"hate_keywords": "thù ghét", "politics_keywords": "chính trị",
                 "suspicious_domains": "domain xấu", "ad_patterns": "quảng cáo"}.get(category, category)

        if removed:
            await interaction.response.send_message(
                embed=utils.mod_embed("🗑️ Đã xóa", f"`{word}` khỏi danh sách **{label}**", 0xE74C3C),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ Không tìm thấy `{word}` trong danh sách **{label}**.", ephemeral=True
            )

    # ── /config channel ─────────────────────────────────────────────────────

    @config_group.command(name="channel", description="Gán kênh cho các chức năng bot")
    @app_commands.describe(
        function="Chức năng cần gán kênh",
        channel="Kênh Discord",
    )
    @app_commands.choices(function=[
        app_commands.Choice(name="📋 Mod Log",   value="mod_log_channel_id"),
        app_commands.Choice(name="📜 Rules",     value="rules_channel_id"),
        app_commands.Choice(name="📝 Appeal",    value="appeal_channel_id"),
        app_commands.Choice(name="🛡️ Staff Channel", value="staff_channel_id"),
    ])
    async def config_channel(self, interaction: discord.Interaction,
                             function: str, channel: discord.abc.GuildChannel):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        cfg.set(function, channel.id)
        label = {"mod_log_channel_id": "Mod Log", "rules_channel_id": "Rules",
                 "appeal_channel_id": "Appeal", "staff_channel_id": "Staff Channel"}.get(function, function)

        await interaction.response.send_message(
            embed=utils.mod_embed(
                "✅ Đã cập nhật kênh",
                f"**{label}** → {channel.mention}",
                0x2ECC71,
            ),
            ephemeral=True,
        )

    # ── /config role ─────────────────────────────────────────────────────────

    @config_group.command(name="role", description="Gán role cho các chức năng bot")
    @app_commands.describe(
        function="Chức năng cần gán role",
        role="Role Discord",
    )
    @app_commands.choices(function=[
        app_commands.Choice(name="👮 Moderator", value="mod_role_id"),
        app_commands.Choice(name="🛡️ Admin",    value="admin_role_id"),
        app_commands.Choice(name="🔇 Muted",     value="muted_role_id"),
    ])
    async def config_role(self, interaction: discord.Interaction,
                          function: str, role: discord.Role):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        cfg.set(function, role.id)
        label = {"mod_role_id": "Moderator", "admin_role_id": "Admin",
                 "muted_role_id": "Muted"}.get(function, function)

        await interaction.response.send_message(
            embed=utils.mod_embed(
                "✅ Đã cập nhật role",
                f"**{label}** → {role.mention}",
                0x2ECC71,
            ),
            ephemeral=True,
        )

    # ── /config reset ────────────────────────────────────────────────────────

    @config_group.command(name="reset", description="Reset một giá trị về mặc định")
    @app_commands.describe(key="Tên config cần reset")
    @app_commands.choices(key=[
        app_commands.Choice(name="spam_threshold",  value="spam_threshold"),
        app_commands.Choice(name="spam_window",     value="spam_window"),
        app_commands.Choice(name="max_emoji",       value="max_emoji"),
        app_commands.Choice(name="max_mentions",    value="max_mentions"),
        app_commands.Choice(name="warn_punishments",value="warn_punishments"),
        app_commands.Choice(name="hate_keywords",   value="hate_keywords"),
        app_commands.Choice(name="politics_keywords", value="politics_keywords"),
        app_commands.Choice(name="suspicious_domains", value="suspicious_domains"),
    ])
    async def config_reset(self, interaction: discord.Interaction, key: str):
        if not self._check_admin(interaction):
            return await interaction.response.send_message("❌ Chỉ Admin mới dùng được!", ephemeral=True)

        cfg.reset(key)
        await interaction.response.send_message(
            embed=utils.mod_embed(
                "🔄 Đã reset",
                f"**{key}** → về giá trị mặc định",
                0x3498DB,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfigCommand(bot))
