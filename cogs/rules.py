"""
cogs/rules.py – Hiển thị nội quy server dưới dạng embed đẹp
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import cfg
import utils

# ─── Nội quy chi tiết ────────────────────────────────────────────────────────

RULES_DATA = [
    {
        "emoji": "🤝",
        "title": "1. Tôn trọng lẫn nhau",
        "rules": [
            "Luôn tôn trọng và lịch sự với mọi người.",
            "Cấm quấy rối dưới mọi hình thức.",
            "**Cấm tuyệt đối** phát ngôn thù ghét, từ ngữ xúc phạm hoặc phân biệt đối xử (giới tính, chủng tộc, tôn giáo...).",
            "Cấm đe dọa người khác.",
            "Không tranh cãi công khai – xử lý mâu thuẫn qua DM.",
            "Không **rage bait** (cố tình khiêu khích để gây tranh luận).",
            "Không lạm dụng ngôn từ tục tĩu quá mức.",
        ],
    },
    {
        "emoji": "⚖️",
        "title": "2. Không chia sẻ nội dung vi phạm pháp luật",
        "rules": [
            "**Cấm tuyệt đối** chia sẻ nội dung đồi trụy, bạo lực, lừa đảo hoặc vi phạm pháp luật.",
        ],
    },
    {
        "emoji": "👮",
        "title": "3. Tôn trọng Staff Server",
        "rules": [
            "Tuân thủ hướng dẫn từ nhân viên server.",
            "Nếu có thắc mắc về quyết định của mod, liên hệ qua kênh phù hợp, không tranh cãi công khai.",
        ],
    },
    {
        "emoji": "📢",
        "title": "4. Cấm Quảng Cáo",
        "rules": [
            "**Cấm** mọi hình thức quảng cáo (server Discord khác, shop, v.v.).",
            "Chỉ được quảng cáo khi có phép từ admin.",
            "Cấm quảng cáo qua DM.",
            "Nhắc đến gián tiếp cũng bị tính là vi phạm.",
        ],
    },
    {
        "emoji": "🚫",
        "title": "5. Nội dung bị cấm",
        "rules": [
            "**Spam:** Gửi tin nhắn lặp đi lặp lại.",
            "**NSFW/NSFL/Gore:** Cấm mọi hình thức.",
            "**GIF/Video nhấp nháy mạnh** không gắn spoiler.",
            "**Link đáng ngờ/độc hại** → ban ngay lập tức.",
            "**Thông tin cá nhân người khác** → ban vĩnh viễn.",
            "**Nội dung chính trị bao gồm nhưng không giới hạn ở tôn giáo , chính trị , ...** → xóa và cảnh báo; tái phạm → mute/ban.",
        ],
    },
    {
        "emoji": "👤",
        "title": "6. Tên & Ảnh đại diện",
        "rules": [
            "Không dùng tên/avatar phản cảm hoặc chính trị cực đoan.",
            "Vi phạm sẽ bị reset username hoặc tạm mute.",
        ],
    },
    {
        "emoji": "🤖",
        "title": "7. Cấm mạo danh / Lạm dụng AI",
        "rules": [
            "Cấm mạo danh và sử dụng AI để giả mạo người khác.",
        ],
    },
    {
        "emoji": "📌",
        "title": "8. Sử dụng kênh đúng mục đích",
        "rules": [
            "Dùng kênh theo đúng mục đích đã đặt ra.",
            "Đọc mô tả kênh trước khi gửi tin nhắn.",
            "Kênh **Chat Chung** là kênh duy nhất không áp dụng luật này.",
        ],
    },
    {
        "emoji": "🎙️",
        "title": "9. Kênh Voice",
        "rules": [
            "Không la hét vào micro, gây nhiễu hoặc để tiếng ồn nền quá mức.",
            "Cố tình vi phạm → bị chặn quyền dùng voice.",
        ],
    },
    {
        "emoji": "📜",
        "title": "10. Điều khoản Discord",
        "rules": [
            "Tuân thủ [Điều khoản dịch vụ](https://discord.com/terms) và [Quy tắc cộng đồng](https://discord.com/guidelines) của Discord.",
        ],
    },
]

PUNISHMENT_INFO = """
**Hệ thống xử phạt leo thang cho Thành viên:**
> ⚠️ Warn 1-2 → Cảnh cáo + DM
> 🔇 Warn 3 → Mute **1 giờ**
> 🔇 Warn 4 → Mute **2 giờ**
> 🔇 Warn 5 → Mute **7 giờ**
> 🔇 Warn 6 → Mute **14 giờ**
> 🔇 Warn 7 → Mute **28 giờ**
> 🔇 Warn 8 → Mute **56 giờ**
> 🔇 Warn 9 → Mute **72 giờ**
> ⚖️ Warn 10+ → Mute **72 giờ** + Đề xuất **BAN** lên nhóm Staff để Admin duyệt

