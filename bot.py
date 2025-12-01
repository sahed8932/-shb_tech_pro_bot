"""
Full Task & Earn Bot (Full System)
Features:
- Tasks (do -> send proof -> admin approve -> credit)
- Ads view reward
- Daily bonus
- Referral bonus
- Withdraw (Bkash/Nagad) request flow (sends to admin)
- Admin commands: /approve, /reject, /paid, /addbal, /stats
- Uses JSON file db.json to store data
- Blocks sending passwords/OTP in proofs
CONFIG: API_ID, API_HASH, BOT_TOKEN, ADMIN_USERNAME are embedded below as provided by user.
WARNING: Keep BOT_TOKEN secret. Do not share publicly.
"""

import json, os, time, re
from pyrogram import Client, filters

# ----------------- CONFIG (embedded) -----------------
API_ID = 37702767
API_HASH = "d8d98dcd337bd6824a595d3949d794cf"
BOT_TOKEN = "8278010034:AAE2lSM0TDfuKsyEXn_suDRYlcqfdfFUQ-I"
ADMIN_USERNAME = "Sahed_hossain113"
WITHDRAW_MIN = 100
REF_BONUS = 2
DAILY_BONUS = 3
# Reward per ad view (in currency units)
AD_REWARD = 0.5
# Default task list (id,title,reward)
DEFAULT_TASKS = [
    {"id":1,"title":"Join Telegram channel (send screenshot)","reward":1},
    {"id":2,"title":"Watch a YouTube video (send screenshot)","reward":1},
    {"id":3,"title":"Share a post (send screenshot)","reward":1},
    {"id":4,"title":"Follow Instagram (send proof)","reward":2},
    {"id":5,"title":"Install an app (send proof)","reward":5},
    {"id":6,"title":"Complete a short survey (send proof)","reward":15}
]

