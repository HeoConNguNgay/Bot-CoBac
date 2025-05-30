import discord
from discord.ext import commands, tasks
from discord import app_commands
import random, datetime, asyncio
from database_utils import get_balance, update_balance, load_json, save_json
from config import CURRENCY_NAME

# --- Cấu hình ---
LOTTERY_FILE = "data/lottery.json"
MAX_DAILY_ENTRY = 1_000_000
VIETNAM_TZ = datetime.timezone(datetime.timedelta(hours=7))
MY_USER_ID = 426804092778840095  # ⚠️ Thay bằng ID của bạn

class Lottery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lottery_reset_loop.start()

    # --- Hàm tiện ích ---
    def get_today_key(self):
        now = datetime.datetime.now(tz=VIETNAM_TZ)
        return now.strftime("%Y-%m-%d")

    def load_data(self):
        return load_json(LOTTERY_FILE)

    def save_data(self, data):
        save_json(LOTTERY_FILE, data)

    def is_banned(self, uid):
        return load_json("data/banned.json").get(str(uid), False)

    def is_locked(self, uid):
        return load_json("data/locked.json").get(str(uid), False)

    # --- Slash command: /lottery ---
    @app_commands.command(name="lottery", description="🎟️ Tham gia xổ số hôm nay với một số tiền nhất định")
    @app_commands.describe(amount="Số tiền cược (tối đa 1.000.000 mỗi ngày)")
    async def lottery(self, interaction: discord.Interaction, amount: int):
        user_id = str(interaction.user.id)
        if self.is_banned(user_id):
            return await interaction.response.send_message("🚫 Bạn đã bị cấm sử dụng bot.", ephemeral=True)
        if self.is_locked(user_id):
            return await interaction.response.send_message("🔐 Tài khoản của bạn đã bị khóa chức năng chơi game.", ephemeral=True)

        balance = get_balance(user_id)
        if amount < 1:
            return await interaction.response.send_message("❗ Số tiền phải lớn hơn 0.", ephemeral=True)
        if amount > MAX_DAILY_ENTRY:
            return await interaction.response.send_message(f"❗ Giới hạn cược mỗi ngày là {MAX_DAILY_ENTRY:,} {CURRENCY_NAME}.", ephemeral=True)
        if amount > balance:
            return await interaction.response.send_message("❗ Bạn không đủ tiền.", ephemeral=True)

        await asyncio.sleep(5)

        data = self.load_data()
        today = self.get_today_key()
        if today not in data:
            data[today] = {"entries": {}, "total": 0, "winner": None, "played": []}

        if user_id in data[today]["played"]:
            return await interaction.response.send_message("🔁 Bạn chỉ được tham gia xổ số một lần mỗi ngày.", ephemeral=True)
        if data[today]["winner"] == user_id:
            return await interaction.response.send_message("🏆 Bạn đã trúng thưởng hôm nay và không thể cược thêm.", ephemeral=True)

        data[today]["entries"][user_id] = amount
        data[today]["total"] += amount
        data[today]["played"].append(user_id)
        self.save_data(data)
        update_balance(user_id, -amount)

        if amount <= 50000:
            win_chance = 1 / 3
        elif amount <= 150000:
            win_chance = 1 / 4.5
        elif amount <= 300000:
            win_chance = 1 / 6
        else:
            win_chance = 1 / 9

        won = data[today]["winner"] is None and random.random() < win_chance
        if won:
            reward = amount * 5
            data[today]["winner"] = user_id
            self.save_data(data)
            update_balance(user_id, reward)
            msg = f"🎉 Chúc mừng! Bạn đã trúng thưởng và nhận {reward:,} {CURRENCY_NAME} (x5 số cược)!"
        else:
            msg = f"😥 Rất tiếc, bạn không trúng thưởng hôm nay."

        await interaction.response.send_message(msg)

    # --- Slash command: /lotterystats ---
    @app_commands.command(name="lotterystats", description="📊 Xem thông tin xổ số hôm nay của bạn")
    async def lottery_stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = self.load_data()
        today = self.get_today_key()
        entry = data.get(today, {}).get("entries", {}).get(user_id, 0)
        total = data.get(today, {}).get("total", 0)

        embed = discord.Embed(title="📊 Thống Kê Xổ Số Hôm Nay", color=discord.Color.blue())
        embed.add_field(name="Bạn đã cược", value=f"{entry:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Tổng giải thưởng", value=f"{total:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Tỷ lệ thắng (lý thuyết)", value="~16.67% mỗi lượt", inline=True)
        await interaction.response.send_message(embed=embed)

    # --- RESET TỰ ĐỘNG 0H HÀNG NGÀY ---
    @tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=VIETNAM_TZ))
    async def lottery_reset_loop(self):
        await self.bot.wait_until_ready()
        data = self.load_data()
        yesterday = (datetime.datetime.now(tz=VIETNAM_TZ) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        if yesterday in data and data[yesterday]["entries"]:
            winner_id = data[yesterday].get("winner")
            total = data[yesterday]["total"]
            if winner_id:
                update_balance(winner_id, total)
                try:
                    user = await self.bot.fetch_user(int(winner_id))
                    embed = discord.Embed(title="🎉 KẾt Quả Xổ Số Hôm Qua", color=discord.Color.green())
                    embed.add_field(name="Người trúng thưởng", value=f"{user.mention} 🎉", inline=False)
                    embed.add_field(name="Giải thưởng (tổng cộng)", value=f"💰 {total:,} {CURRENCY_NAME}", inline=False)
                except:
                    pass

    # --- PREFIX COMMAND: !lottery ---
    @commands.command(name="lottery")
    async def lottery_prefix(self, ctx: commands.Context, amount: int):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.lottery(interaction, amount)

    @commands.command(name="lotterystats")
    async def lotterystats_prefix(self, ctx: commands.Context):
        interaction = await self.bot.get_application_context(ctx.message)
        await self.lottery_stats(interaction)

# --- ĐĂNG KÝ ---
async def setup(bot):
    await bot.add_cog(Lottery(bot))
