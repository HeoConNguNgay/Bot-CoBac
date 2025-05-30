import discord
from discord.ext import commands
from discord import app_commands
from database_utils import update_balance, load_json, save_json
import os
from config import CURRENCY_NAME

# ==== TIỆN ÍCH KIỂM TRA TRẠNG THÁI ====
def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

# ==== COG ADMIN ====
class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 💰 Cộng tiền (slash)
    @app_commands.command(name="addtien", description="🛠️ Admin cộng tiền cho người chơi")
    @app_commands.describe(user="Người cần cộng tiền", amount="Số {CURRENCY_NAME} muốn cộng")
    @app_commands.checks.has_permissions(administrator=True)
    async def addtien(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Số tiền phải > 0.", ephemeral=True)
        if is_banned(user.id) or is_locked(user.id):
            return await interaction.response.send_message("⚠️ Người này đã bị ban/lock. Không thể cộng tiền.", ephemeral=True)
        update_balance(user.id, amount)
        await interaction.response.send_message(f"✅ Đã cộng {amount:,} {CURRENCY_NAME} cho {user.mention}.")

    # 💣 Xóa toàn bộ dữ liệu (slash)
    @app_commands.command(name="resetall", description="🧨 Admin xóa toàn bộ dữ liệu người chơi")
    @app_commands.describe(member="Người cần reset dữ liệu")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_data(self, interaction: discord.Interaction, member: discord.Member):
        uid = str(member.id)
        if is_banned(uid) or is_locked(uid):
            return await interaction.response.send_message("⚠️ Người này đã bị ban/lock. Không thể thao tác.", ephemeral=True)
        files = ["balance.json", "streak.json", "wins.json", "stats.json", "transfer_limits.json"]
        deleted = False
        for f in files:
            path = os.path.join("data", f)
            data = load_json(path)
            if uid in data:
                del data[uid]
                save_json(path, data)
                deleted = True
        if deleted:
            await interaction.response.send_message(f"✅ Đã xóa toàn bộ dữ liệu của {member.mention}.")
        else:
            await interaction.response.send_message("⚠️ Người dùng chưa có dữ liệu để xóa.", ephemeral=True)

    # ⛔ Ban (slash)
    @app_commands.command(name="ban", description="⛔ Cấm người dùng sử dụng bot")
    @app_commands.describe(user="Người cần cấm")
    @app_commands.checks.has_permissions(administrator=True)
    async def ban_user(self, interaction: discord.Interaction, user: discord.User):
        banned = load_json("data/banned.json")
        banned[str(user.id)] = True
        save_json("data/banned.json", banned)
        await interaction.response.send_message(f"🚫 {user.mention} đã bị cấm sử dụng bot.")

    # 🔒 Lock (slash)
    @app_commands.command(name="lock", description="🔒 Khóa tính năng chuyển tiền hoặc chơi game")
    @app_commands.describe(user="Người cần khóa")
    @app_commands.checks.has_permissions(administrator=True)
    async def lock_user(self, interaction: discord.Interaction, user: discord.User):
        locked = load_json("data/locked.json")
        locked[str(user.id)] = True
        save_json("data/locked.json", locked)
        await interaction.response.send_message(f"🔒 Đã khóa một số tính năng với {user.mention}.")

    # 📂 Xem dữ liệu (slash)
    @app_commands.command(name="xemdata", description="📂 Xem dữ liệu người chơi")
    @app_commands.describe(user="Người cần xem")
    @app_commands.checks.has_permissions(administrator=True)
    async def xem_data(self, interaction: discord.Interaction, user: discord.User):
        uid = str(user.id)
        paths = {
            "balance": "balance.json",
            "streak": "streak.json",
            "wins": "wins.json",
            "stats": "stats.json",
            "transfer": "transfer_limits.json"
        }
        report = f"📊 Dữ liệu của {user.display_name} ({user.id}):\n"
        for label, file in paths.items():
            path = os.path.join("data", file)
            data = load_json(path).get(uid)
            report += f"- {label}: {data}\n"
        await interaction.response.send_message(report[:2000])

    # ✅ PREFIX VERSION ĐẦY ĐỦ ---

    @commands.command(name="addtien")
    @commands.has_permissions(administrator=True)
    async def addtien_prefix(self, ctx: commands.Context, user: discord.User, amount: int):
        if amount <= 0:
            return await ctx.send("Số tiền phải > 0.")
        if is_banned(user.id) or is_locked(user.id):
            return await ctx.send("⚠️ Người này đã bị ban/lock. Không thể cộng tiền.")
        update_balance(user.id, amount)
        await ctx.send(f"✅ Đã cộng {amount:,} {CURRENCY_NAME} cho {user.mention}.")

    @commands.command(name="resetall")
    @commands.has_permissions(administrator=True)
    async def resetall_prefix(self, ctx: commands.Context, member: discord.Member):
        uid = str(member.id)
        if is_banned(uid) or is_locked(uid):
            return await ctx.send("⚠️ Người này đã bị ban/lock. Không thể thao tác.")
        files = ["balance.json", "streak.json", "wins.json", "stats.json", "transfer_limits.json"]
        deleted = False
        for f in files:
            path = os.path.join("data", f)
            data = load_json(path)
            if uid in data:
                del data[uid]
                save_json(path, data)
                deleted = True
        if deleted:
            await ctx.send(f"✅ Đã xóa toàn bộ dữ liệu của {member.mention}.")
        else:
            await ctx.send("⚠️ Người dùng chưa có dữ liệu để xóa.")

    @commands.command(name="ban")
    @commands.has_permissions(administrator=True)
    async def ban_prefix(self, ctx: commands.Context, user: discord.User):
        banned = load_json("data/banned.json")
        banned[str(user.id)] = True
        save_json("data/banned.json", banned)
        await ctx.send(f"🚫 {user.mention} đã bị cấm sử dụng bot.")

    @commands.command(name="lock")
    @commands.has_permissions(administrator=True)
    async def lock_prefix(self, ctx: commands.Context, user: discord.User):
        locked = load_json("data/locked.json")
        locked[str(user.id)] = True
        save_json("data/locked.json", locked)
        await ctx.send(f"🔒 Đã khóa một số tính năng với {user.mention}.")

    @commands.command(name="xemdata")
    @commands.has_permissions(administrator=True)
    async def xemdata_prefix(self, ctx: commands.Context, user: discord.User):
        uid = str(user.id)
        paths = {
            "balance": "balance.json",
            "streak": "streak.json",
            "wins": "wins.json",
            "stats": "stats.json",
            "transfer": "transfer_limits.json"
        }
        report = f"📊 Dữ liệu của {user.display_name} ({user.id}):\n"
        for label, file in paths.items():
            path = os.path.join("data", file)
            data = load_json(path).get(uid)
            report += f"- {label}: {data}\n"
        await ctx.send(report[:2000])

# Đăng ký cog
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))