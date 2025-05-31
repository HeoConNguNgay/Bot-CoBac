# ✅ Blackjack.py - Đã bổ sung đầy đủ lệnh prefix và hệ thống hiển thị cooldown rõ ràng
# ✅ Có thông báo kiểu "❗ Slow down! Bạn còn phải chờ **X giây**..."
# ✅ Giữ nguyên toàn bộ logic, không bớt xén nội dung gốc, có chú thích rõ ràng từng phần

import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import time
import asyncio
from database_utils import get_balance, update_balance, load_json, save_json, update_stats, get_streak, update_streak
from config import CURRENCY_NAME
from cooldown import check_cooldown

# ==== CẤU HÌNH ====
SUITS = ['♥', '♦', '♣', '♠']
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
BJ_STATS_FILE = "data/blackjack.json"
MAX_BET = 1_000_000
COOLDOWN_SECONDS = 10
MY_USER_ID = 426804092778840095  # ⚠️ Thay bằng ID thật của bạn

# ==== TIỆN ÍCH TÍNH BÀI ====
def draw_card():
    return random.choice(RANKS), random.choice(SUITS)

def calculate_score(cards):
    score = 0
    aces = 0
    for rank, _ in cards:
        if rank in ["J", "Q", "K"]:
            score += 10
        elif rank == "A":
            score += 11
            aces += 1
        else:
            score += int(rank)
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def format_cards(cards):
    return ' '.join([f"`{r}{s}`" for r, s in cards])

def create_blackjack_embed(player_cards, dealer_cards, result="", hidden=False):
    embed = discord.Embed(title="🎴 Blackjack", color=discord.Color.blue())
    embed.add_field(name="Bạn", value=f"{format_cards(player_cards)} [{calculate_score(player_cards)}]", inline=False)
    if hidden:
        embed.add_field(name="Nhà cái", value=f"`{dealer_cards[0][0]}{dealer_cards[0][1]}` ??", inline=False)
    else:
        embed.add_field(name="Nhà cái", value=f"{format_cards(dealer_cards)} [{calculate_score(dealer_cards)}]", inline=False)
    if result:
        embed.set_footer(text=result)
    return embed

# ==== DỮ LIỆU NGƯỜI CHƠI ====
def load_bj_stats():
    return load_json(BJ_STATS_FILE) if os.path.exists(BJ_STATS_FILE) else {}

def save_bj_stats(stats):
    save_json(BJ_STATS_FILE, stats)

def is_banned(uid):
    return load_json("data/banned.json").get(str(uid), False)

def is_locked(uid):
    return load_json("data/locked.json").get(str(uid), False)

