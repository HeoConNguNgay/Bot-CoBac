# ✅ Đã giữ nguyên toàn bộ cấu trúc và logic gốc của bạn
# ✅ Chỉ tích hợp kiểm tra quyền user.id == MY_USER_ID cho lệnh /cupsreset và !cupsreset
# ✅ Không rút gọn, xoá hay thay đổi bất kỳ chi tiết nào

import discord
from discord.ext import commands
from discord import app_commands
import random
import os
import json
import time
from database_utils import get_balance, update_balance, add_win, load_json, save_json
from config import CURRENCY_NAME
from cooldown import check_cooldown

STATS_FILE = "data/cups.json"
MAX_BET = 1_000_000
COOLDOWN_SECONDS = 10
MY_USER_ID = 426804092778840095  # ⚠️ Thay ID thật của bạn

def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

class Cups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "🍀", "7️"]

    def get_win_chance(self, bet):
        if bet <= 50000:
            return 1/2
        elif bet <= 150000:
            return 1/4
        elif bet <= 300000:
            return 1/7
        else:
            return 1/10

    # 🎮 Slash command chính của cups
    @app_commands.command(name="cups", description="🥄 Đoán vị trí ô vuông dưới 3 cái cốc để thắng cược!")
    @app_commands.describe(bet="Số tiền cược")
    async def cups_game(self, interaction: discord.Interaction, bet: int):
        user_id = str(interaction.user.id)

        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {wait_time:.1f} giây...", ephemeral=True)

        if is_banned(user_id):
            return await interaction.response.send_message("🚫 Bạn đã bị cấm sử dụng bot.", ephemeral=True)
        if is_locked(user_id):
            return await interaction.response.send_message("🔒 Tài khoản đã bị khóa chơi game.", ephemeral=True)

        balance = get_balance(interaction.user.id)
        if bet <= 0:
            return await interaction.response.send_message("❗ Cược phải lớn hơn 0!", ephemeral=True)
        if bet > MAX_BET:
            return await interaction.response.send_message("❗ Cược tối đa 1,000,000!", ephemeral=True)
        if bet > balance:
            return await interaction.response.send_message(f"❗ Không đủ tiền! Hiện tại: {balance:,} {CURRENCY_NAME}", ephemeral=True)

        win_chance = self.get_win_chance(bet)
        stats = load_json(STATS_FILE)
        user_stats = stats.get(user_id, {"plays": 0, "wins": 0})

        won = random.random() < win_chance
        if won:
            result = ["💎"] * 3
            reward = bet * 5
            update_balance(interaction.user.id, reward)
            user_stats["wins"] += 1
            add_win(user_id)
            outcome = f"🎉 **THẮNG**! Nhận {reward:,} {CURRENCY_NAME}!"
        else:
            result = [random.choice(self.SYMBOLS) for _ in range(3)]
            update_balance(interaction.user.id, -bet)
            outcome = f"😥 Không trúng. Mất {bet:,} {CURRENCY_NAME}."

        user_stats["plays"] += 1
        stats[user_id] = user_stats
        save_json(STATS_FILE, stats)

        embed = discord.Embed(title="🥄 CUPS", color=discord.Color.fuchsia())
        embed.description = f"{' | '.join(result)}\n\n{interaction.user.mention} cược 💸 {bet} {CURRENCY_NAME}\n{outcome}"
        await interaction.response.send_message(embed=embed)

    # 🎮 All-in theo số dư
    @app_commands.command(name="cupsall", description="🥄 Đoán vị trí với toàn bộ số dư hiện có")
    async def cups_all(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {wait_time:.1f} giây...", ephemeral=True)

        if is_banned(user_id):
            return await interaction.response.send_message("🚫 Bị cấm chơi.", ephemeral=True)
        if is_locked(user_id):
            return await interaction.response.send_message("🔒 Bị khóa tài khoản.", ephemeral=True)

        balance = get_balance(interaction.user.id)
        if balance <= 0:
            return await interaction.response.send_message(f"❗ Bạn không có {CURRENCY_NAME} để chơi!", ephemeral=True)

        bet = min(balance, MAX_BET)
        win_chance = self.get_win_chance(bet)

        stats = load_json(STATS_FILE)
        user_stats = stats.get(user_id, {"plays": 0, "wins": 0})

        won = random.random() < win_chance
        if won:
            result = ["💎"] * 3
            reward = bet * 5
            update_balance(interaction.user.id, reward)
            user_stats["wins"] += 1
            add_win(user_id)
            outcome = f"🎉 **THẮNG**! Nhận {reward:,} {CURRENCY_NAME}!"
        else:
            result = [random.choice(self.SYMBOLS) for _ in range(3)]
            update_balance(interaction.user.id, -bet)
            outcome = f"😥 Không trúng. Mất {bet:,} {CURRENCY_NAME}."

        user_stats["plays"] += 1
        stats[user_id] = user_stats
        save_json(STATS_FILE, stats)

        embed = discord.Embed(title="🥄 CUPS (All-in)", color=discord.Color.fuchsia())
        embed.description = f"{' | '.join(result)}\n\n{interaction.user.mention} all-in 💸 {bet} {CURRENCY_NAME}\n{outcome}"
        await interaction.response.send_message(embed=embed)

    # 📊 Thống kê cá nhân
    @app_commands.command(name="cupsstats", description="📊 Xem thống kê cá nhân trò chơi Cups")
    async def cups_stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        stats = load_json(STATS_FILE).get(user_id, {"plays": 0, "wins": 0})
        plays, wins = stats["plays"], stats["wins"]
        winrate = f"{(wins / plays * 100):.2f}%" if plays else "N/A"

        embed = discord.Embed(title="📊 Cups Stats", color=discord.Color.green())
        embed.add_field(name="🎠 Lượt chơi", value=str(plays), inline=True)
        embed.add_field(name="🏆 Thắng", value=str(wins), inline=True)
        embed.add_field(name="📈 Tỷ lệ", value=winrate, inline=True)
        await interaction.response.send_message(embed=embed)

    # 🏆 Bảng xếp hạng top người chơi
    @app_commands.command(name="cupsleaderboard", description="🏆 Xem top người chơi thắng nhiều nhất")
    async def cups_leaderboard(self, interaction: discord.Interaction):
        if not os.path.exists(STATS_FILE):
            return await interaction.response.send_message("❗ Chưa có dữ liệu.", ephemeral=True)

        try:
            with open(STATS_FILE, "r") as f:
                stats = json.load(f)
        except:
            stats = {}

        top = sorted(stats.items(), key=lambda x: x[1].get("wins", 0), reverse=True)[:10]

        embed = discord.Embed(title="🥄 Bảng Xếp Hạng Cups", color=discord.Color.gold())
        for idx, (user_id, data) in enumerate(top, start=1):
            user = await self.bot.fetch_user(int(user_id))
            plays = data.get("plays", 0)
            wins = data.get("wins", 0)
            losses = plays - wins
            winrate = f"{(wins / plays * 100):.2f}%" if plays else "N/A"
            embed.add_field(
                name=f"#{idx} – {user.display_name}",
                value=f"✅ Thắng: {wins} | ❌ Thua: {losses} | 📈 Tỷ lệ: {winrate}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    # 🛠️ Admin reset thống kê người chơi
    @app_commands.command(name="cupsreset", description="🛠️ (Admin) Xóa thống kê Cups của người chơi")
    @app_commands.describe(user="Người cần xóa dữ liệu")
    @app_commands.checks.has_permissions(administrator=True)
    async def cups_reset(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id != MY_USER_ID:
            return await interaction.response.send_message("🚫 Bạn không có quyền sử dụng lệnh này.", ephemeral=True)

        user_id = str(user.id)
        stats = load_json(STATS_FILE)
        if user_id in stats:
            del stats[user_id]
            save_json(STATS_FILE, stats)
            await interaction.response.send_message(f"✅ Đã xóa dữ liệu của {user.mention}.")
        else:
            await interaction.response.send_message("❗ Người này chưa có dữ liệu.", ephemeral=True)

    # 📦 Prefix commands (!cups ...)
    @commands.command(name="cups")
    async def cups_prefix(self, ctx: commands.Context, bet: int):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cups_game(interaction, bet)

    @commands.command(name="cupsall")
    async def cupsall_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cups_all(interaction)

    @commands.command(name="cupsstats")
    async def cupsstats_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cups_stats(interaction)

    @commands.command(name="cupsleaderboard")
    async def cupsleaderboard_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cups_leaderboard(interaction)

    @commands.command(name="cupsreset")
    @commands.has_permissions(administrator=True)
    async def cupsreset_prefix(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id != MY_USER_ID:
            return await ctx.send("🚫 Bạn không có quyền sử dụng lệnh này.")
        interaction = await self.bot.get_application_context(ctx.message)
        await self.cups_reset(interaction, user)

# 🔄 Đăng ký cog
async def setup(bot):
    await bot.add_cog(Cups(bot))
