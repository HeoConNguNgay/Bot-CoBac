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

STATS_FILE = "data/slots.json"
MAX_BET = 1_000_000
MY_USER_ID = 426804092778840095

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "🍀", "7️⃣"]

    async def _respond(self, ctx_or_interaction, message, ephemeral=False, is_prefix=False):
        if is_prefix:
            await ctx_or_interaction.send(message)
        else:
            await ctx_or_interaction.response.send_message(message, ephemeral=ephemeral)

    def get_win_chance(self, bet):
        if bet <= 50000:
            return 1 / 2
        elif bet <= 150000:
            return 1 / 4
        elif bet <= 300000:
            return 1 / 6
        else:
            return 1 / 10

    async def play_slots(self, ctx_or_interaction, user, bet, is_allin=False, is_prefix=False):
        user_id = str(user.id)
        wait_time = check_cooldown(user_id)
        if wait_time:
            seconds = int(wait_time) + 1
            return await self._respond(ctx_or_interaction, f"❗ Slow down! Bạn còn phải chờ **{seconds} giây** trước khi dùng lại.", ephemeral=True, is_prefix=is_prefix)
        if load_json("data/banned.json").get(user_id, False):
            return await self._respond(ctx_or_interaction, "🚫 Bị cấm.", ephemeral=True, is_prefix=is_prefix)
        if load_json("data/locked.json").get(user_id, False):
            return await self._respond(ctx_or_interaction, "🔒 Bị khoá game.", ephemeral=True, is_prefix=is_prefix)

        balance = get_balance(user.id)
        if bet <= 0:
            return await self._respond(ctx_or_interaction, "❗ Cược phải > 0", ephemeral=True, is_prefix=is_prefix)
        if bet > MAX_BET:
            return await self._respond(ctx_or_interaction, f"❗ Tối đa {MAX_BET:,}", ephemeral=True, is_prefix=is_prefix)
        if bet > balance:
            return await self._respond(ctx_or_interaction, f"❗ Không đủ tiền ({balance:,} {CURRENCY_NAME})", ephemeral=True, is_prefix=is_prefix)

        if is_prefix:
            msg = await ctx_or_interaction.send(f"**{user.display_name}** đang quay...\n🔄 Chuẩn bị...")
        else:
            await ctx_or_interaction.response.send_message(f"**{user.display_name}** đang quay...\n🔄 Chuẩn bị...")
            msg = await ctx_or_interaction.original_response()

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

        win_chance = self.get_win_chance(bet)
        stats = load_json(STATS_FILE)
        user_stats = stats.get(user_id, {"plays": 0, "wins": 0})

        won = random.random() < win_chance
        if won:
            result = ["💎"] * 3
            reward = bet * 5
            update_balance(user.id, reward)
            user_stats["wins"] += 1
            add_win(user_id)
        else:
            result = [random.choice(self.SYMBOLS) for _ in range(3)]
            update_balance(user.id, -bet)

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
🎉 {user.display_name} {'all-in' if is_allin else 'bet'} 💸 {bet:,} và thắng {reward:,} {CURRENCY_NAME}!
"""
        else:
            message = f"""
╭━━━ SLOTS {'(ALL-IN)' if is_allin else ''} ━━━╮
   {symbols}
╰━━━━━━━━━━━━━╯
 |___|___|___|
 |___|___|___|
💸 {user.display_name} {'all-in' if is_allin else 'bet'} 💸 {bet:,} và thua... :c
"""
        await msg.edit(content=message)

    # === Slash Commands ===
    @app_commands.command(name="sl", description="🎰 Quay máy đánh bạc để thử vận may!")
    @app_commands.describe(bet="Số tiền cược")
    async def slots(self, interaction: discord.Interaction, bet: int):
        await self.play_slots(interaction, interaction.user, bet)

    @app_commands.command(name="slall", description="🎰 Quay máy slots với toàn bộ số dư bạn đang có")
    async def slots_all(self, interaction: discord.Interaction):
        balance = get_balance(interaction.user.id)
        if balance <= 0:
            return await interaction.response.send_message("❗ Bạn không có tiền để chơi!", ephemeral=True)
        await self.play_slots(interaction, interaction.user, balance, is_allin=True)

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

    # === Prefix Commands ===
    @commands.command(name="sl")
    async def slotgame_prefix(self, ctx: commands.Context, bet: int):
        await self.play_slots(ctx, ctx.author, bet, is_prefix=True)

    @commands.command(name="slall")
    async def slotall_prefix(self, ctx: commands.Context):
        balance = get_balance(ctx.author.id)
        if balance <= 0:
            return await ctx.send("❗ Bạn không có tiền để chơi!")
        await self.play_slots(ctx, ctx.author, balance, is_allin=True, is_prefix=True)

    @commands.command(name="slreset")
    @commands.has_permissions(administrator=True)
    async def slotreset_prefix(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id != MY_USER_ID:
            return await ctx.send("🚫 Bạn không có quyền dùng lệnh này.")
        interaction = await self.bot.get_application_context(ctx.message)
        await self.slots_reset(interaction, user)

async def setup(bot):
    await bot.add_cog(Slots(bot))
