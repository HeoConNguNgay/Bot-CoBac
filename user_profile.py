import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from database_utils import get_balance, get_streak, load_json, get_level, STATS_FILE
import os
import traceback
from config import CURRENCY_NAME

TEMPLATE_PATH = "nen_profile.png"
FONT_PATH = "DejaVuSans-Bold.ttf"

# --- HÀM TẠO HÌNH ẢNH HỒ SƠ ---
def generate_profile(user):
    uid = str(user.id)
    balance = get_balance(uid)
    stats = load_json(STATS_FILE).get(uid, {"win": 0, "loss": 0, "tie": 0})
    wins = stats.get("win", 0)
    losses = stats.get("loss", 0)
    draws = stats.get("tie", 0)
    total = wins + losses + draws
    winrate = f"{(wins / total * 100):.1f}%" if total else "0%"
    level = get_level(wins)

    try:
        img = Image.open(TEMPLATE_PATH).convert("RGBA")
    except FileNotFoundError:
        raise FileNotFoundError(f"Không tìm thấy template: {TEMPLATE_PATH}")

    draw = ImageDraw.Draw(img)
    try:
        font_user = ImageFont.truetype(FONT_PATH, 75)
        font_money = ImageFont.truetype(FONT_PATH, 72)
        font_stats = ImageFont.truetype(FONT_PATH, 60)
    except Exception as e:
        raise RuntimeError(f"Lỗi load font: {e}")

    # --- VẼ DỮ LIỆU LÊN ẢNH ---
    draw.text((203, 40), user.display_name, font=font_user, fill="white")
    draw.text((525, 1050), f"{balance:,} {CURRENCY_NAME}", font=font_money, fill="white")
    draw.text((156, 1342), str(wins), font=font_stats, fill="white")
    draw.text((483, 1342), str(losses), font=font_stats, fill="white")
    draw.text((813, 1342), str(draws), font=font_stats, fill="white")
    draw.text((156, 1448), str(level), font=font_stats, fill="white")
    draw.text((813, 1448), winrate, font=font_stats, fill="white")

    # --- AVATAR ---
    try:
        response = requests.get(user.display_avatar.url, timeout=5)
        avatar_data = BytesIO(response.content)
        avatar = Image.open(avatar_data).convert("RGBA").resize((383, 384))
        img.paste(avatar, (47, 912), avatar)
    except Exception as e:
        print(f"⚠️ Không thể tải avatar: {e}")

    output_path = f"profile_{uid}.png"
    img.save(output_path)
    return output_path

# --- COG CHÍNH ---
class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash command
    @app_commands.command(name="hoso", description="📋 Xem hồ sơ cá nhân bằng hình ảnh")
    async def hoso(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            path = generate_profile(interaction.user)
            file = discord.File(path, filename="profile.png")
            embed = discord.Embed(
                title=f"📋 Hồ sơ của {interaction.user.display_name}",
                description=f"💰 Số dư hiện tại: {get_balance(interaction.user.id):,} {CURRENCY_NAME}",
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://profile.png")
            await interaction.followup.send(file=file, embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi tạo hồ sơ: {e}", ephemeral=True)

    # Prefix command
    @commands.command(name="hoso")
    async def hoso_prefix(self, ctx: commands.Context):
        await ctx.typing()
        try:
            path = generate_profile(ctx.author)
            file = discord.File(path, filename="profile.png")
            embed = discord.Embed(
                title=f"📋 Hồ sơ của {ctx.author.display_name}",
                description=f"💰 Số dư hiện tại: {get_balance(ctx.author.id):,} {CURRENCY_NAME}",
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://profile.png")
            await ctx.send(file=file, embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Lỗi tạo hồ sơ: {e}")

# --- ĐĂNG KÝ COG ---
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
