# ✅ Dice.py - Đã tích hợp defer() và hiển thị cooldown rõ ràng
# ✅ Giữ nguyên toàn bộ nội dung, comment, cấu trúc logic

# ==== IMPORT CẦN THIẾT ====
import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import time
import asyncio
from database_utils import add_win, get_balance, update_balance, load_json, save_json
from config import CURRENCY_NAME
from cooldown import check_cooldown  # Cooldown chống spam lệnh

# ==== CẤU HÌNH ====
DICE_STATS_FILE = "data/dice.json"
MAX_BET = 1_000_000
COOLDOWN_SECONDS = 10
MY_USER_ID = 426804092778840095  # ⚠️ Thay bằng ID thật của bạn

# ==== HÀM TIỆN ÍCH ====
def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

# ==== LỚP CHÍNH CHỨA CÁC LỆNH DICE ====
class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === Tính toán tỷ lệ thắng dựa trên mức cược ===
    def get_win_chance(self, bet):
        if bet <= 50000:
            return 1 / 2
        elif bet <= 150000:
            return 1 / 4
        elif bet <= 300000:
            return 1 / 7
        else:
            return 1 / 10

    async def _respond(self, ctx_or_interaction, message, ephemeral=False, is_prefix=False):
        if is_prefix:
            await ctx_or_interaction.send(message)
        else:
            await ctx_or_interaction.response.send_message(message, ephemeral=ephemeral)

    async def run_dice(self, ctx_or_interaction, user, guess, bet, is_prefix=False):
        user_id = str(user.id)

        if not (1 <= guess <= 6):
            return await self._respond(ctx_or_interaction, "❗ Số đoán phải từ 1 đến 6.", ephemeral=True, is_prefix=is_prefix)
        if bet <= 0 or bet > MAX_BET:
            return await self._respond(ctx_or_interaction, f"❗ Cược phải từ 1 đến {MAX_BET:,}.", ephemeral=True, is_prefix=is_prefix)

        wait_time = check_cooldown(user_id)
        if wait_time:
            seconds = int(wait_time) + 1
            message = f"❗ Slow down! Bạn còn phải chờ **{seconds} giây** trước khi dùng lại."
            return await self._respond(ctx_or_interaction, message, ephemeral=True, is_prefix=is_prefix)

        if is_banned(user_id):
            return await self._respond(ctx_or_interaction, "🚫 Tài khoản bị cấm sử dụng bot.", ephemeral=True, is_prefix=is_prefix)
        if is_locked(user_id):
            return await self._respond(ctx_or_interaction, "🔒 Tài khoản bị khoá chức năng chơi game.", ephemeral=True, is_prefix=is_prefix)

        balance = get_balance(user.id)
        if bet > balance:
            return await self._respond(ctx_or_interaction, f"❗ Không đủ tiền. Hiện có {balance:,} {CURRENCY_NAME}.", ephemeral=True, is_prefix=is_prefix)

        win_chance = self.get_win_chance(bet)
        announce = f"🎲 {user.display_name} cược 🧨 {bet:,} và đoán số {guess}\n🎲 Tung xúc xắc..."

        if is_prefix:
            msg = await ctx_or_interaction.send(announce)
        else:
            await ctx_or_interaction.response.send_message(announce, ephemeral=False)
            msg = await ctx_or_interaction.original_response()

        for count in [3, 2, 1]:
            await msg.edit(content=announce + f"\n⏳ {count}...")
            await asyncio.sleep(1)

        result = random.randint(1, 6)
        stats = load_json(DICE_STATS_FILE)
        if user_id not in stats:
            stats[user_id] = {"win": 0, "loss": 0}

        if guess == result and random.random() < win_chance:
            reward = bet * 2
            update_balance(user.id, reward)
            stats[user_id]["win"] += 1
            add_win(user_id)
            outcome = f"🎯 Kết quả: {result} — 🎉 Thắng! Nhận {reward:,} {CURRENCY_NAME}!"
        else:
            update_balance(user.id, -bet)
            stats[user_id]["loss"] += 1
            outcome = f"🎯 Kết quả: {result} — 💥 Thua. Mất {bet:,} {CURRENCY_NAME}."

        save_json(DICE_STATS_FILE, stats)
        await msg.edit(content=announce + f"\n{outcome}")

    # === Slash Command: /dc đoán số và cược ===
    @app_commands.command(name="dc", description="Chọn số từ 1-6 để đổ xúc xắc và cược")
    @app_commands.describe(guess="Số bạn đoán (1 đến 6)", bet="Số tiền muốn cược")
    @app_commands.rename(guess="sodoan", bet="cuoc")
    async def roll_dice(self, interaction: discord.Interaction, guess: int, bet: int):
        await interaction.response.defer()
        await self.run_dice(interaction, interaction.user, guess, bet)

    # === Cược toàn bộ số dư ===
    @app_commands.command(name="dcall", description="All-in xúc xắc với 1 số")
    @app_commands.describe(guess="Số bạn đoán (1 đến 6)")
    async def dice_all(self, interaction: discord.Interaction, guess: int):
        await interaction.response.defer()
        balance = get_balance(interaction.user.id)
        if balance <= 0:
            return await interaction.followup.send(f"❗ Bạn không có {CURRENCY_NAME} để cược.", ephemeral=True)
        await self.run_dice(interaction, interaction.user, guess, balance)

    # === Xem thống kê cá nhân ===
    @app_commands.command(name="dcstats", description="Xem thống kê xúc xắc của bạn")
    async def dice_stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        stats = load_json(DICE_STATS_FILE).get(user_id, {"win": 0, "loss": 0})
        win, loss = stats["win"], stats["loss"]
        total = win + loss
        winrate = f"{(win / total * 100):.2f}%" if total else "N/A"

        embed = discord.Embed(title="🎲 Thống kê Dice", color=discord.Color.green())
        embed.add_field(name="✅ Thắng", value=str(win), inline=True)
        embed.add_field(name="❌ Thua", value=str(loss), inline=True)
        embed.add_field(name="📊 Tỷ lệ thắng", value=winrate, inline=True)

        await interaction.response.send_message(embed=embed)

    # === Bảng xếp hạng người thắng nhiều ===
    @app_commands.command(name="dcleaderboard", description="Xem top cao thủ xúc xắc")
    async def dice_leaderboard(self, interaction: discord.Interaction):
        stats = load_json(DICE_STATS_FILE)
        leaderboard = sorted(stats.items(), key=lambda x: x[1].get("win", 0), reverse=True)[:10]

        embed = discord.Embed(title="🏆 Bảng Xếp Hạng Dice", color=discord.Color.gold())
        for idx, (user_id, data) in enumerate(leaderboard, start=1):
            user = await self.bot.fetch_user(int(user_id))
            win = data.get("win", 0)
            loss = data.get("loss", 0)
            total = win + loss
            winrate = f"{(win / total * 100):.2f}%" if total else "N/A"
            embed.add_field(
                name=f"#{idx} – {user.display_name}",
                value=f"✅ {win} | ❌ {loss} | 📊 {winrate}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    # === Reset thống kê cho người chơi (admin) ===
    @app_commands.command(name="dcreset", description="Reset thống kê Dice của người chơi")
    @app_commands.describe(user="Người cần reset")
    @app_commands.checks.has_permissions(administrator=True)
    async def dice_reset(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id != MY_USER_ID:
            return await interaction.response.send_message("🚫 Bạn không được cấp quyền dùng lệnh này.", ephemeral=True)

        user_id = str(user.id)
        stats = load_json(DICE_STATS_FILE)
        stats[user_id] = {"win": 0, "loss": 0}
        save_json(DICE_STATS_FILE, stats)
        await interaction.response.send_message(f"✅ Đã reset cho {user.mention}.")

    # === Các lệnh dạng prefix (dành cho !dc, !dcstats, ...) ===
    @commands.command(name="dc")
    async def dc_prefix(self, ctx: commands.Context, guess: int, bet: int):
        await self.run_dice(ctx, ctx.author, guess, bet, is_prefix=True)

    @commands.command(name="dcall")
    async def dcall_prefix(self, ctx: commands.Context, guess: int):
        balance = get_balance(ctx.author.id)
        if balance <= 0:
            return await ctx.send("❗ Bạn không có tiền để cược.")
        await self.run_dice(ctx, ctx.author, guess, balance, is_prefix=True)

    @commands.command(name="dcstats")
    async def dcstats_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.dice_stats(interaction)

    @commands.command(name="dcleaderboard")
    async def dcleaderboard_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.dice_leaderboard(interaction)

    @commands.command(name="dcreset")
    @commands.has_permissions(administrator=True)
    async def dcreset_prefix(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id != MY_USER_ID:
            return await ctx.send("🚫 Bạn không có quyền dùng lệnh này.")
        interaction = await self.bot.get_application_context(ctx.message)
        await self.dice_reset(interaction, user)

# === Gắn cog vào bot ===
async def setup(bot):
    await bot.add_cog(Dice(bot))
