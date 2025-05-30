import discord
from discord.ext import commands
from discord import app_commands
from config import CURRENCY_NAME

MY_USER_ID = 426804092778840095  # ⚠️ Thay ID admin của bạn ở đây

# --- DANH MỤC CÁC LẬNH THEO NHÓM ---
HELP_CATEGORIES = {
    "blackjack": {
        "title": "🎴 Lệnh Blackjack",
        "thumbnail": "https://i.imgur.com/YvYgAYy.png",
        "admin_only": False,
        "commands": [
            ("/bj [số tiền]", "Chơi Blackjack với số tiền cược."),
            ("/bjall", "Cược toàn bộ số dư vào Blackjack."),
            ("/bjstats", "Xem thống kê Blackjack cá nhân."),
            ("/bjleaderboard", "Xem bảng xếp hạng Blackjack."),
            ("/bjreset [@user]", "(Admin) Reset thống kê Blackjack."),
        ]
    },
    "daily": {
        "title": "🏱 Thưởng Hàng Ngày",
        "thumbnail": "https://i.imgur.com/TDiJ0lm.png",
        "admin_only": False,
        "commands": [
            ("/diemdanh", f"Nhận thưởng điểm danh mỗi ngày (+25.000 {CURRENCY_NAME}, cộng thêm nếu điểm danh liên tiếp).")
        ]
    },
    "coinflip": {
        "title": "🪙 Lệnh Coinflip",
        "thumbnail": "https://i.imgur.com/xDZwTOk.png",
        "admin_only": False,
        "commands": [
            ("/cf [số tiền] [side]", "Cược số tiền cụ thể vào mặt đồng xu."),
            ("/cfall [side]", "Cược toàn bộ số dư vào mặt đồng xu."),
            ("/cfstats", "Xem thống kê thắng, thua và chuỗi thắng."),
            ("/cfleaderboard", "Xem bảng xếp hạng Coinflip."),
            ("/cfreset [@user]", "(Admin) Reset dữ liệu Coinflip."),
        ]
    },
    "slots": {
        "title": "🎰 Lệnh Slots",
        "thumbnail": "https://i.imgur.com/rbD5bVV.png",
        "admin_only": False,
        "commands": [
            ("/sl [số tiền]", "Quay máy slots để nhận phần thưởng."),
            ("/slall", "Quay máy Slots với toàn bộ số dư hiện tại."),
            ("/slstats", "Xem lịch sử quay và chuỗi thắng."),
            ("/slleaderboard", "BXH người thắng Slots nhiều nhất."),
            ("/slreset [@user]", "(Admin) Xóa lịch sử quay của người chơi."),
        ]
    },
    "lottery": {
        "title": "🎟️ Lệnh Lottery",
        "thumbnail": "https://i.imgur.com/tBIu8do.png",
        "admin_only": False,
        "commands": [
            ("/lottery [số tiền]", "Tham gia xổ số mỗi ngày."),
            ("/lotterystats", "Xem thống kê cá nhân và tỷ lệ trúng."),
        ]
    },
    "cups": {
        "title": "🥄 Lệnh Cups",
        "thumbnail": "https://i.imgur.com/SFxnh9v.png",
        "admin_only": False,
        "commands": [
            ("/cups [số tiền]", "Đoán vị trí ô vuông dưới 3 cái cốc."),
            ("/cupsall", f"Cược toàn bộ {CURRENCY_NAME} vào trò chơi 3 chiếc cốc."),
            ("/cupsstats", "Xem thống kê trò chơi Cups."),
            ("/cupsleaderboard", "BXH người thắng Cups nhiều nhất."),
            ("/cupsreset [@user]", "(Admin) Reset Cups."),
        ]
    },
    "dice": {
        "title": "🎲 Lệnh Dice",
        "thumbnail": "https://i.imgur.com/ZUyYmLf.png",
        "admin_only": False,
        "commands": [
            ("/dc [số]", "Lăn xúc xắc 1–6. Đoán đúng để thắng!"),
            ("/dcstats", "Xem thống kê thắng/thua xúc xắc."),
            ("/dcall", f"Cược toàn bộ số {CURRENCY_NAME} vào trò chơi."),
            ("/dcleaderboard", "Xem BXH Dice."),
            ("/dcreset [@user]", "(Admin) Reset Dice."),
        ]
    },
    "profile": {
        "title": "👤 Hồ Sơ Cá Nhân",
        "thumbnail": "https://i.imgur.com/uVnMbmH.png",
        "admin_only": False,
        "commands": [
            ("/hoso", "Xem hồ sơ cá nhân bằng hình ảnh.")
        ]
    },
    "admin": {
        "title": "🛠️ Lệnh Quản Trị (Admin)",
        "thumbnail": "https://i.imgur.com/bKHAGjP.png",
        "admin_only": True,
        "commands": [
            ("/cfreset @user", "Reset dữ liệu Coinflip người chơi."),
            ("/slreset @user", "Xóa lịch sử quay máy Slots."),
            ("/cupsreset @user", "Reset thống kê Cups."),
            ("/bjreset @user", "Reset thống kê Blackjack."),
            ("/dcreset @user", "Reset Dice."),
            ("/resetdata @user", "Xóa toàn bộ dữ liệu người chơi."),
            ("/dongbo", "Đồng bộ slash command với máy chủ."),
        ]
    }
}