💡 Thành viên có thể dùng lệnh `/report @user <lý do>` để báo cáo vi phạm đến Ban Quản Trị.

**Kháng cáo:** Dùng lệnh `/appeal` nếu bạn cho rằng mình bị xử oan.
"""
STAFF_RULES_DATA = [
    {
        "emoji": "⚖️",
        "title": "1. Không lạm quyền (Abuse of Power)",
        "rules": [
            "Không ban/kick/mute thành viên vì lý do cá nhân hoặc xích mích riêng tư.",
            "Phải có lý do chính đáng và bằng chứng (nếu cần) khi xử phạt. Dùng lệnh bot phải kèm theo lý do rõ ràng.",
            "**Moderator không được tự ý Ban/Kick** thành viên. Phải dùng lệnh `/propose` để đề xuất lên nhóm Staff, chờ Admin duyệt.",
        ],
    },
    {
        "emoji": "🌟",
        "title": "2. Thái độ chuẩn mực",
        "rules": [
            "Luôn giữ thái độ khách quan, bình tĩnh và tôn trọng khi giải quyết khiếu nại/kháng cáo của member.",
            "Tuyệt đối không dùng từ ngữ xúc phạm hoặc chửi bới thành viên, dù họ có sai. Staff phải làm gương.",
        ],
    },
    {
        "emoji": "🔒",
        "title": "3. Bảo mật thông tin",
        "rules": [
            "Không tiết lộ thông tin nội bộ của ban quản trị (các cuộc họp, kênh chat riêng của staff, hoặc thông tin cá nhân của member) ra ngoài.",
        ],
    },
    {
        "emoji": "📝",
        "title": "4. Xử lý công việc & Kháng cáo",
        "rules": [
            "Khi có member dùng `/appeal` (kháng cáo), cần xem xét kỹ log và bằng chứng trước khi quyết định Accept/Reject.",
            "Không tự ý can thiệp hoặc gỡ phạt (unmute/unban) một case do Admin/Mod khác xử lý nếu chưa thảo luận với người đó.",
        ],
    },
    {
        "emoji": "👀",
        "title": "5. Hoạt động & Trách nhiệm",
        "rules": [
            "Thường xuyên theo dõi kênh mod-log và các cảnh báo từ Auto-Mod.",
        ],
    },
]

STAFF_PUNISHMENT_INFO = """
**Hệ thống xử phạt dành cho Staff vi phạm:**
> ⚠️ **Lần 1:** Nhắc nhở nội bộ.
> ⚠️ **Lần 2:** Cảnh cáo chính thức + ghi nhận.
> 🔻 **Lần 3:** Tước quyền Mod **1 giờ**.
> 🔻 **Lần 4:** Tước quyền Mod **2 giờ**.
> 🔻 **Lần 5:** Tước quyền Mod **7 giờ**.
> 🔻 **Lần 6:** Tước quyền Mod **14 giờ**.
> 🔻 **Lần 7:** Tước quyền Mod **28 giờ**.
> 🔻 **Lần 8:** Tước quyền Mod **56 giờ**.
> 🔻 **Lần 9:** Tước quyền Mod **72 giờ**.
> 🔨 **Nghiêm trọng:** (Tự ý ban/kick hàng loạt, phá server, lạm quyền nghiêm trọng) → **Ban vĩnh viễn** lập tức, không kháng cáo.

