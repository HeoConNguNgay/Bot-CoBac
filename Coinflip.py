# ✅ Coinflip.py - Đã bổ sung defer() và hiển thị cooldown rõ ràng
# ✅ Không thay đổi logic hay rút gọn dòng nào, giữ nguyên nội dung gốc

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
MY_USER_ID = 426804092778840095

# ==== TIỆN ÍCH KIỂM TRA TRẠNG THÁI NGƯỜI CHƠI ====
def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

# ==== LỚP CHÍNH: COINFLIP GAME ====
class Coinflip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _respond(self, ctx_or_interaction, message, ephemeral=False, is_prefix=False):
        if is_prefix:
            await ctx_or_interaction.send(message)
        else:
            await ctx_or_interaction.response.send_message(message, ephemeral=ephemeral)

    async def run_coinflip(self, ctx_or_interaction, user, bet, side, is_prefix=False):
        user_id = user.id
        wait_time = check_cooldown(user_id)
        if wait_time:
            seconds = int(wait_time) + 1
            return await self._respond(ctx_or_interaction, f"❗ Slow down! Bạn còn phải chờ **{seconds} giây** trước khi dùng lại.", ephemeral=True, is_prefix=is_prefix)
        if is_banned(user_id) or is_locked(user_id):
            return await self._respond(ctx_or_interaction, "🚫 Tài khoản của bạn bị hạn chế.", ephemeral=True, is_prefix=is_prefix)

        balance = get_balance(user_id)
        if bet < 1:
            return await self._respond(ctx_or_interaction, "❗ Cược phải lớn hơn 0.", ephemeral=True, is_prefix=is_prefix)
        if bet > 1_000_000:
            return await self._respond(ctx_or_interaction, "❗ Cược tối đa là 1,000,000.", ephemeral=True, is_prefix=is_prefix)
        if bet > balance:
            return await self._respond(ctx_or_interaction, f"❗ Không đủ tiền! Hiện có {balance:,} {CURRENCY_NAME}.", ephemeral=True, is_prefix=is_prefix)

        await self.resolve_flip(ctx_or_interaction, user, bet, side, is_prefix)

    async def resolve_flip(self, ctx_or_interaction, user, bet, chosen, is_prefix):
        mention = user.mention
        if is_prefix:
            msg = await ctx_or_interaction.send(f"{mention} đã cược 🧨 {bet:,} và chọn **{chosen.upper()}**...")
        else:
            await ctx_or_interaction.response.send_message(f"{mention} đã cược 🧨 {bet:,} và chọn **{chosen.upper()}**...")
            msg = await ctx_or_interaction.original_response()

        for countdown in ["🔀 Tung đồng xu...", "⏳ 3...", "⏳ 2...", "⏳ 1..."]:
            await msg.edit(content=countdown)
            await asyncio.sleep(1)

        flipped = random.choice(["heads", "tails"])
        is_win = (chosen == flipped)

        if is_win:
            reward = bet * 2
            update_balance(user.id, reward)
            update_stats(user.id, "win")
            streak = get_streak(user.id) + 1
            update_streak(user.id, True)
            result_text = f"🎉 Đồng xu ra **{flipped.upper()}**! Bạn thắng 🧨 {reward:,}! 🔥 Chuỗi thắng: {streak}"
        else:
            update_balance(user.id, -bet)
            update_stats(user.id, "loss")
            update_streak(user.id, False)
            result_text = f"💔 Đồng xu ra **{flipped.upper()}**! Bạn thua 🧨 {bet:,}...\n🧨 Chuỗi thắng bị reset"

        embed = discord.Embed(title="🪙 Kết quả Coinflip", color=discord.Color.blue())
        embed.set_image(url=HEADS_IMG if flipped == "heads" else TAILS_IMG)
        embed.add_field(name="👤 Người chơi", value=mention, inline=True)
        embed.add_field(name="🎯 Mặt đã chọn", value=chosen.upper(), inline=True)
        embed.add_field(name="💼 Kết quả tung", value=flipped.upper(), inline=True)
        embed.add_field(name="💬 Kết luận", value=result_text, inline=False)

        await msg.edit(content=None, embed=embed)

    # === Slash Commands ===
    @app_commands.command(name="cf", description="Chơi tung đồng xu cược tiền")
    @app_commands.describe(bet="Số tiền cược", side="Chọn mặt heads hoặc tails")
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, side: app_commands.Choice[str]):
        await interaction.response.defer()
        await self.run_coinflip(interaction, interaction.user, bet, side.value)

    @app_commands.command(name="cfall", description="Cược toàn bộ số dư")
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip_all(self, interaction: discord.Interaction, side: app_commands.Choice[str]):
        await interaction.response.defer()
        balance = get_balance(interaction.user.id)
        if balance < 1:
            return await interaction.followup.send("❗ Bạn không có tiền để cược.", ephemeral=True)
        await self.run_coinflip(interaction, interaction.user, balance, side.value)

    @app_commands.command(name="cfstats", description="Xem thống kê coinflip")
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
        embed.add_field(name="🔥 Chuỗi thắng", value=str(streak), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cfleaderboard", description="Xem top coinflip")
    async def cf_leaderboard(self, interaction: discord.Interaction):
        stats_data = load_json(STATS_FILE)
        top = sorted(stats_data.items(), key=lambda item: item[1].get("win", 0), reverse=True)[:10]

        embed = discord.Embed(title="🏆 BXH Coinflip", color=discord.Color.purple())
        for idx, (uid, data) in enumerate(top, 1):
            user = await self.bot.fetch_user(int(uid))
            streak = get_streak(int(uid))
            embed.add_field(
                name=f"#{idx} - {user.name}",
                value=f"🎯 Thắng: {data.get('win', 0)} | 🔥 Streak: {streak}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cfreset", description="Reset dữ liệu coinflip (Admin)")
    @app_commands.describe(user="Người cần reset")
    async def cf_reset(self, interaction: discord.Interaction, user: discord.User):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❗ Không có quyền.", ephemeral=True)

        user_id = str(user.id)
        stats = load_json(STATS_FILE)
        if user_id in stats:
            stats[user_id] = {"win": 0, "loss": 0}
            save_json(STATS_FILE, stats)
            update_streak(int(user_id), False)
            await interaction.response.send_message(f"✅ Đã reset coinflip cho {user.mention}.")
        else:
            await interaction.response.send_message("❗ Người này chưa có dữ liệu.", ephemeral=True)

    # === PREFIX Commands ===
    @commands.command(name="cf")
    async def cf_prefix(self, ctx: commands.Context, bet: int, side: str):
        if side.lower() not in ["heads", "tails"]:
            return await ctx.send("❗ Chỉ chấp nhận heads hoặc tails.")
        await self.run_coinflip(ctx, ctx.author, bet, side.lower(), is_prefix=True)

    @commands.command(name="cfall")
    async def cfall_prefix(self, ctx: commands.Context, side: str):
        if side.lower() not in ["heads", "tails"]:
            return await ctx.send("❗ Chỉ chấp nhận heads hoặc tails.")
        balance = get_balance(ctx.author.id)
        if balance < 1:
            return await ctx.send("❗ Bạn không có tiền để cược.")
        await self.run_coinflip(ctx, ctx.author, balance, side.lower(), is_prefix=True)

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

async def setup(bot):
    await bot.add_cog(Coinflip(bot))
