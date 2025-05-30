import os
import json
import datetime

# ────────────── CẤU HÌNH ────────────── #
DATA_DIR = "data"
START_BALANCE = 30_000
DAILY_TRANSFER_LIMIT = 250_000

# ───── ĐƯỜNG DẪN TỆP JSON ───── #
BALANCE_FILE = os.path.join(DATA_DIR, "balance.json")
STREAK_FILE = os.path.join(DATA_DIR, "streak.json")
RANK_FILE = os.path.join(DATA_DIR, "wins.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
TRANSFER_FILE = os.path.join(DATA_DIR, "transfer_limits.json")

# ────────────── HÀM CHUNG ────────────── #
def load_json(file):
    if not os.path.exists(file):
        save_json(file, {})  # Tạo tệp với giá trị mặc định nếu không tồn tại
        return {}
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Lỗi khi đọc tệp JSON {file}. Dữ liệu không hợp lệ.")
        return {}
    except Exception as e:
        print(f"❌ Lỗi khi đọc tệp {file}: {e}")
        return {}

def save_json(file, data):
    try:
        os.makedirs(os.path.dirname(file), exist_ok=True)  # Tạo thư mục nếu chưa có
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Lỗi khi ghi tệp {file}: {e}")

# ────────────── SỐ DƯ ────────────── #
def get_balance(user_id):
    data = load_json(BALANCE_FILE)
    return data.get(str(user_id), START_BALANCE)

def update_balance(user_id, amount):
    uid = str(user_id)
    data = load_json(BALANCE_FILE)
    current = data.get(uid, START_BALANCE)
    new_balance = max(0, current + amount)
    if new_balance == 0:
        print(f"⚠️ Số dư của người dùng {user_id} đã về 0.")
    data[uid] = new_balance
    save_json(BALANCE_FILE, data)

# ────────────── CHUỖI THẮNG ────────────── #
def get_streak(user_id):
    return load_json(STREAK_FILE).get(str(user_id), 0)

def update_streak(user_id, won: bool):
    uid = str(user_id)
    data = load_json(STREAK_FILE)
    data[uid] = data.get(uid, 0) + 1 if won else 0
    save_json(STREAK_FILE, data)

# ────────────── BẢNG XẾP HẠNG ────────────── #
def add_win(user_id):
    uid = str(user_id)
    data = load_json(RANK_FILE)
    data[uid] = data.get(uid, 0) + 1
    save_json(RANK_FILE, data)

def get_ranking():
    data = load_json(RANK_FILE)
    return sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

# ────────────── THỐNG KÊ ────────────── #
def update_stats(user_id, result: str):
    uid = str(user_id)
    data = load_json(STATS_FILE)
    if uid not in data:
        data[uid] = {"win": 0, "loss": 0, "tie": 0}
    if result in data[uid]:
        data[uid][result] += 1
    save_json(STATS_FILE, data)

def get_level(wins: int):
    return wins // 10

# ────────────── CHUYỂN TIỀN HẰNG NGÀY ────────────── #
def get_remaining_transfer(user_id):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    uid = str(user_id)
    data = load_json(TRANSFER_FILE)
    record = data.get(uid, {"date": "", "amount": 0})
    if record["date"] != today:
        return DAILY_TRANSFER_LIMIT
    return max(0, DAILY_TRANSFER_LIMIT - record["amount"])

def record_transfer(user_id, amount: int):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    uid = str(user_id)
    data = load_json(TRANSFER_FILE)
    if uid not in data or data[uid]["date"] != today:
        data[uid] = {"date": today, "amount": 0}
    data[uid]["amount"] += amount
    save_json(TRANSFER_FILE, data)
