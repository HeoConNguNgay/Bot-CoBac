import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import time
import asyncio
from database_utils import get_balance, update_balance, update_stats, get_streak, update_streak, load_json, save_json
from config import CURRENCY_NAME
from cooldown import check_cooldown

STATS_FILE = "data/stats.json"
HEADS_IMG = "https://upload.wikimedia.org/wikipedia/commons/1/1c/US_Nickel_Obv.png"
TAILS_IMG = "https://upload.wikimedia.org/wikipedia/commons/9/9b/US_Nickel_Rev.png"
MY_USER_ID = 426804092778840095  # ⚠️ Thay bằng ID thật của bạn

# ==== TIỆN ÍCH KIỂM TRA TRẠNG THÁI NGƯỜI CHƠI ====
def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

# ==== LỚP CHÍNH: COINFLIP GAME ====
class Coinflip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash lệnh: /cf
    @app_commands.command(name="cf", description="Chơi tung đồng xu cược tiền")
    @app_commands.describe(bet="Số tiền cược", side="Chọn mặt: heads (ngửa) hoặc tails (sấp)")
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, side: app_commands.Choice[str]):
        user_id = interaction.user.id
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi chơi tiếp.", ephemeral=True)
        if is_banned(user_id) or is_locked(user_id):
            return await interaction.response.send_message("🚫 Tài khoản của bạn bị hạn chế.", ephemeral=True)
        balance = get_balance(user_id)
        if bet < 1:
            return await interaction.response.send_message("❗ Cược phải lớn hơn 0.", ephemeral=True)
        if bet > 1_000_000:
            return await interaction.response.send_message("❗ Cược tối đa là 1,000,000.", ephemeral=True)
        if bet > balance:
            return await interaction.response.send_message(f"❗ Không đủ tiền! Hiện có {balance:,} {CURRENCY_NAME}.", ephemeral=True)

        await self.resolve_flip(interaction, user_id, bet, side.value)

    # Slash lệnh: /cfall - all-in toàn bộ
    @app_commands.command(name="cfall", description="Cược toàn bộ số dư vào tung đồng xu")
    @app_commands.describe(side="Chọn mặt")
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip_all(self, interaction: discord.Interaction, side: app_commands.Choice[str]):
        user_id = interaction.user.id
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi chơi tiếp.", ephemeral=True)
        if is_banned(user_id) or is_locked(user_id):
            return await interaction.response.send_message("🚫 Tài khoản của bạn bị hạn chế.", ephemeral=True)
        balance = get_balance(user_id)
        if balance < 1:
            return await interaction.response.send_message("❗ Bạn không có tiền để cược.", ephemeral=True)

        await self.resolve_flip(interaction, user_id, balance, side.value)

    # 📊 Thống kê cá nhân
    @app_commands.command(name="cfstats", description="Xem thống kê thắng/thua xu và chuỗi thắng")
    async def cf_stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        stats = load_json(STATS_FILE).get(user_id, {"win": 0, "loss": 0})
        wins = stats.get("win", 0)
        losses = stats.get("loss", 0)
        total = wins + losses
        winrate = f"{(wins / total * 100):.2f}%" if total else "N/A"
        streak = get_streak(int(user_id))

        embed = discord.Embed(title="📊 Coinflip Stats", color=discord.Color.green())
        embed.add_field(name="🎯 Thắng", value=str(wins), inline=True)
        embed.add_field(name="💥 Thua", value=str(losses), inline=True)
        embed.add_field(name="📈 Tỷ lệ thắng", value=winrate, inline=True)
        embed.add_field(name="🔥 Chuỗi thắng hiện tại", value=str(streak), inline=False)
        await interaction.response.send_message(embed=embed)

    # 🏆 BXH
    @app_commands.command(name="cfleaderboard", description="Xem top người chơi thắng nhiều nhất")
    async def cf_leaderboard(self, interaction: discord.Interaction):
        stats_data = load_json(STATS_FILE)
        top = sorted(stats_data.items(), key=lambda item: item[1].get("win", 0), reverse=True)[:10]

        embed = discord.Embed(title="🏆 Bảng xếp hạng Coinflip", color=discord.Color.purple())
        for idx, (uid, data) in enumerate(top, 1):
            user = await self.bot.fetch_user(int(uid))
            streak = get_streak(int(uid))
            embed.add_field(
                name=f"#{idx} - {user.name}",
                value=f"🎯 Thắng: {data.get('win', 0)} | 🔥 Streak: {streak}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    # 🛠️ Admin reset
    @app_commands.command(name="cfreset", description="Reset dữ liệu coinflip (Admin)")
    @app_commands.describe(user="Người cần reset")
    async def cf_reset(self, interaction: discord.Interaction, user: discord.User):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❗ Bạn không có quyền dùng lệnh này.", ephemeral=True)

        user_id = str(user.id)
        stats = load_json(STATS_FILE)
        if user_id in stats:
            stats[user_id] = {"win": 0, "loss": 0}
            save_json(STATS_FILE, stats)
            update_streak(int(user_id), False)
            await interaction.response.send_message(f"✅ Đã reset dữ liệu coinflip cho {user.mention}.")
        else:
            await interaction.response.send_message("❗ Người dùng này chưa có dữ liệu.", ephemeral=True)

    # 🧠 Hàm chính xử lý tung xu & hiển thị kết quả đẹp
    async def resolve_flip(self, interaction, user_id, bet, chosen):
        await interaction.response.send_message(f"{interaction.user.mention} đã cược 🧊 {bet:,} và chọn **{chosen.upper()}**...")
        msg = await interaction.original_response()

        for countdown in ["🌀 Tung đồng xu...", "⏳ 3...", "⏳ 2...", "⏳ 1..."]:
            await msg.edit(content=countdown)
            await asyncio.sleep(1)

        flipped = random.choice(["heads", "tails"])
        is_win = (chosen == flipped)

        if is_win:
            reward = bet * 2
            update_balance(user_id, reward)
            update_stats(user_id, "win")
            streak = get_streak(user_id) + 1
            update_streak(user_id, True)
            result_text = f"🎉 Đồng xu ra **{flipped.upper()}**! Bạn thắng 🧊 {reward:,}!🔥 Chuỗi thắng: {streak}"
        else:
            update_balance(user_id, -bet)
            update_stats(user_id, "loss")
            update_streak(user_id, False)
            result_text = f"💔 Đồng xu ra **{flipped.upper()}**! Bạn thua 🧊 {bet:,}...\n🧊 Chuỗi thắng bị reset"

        embed = discord.Embed(title="🪙 Kết quả Coinflip", color=discord.Color.blue())
        embed.set_image(url=HEADS_IMG if flipped == "heads" else TAILS_IMG)
        embed.add_field(name="👤 Người chơi", value=interaction.user.mention, inline=True)
        embed.add_field(name="🎯 Mặt đã chọn", value=chosen.upper(), inline=True)
        embed.add_field(name="📀 Kết quả tung", value=flipped.upper(), inline=True)
        embed.add_field(name="💬 Kết luận", value=result_text, inline=False)

        await msg.edit(content=None, embed=embed)

    # PREFIX BACKUP
    @commands.command(name="cf")
    async def cf_prefix(self, ctx: commands.Context, bet: int, side: str):
        class FakeChoice:
            def __init__(self, value): self.value = value
        if side.lower() not in ["heads", "tails"]:
            return await ctx.send("❗ Chỉ chấp nhận heads hoặc tails.")
        choice = FakeChoice(side.lower())
        interaction = await self.bot.get_application_context(ctx.message)
        await self.coinflip(interaction, bet, choice)

    @commands.command(name="cfall")
    async def cfall_prefix(self, ctx: commands.Context, side: str):
        class FakeChoice:
            def __init__(self, value): self.value = value
        if side.lower() not in ["heads", "tails"]:
            return await ctx.send("❗ Chỉ chấp nhận heads hoặc tails.")
        choice = FakeChoice(side.lower())
        interaction = await self.bot.get_application_context(ctx.message)
        await self.coinflip_all(interaction, choice)

    @commands.command(name="cfstats")
    async def cfstats_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cf_stats(interaction)

    @commands.command(name="cfleaderboard")
    async def cfleaderboard_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cf_leaderboard(interaction)

    @commands.command(name="cfreset")
    @commands.has_permissions(administrator=True)
    async def cfreset_prefix(self, ctx: commands.Context, user: discord.User):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cf_reset(interaction, user)

# Đăng ký cog
async def setup(bot):
    await bot.add_cog(Coinflip(bot))
