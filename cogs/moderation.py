"""
cogs/moderation.py – Lệnh thủ công cho Staff / Moderator
Hỗ trợ cả Slash Commands (/warn) và Prefix Commands (!warn)
"""
from __future__ import annotations

import asyncio
from datetime import timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from config import cfg, COLOR_ERROR, COLOR_WARN, COLOR_INFO, COLOR_SUCCESS, COLOR_MOD
import utils


def mod_only():
    """Check: chỉ mod/admin mới dùng được lệnh này."""
    async def predicate(ctx: commands.Context) -> bool:
        if utils.is_mod(ctx.author):
            return True
        await ctx.send(
            embed=utils.mod_embed(
                "❌ Không có quyền",
                "Bạn cần có role Moderator hoặc Admin để dùng lệnh này.",
                COLOR_ERROR,
            ),
            ephemeral=True if hasattr(ctx, "interaction") else False,
        )
        return False
    return commands.check(predicate)


def admin_only():
    """Check: chỉ Admin mới dùng được lệnh này."""
    async def predicate(ctx: commands.Context) -> bool:
        if utils.is_admin(ctx.author):
            return True
        await ctx.send(
            embed=utils.mod_embed(
                "❌ Không có quyền",
                "Bạn cần có role Admin hoặc chủ server để dùng lệnh này (Moderator không được phép).",
                COLOR_ERROR,
            ),
            ephemeral=True if hasattr(ctx, "interaction") else False,
        )
        return False
    return commands.check(predicate)