⚠️ Mod **không được tự ý Ban/Kick** thành viên. Phải dùng `/propose` để đề xuất lên nhóm Staff, Admin sẽ duyệt.
Owner / Admin cấp cao sẽ xem xét và đưa ra quyết định dựa trên mức độ nghiêm trọng.
"""


class Rules(commands.Cog):
    """Cog hiển thị nội quy server."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _send_rules_to_channel(self, channel: discord.abc.Messageable,
                                      guild: discord.Guild) -> None:
        """Gửi toàn bộ nội quy dưới dạng embed đẹp."""

        # Header embed
        header = discord.Embed(
            title="📋 NỘI QUY MÁY CHỦ",
            description=(
                "Chào mừng đến với server! Vui lòng đọc kỹ và tuân thủ "
                "các nội quy dưới đây. Vi phạm sẽ bị xử phạt theo hệ thống "
                "leo thang.\n\n*Bằng việc ở lại server, bạn đồng ý tuân theo các quy tắc này.*"
            ),
            color=0x5865F2,
        )
        if guild.icon:
            header.set_thumbnail(url=guild.icon.url)
        header.set_footer(text=f"{guild.name} • Nội quy có hiệu lực từ khi tham gia")
        await channel.send(embed=header)

        # Gửi từng mục
        for item in RULES_DATA:
            embed = discord.Embed(
                title=f"{item['emoji']} {item['title']}",
                description="\n".join(f"• {r}" for r in item["rules"]),
                color=0x5865F2,
            )
            await channel.send(embed=embed)

        # Hệ thống xử phạt
        punishment_embed = discord.Embed(
            title="⚖️ HỆ THỐNG XỬ PHẠT",
            description=PUNISHMENT_INFO,
            color=0xE74C3C,
        )
        punishment_embed.set_footer(text="Chúc bạn có trải nghiệm vui vẻ! 🎉")
        await channel.send(embed=punishment_embed)

    async def _send_staff_rules_to_channel(self, channel: discord.abc.Messageable,
                                            guild: discord.Guild) -> None:
        """Gửi nội quy dành riêng cho Staff."""

        header = discord.Embed(
            title="🛡️ NỘI QUY DÀNH CHO ADMIN & MODERATOR",
            description=(
                "Để duy trì một môi trường công bằng và an toàn, tất cả thành viên Ban quản trị "
                "đều phải tuân thủ nghiêm ngặt các quy tắc dưới đây. Lạm quyền sẽ không được dung thứ."
            ),
            color=0x2ECC71,
        )
        if guild.icon:
            header.set_thumbnail(url=guild.icon.url)
        await channel.send(embed=header)

        for item in STAFF_RULES_DATA:
            embed = discord.Embed(
                title=f"{item['emoji']} {item['title']}",
                description="\n".join(f"• {r}" for r in item["rules"]),
                color=0x2ECC71,
            )
            await channel.send(embed=embed)

        punishment_embed = discord.Embed(
            title="⚖️ HÌNH PHẠT CHO STAFF VI PHẠM",
            description=STAFF_PUNISHMENT_INFO,
            color=0xE74C3C,
        )
        await channel.send(embed=punishment_embed)

    # ─── /rules ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="rules", description="Hiển thị nội quy server")
    async def rules(self, ctx: commands.Context) -> None:
        """Gửi nội quy vào kênh hiện tại."""
        await self._send_rules_to_channel(ctx.channel, ctx.guild)

    # ─── /staffrules ─────────────────────────────────────────────────────────

    @commands.hybrid_command(name="staffrules", description="Hiển thị nội quy dành cho Admin & Moderator")
    async def staffrules(self, ctx: commands.Context) -> None:
        """Gửi nội quy staff vào kênh hiện tại."""
        await self._send_staff_rules_to_channel(ctx.channel, ctx.guild)

    # ─── /postrules (Admin only – đăng vào kênh #rules) ─────────────────────

    @commands.hybrid_command(
        name="postrules",
        description="[Admin] Đăng nội quy vào kênh rules chính thức"
    )
    async def postrules(self, ctx: commands.Context) -> None:
        if not utils.is_mod(ctx.author):
            return await ctx.send("❌ Chỉ Admin mới dùng được lệnh này.", ephemeral=True)

        await ctx.defer(ephemeral=True)

        rules_ch = ctx.guild.get_channel(cfg.rules_channel_id)
        if not rules_ch:
            return await ctx.send(
                "❌ Không tìm thấy kênh rules. Hãy dùng lệnh `/config channel rules #kênh` để cấu hình trước.",
                ephemeral=True,
            )

        # Xóa tin nhắn cũ trong kênh rules
        try:
            await rules_ch.purge(limit=50)
        except discord.Forbidden:
            pass

        await self._send_rules_to_channel(rules_ch, ctx.guild)
        await ctx.send(f"✅ Đã đăng nội quy vào {rules_ch.mention}!", ephemeral=True)

    @commands.hybrid_command(
        name="poststaffrules",
        description="[Admin] Đăng nội quy dành cho Staff vào kênh Nội quy"
    )
    async def poststaffrules(self, ctx: commands.Context) -> None:
        if not utils.is_mod(ctx.author):
            return await ctx.send("❌ Chỉ Admin mới dùng được lệnh này.", ephemeral=True)

        await ctx.defer(ephemeral=True)

        # Tìm kênh có tên "Nội quy"
        rules_ch = None
        for ch in ctx.guild.text_channels:
            norm_name = utils.normalize_channel_name(ch.name)
            if norm_name in ["noi quy", "nội quy"]:
                rules_ch = ch
                break

        # Nếu không tìm thấy bằng tên, dùng rules_channel_id
        if not rules_ch:
            rules_ch = ctx.guild.get_channel(cfg.rules_channel_id)

        if not rules_ch:
            return await ctx.send(
                "❌ Không tìm thấy kênh Nội quy. Vui lòng thiết lập kênh bằng `/config channel rules #kênh` hoặc tạo kênh tên 'Nội quy'.",
                ephemeral=True,
            )

        # Gửi nội quy staff vào kênh rules_ch
        await self._send_staff_rules_to_channel(rules_ch, ctx.guild)
        await ctx.send(f"✅ Đã đăng nội quy staff vào kênh {rules_ch.mention}!", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Rules(bot))