# -----------------------------------------------------
app = Client("full_task_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DB_FILE = "db.json"
RU_PHONE_RE = re.compile(r"^(?:\+7|7|8)(\d{10})$")
PWD_BLOCK = ["password","pass","пароль","otp","code","код"]

def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "users":{},        # user_id -> {balance, ref_by, referred, invited}
            "tasks": DEFAULT_TASKS.copy(),
            "pending_proofs":{}, # user_id -> {task_id, time}
            "withdraws":{},    # wid -> {user_id, method, number, amount, status, time}
            "next_withdraw_id":1
        }
        save_db(data)
    with open(DB_FILE,"r",encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def ensure_user(data, uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"balance":0,"ref_by":None,"referred":0,"invited":0}
    return data["users"][uid]

async def get_admin_id():
    admin = await app.get_users(ADMIN_USERNAME)
    return admin.id

def contains_pwd(text):
    if not text:
        return False
    low = text.lower()
    return any(k in low for k in PWD_BLOCK)

# ----------------- Bot Commands -----------------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    args = message.text.split()
    data = load_db()
    user = ensure_user(data, message.from_user.id)

    # referral handling: /start <refid>
    if len(args) > 1:
        try:
            ref = int(args[1])
            if str(ref) != str(message.from_user.id) and user.get("ref_by") is None:
                ref_user = ensure_user(data, ref)
                user["ref_by"] = ref
                ref_user["referred"] = ref_user.get("referred",0)+1
                ref_user["balance"] = ref_user.get("balance",0) + REF_BONUS
                save_db(data)
                try:
                    await client.send_message(ref, f"🎉 আপনি {REF_BONUS}৳ পেয়েছেন রেফার বোনাস হিসেবে!")
                except:
                    pass
        except:
            pass

    save_db(data)
    text = (
        "👋 স্বাগতম Task & Earn Bot-এ!\n\n"
        "মেনু:\n"
        "/tasks - টাস্ক লিস্ট\n"
        "/do <id> - টাস্ক নাও\n"
        "/balance - ব্যালান্স দেখাও\n"
        "/ads - অ্যাড সম্পর্কিত\n"
        "/bonus - দৈনন্দিন বোনাস\n"
        "/invite - আপনার রেফার লিংক\n"
        "/withdraw - উইথড্র আবেদন\n\n"
        f"🔰 Withdraw minimum: {WITHDRAW_MIN}৳\n"
        "⚠️ কখনো পাসওয়ার্ড/OTP/লগইন কোড পাঠাবেন না!"
    )
    await message.reply(text)

@app.on_message(filters.command("tasks"))
async def tasks_cmd(client, message):
    data = load_db()
    tasks = data["tasks"]
    lines = ["🗒️ Available Tasks:\n"]
    for t in tasks:
        lines.append(f"ID: {t['id']} | {t['title']} — Reward: {t['reward']}৳")
    lines.append("\nUse /do <id> to start a task.")
    await message.reply("\n".join(lines))

@app.on_message(filters.command("do"))
async def do_cmd(client, message):
    data = load_db()
    try:
        tid = int(message.text.split()[1])
    except:
        return await message.reply("🔸 Use: /do <task_id>")
    task = next((x for x in data["tasks"] if x["id"]==tid), None)
    if not task:
        return await message.reply("❌ Invalid task id.")
    data["pending_proofs"][str(message.from_user.id)] = {"task_id":tid,"time":int(time.time())}
    save_db(data)
    await message.reply(f"✅ Task started: {task['title']}\nPerform the task and send proof (photo/document).")

@app.on_message(filters.photo | filters.document)
async def proof_handler(client, message):
    data = load_db()
    uid = str(message.from_user.id)
    if uid not in data.get("pending_proofs",{}):
        return await message.reply("❌ No pending task. Use /tasks and /do <id> first.")
    txt = (message.caption or "") + " " + (message.text or "")
    if contains_pwd(txt):
        return await message.reply("❌ Do NOT send passwords/OTP/codes. Only screenshots as proof.")
    entry = data["pending_proofs"][uid]
    task = next((x for x in data["tasks"] if x["id"]==entry["task_id"]), None)
    if not task:
        del data["pending_proofs"][uid]; save_db(data)
        return await message.reply("❌ Task not found.")
    admin_id = await get_admin_id()
    # forward media to admin and send meta
    await message.copy(admin_id)
    await client.send_message(admin_id,
        f"📩 Proof from {message.from_user.mention}\nUserID: {message.from_user.id}\nTask: {task['title']}\nReward: {task['reward']}৳\nTo approve: /approve {message.from_user.id} {task['reward']}"
    )
    await message.reply("✅ Proof sent to admin for review. Wait for approval.")

@app.on_message(filters.command("approve"))
async def approve_cmd(client, message):
    admin = await get_admin_id()
    if message.from_user.id != admin:
        return await message.reply("❌ Only admin can use this.")
    try:
        parts = message.text.split()
        uid = str(int(parts[1])); amount = int(parts[2])
    except:
        return await message.reply("❗ Usage: /approve <user_id> <amount>")
    data = load_db()
    user = ensure_user(data, uid)
    user["balance"] = user.get("balance",0) + amount
    if uid in data.get("pending_proofs",{}):
        del data["pending_proofs"][uid]
    save_db(data)
    await client.send_message(int(uid), f"✅ Approved! আপনি পেয়েছেন {amount}৳। আপনার নতুন ব্যালান্স: {user['balance']}৳")
    await message.reply(f"✅ Credited {amount}৳ to user {uid}.")

@app.on_message(filters.command("reject"))
async def reject_cmd(client, message):
    admin = await get_admin_id()
    if message.from_user.id != admin:
        return await message.reply("❌ Only admin can use this.")
    try:
        uid = str(int(message.text.split()[1]))
    except:
        return await message.reply("❗ Usage: /reject <user_id>")
    data = load_db()
    if uid in data.get("pending_proofs",{}):
        del data["pending_proofs"][uid]
        save_db(data)
    await client.send_message(int(uid), "❌ আপনার প্রমাণটি প্রত্যাখ্যাত হয়েছে। আবার চেষ্টা করুন।")
    await message.reply("✅ Rejected and notified user.")

@app.on_message(filters.command("balance"))
async def balance_cmd(client, message):
    data = load_db()
    user = ensure_user(data, message.from_user.id)
    await message.reply(f"💰 আপনার ব্যালান্স: {user.get('balance',0)}৳")

@app.on_message(filters.command("invite"))
async def invite_cmd(client, message):
    uid = message.from_user.id
    bot_user = await app.get_me()
    link = f"https://t.me/{bot_user.username}?start={uid}"
    await message.reply(f"👥 Share this link to invite: {link}\nEach referral gives {REF_BONUS}৳ to the referrer.")

@app.on_message(filters.command("ads"))
async def ads_cmd(client, message):
    await message.reply(f"📺 Ads: Watch /watch to get {AD_REWARD}৳ per ad view.")

@app.on_message(filters.command("watch"))
async def watch_cmd(client, message):
    uid = message.from_user.id
    data = load_db()
    user = ensure_user(data, uid)
    user["balance"] = user.get("balance",0) + AD_REWARD
    save_db(data)
    await message.reply(f"🎉 Ad watched! +{AD_REWARD}৳ added. Balance: {user['balance']}৳")

@app.on_message(filters.command("bonus"))
async def bonus_cmd(client, message):
    uid = message.from_user.id
    data = load_db()
    user = ensure_user(data, uid)
    now = int(time.time())
    last = user.get("last_bonus",0)
    if now - last < 86400:
        return await message.reply("❌ আপনি আজকে বোনাস নিয়েছেন।")
    user["last_bonus"] = now
    user["balance"] = user.get("balance",0) + DAILY_BONUS
    save_db(data)
    await message.reply(f"🎁 দৈনিক বোনাস: +{DAILY_BONUS}৳")

@app.on_message(filters.command("withdraw"))
async def withdraw_cmd(client, message):
    uid = message.from_user.id
    data = load_db()
    user = ensure_user(data, uid)
    bal = user.get("balance",0)
    if bal < WITHDRAW_MIN:
        return await message.reply(f"❌ মিনিমাম {WITHDRAW_MIN}৳ দরকার। আপনার ব্যালান্স: {bal}৳")
    # start withdraw flow: ask method
    data["withdraw_flow"] = data.get("withdraw_flow",{})
    data["withdraw_flow"][str(uid)] = {"step":"method","amount":bal,"time":int(time.time())}
    save_db(data)
    await message.reply("💵 কোন মেথড চান? লিখুন: Bkash অথবা Nagad")

@app.on_message(filters.text & ~filters.command())
async def text_flow(client, message):
    data = load_db()
    uid = message.from_user.id
    wf = data.get("withdraw_flow",{}).get(str(uid))
    if not wf:
        return  # ignore other texts
    step = wf.get("step")
    text = message.text.strip()
    if step == "method":
        method = text.lower()
        if method not in ["bkash","nagad"]:
            return await message.reply("❌ শুধুই লিখুন: Bkash অথবা Nagad")
        wf["method"] = method
        wf["step"] = "number"
        data["withdraw_flow"][str(uid)] = wf
        save_db(data)
        return await message.reply(f"📱 আপনার {method} নাম্বার দিন (country code optional):")
    if step == "number":
        number = text
        if not re.match(r"^\+?\d{10,15}$", number):
            return await message.reply("❌ সঠিক নম্বর দিন (country code optional).")
        amount = wf["amount"]
        method = wf["method"]
        wid = str(data.get("next_withdraw_id",1))
        data["withdraws"][wid] = {"user_id":uid,"method":method,"number":number,"amount":amount,"status":"pending","time":int(time.time())}
        data["next_withdraw_id"] = int(wid)+1
        # clear flow and deduct balance
        data["withdraw_flow"].pop(str(uid),None)
        user = ensure_user(data, uid)
        user["balance"] = 0
        save_db(data)
        admin_id = await get_admin_id()
        await client.send_message(admin_id,
            f"📨 WITHDRAW REQUEST #{wid}\nUser: {message.from_user.mention}\nUserID: {uid}\nMethod: {method}\nNumber: {number}\nAmount: {amount}৳\nTo mark paid: /paid {wid}"
        )
        return await message.reply("✅ Withdraw request sent to admin. Waiting for payment.")

@app.on_message(filters.command("paid"))
async def paid_cmd(client, message):
    admin = await get_admin_id()
    if message.from_user.id != admin:
        return await message.reply("❌ Only admin can use this.")
    try:
        wid = str(int(message.text.split()[1]))
    except:
        return await message.reply("❗ Usage: /paid <withdraw_id>")
    data = load_db()
    w = data.get("withdraws",{}).get(wid)
    if not w:
        return await message.reply("❌ Withdraw id not found.")
    if w.get("status") == "paid":
        return await message.reply("ℹ️ Already marked paid.")
    w["status"] = "paid"
    save_db(data)
    try:
        await client.send_message(w["user_id"], f"✅ আপনার withdraw #{wid} of {w['amount']}৳ PAID by admin. If you didn't get money contact admin.")
    except:
        pass
    await message.reply(f"✅ Withdraw #{wid} marked PAID.")

@app.on_message(filters.command("addbal"))
async def addbal_cmd(client, message):
    admin = await get_admin_id()
    if message.from_user.id != admin:
        return await message.reply("❌ Only admin can use this.")
    try:
        parts = message.text.split()
        uid = str(int(parts[1])); amt = int(parts[2])
    except:
        return await message.reply("❗ Usage: /addbal <user_id> <amount>")
    data = load_db()
    user = ensure_user(data, uid)
    user["balance"] = user.get("balance",0) + amt
    save_db(data)
    await client.send_message(int(uid), f"✅ Admin added {amt}৳ to your account. New balance: {user['balance']}৳")
    await message.reply("✅ Done.")

@app.on_message(filters.command("stats"))
async def stats_cmd(client, message):
    admin = await get_admin_id()
    if message.from_user.id != admin:
        return await message.reply("❌ Only admin can use this.")
    data = load_db()
    users = len(data["users"])
    total_withdraws = len(data["withdraws"])
    await message.reply(f"Users: {users}\nWithdraws: {total_withdraws}")

# run cleanup on start to remove stale withdraw_flow entries
def cleanup():
    data = load_db()
    wf = data.get("withdraw_flow",{})
    now = int(time.time())
    for k,v in list(wf.items()):
        # if flow older than 1 day remove
        if now - v.get("time", now) > 86400:
            wf.pop(k, None)
    data["withdraw_flow"] = wf
    save_db(data)

cleanup()

print("FULL TASK BOT RUNNING...")
app.run()
