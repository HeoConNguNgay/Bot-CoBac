import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv

# --- CẤU HÌNH INTENTS & KHỞI TẠO BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- LỆNH ADMIN: Reload tất cả extension đang chạy ---
@bot.command()
@commands.has_permissions(administrator=True)
async def reloadall(ctx):
    errors = []
    for ext in bot.extensions.copy():
        try:
            await bot.reload_extension(ext)
        except Exception as e:
            errors.append(f"{ext}: {e}")
    if errors:
        await ctx.send("❌ Một số extension bị lỗi:\n" + "\n".join(errors))
    else:
        await ctx.send("♻️ Đã reload tất cả extension.")

# --- SỰ KIỆN BOT SẴN SÀNG ---
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập với tên {bot.user}")

    # 📦 Danh sách tất cả extension cần load (đã đầy đủ)
    extensions = [
        "commands",        # Lệnh thường
        "Lottery",         # Quay số
        "help_menu",       # Menu trợ giúp
        "user_profile",    # Hồ sơ người dùng
        "admin",           # Lệnh quản trị
        "dailycheckin",    # Điểm danh hàng ngày
        "Coinflip",        # Trò tung đồng xu
        "Slots",           # Trò chơi máy xèng
        "Cups",            # Trò chơi ba cái cốc
        "Dice",            # Trò xúc xắc
        "Blackjack"        # Trò blackjack
    ]

    # 🔁 Load từng extension (plugin)
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"🔹 Đã tải {ext}.py")
        except Exception as e:
            print(f"⚠️ Lỗi khi tải {ext}: {e.__class__.__name__}: {e}")

    # 🔄 Đồng bộ slash command
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Đã đồng bộ {len(synced)} slash command vào tất cả server")
        commands_list = await bot.tree.fetch_commands()
        print("📋 Slash commands đã đăng ký:", [cmd.name for cmd in commands_list])
    except Exception as e:
        print(f"❌ Lỗi khi đồng bộ slash command: {e}")

# --- LỆNH TEST KẾT NỐI ---
@bot.command()
async def ping(ctx):
    await ctx.send("✅ Bot đã nhận lệnh prefix thành công!")

# --- CHẠY BOT ---
async def main():
    TOKEN = os.getenv("TOKEN")

    if not TOKEN:
        print("❌ Không tìm thấy biến môi trường TOKEN")
        return


    try:
        await bot.start(TOKEN)
    finally:
        await bot.close()

# 🔧 Chạy nếu là script chính
if __name__ == "__main__":
    asyncio.run(main())