# ==== GIAO DIỆN TƯƠNG TÁC ====
class BlackjackView(discord.ui.View):
    def __init__(self, interaction, bet, player_cards, dealer_cards):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.bet = bet
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards

    @discord.ui.button(label="Rút bài", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("❗ Bạn không phải người chơi ván này.", ephemeral=True)

        self.player_cards.append(draw_card())
        score = calculate_score(self.player_cards)

        if score > 21:
            update_balance(interaction.user.id, -self.bet)
            embed = create_blackjack_embed(self.player_cards, self.dealer_cards, f"💥 Quá 21 điểm! Bạn thua {self.bet:,} {CURRENCY_NAME}.")
            self.disable_all_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed = create_blackjack_embed(self.player_cards, self.dealer_cards, "Bạn muốn tiếp tục hay dừng lại?", hidden=True)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Dừng lại", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("❗ Bạn không phải người chơi ván này.", ephemeral=True)

        bet = self.bet
        if bet <= 50000:
            win_chance = 1 / 2
        elif bet <= 150000:
            win_chance = 1 / 3.5
        elif bet <= 300000:
            win_chance = 1 / 5
        else:
            win_chance = 1 / 7

        player_score = calculate_score(self.player_cards)
        dealer_score = calculate_score(self.dealer_cards)
        while dealer_score < 17:
            self.dealer_cards.append(draw_card())
            dealer_score = calculate_score(self.dealer_cards)

        if random.random() < win_chance:
            update_balance(interaction.user.id, bet)
            result = f"🏆 Bạn thắng và nhận {bet:,} {CURRENCY_NAME}!"
            outcome = "win"
        elif player_score == dealer_score:
            result = "🤝 Hòa! Bạn không mất tiền."
            outcome = "draw"
        else:
            update_balance(interaction.user.id, -bet)
            result = f"💸 Bạn thua {bet:,} {CURRENCY_NAME}."
            outcome = "loss"

        stats = load_bj_stats()
        uid = str(interaction.user.id)
        if uid not in stats:
            stats[uid] = {"win": 0, "loss": 0, "draw": 0}
        stats[uid][outcome] += 1
        save_bj_stats(stats)

        embed = create_blackjack_embed(self.player_cards, self.dealer_cards, result)
        self.disable_all_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True

# ==== COG CHÍNH ====
class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bj", description="🎴 Chơi Blackjack và cược tiền")
    @app_commands.describe(bet="Số {CURRENCY_NAME} bạn muốn cược")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        await self._start_game(interaction, interaction.user, bet)

    @app_commands.command(name="bjall", description="🎴 Chơi Blackjack all-in toàn bộ số dư")
    async def blackjack_all(self, interaction: discord.Interaction):
        balance = get_balance(interaction.user.id)
        if balance < 1:
            return await interaction.response.send_message("❗ Bạn không có đủ tiền để chơi.", ephemeral=True)
        await self._start_game(interaction, interaction.user, min(balance, MAX_BET))

    @app_commands.command(name="bjstats", description="📊 Xem thống kê thắng/thua/hòa Blackjack")
    async def bj_stats(self, interaction: discord.Interaction):
        await self._send_stats(interaction, interaction.user)

    @app_commands.command(name="bjleaderboard", description="🏆 Bảng xếp hạng người chơi Blackjack")
    async def bj_leaderboard(self, interaction: discord.Interaction):
        stats = load_bj_stats()
        top = sorted(stats.items(), key=lambda x: x[1].get("win", 0), reverse=True)[:10]

        embed = discord.Embed(title="🏆 BXH Blackjack", color=discord.Color.gold())
        for idx, (uid, data) in enumerate(top, 1):
            user = await self.bot.fetch_user(int(uid))
            wins = data.get("win", 0)
            losses = data.get("loss", 0)
            draws = data.get("draw", 0)
            total = wins + losses + draws
            winrate = f"{(wins / total * 100):.2f}%" if total else "N/A"
            embed.add_field(
                name=f"#{idx} – {user.display_name}",
                value=f"✅ {wins} | ❌ {losses} | 🤝 {draws} | 📈 {winrate}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    async def _start_game(self, ctx_or_interaction, user, bet):
        user_id = user.id
        wait_time = check_cooldown(user_id)
        if wait_time:
            seconds = int(wait_time) + 1
            message = f"❗ Slow down! Bạn còn phải chờ **{seconds} giây** trước khi dùng lại."
            if isinstance(ctx_or_interaction, commands.Context):
                return await ctx_or_interaction.send(message)
            else:
                return await ctx_or_interaction.response.send_message(message, ephemeral=True)

        balance = get_balance(user_id)
        if bet <= 0 or bet > MAX_BET or bet > balance:
            return

        if isinstance(ctx_or_interaction, commands.Context):
            msg = await ctx_or_interaction.send("🃏 Đang chia bài...")
        else:
            await ctx_or_interaction.response.send_message("🃏 Đang chia bài...", ephemeral=False)
            msg = await ctx_or_interaction.original_response()

        await asyncio.sleep(1)
        player_cards = [draw_card(), draw_card()]
        dealer_cards = [draw_card()]
        embed = create_blackjack_embed(player_cards, dealer_cards, "Bạn muốn rút bài hay dừng lại?", hidden=True)
        view = BlackjackView(ctx_or_interaction if isinstance(ctx_or_interaction, discord.Interaction) else msg, bet, player_cards, dealer_cards)
        await msg.edit(content=None, embed=embed, view=view)

    async def _send_stats(self, interaction, user):
        stats = load_bj_stats()
        uid = str(user.id)
        s = stats.get(uid, {"win": 0, "loss": 0, "draw": 0})
        total = s["win"] + s["loss"] + s["draw"]
        winrate = f"{(s['win'] / total * 100):.2f}%" if total else "N/A"

        embed = discord.Embed(title="📊 Thống kê Blackjack", color=discord.Color.blue())
        embed.add_field(name="✅ Thắng", value=s["win"], inline=True)
        embed.add_field(name="❌ Thua", value=s["loss"], inline=True)
        embed.add_field(name="🤝 Hòa", value=s["draw"], inline=True)
        embed.add_field(name="📈 Tỷ lệ thắng", value=winrate, inline=True)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="bj")
    async def bj_prefix(self, ctx: commands.Context, bet: int):
        await self._start_game(ctx, ctx.author, bet)

    @commands.command(name="bjall")
    async def bjall_prefix(self, ctx: commands.Context):
        balance = get_balance(ctx.author.id)
        if balance <= 0:
            return await ctx.send("❗ Bạn không có đủ tiền để chơi.")
        await self._start_game(ctx, ctx.author, min(balance, MAX_BET))

    @commands.command(name="bjstats")
    async def bjstats_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self._send_stats(interaction, ctx.author)

    @commands.command(name="bjleaderboard")
    async def bjleaderboard_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.bj_leaderboard(interaction)

# ✅ Đăng ký cog
async def setup(bot):
    await bot.add_cog(Blackjack(bot))
