# ✅ Slots.py - Bản đầy đủ giữ nguyên mọi dòng của bạn
# ✅ Tích hợp kiểm tra ID admin cho lệnh /slreset và !slreset
# ✅ Giữ nguyên toàn bộ dòng chú thích, logic, bố cục gốc của bạn
# ✅ Có hiệu ứng đếm ngược + xoay biểu tượng khi quay slot

import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import json
import time
import asyncio
from database_utils import add_win, get_balance, update_balance, load_json, save_json
from config import CURRENCY_NAME
from cooldown import check_cooldown

# ==== CẤU HÌNH ====
STATS_FILE = "data/slots.json"
MAX_BET = 1_000_000
MY_USER_ID = 426804092778840095  # ⚠️ Thay bằng ID thật của bạn

# ==== HÀM TIỆN ÍCH ====
def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

# ==== LỚP TRÒ CHƠI SLOTS ====
class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "🍀", "7️⃣"]

    # === HÀM QUAY SLOTS CÓ ĐẾM NGƯỢC & XOAY BIỂU TƯỢNG ===
    async def countdown_result(self, interaction, bet, is_allin=False):
        user_id = str(interaction.user.id)
        await interaction.response.send_message(f"**{interaction.user.display_name}** đang quay...\n🔄 Chuẩn bị...")
        msg = await interaction.original_response()

        for i in [3, 2, 1]:
            spinning = " | ".join(random.choices(self.SYMBOLS, k=3))
            display = f"""
╭━━━ SLOTS ━━━╮
   {spinning}
╰━━━━━━━━━━━━━╯
 |___|___|___|
 |___|___|___|
⏳ {i}..."""
            await msg.edit(content=display)
            await asyncio.sleep(1)

        # Tính tỷ lệ thắng theo mức cược
        if bet <= 50000:
            win_chance = 1 / 2
        elif bet <= 150000:
            win_chance = 1 / 4
        elif bet <= 300000:
            win_chance = 1 / 6
        else:
            win_chance = 1 / 10

        # Ghi nhận thống kê cá nhân
        stats = load_json(STATS_FILE)
        user_stats = stats.get(user_id, {"plays": 0, "wins": 0})

        won = random.random() < win_chance
        if won:
            result = ["💎"] * 3
            reward = bet * 5
            update_balance(interaction.user.id, reward)
            user_stats["wins"] += 1
            add_win(user_id)
        else:
            result = [random.choice(self.SYMBOLS) for _ in range(3)]
            update_balance(interaction.user.id, -bet)

        user_stats["plays"] += 1
        stats[user_id] = user_stats
        save_json(STATS_FILE, stats)

        symbols = " | ".join(result)
        if won:
            message = f"""
╭━━━ SLOTS {'(ALL-IN)' if is_allin else ''} ━━━╮
   {symbols}
╰━━━━━━━━━━━━━╯
 |___|___|___|
 |___|___|___|
🎉 {interaction.user.display_name} {'all-in' if is_allin else 'bet'} 💸 {bet:,} and won {reward:,} {CURRENCY_NAME}!
"""
        else:
            message = f"""
╭━━━ SLOTS {'(ALL-IN)' if is_allin else ''} ━━━╮
   {symbols}
╰━━━━━━━━━━━━━╯
 |___|___|___|
 |___|___|___|
💸 {interaction.user.display_name} {'all-in' if is_allin else 'bet'} 💸 {bet:,} and lost... :c
"""

        await msg.edit(content=message)

    # === Slash: /sl cược số tiền cố định ===
    @app_commands.command(name="sl", description="🎰 Quay máy đánh bạc để thử vận may!")
    @app_commands.describe(bet="Số tiền cược")
    async def slots(self, interaction: discord.Interaction, bet: int):
        user_id = str(interaction.user.id)
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(
                f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi dùng lại lệnh này.", ephemeral=True
            )

        if is_banned(user_id):
            return await interaction.response.send_message("🚫 Bạn đã bị cấm sử dụng bot.", ephemeral=True)
        if is_locked(user_id):
            return await interaction.response.send_message("🔒 Tài khoản của bạn đã bị khóa chức năng chơi game.", ephemeral=True)

        balance = get_balance(interaction.user.id)
        if bet <= 0:
            return await interaction.response.send_message("❗ Cược phải lớn hơn 0!", ephemeral=True)
        if bet > MAX_BET:
            return await interaction.response.send_message("❗ Mỗi lần chỉ được cược tối đa 1,000,000 {CURRENCY_NAME}.", ephemeral=True)
        if bet > balance:
            return await interaction.response.send_message(f"❗ Không đủ tiền! Số dư hiện tại: {balance:,} {CURRENCY_NAME}", ephemeral=True)

        await self.countdown_result(interaction, bet)

    # === Slash: /slall cược toàn bộ số dư ===
    @app_commands.command(name="slall", description="🎰 Quay máy slots với toàn bộ số dư bạn đang có")
    async def slots_all(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Chờ {wait_time:.1f}s trước khi chơi lại", ephemeral=True)

        if is_banned(user_id):
            return await interaction.response.send_message("🚫 Bạn đã bị cấm chơi", ephemeral=True)
        if is_locked(user_id):
            return await interaction.response.send_message("🔒 Tài khoản bị khoá game", ephemeral=True)

        balance = get_balance(interaction.user.id)
        if balance <= 0:
            return await interaction.response.send_message("❗ Bạn không có tiền để chơi!", ephemeral=True)

        await self.countdown_result(interaction, balance, is_allin=True)

    # === Slash: /slreset admin xoá thống kê người chơi ===
    @app_commands.command(name="slreset", description="🛠️ (Admin) Xoá thống kê slot của người chơi")
    @app_commands.describe(user="Người chơi cần xoá dữ liệu slot")
    @app_commands.checks.has_permissions(administrator=True)
    async def slots_reset(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id != MY_USER_ID:
            return await interaction.response.send_message("🚫 Bạn không có quyền dùng lệnh này.", ephemeral=True)

        user_id = str(user.id)
        stats = load_json(STATS_FILE)
        if user_id in stats:
            del stats[user_id]
            save_json(STATS_FILE, stats)
            await interaction.response.send_message(f"✅ Đã xoá thống kê slot của {user.mention}.")
        else:
            await interaction.response.send_message("❗ Người dùng này chưa có thống kê để xoá.", ephemeral=True)

    # === PREFIX: !sl cược ===
    @commands.command(name="sl")
    async def slotgame_prefix(self, ctx: commands.Context, bet: int):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.slots(interaction, bet)

    # === PREFIX: !slall all-in ===
    @commands.command(name="slall")
    async def slotall_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.slots_all(interaction)

    # === PREFIX: !slreset admin xoá dữ liệu ===
    @commands.command(name="slreset")
    @commands.has_permissions(administrator=True)
    async def slotreset_prefix(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id != MY_USER_ID:
            return await ctx.send("🚫 Bạn không có quyền dùng lệnh này.")
        interaction = await self.bot.get_application_context(ctx.message)
        await self.slots_reset(interaction, user)

# === ĐĂNG KÝ COG ===
async def setup(bot):
    await bot.add_cog(Slots(bot))