class ProposalView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Duyệt (Approve)",
        style=discord.ButtonStyle.success,
        custom_id="proposal_approve",
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not utils.is_admin(interaction.user):
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền duyệt đề nghị này.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        target_id = None
        action = None
        reason = None
        for field in embed.fields:
            if field.name == "ID Người vi phạm":
                target_id = int(field.value)
            elif field.name == "Hành động đề nghị":
                action = field.value.lower()
            elif field.name == "Lý do":
                reason = field.value

        if not target_id or not action:
            await interaction.response.send_message("❌ Lỗi: Không tìm thấy thông tin đối tượng hoặc hành động trong Embed.", ephemeral=True)
            return

        guild = interaction.guild
        try:
            target = await guild.fetch_member(target_id)
        except discord.HTTPException:
            try:
                target = await interaction.client.fetch_user(target_id)
            except discord.HTTPException:
                await interaction.response.send_message("❌ Không tìm thấy người dùng này trên Discord.", ephemeral=True)
                return

        try:
            if action == "ban":
                await guild.ban(target, reason=f"[Duyệt Đề Nghị bởi {interaction.user}] {reason}", delete_message_days=0)
                utils.log_case("BAN", target, interaction.user, f"[Duyệt Đề Nghị] {reason}")
            elif action == "kick":
                await guild.kick(target, reason=f"[Duyệt Đề Nghị bởi {interaction.user}] {reason}")
                utils.log_case("KICK", target, interaction.user, f"[Duyệt Đề Nghị] {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot không đủ quyền để thực hiện hành động này.", ephemeral=True)
            return

        embed.color = COLOR_SUCCESS
        embed.title = "✅ ĐỀ NGHỊ XỬ PHẠT - ĐÃ DUYỆT"
        embed.description = f"Đề nghị tạo bởi: {embed.description.replace('Đề nghị được tạo bởi: ', '')}\n\n**Trạng thái:** Đã duyệt bởi {interaction.user.mention}"
        embed.set_footer(text=f"Thực thi vào {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"✅ Đã duyệt và thực thi **{action.upper()}** đối với {target}.", ephemeral=True)

    @discord.ui.button(
        label="Từ chối (Reject)",
        style=discord.ButtonStyle.danger,
        custom_id="proposal_reject",
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not utils.is_admin(interaction.user):
            await interaction.response.send_message("❌ Chỉ Admin mới có quyền từ chối đề nghị này.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = 0x95A5A6
        embed.title = "❌ ĐỀ NGHỊ XỬ PHẠT - ĐÃ TỪ CHỐI"
        embed.description = f"Đề nghị tạo bởi: {embed.description.replace('Đề nghị được tạo bởi: ', '')}\n\n**Trạng thái:** Đã từ chối bởi {interaction.user.mention}"
        embed.set_footer(text=f"Từ chối vào {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("❌ Đã từ chối đề nghị xử phạt.", ephemeral=True)


async def send_proposal(guild: discord.Guild, target: discord.Member | discord.User, action: str, reason: str, proposer_mention: str) -> bool:
    staff_ch_id = cfg.staff_channel_id
    if not staff_ch_id:
        return False
    channel = guild.get_channel(staff_ch_id)
    if not channel:
        return False

    embed = discord.Embed(
        title="⚖️ ĐỀ NGHỊ XỬ PHẠT (PROPOSAL)",
        description=f"Đề nghị được tạo bởi: {proposer_mention}",
        color=COLOR_WARN if action.lower() == "kick" else COLOR_ERROR
    )
    embed.add_field(name="Người vi phạm", value=f"{target.mention} ({target})", inline=True)
    embed.add_field(name="ID Người vi phạm", value=str(target.id), inline=True)
    embed.add_field(name="Hành động đề nghị", value=action.upper(), inline=True)
    embed.add_field(name="Lý do", value=reason, inline=False)
    embed.set_footer(text="Chọn nút dưới đây để duyệt hoặc từ chối đề nghị này.")

    view = ProposalView()
    await channel.send(embed=embed, view=view)
    return True


class Moderation(commands.Cog):
    """Lệnh kiểm duyệt thủ công."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Utility ──────────────────────────────────────────────────────────────

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        ch = guild.get_channel(cfg.mod_log_channel_id)
        if ch:
            await ch.send(embed=embed)

    async def _dm_user(self, member: discord.Member, action: str,
                       reason: str, duration_str: str = "") -> None:
        try:
            embed = utils.mod_embed(
                title=f"⚖️ Bạn đã bị {action}",
                description=(
                    f"**Server:** {member.guild.name}\n"
                    f"**Lý do:** {reason}\n"
                    + (f"**Thời gian:** {duration_str}\n" if duration_str else "")
                    + "\nNếu bạn muốn kháng cáo, hãy dùng lệnh `/appeal`."
                ),
                color=COLOR_WARN,
            )
            await member.send(embed=embed)
        except discord.HTTPException:
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    # WARN
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="warn", description="Cảnh cáo một thành viên")
    @app_commands.describe(member="Thành viên cần cảnh cáo", reason="Lý do cảnh cáo")
    @mod_only()
    async def warn(self, ctx: commands.Context,
                   member: discord.Member, *, reason: str = "Không có lý do") -> None:

        if member.bot:
            return await ctx.send("Không thể cảnh cáo bot.")
        if member == ctx.author:
            return await ctx.send("Bạn không thể tự cảnh cáo bản thân.")

        total = utils.add_warning(member.id, ctx.author.id, reason, ctx.guild.id)
        case_id = utils.log_case("WARN", member, ctx.author, reason)

        # Escalation
        wp = cfg.warn_punishments
        punishment = wp.get(str(total), wp.get(str(max(int(k) for k in wp)), ["ban", 0]))
        action_type, duration = punishment
        extra_note = ""

        # Đề xuất xử phạt lên kênh staff nếu warn >= 10
        if total >= 10:
            success = await send_proposal(ctx.guild, member, "ban", f"Tích lũy {total} cảnh cáo", ctx.author.mention)
            if success:
                extra_note = f"\n⚠️ Đã đạt {total} cảnh cáo! Đã tự động đề xuất BAN lên kênh Staff."
            else:
                extra_note = f"\n⚠️ Đã đạt {total} cảnh cáo! (Chưa cấu hình Staff Channel để đề xuất BAN)"

        if action_type == "mute" and duration > 0:
            dur_str = utils.duration_str(duration)
            try:
                timeout_td = discord.utils.utcnow() + timedelta(minutes=duration)
                await member.timeout(timeout_td, reason=f"[Warn #{total}] {reason}")
                extra_note = f"\n🔇 Đã tự động mute **{dur_str}** (warn #{total})"
                utils.log_case("AUTO-MUTE", member, ctx.author, reason, duration)
            except discord.Forbidden:
                extra_note = "\n⚠️ Không đủ quyền để mute."

        elif action_type == "ban":
            try:
                await member.send("Bạn đã bị ban khỏi server do vi phạm nhiều lần.")
            except Exception:
                pass
            try:
                await ctx.guild.ban(member, reason=f"[Warn #{total}] {reason}")
                extra_note = f"\n🔨 Đã tự động **ban** (warn #{total})"
                utils.log_case("AUTO-BAN", member, ctx.author, reason)
            except discord.Forbidden:
                extra_note = "\n⚠️ Không đủ quyền để ban."

        # Phản hồi
        embed = utils.mod_embed(
            title="⚠️ Đã cảnh cáo",
            description=f"{member.mention} đã bị cảnh cáo.{extra_note}",
            color=COLOR_WARN,
            fields=[
                ("Người vi phạm", f"{member} (`{member.id}`)", True),
                ("Moderator",     str(ctx.author),              True),
                ("Tổng warn",     str(total),                   True),
                ("Lý do",         reason,                       False),
                ("Case ID",       f"#{case_id}",                True),
            ],
        )
        await ctx.send(embed=embed)
        await self._dm_user(member, "cảnh cáo", reason)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # MUTE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="mute", description="Mute (timeout) một thành viên")
    @app_commands.describe(
        member="Thành viên cần mute",
        duration="Thời gian (phút, mặc định 60)",
        reason="Lý do"
    )
    @mod_only()
    async def mute(self, ctx: commands.Context, member: discord.Member,
                   duration: int = 60, *, reason: str = "Không có lý do") -> None:

        if member.bot:
            return await ctx.send("Không thể mute bot.")
        dur_str = utils.duration_str(duration)
        try:
            timeout_td = discord.utils.utcnow() + timedelta(minutes=duration)
            await member.timeout(timeout_td, reason=reason)
        except discord.Forbidden:
            return await ctx.send("❌ Tôi không có quyền mute thành viên này.")

        case_id = utils.log_case("MUTE", member, ctx.author, reason, duration)
        embed = utils.mod_embed(
            title="🔇 Đã mute",
            description=f"{member.mention} bị mute {dur_str}.",
            color=COLOR_MOD,
            fields=[
                ("Người dùng", f"{member} (`{member.id}`)", True),
                ("Moderator",  str(ctx.author),             True),
                ("Thời gian",  dur_str,                     True),
                ("Lý do",      reason,                      False),
                ("Case ID",    f"#{case_id}",               True),
            ],
        )
        await ctx.send(embed=embed)
        await self._dm_user(member, "mute", reason, dur_str)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # UNMUTE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="unmute", description="Bỏ mute một thành viên")
    @app_commands.describe(member="Thành viên cần bỏ mute")
    @mod_only()
    async def unmute(self, ctx: commands.Context, member: discord.Member) -> None:
        try:
            await member.timeout(None)
        except discord.Forbidden:
            return await ctx.send("❌ Không có quyền bỏ mute.")

        case_id = utils.log_case("UNMUTE", member, ctx.author, "Bỏ mute thủ công")
        embed = utils.mod_embed(
            title="🔊 Đã bỏ mute",
            description=f"{member.mention} đã được bỏ mute.",
            color=COLOR_SUCCESS,
            fields=[
                ("Người dùng", f"{member} (`{member.id}`)", True),
                ("Moderator",  str(ctx.author),             True),
                ("Case ID",    f"#{case_id}",               True),
            ],
        )
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # KICK
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="kick", description="Kick một thành viên")
    @app_commands.describe(member="Thành viên cần kick", reason="Lý do")
    @admin_only()
    async def kick(self, ctx: commands.Context,
                   member: discord.Member, *, reason: str = "Không có lý do") -> None:
        try:
            await self._dm_user(member, "kick", reason)
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await ctx.send("❌ Không có quyền kick.")

        case_id = utils.log_case("KICK", member, ctx.author, reason)
        embed = utils.mod_embed(
            title="👢 Đã kick",
            description=f"**{member}** đã bị kick.",
            color=COLOR_MOD,
            fields=[
                ("Người dùng", f"{member} (`{member.id}`)", True),
                ("Moderator",  str(ctx.author),             True),
                ("Lý do",      reason,                      False),
                ("Case ID",    f"#{case_id}",               True),
            ],
        )
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # BAN
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="ban", description="Ban một thành viên")
    @app_commands.describe(member="Thành viên cần ban", reason="Lý do")
    @admin_only()
    async def ban(self, ctx: commands.Context,
                  member: discord.Member, *, reason: str = "Không có lý do") -> None:
        try:
            await self._dm_user(member, "ban", reason)
            await ctx.guild.ban(member, reason=reason, delete_message_days=0)
        except discord.Forbidden:
            return await ctx.send("❌ Không có quyền ban.")

        case_id = utils.log_case("BAN", member, ctx.author, reason)
        embed = utils.mod_embed(
            title="🔨 Đã ban",
            description=f"**{member}** đã bị ban vĩnh viễn.",
            color=COLOR_ERROR,
            fields=[
                ("Người dùng", f"{member} (`{member.id}`)", True),
                ("Moderator",  str(ctx.author),             True),
                ("Lý do",      reason,                      False),
                ("Case ID",    f"#{case_id}",               True),
            ],
        )
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # UNBAN
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="unban", description="Bỏ ban một người dùng")
    @app_commands.describe(user_id="ID người dùng cần bỏ ban", reason="Lý do")
    @admin_only()
    async def unban(self, ctx: commands.Context,
                    user_id: int, *, reason: str = "Kháng cáo được chấp nhận") -> None:
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
        except discord.NotFound:
            return await ctx.send("❌ Không tìm thấy người dùng hoặc họ chưa bị ban.")
        except discord.Forbidden:
            return await ctx.send("❌ Không có quyền bỏ ban.")

        case_id = utils.log_case("UNBAN", user, ctx.author, reason)
        embed = utils.mod_embed(
            title="✅ Đã bỏ ban",
            description=f"**{user}** đã được bỏ ban.",
            color=COLOR_SUCCESS,
            fields=[
                ("Người dùng", f"{user} (`{user.id}`)", True),
                ("Moderator",  str(ctx.author),         True),
                ("Lý do",      reason,                  False),
                ("Case ID",    f"#{case_id}",           True),
            ],
        )
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # WARNS
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="warns", description="Xem danh sách cảnh cáo của thành viên")
    @app_commands.describe(member="Thành viên cần xem")
    @mod_only()
    async def warns(self, ctx: commands.Context, member: discord.Member) -> None:
        warnings = utils.get_warnings(member.id)
        if not warnings:
            return await ctx.send(
                embed=utils.mod_embed(
                    "📋 Danh sách cảnh cáo",
                    f"{member.mention} chưa có cảnh cáo nào. ✅",
                    COLOR_SUCCESS,
                )
            )

        lines = []
        for w in warnings[-10:]:  # hiện 10 gần nhất
            ts = w.get("timestamp", "")[:10]
            lines.append(f"**#{w['id']}** – {w['reason']} *(ngày {ts})*")

        embed = utils.mod_embed(
            title=f"⚠️ Cảnh cáo của {member.display_name}",
            description="\n".join(lines),
            color=COLOR_WARN,
            fields=[("Tổng cảnh cáo", str(len(warnings)), True)],
        )
        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # CLEARWARNS
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="clearwarns", description="Xóa toàn bộ cảnh cáo của thành viên")
    @app_commands.describe(member="Thành viên cần xóa cảnh cáo")
    @mod_only()
    async def clearwarns(self, ctx: commands.Context, member: discord.Member) -> None:
        utils.clear_warnings(member.id)
        embed = utils.mod_embed(
            title="🗑️ Đã xóa cảnh cáo",
            description=f"Đã xóa toàn bộ cảnh cáo của {member.mention}.",
            color=COLOR_SUCCESS,
            fields=[("Moderator", str(ctx.author), True)],
        )
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # UNWARN
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="unwarn", description="Xóa một cảnh cáo cụ thể của thành viên theo ID cảnh cáo")
    @app_commands.describe(member="Thành viên cần xóa cảnh cáo", warn_id="ID của cảnh cáo cần xóa (số)")
    @mod_only()
    async def unwarn(self, ctx: commands.Context, member: discord.Member, warn_id: int) -> None:
        success = utils.remove_warning(member.id, warn_id)
        if success:
            case_id = utils.log_case("UNWARN", member, ctx.author, f"Xóa cảnh cáo #{warn_id}")
            embed = utils.mod_embed(
                title="🗑️ Đã xóa cảnh cáo",
                description=f"Đã xóa cảnh cáo **#{warn_id}** của {member.mention}.",
                color=COLOR_SUCCESS,
                fields=[
                    ("Thành viên", f"{member} (`{member.id}`)", True),
                    ("Moderator", str(ctx.author), True),
                    ("Case ID", f"#{case_id}", True),
                ]
            )
            await ctx.send(embed=embed)
            await self._send_log(ctx.guild, embed)
        else:
            await ctx.send(f"❌ Không tìm thấy cảnh cáo #{warn_id} của thành viên {member}.", ephemeral=False)

    # ═══════════════════════════════════════════════════════════════════════════
    # PURGE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="purge", description="Xóa nhiều tin nhắn cùng lúc")
    @app_commands.describe(amount="Số tin nhắn cần xóa (tối đa 100)")
    @mod_only()
    async def purge(self, ctx: commands.Context, amount: int = 10) -> None:
        amount = min(max(amount, 1), 100)
        if hasattr(ctx, "interaction") and ctx.interaction:
            await ctx.defer(ephemeral=False)
        deleted = await ctx.channel.purge(limit=amount)
        embed = utils.mod_embed(
            title="🧹 Đã dọn dẹp",
            description=f"Đã xóa **{len(deleted)}** tin nhắn trong {ctx.channel.mention}.",
            color=COLOR_INFO,
            fields=[("Moderator", str(ctx.author), True)],
        )
        await self._send_log(ctx.guild, embed)
        await ctx.send(
            embed=utils.mod_embed("✅", f"Đã xóa {len(deleted)} tin nhắn.", COLOR_SUCCESS),
            ephemeral=False,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CASE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="case", description="Xem thông tin một case")
    @app_commands.describe(case_id="ID của case")
    @mod_only()
    async def case(self, ctx: commands.Context, case_id: int) -> None:
        c = utils.get_case(case_id)
        if not c:
            return await ctx.send(f"❌ Không tìm thấy case #{case_id}.")

        embed = utils.mod_embed(
            title=f"📁 Case #{case_id} – {c['action']}",
            description="",
            color=COLOR_INFO,
            fields=[
                ("Người vi phạm", f"{c['target_tag']} (`{c['target_id']}`)", True),
                ("Moderator",     f"{c['mod_tag']} (`{c['mod_id']}`)",       True),
                ("Lý do",         c["reason"],                               False),
                ("Thời gian",     c["timestamp"][:19].replace("T", " "),    True),
            ],
        )
        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # PROPOSE
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="propose", description="Đề nghị xử phạt một thành viên (Ban/Kick)")
    @app_commands.describe(
        member="Thành viên cần xử lý",
        action="Hành động đề xuất (Ban hoặc Kick)",
        reason="Lý do đề xuất"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="🔨 Ban vĩnh viễn", value="ban"),
        app_commands.Choice(name="👢 Kick khỏi server", value="kick")
    ])
    @mod_only()
    async def propose(self, ctx: commands.Context,
                      member: discord.Member, action: str, *, reason: str = "Không có lý do") -> None:
        if member.bot:
            return await ctx.send("Không thể đề xuất xử phạt bot.")
        if member == ctx.author:
            return await ctx.send("Bạn không thể tự đề xuất xử phạt bản thân.")

        if action.lower() not in ["ban", "kick"]:
            return await ctx.send("❌ Hành động chỉ được chọn là `ban` hoặc `kick`.")

        success = await send_proposal(ctx.guild, member, action, reason, ctx.author.mention)
        if success:
            await ctx.send(
                embed=utils.mod_embed(
                    "✅ Đã gửi đề xuất",
                    f"Đã gửi đề xuất **{action.upper()}** đối với {member.mention} vào nhóm Staff.",
                    COLOR_SUCCESS
                ),
                ephemeral=False
            )
        else:
            await ctx.send(
                embed=utils.mod_embed(
                    "❌ Thất bại",
                    "Không thể gửi đề xuất. Vui lòng kiểm tra xem Kênh Staff đã được thiết lập chưa (`/guardbot config channel`).",
                    COLOR_ERROR
                ),
                ephemeral=False
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # BAOCAO
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="baocao", description="Xem báo cáo thống kê các vi phạm trên server")
    @mod_only()
    async def baocao(self, ctx: commands.Context) -> None:
        cases = utils.load_json(utils.CASES_FILE)
        if not cases:
            return await ctx.send("📋 Chưa có dữ liệu xử phạt nào để báo cáo.")

        total_cases = len(cases)
        action_counts = {}
        target_counts = {}
        mod_counts = {}

        for c in cases.values():
            action = c.get("action", "UNKNOWN")
            action_counts[action] = action_counts.get(action, 0) + 1

            target = c.get("target_tag", "Unknown User")
            target_id = c.get("target_id")
            target_key = f"{target} (ID: {target_id})" if target_id else target
            target_counts[target_key] = target_counts.get(target_key, 0) + 1

            mod = c.get("mod_tag", "Unknown Mod")
            mod_id = c.get("mod_id")
            mod_key = f"{mod} (ID: {mod_id})" if mod_id else mod
            mod_counts[mod_key] = mod_counts.get(mod_key, 0) + 1

        top_targets = sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_mods = sorted(mod_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        embed = discord.Embed(
            title="📊 BÁO CÁO THỐNG KÊ VI PHẠM",
            description=f"Tổng số vụ xử lý ghi nhận: **{total_cases}**",
            color=COLOR_INFO
        )

        action_desc = "\n".join(f"• **{act}**: {count} lần" for act, count in action_counts.items())
        embed.add_field(name="🗂️ Phân loại hành động", value=action_desc or "Không có", inline=False)

        target_desc = "\n".join(f"• {user}: **{count}** vi phạm" for user, count in top_targets)
        embed.add_field(name="⚠️ Thành viên vi phạm nhiều nhất", value=target_desc or "Không có", inline=False)

        mod_desc = "\n".join(f"• {m}: **{count}** tác vụ" for m, count in top_mods)
        embed.add_field(name="👮 Staff hoạt động năng nổ nhất", value=mod_desc or "Không có", inline=False)

        embed.set_footer(text=f"Yêu cầu bởi {ctx.author}")
        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # REPORT
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.hybrid_command(name="report", description="Báo cáo người dùng vi phạm đến Ban Quản Trị")
    @app_commands.describe(member="Thành viên bạn muốn báo cáo", reason="Lý do báo cáo")
    async def report(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

        staff_ch_id = cfg.staff_channel_id
        if not staff_ch_id:
            await ctx.send("❌ Tính năng báo cáo hiện chưa khả dụng (Admin chưa thiết lập Staff Channel).", ephemeral=True)
            return

        channel = ctx.guild.get_channel(staff_ch_id)
        if not channel:
            await ctx.send("❌ Không tìm thấy kênh Staff để gửi báo cáo.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📢 BÁO CÁO NGƯỜI DÙNG MỚI",
            description=f"Có một báo cáo mới được gửi từ kênh {ctx.channel.mention}",
            color=COLOR_WARN
        )
        embed.add_field(name="Người báo cáo", value=f"{ctx.author.mention} ({ctx.author})", inline=True)
        embed.add_field(name="Đối tượng bị báo cáo", value=f"{member.mention} ({member})", inline=True)
        embed.add_field(name="Lý do", value=reason, inline=False)
        embed.set_footer(text=f"ID Đối tượng: {member.id}")

        await channel.send(embed=embed)
        await ctx.send("✅ Đã gửi báo cáo của bạn đến Ban Quản Trị để xử lý. Cảm ơn bạn!", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
