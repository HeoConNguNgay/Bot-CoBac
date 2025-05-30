import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import os
import json
import time
from database_utils import get_balance, update_balance, load_json, save_json
from config import CURRENCY_NAME

# --- Định nghĩa các tệp và thông số ---
STATS_FILE = "data/stats.json"
MAX_BET = 1_000_000
COOLDOWN_SECONDS = 10  # Thời gian chờ giữa các lần thực thi lệnh (10 giây)
cooldown_data = {}  # Dùng để lưu trữ thời gian cooldown của người dùng

# --- Hàm đọc và ghi dữ liệu ---
def load_json(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --- Kiểm tra cooldown ---
def check_cooldown(user_id):
    now = time.time()
    last_used = cooldown_data.get(user_id, 0)
    if now - last_used < COOLDOWN_SECONDS:
        remaining = COOLDOWN_SECONDS - (now - last_used)
        return remaining  # Nếu còn cooldown, trả về thời gian còn lại
    cooldown_data[user_id] = now  # Nếu không, cập nhật thời gian cooldown cho người dùng
    return 0  # Không còn cooldown, có thể thực hiện lệnh

# --- Lớp chính của bot ---
class Bot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="command1", description="Lệnh ví dụ 1")
    async def command1(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Kiểm tra cooldown
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi dùng lại lệnh này.", ephemeral=True)
        
        # Thực thi lệnh chính
        await interaction.response.send_message("Lệnh 1 đã được thực thi.")

    @app_commands.command(name="command2", description="Lệnh ví dụ 2")
    async def command2(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Kiểm tra cooldown
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await interaction.response.send_message(f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi dùng lại lệnh này.", ephemeral=True)
        
        # Thực thi lệnh chính
        await interaction.response.send_message("Lệnh 2 đã được thực thi.")

    @commands.command(name="prefix_command")
    async def prefix_command(self, ctx: commands.Context):
        user_id = str(ctx.author.id)

        # Kiểm tra cooldown
        wait_time = check_cooldown(user_id)
        if wait_time:
            return await ctx.send(f"⏳ Vui lòng chờ {wait_time:.1f} giây trước khi dùng lại lệnh này.")
        
        # Thực thi lệnh chính
        await ctx.send("Lệnh với prefix đã được thực thi.")

# --- Khởi tạo và đăng ký bot ---
async def setup(bot):
    await bot.add_cog(Bot(bot))