# --- VIEW & SELECT DYNAMIC ---
class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool):
        super().__init__(timeout=None)
        self.add_item(HelpSelect(is_admin))

class HelpSelect(discord.ui.Select):
    def __init__(self, is_admin: bool):
        options = [
            discord.SelectOption(label=cat["title"], value=key)
            for key, cat in HELP_CATEGORIES.items()
            if not cat["admin_only"] or is_admin
        ]
        super().__init__(placeholder="Chọn nhóm lệnh...", min_values=1, max_values=1, options=options)
        self.is_admin = is_admin

    async def callback(self, interaction: discord.Interaction):
        category = HELP_CATEGORIES[self.values[0]]
        embed = discord.Embed(title=category["title"], color=discord.Color.blurple())
        embed.set_thumbnail(url=category["thumbnail"])
        for name, desc in category["commands"]:
            if "(Admin)" in desc and not self.is_admin:
                continue
            embed.add_field(name=name, value=desc, inline=False)
        await interaction.response.edit_message(embed=embed, view=HelpView(self.is_admin))

# --- COG CHÍNH ---
class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trogiup", description="Hiển thị danh sách các lệnh theo nhóm")
    async def trogiup(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator
        embed = discord.Embed(
            title="📜 Hướng Dẫn Sử Dụng Bot",
            description="Chọn nhóm lệnh cần xem ở menu bên dưới:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=HelpView(is_admin), ephemeral=True)

    @app_commands.command(name="dongbo", description="Đồng bộ slash command với máy chủ")
    @app_commands.checks.has_permissions(administrator=True)
    async def dongbo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"🔄 Đã đồng bộ {len(synced)} slash command!", ephemeral=True)
        except Exception as e:
            print("Лỗi khi đồng bộ slash command:", e)
            await interaction.followup.send(f"❌ Lỗi khi đồng bộ: {e}", ephemeral=True)

    @commands.command(name="trogiup")
    async def trogiup_prefix(self, ctx: commands.Context):
        is_admin = ctx.author.guild_permissions.administrator
        embed = discord.Embed(
            title="📜 Hướng Dẫn Sử Dụng Bot",
            description="Chọn nhóm lệnh cần xem ở menu bên dưới:",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed, view=HelpView(is_admin))

    @commands.command(name="dongbo")
    @commands.has_permissions(administrator=True)
    async def dongbo_prefix(self, ctx: commands.Context):
        try:
            synced = await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
            await ctx.send(f"🔄 Đã đồng bộ {len(synced)} slash command!", delete_after=10)
        except Exception as e:
            print("Лỗi khi đồng bộ slash command:", e)
            await ctx.send(f"❌ Lỗi khi đồng bộ: {e}")

# --- ĐĂNG KÝ ---
async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
