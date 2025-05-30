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

    # === Slash Command: /dc đoán số và cược ===
    @app_commands.command(name="dc", description="Chọn số từ 1-6 để đổ xúc xắc và cược")
    @app_commands.describe(
        guess="Số bạn đoán (1 đến 6)",
        bet="Số tiền muốn cược"
    )
    @app_commands.rename(guess="sodoan", bet="cuoc")
    async def roll_dice(self, interaction: discord.Interaction, guess: int, bet: int):
        user_id = str(interaction.user.id)

        # Kiểm tra giới hạn đầu vào thủ công
        if not (1 <= guess <= 6):
            return await interaction.response.send_message("❗ Số đoán phải từ 1 đến 6.", ephemeral=True)
        if bet <= 0 or bet > MAX_BET:
            return await interaction.response.send_message(f"❗ Cược phải từ 1 đến {MAX_BET:,}.", ephemeral=True)

        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(
                f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi chơi tiếp.", ephemeral=True)
        if is_banned(user_id):
            return await interaction.response.send_message("🚫 Tài khoản bị cấm sử dụng bot.", ephemeral=True)
        if is_locked(user_id):
            return await interaction.response.send_message("🔒 Tài khoản bị khoá chức năng chơi game.", ephemeral=True)

        balance = get_balance(interaction.user.id)
        if bet > balance:
            return await interaction.response.send_message(
                f"❗ Không đủ tiền. Hiện có {balance:,} {CURRENCY_NAME}.", ephemeral=True)

        win_chance = self.get_win_chance(bet)
        await interaction.response.send_message(
            f"🎲 {interaction.user.display_name} cược 🧨 {bet:,} và đoán số {guess}\n🎲 Tung xúc xắc...", wait=True)
        message = await interaction.original_response()

        for count in [3, 2, 1]:
            await message.edit(content=f"🎲 {interaction.user.display_name} cược 🧨 {bet:,} và đoán số {guess}\n🎲 Tung xúc xắc...\n⏳ {count}...")
            await asyncio.sleep(1)

        result = random.randint(1, 6)
        stats = load_json(DICE_STATS_FILE)
        if user_id not in stats:
            stats[user_id] = {"win": 0, "loss": 0}

        if guess == result and random.random() < win_chance:
            reward = bet * 2
            update_balance(interaction.user.id, reward)
            stats[user_id]["win"] += 1
            add_win(user_id)
            outcome = f"🎯 Kết quả: {result} — 🎉 Thắng! Nhận {reward:,} {CURRENCY_NAME}!"
        else:
            update_balance(interaction.user.id, -bet)
            stats[user_id]["loss"] += 1
            outcome = f"🎯 Kết quả: {result} — 💥 Thua. Mất {bet:,} {CURRENCY_NAME}."

        save_json(DICE_STATS_FILE, stats)
        await message.edit(content=f"🎲 {interaction.user.display_name} cược 🧨 {bet:,} và đoán số {guess}\n🎲 Tung xúc xắc...\n{outcome}")

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

    # === Cược toàn bộ số dư ===
    @app_commands.command(name="dcall", description="All-in xúc xắc với 1 số")
    @app_commands.describe(guess="Số bạn đoán (1 đến 6)")
    async def dice_all(self, interaction: discord.Interaction, guess: int):
        user_id = str(interaction.user.id)
        bet = get_balance(interaction.user.id)

        if bet <= 0:
            return await interaction.response.send_message(f"❗ Bạn không có {CURRENCY_NAME} để cược.", ephemeral=True)
        if not (1 <= guess <= 6):
            return await interaction.response.send_message("❗ Số đoán phải từ 1 đến 6.", ephemeral=True)

        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(
                f"⏳ Chờ {wait_time:.1f} giây nữa để chơi tiếp.", ephemeral=True)
        if is_banned(user_id):
            return await interaction.response.send_message("🚫 Tài khoản bị cấm.", ephemeral=True)
        if is_locked(user_id):
            return await interaction.response.send_message("🔒 Tài khoản bị khoá chơi game.", ephemeral=True)

        win_chance = self.get_win_chance(bet)
        result = random.randint(1, 6)
        stats = load_json(DICE_STATS_FILE)
        if user_id not in stats:
            stats[user_id] = {"win": 0, "loss": 0}

        if guess == result and random.random() < win_chance:
            reward = bet * 2
            update_balance(interaction.user.id, reward)
            stats[user_id]["win"] += 1
            add_win(user_id)
            message = f"🎲 Đổ ra **{result}**! THẮNG {reward:,} {CURRENCY_NAME}!"
        else:
            update_balance(interaction.user.id, -bet)
            stats[user_id]["loss"] += 1
            message = f"🎲 Đổ ra **{result}**! Thua. Mất {bet:,} {CURRENCY_NAME}."

        save_json(DICE_STATS_FILE, stats)
        await interaction.response.send_message(message)

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
        interaction = await self.bot.get_application_context(ctx.message)
        await self.roll_dice(interaction, guess, bet)

    @commands.command(name="dcall")
    async def dcall_prefix(self, ctx: commands.Context, guess: int):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.dice_all(interaction, guess)

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
