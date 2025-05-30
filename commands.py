import discord
from discord.ext import commands
from discord import app_commands
from config import CURRENCY_NAME
from database_utils import (
    get_balance, get_remaining_transfer, update_balance, record_transfer,
    get_ranking, get_level, load_json, save_json, STATS_FILE, get_streak
)

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- SLASH COMMANDS ---

    @app_commands.command(name="balance", description="Xem số dư và hạn mức chuyển tiền còn lại")
    async def balance(self, interaction: discord.Interaction):
        bal = get_balance(interaction.user.id)
        remaining = get_remaining_transfer(interaction.user.id)
        await interaction.response.send_message(
            f"💰 Số dư: {bal:,} {CURRENCY_NAME}\n📤 Còn lại chuyển hôm nay: {remaining:,} {CURRENCY_NAME}"
        )

    @app_commands.command(name="chuyen", description="Chuyển tiền cho người chơi khác")
    @app_commands.describe(member="Người nhận", amount="Số tiền")
    async def chuyen(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❗ Số tiền phải > 0!", ephemeral=True)
        sender_id = interaction.user.id
        receiver_id = member.id
        if get_balance(sender_id) < amount:
            return await interaction.response.send_message("❗ Bạn không đủ tiền!", ephemeral=True)
        if get_remaining_transfer(sender_id) < amount:
            return await interaction.response.send_message("❗ Vượt quá hạn mức chuyển hôm nay!", ephemeral=True)
        update_balance(sender_id, -amount)
        update_balance(receiver_id, amount)
        record_transfer(sender_id, amount)
        await interaction.response.send_message(
            f"💸 {interaction.user.mention} đã chuyển {amount:,} {CURRENCY_NAME} cho {member.mention}!"
        )

    @app_commands.command(name="rank", description="Xem bảng xếp hạng người chơi")
    async def rank(self, interaction: discord.Interaction):
        top = get_ranking()
        desc = "\n".join([f"<@{uid}>: {wins} thắng | Cấp {get_level(wins)}" for uid, wins in top])
        embed = discord.Embed(
            title="🏆 BXH Blackjack",
            description=desc or "Chưa ai thắng.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="Thống kê cá nhân")
    async def stats(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        data = load_json(STATS_FILE)
        s = data.get(uid, {"win": 0, "loss": 0, "tie": 0})
        total = s["win"] + s["loss"] + s["tie"]
        winrate = (s["win"] / total * 100) if total else 0
        embed = discord.Embed(title=f"📋 Hồ sơ {interaction.user.display_name}", color=discord.Color.purple())
        embed.add_field(name="🏅 Cấp độ", value=str(get_level(s["win"])))
        embed.add_field(name="📈 Tỉ lệ thắng", value=f"{winrate:.1f}%")
        embed.add_field(name="✅ Thắng", value=str(s["win"]))
        embed.add_field(name="❌ Thua", value=str(s["loss"]))
        embed.add_field(name="⚖️ Hòa", value=str(s["tie"]))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="profile", description="📋 Hiển thị hồ sơ chi tiết của bạn")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        stats = load_json(STATS_FILE).get(uid, {"win": 0, "loss": 0, "tie": 0})
        balance = get_balance(uid)
        streak = get_streak(int(uid))
        wins = stats.get("win", 0)
        losses = stats.get("loss", 0)
        ties = stats.get("tie", 0)
        total = wins + losses + ties
        level = get_level(wins)
        winrate = f"{(wins / total * 100):.2f}%" if total else "N/A"

        embed = discord.Embed(title=f"📋 Hồ Sơ Cá Nhân – {interaction.user.display_name}", color=discord.Color.blurple())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="💰 Số dư", value=f"{balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="🏅 Cấp độ", value=f"{level}", inline=True)
        embed.add_field(name="🔥 Chuỗi thắng", value=f"{streak}", inline=True)
        embed.add_field(name="✅ Thắng", value=str(wins), inline=True)
        embed.add_field(name="❌ Thua", value=str(losses), inline=True)
        embed.add_field(name="🤝 Hòa", value=str(ties), inline=True)
        embed.add_field(name="📈 Tỷ lệ thắng", value=winrate, inline=True)
        await interaction.response.send_message(embed=embed)

    # --- PREFIX COMMANDS ---

    @commands.command(name="balance")
    async def balance_prefix(self, ctx: commands.Context):
        bal = get_balance(ctx.author.id)
        remaining = get_remaining_transfer(ctx.author.id)
        await ctx.send(f"💰 Số dư: {bal:,} {CURRENCY_NAME}\n📤 Còn lại chuyển hôm nay: {remaining:,} {CURRENCY_NAME}")

    @commands.command(name="chuyen")
    async def chuyen_prefix(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❗ Số tiền phải > 0!")
        sender_id = ctx.author.id
        receiver_id = member.id
        if get_balance(sender_id) < amount:
            return await ctx.send("❗ Bạn không đủ tiền!")
        remaining = get_remaining_transfer(sender_id)
        if remaining < amount:
            return await ctx.send(f"❗ Bạn chỉ còn có thể chuyển {remaining:,} {CURRENCY_NAME} hôm nay.")
        update_balance(sender_id, -amount)
        update_balance(receiver_id, amount)
        record_transfer(sender_id, amount)
        await ctx.send(f"💸 {ctx.author.mention} đã chuyển {amount:,} {CURRENCY_NAME} cho {member.mention}!")

    @commands.command(name="rank")
    async def rank_prefix(self, ctx: commands.Context):
        top = get_ranking()
        desc = "\n".join([f"<@{uid}>: {wins} thắng | Cấp {get_level(wins)}" for uid, wins in top])
        embed = discord.Embed(
            title="🏆 BXH Blackjack",
            description=desc or "Chưa ai thắng.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def stats_prefix(self, ctx: commands.Context):
        uid = str(ctx.author.id)
        data = load_json(STATS_FILE)
        s = data.get(uid, {"win": 0, "loss": 0, "tie": 0})
        total = s["win"] + s["loss"] + s["tie"]
        winrate = (s["win"] / total * 100) if total else 0
        embed = discord.Embed(title=f"📋 Hồ sơ {ctx.author.display_name}", color=discord.Color.purple())
        embed.add_field(name="🏅 Cấp độ", value=str(get_level(s["win"])))
        embed.add_field(name="📈 Tỉ lệ thắng", value=f"{winrate:.1f}%")
        embed.add_field(name="✅ Thắng", value=str(s["win"]))
        embed.add_field(name="❌ Thua", value=str(s["loss"]))
        embed.add_field(name="⚖️ Hòa", value=str(s["tie"]))
        await ctx.send(embed=embed)

    @commands.command(name="profile")
    async def profile_prefix(self, ctx: commands.Context):
        uid = str(ctx.author.id)
        stats = load_json(STATS_FILE).get(uid, {"win": 0, "loss": 0, "tie": 0})
        balance = get_balance(uid)
        streak = get_streak(int(uid))
        wins = stats.get("win", 0)
        losses = stats.get("loss", 0)
        ties = stats.get("tie", 0)
        total = wins + losses + ties
        level = get_level(wins)
        winrate = f"{(wins / total * 100):.2f}%" if total else "N/A"
        embed = discord.Embed(title=f"📋 Hồ Sơ Cá Nhân – {ctx.author.display_name}", color=discord.Color.blurple())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="💰 Số dư", value=f"{balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="🏅 Cấp độ", value=f"{level}", inline=True)
        embed.add_field(name="🔥 Chuỗi thắng", value=f"{streak}", inline=True)
        embed.add_field(name="✅ Thắng", value=str(wins), inline=True)
        embed.add_field(name="❌ Thua", value=str(losses), inline=True)
        embed.add_field(name="🤝 Hòa", value=str(ties), inline=True)
        embed.add_field(name="📈 Tỷ lệ thắng", value=winrate, inline=True)
        await ctx.send(embed=embed)

# Đăng ký cog
async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))
