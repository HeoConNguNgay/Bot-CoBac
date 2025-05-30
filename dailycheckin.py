# ✅ File dailycheckin.py đã được rà soát và tối ưu hoàn chỉnh
# ✅ Giữ nguyên cả slash command /diemdanh và prefix !diemdanh
# ✅ Đồng bộ phần tính chuỗi ngày liên tiếp và phần thưởng
# ✅ Ghi chú chi tiết từng bước để dễ chỉnh sửa về sau

import discord
from discord.ext import commands
from discord import app_commands
import datetime, os
from database_utils import update_balance, load_json, save_json
from config import CURRENCY_NAME

# === CẤU HÌNH ===
DAILY_FILE = "data/daily.json"
VIETNAM_TZ = datetime.timezone(datetime.timedelta(hours=7))  # múi giờ Việt Nam

class DailyCheckin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- SLASH COMMAND ---
    @app_commands.command(name="diemdanh", description="📅 Điểm danh hàng ngày để nhận phần thưởng")
    async def diemdanh(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now(tz=VIETNAM_TZ)
        today = now.date().isoformat()

        # Load dữ liệu điểm danh
        data = load_json(DAILY_FILE)
        user_data = data.get(user_id, {"last": "", "streak": 0})
        last_day = user_data["last"]
        streak = user_data["streak"]

        # Kiểm tra đã điểm danh hôm nay chưa
        if last_day == today:
            return await interaction.response.send_message("📆 Bạn đã điểm danh hôm nay rồi!", ephemeral=True)

        # Tăng chuỗi nếu hôm qua cũng điểm danh
        yesterday = (now - datetime.timedelta(days=1)).date().isoformat()
        if last_day == yesterday:
            streak += 1
        else:
            streak = 1

        # Tính phần thưởng
        reward = 25000
        if streak > 1:
            reward += 10000

        # Cập nhật dữ liệu
        update_balance(interaction.user.id, reward)
        data[user_id] = {"last": today, "streak": streak}
        save_json(DAILY_FILE, data)

        await interaction.response.send_message(
            f"📅 Bạn đã điểm danh thành công!\n🔥 Chuỗi ngày liên tiếp: {streak}\n💰 Nhận: {reward:,} {CURRENCY_NAME}",
            ephemeral=False
        )

    # --- PREFIX COMMAND ---
    @commands.command(name="diemdanh")
    async def diemdanh_prefix(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        now = datetime.datetime.now(tz=VIETNAM_TZ)
        today = now.date().isoformat()

        data = load_json(DAILY_FILE)
        user_data = data.get(user_id, {"last": "", "streak": 0})
        last_day = user_data["last"]
        streak = user_data["streak"]

        if last_day == today:
            return await ctx.send("📆 Bạn đã điểm danh hôm nay rồi!")

        yesterday = (now - datetime.timedelta(days=1)).date().isoformat()
        if last_day == yesterday:
            streak += 1
        else:
            streak = 1

        reward = 25000
        if streak > 1:
            reward += 10000

        update_balance(ctx.author.id, reward)
        data[user_id] = {"last": today, "streak": streak}
        save_json(DAILY_FILE, data)

        await ctx.send(
            f"📅 Bạn đã điểm danh thành công!\n🔥 Chuỗi ngày liên tiếp: {streak}\n💰 Nhận: {reward:,} {CURRENCY_NAME}"
        )

# --- ĐĂNG KÝ COG ---
async def setup(bot):
    await bot.add_cog(DailyCheckin(bot))
