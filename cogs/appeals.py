"""
cogs/appeals.py – Hệ thống kháng cáo cho thành viên bị xử phạt
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import cfg, COLOR_INFO, COLOR_SUCCESS, COLOR_ERROR
import utils


class AppealModal(discord.ui.Modal, title="📝 Gửi Kháng Cáo"):
    violation = discord.ui.TextInput(
        label="Hành vi vi phạm bị xử phạt",
        placeholder="Bạn bị xử phạt vì lý do gì?",
        max_length=200,
    )
    explanation = discord.ui.TextInput(
        label="Giải trình của bạn",
        style=discord.TextStyle.paragraph,
        placeholder="Hãy giải thích tại sao bạn cho rằng mình bị xử oan...",
        max_length=1000,
    )
    case_id = discord.ui.TextInput(
        label="Case ID (nếu có)",
        placeholder="Ví dụ: #42 (để trống nếu không biết)",
        required=False,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        appeal_ch = guild.get_channel(cfg.appeal_channel_id)

        embed = discord.Embed(
            title="📨 Kháng Cáo Mới",
            description=f"Thành viên {interaction.user.mention} gửi kháng cáo.",
            color=COLOR_INFO,
        )
        embed.add_field(
            name="Vi phạm bị xử phạt",
            value=self.violation.value,
            inline=False,
        )
        embed.add_field(
            name="Giải trình",
            value=self.explanation.value,
            inline=False,
        )
        embed.add_field(
            name="Case ID",
            value=self.case_id.value or "Không cung cấp",
            inline=True,
        )
        embed.add_field(
            name="Người dùng",
            value=f"{interaction.user} (`{interaction.user.id}`)",
            inline=True,
        )
        embed.set_footer(text="Xem xét và phản hồi qua DM của người dùng.")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        view = AppealActionView(interaction.user.id)

        if appeal_ch:
            await appeal_ch.send(embed=embed, view=view)
            await interaction.response.send_message(
                embed=utils.mod_embed(
                    "✅ Kháng cáo đã được gửi",
                    "Ban quản trị sẽ xem xét và phản hồi qua DM của bạn sớm nhất có thể.\n"
                    "Vui lòng giữ nguyên trạng thái DM để nhận thông báo.",
                    COLOR_SUCCESS,
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Kênh kháng cáo chưa được cấu hình. Hãy liên hệ trực tiếp với Admin.",
                ephemeral=True,
            )


class AppealActionView(discord.ui.View):
    """View nút Chấp nhận / Từ chối kháng cáo cho Staff."""

    def __init__(self, appellant_id: int) -> None:
        super().__init__(timeout=None)
        self.appellant_id = appellant_id

    @discord.ui.button(label="✅ Chấp nhận", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction,
                     button: discord.ui.Button) -> None:
        if not utils.is_mod(interaction.user):
            return await interaction.response.send_message(
                "❌ Chỉ Moderator mới có thể xử lý kháng cáo.", ephemeral=True
            )

        user = interaction.guild.get_member(self.appellant_id)
        if user:
            try:
                await user.send(
                    embed=utils.mod_embed(
                        "✅ Kháng cáo được chấp nhận",
                        "Ban quản trị đã xem xét và chấp nhận kháng cáo của bạn.\n"
                        "Xử phạt của bạn đã được gỡ bỏ (nếu có). Chào mừng trở lại!",
                        COLOR_SUCCESS,
                    )
                )
            except discord.HTTPException:
                pass

        embed = interaction.message.embeds[0]
        embed.color = COLOR_SUCCESS
        embed.set_footer(text=f"✅ Chấp nhận bởi {interaction.user} | {embed.footer.text}")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            f"✅ Đã chấp nhận kháng cáo và thông báo cho người dùng.", ephemeral=True
        )

    @discord.ui.button(label="❌ Từ chối", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction,
                     button: discord.ui.Button) -> None:
        if not utils.is_mod(interaction.user):
            return await interaction.response.send_message(
                "❌ Chỉ Moderator mới có thể xử lý kháng cáo.", ephemeral=True
            )

        user = interaction.guild.get_member(self.appellant_id)
        if user:
            try:
                await user.send(
                    embed=utils.mod_embed(
                        "❌ Kháng cáo bị từ chối",
                        "Ban quản trị đã xem xét kháng cáo của bạn và quyết định giữ nguyên hình phạt.\n"
                        "Nếu bạn có thêm bằng chứng hoặc thắc mắc, hãy liên hệ Admin.",
                        COLOR_ERROR,
                    )
                )
            except discord.HTTPException:
                pass

        embed = interaction.message.embeds[0]
        embed.color = COLOR_ERROR
        embed.set_footer(text=f"❌ Từ chối bởi {interaction.user} | {embed.footer.text}")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            "❌ Đã từ chối kháng cáo và thông báo cho người dùng.", ephemeral=True
        )


class Appeals(commands.Cog):
    """Hệ thống kháng cáo."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="appeal", description="Gửi kháng cáo lên ban quản trị")
    async def appeal(self, ctx: commands.Context) -> None:
        """Mở form kháng cáo."""
        if hasattr(ctx, "interaction") and ctx.interaction:
            await ctx.interaction.response.send_modal(AppealModal())
        else:
            # Prefix command: gửi link hướng dẫn
            await ctx.send(
                embed=utils.mod_embed(
                    "📝 Hướng dẫn kháng cáo",
                    "Dùng lệnh **slash** `/appeal` để mở form kháng cáo.\n"
                    "Hoặc liên hệ trực tiếp với Admin qua DM.",
                    COLOR_INFO,
                ),
                ephemeral=False,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Appeals(bot))
