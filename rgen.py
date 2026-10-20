import hmac, hashlib, requests, string, random, json, codecs, time, os, sys
import base64, signal, threading, re, subprocess, importlib, queue
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from colorama import Fore, Style, init
import urllib3
from requests.adapters import HTTPAdapter

urllib3.disable_warnings()
init(autoreset=True)

# ============================================================
# CREDIT PROTECTION SYSTEM - BRAND: FREXY
# ============================================================
def _verify_credit():
    return True

_verify_credit()

# ============================================================
SERVER = {
    1: bytes.fromhex(
        "68747470733a2f2f7465736e65776d616a6f72312e76657263656c2e6170702f6170692f76322f67656e"
    ).decode("utf-8"),
}

API_ACTIVE = 0

class Config:
    AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    REGION_LANG = {"ME":"ar","IND":"hi","ID":"id","VN":"vi","TH":"th","BD":"bn","PK":"ur","TW":"zh","CIS":"ru","SAC":"es","BR":"pt"}

REGION_LANG = Config.REGION_LANG
HEX_KEY = bytes.fromhex(
    "32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533"
)

# ============================================================
# TUNING FOR 200 THREADS
# ============================================================
HTTP_TIMEOUT = 12
HTTP_RETRIES = 1
HTTP_BACKOFF = 0.01
PROGRESS_STEP = 100
MAX_WORKERS = 200
DEFAULT_WORKERS = 200

# ============================================================
# COLORS
# ============================================================
OK       = Fore.GREEN
OK_B     = Fore.GREEN + Style.BRIGHT
RARE     = Fore.YELLOW
RARE_B   = Fore.YELLOW + Style.BRIGHT
INFO     = Fore.CYAN
INFO_B   = Fore.CYAN + Style.BRIGHT
WARN     = Fore.MAGENTA
WARN_B   = Fore.MAGENTA + Style.BRIGHT
ERR      = Fore.RED
ERR_B    = Fore.RED + Style.BRIGHT
MENU     = Fore.WHITE + Style.BRIGHT
DIM      = Style.DIM
RST      = Style.RESET_ALL

BOX_GREEN   = Fore.GREEN + Style.BRIGHT
BOX_YELLOW  = Fore.YELLOW + Style.BRIGHT
LABEL_CYAN  = Fore.CYAN + Style.BRIGHT
VALUE_WHITE = Fore.WHITE + Style.BRIGHT
BAR_FILL    = Fore.YELLOW + Style.BRIGHT
BAR_EMPTY   = Fore.WHITE + Style.DIM
THREAD_CLR  = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
UID_CLR     = Fore.LIGHTGREEN_EX + Style.BRIGHT
PASS_CLR    = Fore.LIGHTYELLOW_EX + Style.BRIGHT
NAME_CLR    = Fore.LIGHTBLUE_EX + Style.BRIGHT
REGION_CLR  = Fore.LIGHTRED_EX + Style.BRIGHT

# ============================================================
# GLOBAL SESSION WITH HIGH CONNECTION POOL
# ============================================================
_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=1000, pool_maxsize=2000, max_retries=0, pool_block=False)
_session.mount('https://', _adapter)
_session.mount('http://', _adapter)

# ============================================================
# IP SPOOFER
# ============================================================
class FastIPSpoofer:
    _POOL = [f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(50000)]
    _idx = 0
    _lock = threading.Lock()
    @classmethod
    def get(cls):
        with cls._lock:
            ip = cls._POOL[cls._idx % len(cls._POOL)]
            cls._idx += 1
            return ip

    @classmethod
    def get_ip(cls):
        return cls.get()

# ============================================================
# UA
# ============================================================
class WAFBypass:
    _uas = [
        "GarenaMSDK/4.0.42(SM-A525F ;Android)",
        "GarenaMSDK/4.0.39(SM-A325M;Android 13;en;HK;)",
        "GarenaMSDK/4.0.38(Redmi Note 10;Android 12;en;ID;)",
        "GarenaMSDK/4.0.40(Poco X3;Android 11;en;SG;)",
        "GarenaMSDK/4.0.41(SM-S918B;Android 14;en;IN;)",
        "GarenaMSDK/4.0.42(OnePlus 11;Android 13;en;US;)",
        "GarenaMSDK/4.0.39(Xiaomi 13 Pro;Android 13;pt;BR;)",
        "GarenaMSDK/4.0.40(Pixel 7 Pro;Android 14;en;US;)",
        "GarenaMSDK/4.0.42(Infinix X6819;Android 13;en;PK;)",
        "GarenaMSDK/4.0.41(vivo 1906;Android 11;en;BD;)",
    ]
    @staticmethod
    def get_ua(): return random.choice(WAFBypass._uas)

# ============================================================
# THREAD LOCAL
# ============================================================
_thread_local = threading.local()

# ============================================================
# DEVICE POOL (500+ DEVICE COMBINATIONS)
# ============================================================
class DevicePool:
    _devices, _index, _lock = [], 0, threading.Lock()
    DEVICE_MODELS = [
        ("Asus ASUS_I005DA", "ARMv7 VFPv3 NEON VMH | 2400 | 2", "Adreno (TM) 640"),
        ("SM-A525F", "ARMv8 VFPv4 NEON VMH | 2200 | 8", "Adreno (TM) 618"),
        ("SM-A325M", "ARMv8 VFPv4 NEON VMH | 2000 | 8", "Mali-G52"),
        ("SM-S918B", "ARMv8 VFPv4 NEON VMH | 3200 | 8", "Adreno (TM) 740"),
        ("Redmi Note 10","ARMv8 VFPv4 NEON VMH | 2200 | 8","Adreno (TM) 619"),
        ("Redmi Note 11","ARMv8 VFPv4 NEON VMH | 2400 | 8","Adreno (TM) 610"),
        ("Poco X3","ARMv8 VFPv4 NEON VMH | 2300 | 8","Adreno (TM) 618"),
        ("Poco M4 Pro","ARMv8 VFPv4 NEON VMH | 2200 | 8","Mali-G57"),
        ("Pixel 6","ARMv8 VFPv4 NEON VMH | 2800 | 8","Mali-G78"),
        ("Pixel 7 Pro","ARMv8 VFPv4 NEON VMH | 2800 | 8","Mali-G710"),
        ("OnePlus 9","ARMv8 VFPv4 NEON VMH | 2800 | 8","Adreno (TM) 660"),
        ("OnePlus 11","ARMv8 VFPv4 NEON VMH | 3200 | 8","Adreno (TM) 740"),
        ("Xiaomi 13 Pro","ARMv8 VFPv4 NEON VMH | 3200 | 8","Adreno (TM) 740"),
        ("Infinix X6819","ARMv8 VFPv4 NEON VMH | 2400 | 8","Mali-G57"),
        ("vivo 1906","ARMv8 VFPv4 NEON VMH | 2000 | 8","Adreno (TM) 610"),
        ("OPPO CPH2211","ARMv8 VFPv4 NEON VMH | 2200 | 8","Adreno (TM) 619"),
        ("realme RMX3363","ARMv8 VFPv4 NEON VMH | 2400 | 8","Adreno (TM) 642"),
        ("TECNO KI5","ARMv8 VFPv4 NEON VMH | 2000 | 8","Mali-G52"),
        ("SM-G998B", "ARMv8 VFPv4 NEON VMH | 2900 | 8", "Mali-G78"),
        ("Redmi K50", "ARMv8 VFPv4 NEON VMH | 3050 | 8", "Mali-G710"),
        ("vivo X90", "ARMv8 VFPv4 NEON VMH | 3050 | 8", "Mali-G715")
    ]
    ANDROID_VERSIONS = [
        ("Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)","9","28"),
        ("Android OS 10 / API-29 (QKQ1.200114.002)","10","29"),
        ("Android OS 11 / API-30 (RP1A.201005.001)","11","30"),
        ("Android OS 12 / API-31 (SP1A.210812.016)","12","31"),
        ("Android OS 12L / API-32 (SP2A.220505.002)","12","32"),
        ("Android OS 13 / API-33 (TQ3A.230805.001)","13","33"),
        ("Android OS 14 / API-34 (UP1A.231005.007)","14","34"),
    ]
    NETWORKS  = ["WIFI","4G","5G"]
    OPERATORS = ["ATM Mobils","Telkomsel","Indosat","XL Axiata","Airtel","Jio","Vodafone","Globe","Smart","Viettel","Mobifone","Claro","Vivo","Grameenphone","Robi","Banglalink"]
    SDK_VER   = ["4.0.38","4.0.39","4.0.40","4.0.41","4.0.42"]

    @classmethod
    def _rh(cls, n): return ''.join(random.choices("0123456789abcdef", k=n))
    @classmethod
    def _uuid(cls): return f"{cls._rh(8)}-{cls._rh(4)}-{cls._rh(4)}-{cls._rh(4)}-{cls._rh(12)}"
    @classmethod
    def _mac(cls):  return "02:" + ":".join(cls._rh(2) for _ in range(5))

    @classmethod
    def init_pool(cls, count=1000):
        if cls._devices: return
        for _ in range(count):
            model, cpu, gpu = random.choice(cls.DEVICE_MODELS)
            android_full, android_ver, api = random.choice(cls.ANDROID_VERSIONS)
            cls._devices.append({
                "model": model, "brand": model.split()[0], "cpu": cpu, "gpu": gpu,
                "android_full": android_full, "android_version": android_ver, "api_level": api,
                "operator": random.choice(cls.OPERATORS), "network": random.choice(cls.NETWORKS),
                "sdk": random.choice(cls.SDK_VER), "mac": cls._mac(),
                "device_id": cls._rh(32), "android_id": cls._rh(16), "uuid": cls._uuid(),
                "imei": cls._rh(15), "fingerprint": cls._rh(40), "gl_renderer": "OpenGL ES 3.2",
                "lang_code": random.choice(["en","in","ar","hi","vi","th","pt","ru","es","bn","ur","zh"]),
            })

    @classmethod
    def get(cls):
        with cls._lock:
            dev = cls._devices[cls._index % len(cls._devices)]
            cls._index += 1
            return dev

    @classmethod
    def headers(cls, device=None):
        d = device or cls.get()
        return {
            "X-Device-Id": d["device_id"], "X-Android-Id": d["android_id"],
            "X-Device-Model": d["model"],  "X-Device-Brand": d["brand"],
            "X-OS-Version": d["android_version"], "X-API-Level": d["api_level"],
            "X-SDK-Version": d["sdk"], "X-Network-Type": d["network"],
            "X-Operator": d["operator"], "X-IMEI": d["imei"],
            "X-Mac": d["mac"], "X-Client-Uuid": d["uuid"],
        }

DevicePool.init_pool(1000)

def get_thread_device():
    if not hasattr(_thread_local, "device"):
        _thread_local.device = DevicePool.get()
    return _thread_local.device

def reset_thread_device():
    _thread_local.device = DevicePool.get()
    _thread_local.session = requests.Session()

def get_thread_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session

# ============================================================
# F14 ENCODE
# ============================================================
def encode_f14(s):
    ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,
          0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
          0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,
          0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    return bytes(ord(c) ^ ks[i % len(ks)] for i, c in enumerate(s))

FIELD_22 = bytes.fromhex(
    "4747524501010100620200001052aa0d669c6a368f08338060d2ee0690053af84a41edcd3558556ec10f24f4"
    "6c93ac64ca41a16732c46a2cb071246a79b8929032f9e1b6f4ef331bd53cabf29b09b97349a46e9863c0314e"
    "1a0d80819fef8aabf03876b3d037db354a7ccb5c1bce96411fb3753f6f50e44c69c4ed617fa30efb8ffc0517"
    "ff2f636739be1f304d999cfd6fd48bf69454199794c3dc88f55a4bdbd66534d5a061359cdfd1fb680cd37918"
    "df9fdb3cf7d80067b0a3506c90063cf62b2ccec11e23913a2fd7c4ef091331967bb518a5ad1e551146b90821"
    "be800883abadde39d6c80a5d798611466c748f075481806c5842ce45e6bd4e3368ec08fe2ec41ceb880cd862"
    "49eb71693f79f0bccf9e590c3fae12519fe08c7a1905d0927690109e0df28574bb14847225db1a59230e6662"
    "ed7730e15ff9a6c815cb41b420edeada735a4b03e181037c37c2c850257311df2f07b0a56e759372cbd0268e"
    "3f13a292ee4373e38ab5096e0342a5e0d7fec6da2bbc265d74baadd2b24ee4f74862f82c21d6694bac53f8ce"
    "80312a30068a6276a641c19b11d0305c6fe2f531ac7de578b29f543697f5c73663e6f23aa15277b6122dcd4d"
    "4171e38f9ac0b173f39c58416a16c5c1f4a35acd065ce78f449cf538a249339e763272d458e4ed86c976591a"
    "9c066b3a37111e44091eb6b5a795249f3e5145db022a6055f2cc675936391312f688f89627845df222a91156"
    "555225be36f9714a0ba50246d0f003bda3c9c1292ab73b4f79635ddd023218eda93a302d79e023404c143965"
    "44a930b98ed54771aca7fec10d095587685b473e81a9619764fad9256529dcd6e911f4f4629612287d4ee3ec"
    "5389f6ec4ec020b0e2aac017232a9197be9e46239ce690fe5d4872b2e98e651510c971667f3aca8b59f3e9d5"
    "0e43"
)

# ============================================================
# PROTO
# ============================================================
def encode_varint(n):
    if n < 0: return b''
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        out.append(b)
        if not n: break
    return bytes(out)

def build_proto(fields):
    parts = []
    for k, v in fields.items():
        if isinstance(v, dict):
            nested = build_proto(v)
            parts.append(encode_varint((k << 3) | 2) + encode_varint(len(nested)) + nested)
        elif isinstance(v, int):
            parts.append(encode_varint((k << 3) | 0) + encode_varint(v))
        elif isinstance(v, (str, bytes)):
            ev = v.encode() if isinstance(v, str) else v
            parts.append(encode_varint((k << 3) | 2) + encode_varint(len(ev)) + ev)
    return b''.join(parts)

def aes_encrypt(hex_data):
    return AES.new(Config.AES_KEY, AES.MODE_CBC, Config.AES_IV).encrypt(pad(bytes.fromhex(hex_data), AES.block_size))

def encrypt_api(plain_hex):
    return AES.new(Config.AES_KEY, AES.MODE_CBC, Config.AES_IV).encrypt(pad(bytes.fromhex(plain_hex), AES.block_size)).hex()

# ============================================================
# MERGE HEADERS
# ============================================================
def _merge_headers(headers, device=None):
    if headers is None: headers = {}
    dev = device or get_thread_device()
    for k, v in DevicePool.headers(dev).items():
        headers.setdefault(k, v)
    headers.setdefault("X-Forwarded-For", FastIPSpoofer.get())
    headers.setdefault("X-Real-IP",       FastIPSpoofer.get())
    headers.setdefault("X-Client-IP",     FastIPSpoofer.get())
    headers.setdefault("CF-Connecting-IP", FastIPSpoofer.get())
    headers.setdefault("True-Client-IP",  FastIPSpoofer.get())
    headers.setdefault("Forwarded",       f"for={FastIPSpoofer.get()}")
    return headers

# ============================================================
# REQUEST RETRY
# ============================================================
def request_retry(method, url, tag="HTTP", **kwargs):
    sess = get_thread_session()
    for attempt in range(HTTP_RETRIES + 1):
        try:
            kwargs.setdefault('timeout', HTTP_TIMEOUT)
            kwargs['headers'] = _merge_headers(kwargs.get('headers'))
            kwargs['verify'] = False
            resp = sess.request(method, url, **kwargs)

            if resp and resp.status_code in (200, 201):
                return resp
            reset_thread_device()
            sess = get_thread_session()
        except Exception:
            reset_thread_device()
            sess = get_thread_session()
    return None

# ============================================================
# INSTANT FILE WRITER (THREAD SAFE)
# ============================================================
FILE_LOCK = threading.Lock()

def save_json_instant(fn, data):
    with FILE_LOCK:
        try:
            accounts = []
            if os.path.exists(fn) and os.path.getsize(fn) > 0:
                try:
                    with open(fn, "r", encoding="utf-8") as f:
                        accounts = json.load(f)
                    if not isinstance(accounts, list):
                        accounts = []
                except Exception:
                    accounts = []
            accounts.append(data)
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(accounts, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

# ============================================================
# FAST PRINT
# ============================================================
_print_lock = threading.Lock()
_stdout_write = sys.stdout.write
_stdout_flush = sys.stdout.flush

def fast_print(msg):
    with _print_lock:
        try:
            _stdout_write(msg + "\n")
            _stdout_flush()
        except: pass

# ============================================================
# GLOBAL STATE
# ============================================================
EXIT = False
COUNT_OK = 0
TARGET = 0
RARE_CNT = 0
THRESHOLD = 6
LOCK = threading.Lock()
STOP_EVENT = threading.Event()
API_OK = {i: 0 for i in range(1, 39)}
API_FAIL = {i: 0 for i in range(1, 39)}
START_TIME = time.time()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_FOLDER = os.path.join(BASE_DIR, "FREXY-MODS")
TOKENS_FOLDER = os.path.join(BASE_FOLDER, "TOKENS-JWT")
ACCOUNTS_FOLDER = os.path.join(BASE_FOLDER, "ACCOUNTS")
RARE_FOLDER = os.path.join(BASE_FOLDER, "RARE ACCOUNTS")
GHOST_FOLDER = os.path.join(BASE_FOLDER, "GHOST")
GHOST_ACCOUNTS = os.path.join(GHOST_FOLDER, "ACCOUNTS")
GHOST_RARE = os.path.join(GHOST_FOLDER, "RAREACCOUNT")

for folder in [BASE_FOLDER, TOKENS_FOLDER, ACCOUNTS_FOLDER, RARE_FOLDER, GHOST_FOLDER, GHOST_ACCOUNTS, GHOST_RARE]:
    os.makedirs(folder, exist_ok=True)

# ============================================================
# RARITY
# ============================================================
_PATTERNS_RAW = {
    "R4": [r"(\d)\1{3,}", 3], "R3": [r"(\d)\1\1(\d)\2\2", 2],
    "S5": [r"(12345|23456|34567|45678|56789)", 4],
    "S4": [r"(0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321|3210)", 3],
    "P6": [r"^(\d)(\d)(\d)\3\2\1$", 5], "P4": [r"^(\d)(\d)\2\1$", 3],
    "SPH": [r"(69|420|1337|007)", 4], "SPM": [r"(100|200|300|400|500|666|777|888|999)", 2],
    "QD": [r"(1111|2222|3333|4444|5555|6666|7777|8888|9999|0000)", 4],
    "MH": [r"^(\d{2,3})\1$", 3], "MM": [r"(\d{2})0\1", 2], "GD": [r"1618|0618", 3],
    "PAIR3": [r"(\d)\1(\d)\2(\d)\3", 3],
    "PAIRX": [r"(\d)\1.*(\d)\2.*(\d)\3", 2],
    "ALT": [r"(\d)(\d)\1\2\1\2", 3], "ALT8": [r"(\d)(\d)\1\2\1\2\1\2", 4],
    "TAIL0": [r"0{4,}$", 3], "HEAD1": [r"^1{2,}", 2],
    "BLOCK": [r"(\d{2,3})\1{1,}", 4],
    "STEP2": [r"(13579|2468|8642|97531)", 4],
    "MIX": [r"(55|66|77|88|99){2,}", 3]
}
PATTERNS = [(re.compile(v[0]), v[1]) for v in _PATTERNS_RAW.values()]

def check_rarity(account_id):
    global THRESHOLD
    if not account_id or account_id == "N/A":
        return False, 0
    score = 0
    for pat, pts in PATTERNS:
        if pat.search(account_id): score += pts
    digits = [int(d) for d in account_id if d.isdigit()]
    if len(digits) >= 4 and len(set(digits)) == 1: score += 5
    if len(digits) >= 4:
        diffs = [digits[i+1] - digits[i] for i in range(len(digits)-1)]
        if len(set(diffs)) == 1: score += 4
    if len(account_id) <= 8 and account_id.isdigit() and int(account_id) < 1000000: score += 3
    return (score > THRESHOLD), score

# ============================================================
# SAVE
# ============================================================
def save_normal(acc, region, is_ghost):
    fn = (
        os.path.join(GHOST_ACCOUNTS, "ghost.json")
        if is_ghost
        else os.path.join(ACCOUNTS_FOLDER, f"accounts-{region}.json")
    )
    data = {
        "uid": acc.get("uid", "N/A"),
        "password": acc.get("password", ""),
        "account_id": acc.get("account_id", "N/A")
    }
    save_json_instant(fn, data)


def save_rare(acc, region, is_ghost, score):
    fn = (
        os.path.join(GHOST_RARE, "rare-ghost.json")
        if is_ghost
        else os.path.join(RARE_FOLDER, f"rare-{region}.json")
    )
    data = {
        "uid": acc.get("uid", "N/A"),
        "password": acc.get("password", ""),
        "account_id": acc.get("account_id", "N/A"),
        "score": score
    }
    save_json_instant(fn, data)


def save_jwt(acc, region, is_ghost):
    if not acc.get("jwt_token"):
        return
    fn = (
        os.path.join(GHOST_FOLDER, "tokens-ghost.json")
        if is_ghost
        else os.path.join(TOKENS_FOLDER, f"tokens-{region}.json")
    )
    data = {
        "uid": acc.get("uid", "N/A"),
        "account_id": acc.get("account_id", "N/A"),
        "jwt_token": acc.get("jwt_token")
    }
    save_json_instant(fn, data)

# ============================================================
# NAME
# ============================================================
def generate_random_name(name_prefix):
    characters = string.ascii_letters + string.digits
    return name_prefix + ''.join(random.choice(characters) for _ in range(6)).upper()

# ============================================================
# COLORED PROGRESS BAR
# ============================================================
def draw_progress_bar(current, total, speed, eta):
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    if filled > bar_len: filled = bar_len
    bar_fill  = f"{BAR_FILL}{'█' * filled}{RST}"
    bar_empty = f"{BAR_EMPTY}{'░' * (bar_len - filled)}{RST}"
    bar = bar_fill + bar_empty
    eta_str = f"{int(eta)}s" if eta < 3600 else f"{int(eta/60)}m"
    return f"{BOX_YELLOW}[{RST}{bar}{BOX_YELLOW}]{RST} {VALUE_WHITE}{current}{RST}{DIM}/{RST}{VALUE_WHITE}{total}{RST} {DIM}|{RST} {OK_B}{speed:.2f}/s{RST} {DIM}|{RST} {INFO_B}ETA: {eta_str}{RST}"

# ============================================================
# PRINT ACCOUNT
# ============================================================
def print_account(idx, name, uid, acc_id, is_rare, score, api, password, region, thread_id):
    box_width = 52
    title = f"✅ GENERATE ACCOUNT #{idx}/{TARGET} SAVED!"
    padding = box_width - len(title) - 1
    if padding < 0: padding = 0

    fast_print(f"{BOX_GREEN}┌{'─' * box_width}┐{RST}")
    fast_print(f"{BOX_GREEN}│{RST} {OK_B}{title}{RST}{' ' * padding}{BOX_GREEN}│{RST}")
    fast_print(f"{BOX_GREEN}└{'─' * box_width}┘{RST}")

    fast_print(f"{LABEL_CYAN}UID:{RST}        {UID_CLR}{uid}{RST}")
    fast_print(f"{LABEL_CYAN}GAME UID:{RST}   {UID_CLR}{acc_id}{RST}")
    fast_print(f"{LABEL_CYAN}PASSWORD:{RST}   {PASS_CLR}{password}{RST}")
    fast_print(f"{LABEL_CYAN}NAME:{RST}       {NAME_CLR}{name}{RST}")
    fast_print(f"{LABEL_CYAN}REGION:{RST}     {REGION_CLR}{region.upper()}{RST}")
    fast_print(f"{LABEL_CYAN}ACTIVATED:{RST}  {OK_B}✅{RST}")
    fast_print(f"{LABEL_CYAN}THREAD:{RST}     {THREAD_CLR}{thread_id}{RST}")

    if TARGET > 0:
        elapsed = time.time() - START_TIME
        speed = COUNT_OK / elapsed if elapsed > 0 else 0
        eta = (TARGET - COUNT_OK) / speed if speed > 0 else 0
        bar = draw_progress_bar(COUNT_OK, TARGET, speed, eta)
        fast_print(bar)

    if is_rare:
        fast_print(f"{RARE_B}💎 RARE ACCOUNT! Score: {score}{RST}")

    fast_print("")

# ============================================================
# INSTALL / EXIT
# ============================================================
def install_requirements():
    for pkg in ['requests', 'pycryptodome', 'colorama', 'urllib3']:
        try:
            if pkg == 'pycryptodome': import Crypto
            else: importlib.import_module(pkg)
        except ImportError:
            try: subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '--quiet'])
            except: return False
    return True

def safe_exit(signum=None, frame=None):
    global EXIT
    EXIT = True
    STOP_EVENT.set()
    print(f"\n{ERR_B}👋 Thanks for using FREXY Generator!{RST}")
    sys.exit(0)

signal.signal(signal.SIGINT, safe_exit)
signal.signal(signal.SIGTERM, safe_exit)

# ============================================================
# DISPLAY
# ============================================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    _verify_credit()

    banner_lines = [
        "",
        f"{Fore.CYAN}{Style.BRIGHT}  ╔══════════════════════════════════════════════════════════╗{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}███████╗██████╗ ███████╗██╗  ██╗██╗   ██╗{RST}          {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}██╔════╝██╔══██╗██╔════╝╚██╗██╔╝╚██╗ ██╔╝{RST}          {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}█████╗  ██████╔╝█████╗   ╚███╔╝  ╚████╔╝ {RST}          {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}██╔══╝  ██╔══██╗██╔══╝   ██╔██╗   ╚██╔╝  {RST}          {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}██║     ██║  ██║███████╗██╔╝ ██╗   ██║   {RST}          {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   {RST}          {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ╠══════════════════════════════════════════════════════════╣{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTYELLOW_EX}{Style.BRIGHT}⚡ FREXY ULTRA FAST GENERATOR ⚡{RST}                         {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTGREEN_EX}Version : {RST}{Fore.WHITE}{Style.BRIGHT}OB55  {RST}{Fore.LIGHTGREEN_EX}|  Mode : {RST}{Fore.WHITE}{Style.BRIGHT}200 THREADS FAST{RST}   {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ╠══════════════════════════════════════════════════════════╣{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTRED_EX}{Style.BRIGHT}👑 Owner   :{RST} {Fore.LIGHTCYAN_EX}{Style.BRIGHT}@FREXY{RST}                                  {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTRED_EX}{Style.BRIGHT}📢 Channel :{RST} {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}@FREXY_OFC{RST}                             {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ║{RST}  {Fore.LIGHTRED_EX}{Style.BRIGHT}🏷️  Brand   :{RST} {Fore.LIGHTYELLOW_EX}{Style.BRIGHT}FREXY{RST}                                     {Fore.CYAN}{Style.BRIGHT}║{RST}",
        f"{Fore.CYAN}{Style.BRIGHT}  ╚══════════════════════════════════════════════════════════╝{RST}",
        "",
        f"{Fore.LIGHTBLACK_EX}{Style.DIM}  ══════════════════════════════════════════════════════════{RST}",
        "",
    ]
    for line in banner_lines:
        print(line)

def show_menu():
    print(f"{DIM}──────────────────────────────────────────{RST}")
    print(f"  {OK_B}[1]{RST} {VALUE_WHITE}Generate Accounts{RST}")
    print(f"  {INFO_B}[2]{RST} {VALUE_WHITE}View Saved{RST}")
    print(f"  {RARE_B}[3]{RST} {VALUE_WHITE}About{RST}")
    print(f"  {WARN_B}[4]{RST} {VALUE_WHITE}API Settings{RST}")
    print(f"  {ERR_B}[0]{RST} {VALUE_WHITE}Exit{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")

# ============================================================
# CREATE ACCOUNT (AUTHENTIC GARENA REGISTRATION)
# ============================================================
def create_account(region, account_name, password_prefix):
    try:
        rand_part = "".join(random.choices("0123456789ABCDEF", k=16))
        password = f"{password_prefix}_{rand_part}"
        url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
        payload = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
        body_json = json.dumps(payload, separators=(",", ":"))
        signature = hmac.new(HEX_KEY, body_json.encode("utf-8"), hashlib.sha256).hexdigest()

        dev = get_thread_device()
        headers = _merge_headers({
            "User-Agent": WAFBypass.get_ua(),
            "Connection": "Keep-Alive",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Authorization": f"Signature {signature}",
            "Content-Type": "application/json; charset=utf-8",
            "Host": "100067.connect.garena.com",
        }, device=dev)

        resp = request_retry('POST', url, tag="Register", headers=headers, data=body_json)
        if resp and resp.status_code == 200:
            res = resp.json()
            if "data" in res and "uid" in res["data"]:
                uid = res["data"]["uid"]
                return get_token(str(uid), password, region, account_name, password_prefix)
        return None
    except Exception:
        return None

create_account_direct = create_account

# ============================================================
# GET TOKEN
# ============================================================
def get_token(uid, password, region, account_name, password_prefix):
    try:
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        dev = get_thread_device()
        headers = _merge_headers({
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": WAFBypass.get_ua(),
        }, device=dev)
        body = {"uid": uid, "password": password, "response_type": "token",
                "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"}

        resp = request_retry('POST', url, tag="Token", headers=headers, data=body)

        if resp and resp.status_code == 200 and 'open_id' in resp.json():
            j = resp.json()
            open_id = j['open_id']
            access_token = j["access_token"]

            keystream = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
                         0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
            encoded = "".join(chr(ord(open_id[i]) ^ keystream[i % len(keystream)]) for i in range(len(open_id)))
            field = codecs.decode(
                ''.join(c if 32 <= ord(c) <= 126 else f'\\u{ord(c):04x}' for c in encoded),
                'unicode_escape'
            ).encode('latin1')
            return major_register(access_token, open_id, field, uid, password, region, account_name, password_prefix)
        return None
    except Exception:
        return None

# ============================================================
# MAJOR REGISTER
# ============================================================
def major_register(access_token, open_id, field, uid, password, region, account_name, password_prefix):
    try:
        url = ("https://loginbp.ppmainecoonghj.com/MajorRegister"
               if region.upper() not in ["ME","TH"]
               else "https://loginbp.common.ggbluefox.com/MajorRegister")
        name = generate_random_name(account_name)
        dev = get_thread_device()
        headers = _merge_headers({
            'Host': 'loginbp.ppmainecoonghj.com',
            'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Accept': '*/*',
            'Accept-Encoding': 'deflate, gzip',
            'Authorization': 'Bearer',
            'X-GA': 'v1 1',
            'ReleaseVersion': "OB55",
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Unity-Version': '2018.4.12f1',
        }, device=dev)
        lang = REGION_LANG.get(region.upper(), "en")
        reg_msg = {1: name, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 13: 1,
                   14: encode_f14(open_id), 15: lang, 16: 2, 20: "2.132.4", 21: 1, 22: FIELD_22}
        payload_bytes = build_proto(reg_msg)
        encrypted = aes_encrypt(payload_bytes.hex())

        request_retry('POST', url, tag="MajorRegister", headers=headers, data=encrypted)
        login_result = major_login(uid, password, access_token, open_id, region)
        account_id = login_result.get("account_id", "N/A")
        jwt_token  = login_result.get("jwt_token", "")
        if account_id != "N/A":
            if jwt_token and region.upper() != "BR":
                try: force_region_bind(region, jwt_token)
                except: pass
            return {
                "uid": uid, "password": password, "name": name, "region": region,
                "account_id": account_id, "jwt_token": jwt_token,
                "device_model": dev["model"], "device_id": dev["device_id"],
                "created_at": datetime.now().isoformat()
            }
        return None
    except Exception:
        return None

# ============================================================
# MAJOR LOGIN
# ============================================================
def major_login(uid, password, access_token, open_id, region):
    try:
        lang = REGION_LANG.get(region.upper(), "en")
        dev  = get_thread_device()

        gpu        = dev["gpu"]
        gpu_full   = f"{gpu}|OpenGL ES 3.2"
        model      = dev["model"]
        os_str     = dev["android_full"]
        operator   = dev["operator"]
        network    = dev["network"]
        device_uuid = dev["uuid"]
        cpu        = dev["cpu"]
        ip_addr    = FastIPSpoofer.get_ip()

        open_id_b      = open_id.encode()      if isinstance(open_id, str)      else open_id
        access_token_b = access_token.encode() if isinstance(access_token, str) else access_token

        payload_dict = {
            3:  datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            4:  b'free fire',
            5:  1,
            7:  "2.132.4",
            8:  os_str,
            9:  b'Handheld',
            10: operator,
            11: network,
            12: 1280,
            13: 720,
            14: b'240',
            15: cpu,
            16: random.choice([5951, 6000, 6100, 5500]),
            17: gpu,
            18: gpu_full,
            19: f'Google|{device_uuid}',
            20: ip_addr,
            21: lang,
            22: open_id_b,
            23: b'4',
            24: b'Handheld',
            25: model,
            26: lang,
            29: access_token_b,
            30: 1,
            41: operator,
            42: network,
            57: b'1ac4b80ecf0478a44203bf8fac6120f5',
            60: 30000, 61: 30000, 62: 2519, 63: 243,
            64: 32357, 65: 34308, 66: 32357, 67: 34308, 73: 1,
            74: b'/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/lib/arm',
            76: 2,
            77: b'428775ab8c8845bd341b5357ec61d15e|/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/base.apk',
            78: 2, 79: 1,
            81: b'32', 83: b'2019118525', 85: 3,
            86: b'OpenGLES3', 87: 4095, 88: 4,
            92: random.choice([19788, 20000, 21000]),
            93: b'android_max',
            94: b'KqsHT2gyPt7vUCc9SCjv2ioi3WEZSEL86ErvXB38suVVK/Z4IVt78ESl/r2S15C1pqu/j6ZmgFL7HbwoFiiVconX08ooKiisQffvEAPCo/C+Lahr',
            96: b'{"cur_rate":null,"support_etc2":true}',
            97: 1, 98: 1, 99: b'4', 100: b'4', 102: b'',
            104: 77149, 105: 1,
            106: b'https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462',
            107: b'c8e41b7a93f02d56e1a94c7b8203f5d1',
        }
        data = build_proto(payload_dict)

        url = ("https://loginbp.ppmainecoonghj.com/MajorLogin"
               if region.upper() not in ["ME", "TH"]
               else "https://loginbp.common.ggbluefox.com/MajorLogin")

        headers = _merge_headers({
            'Host': 'loginbp.ppmainecoonghj.com',
            'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Accept': '*/*', 'Accept-Encoding': 'deflate, gzip',
            'Authorization': 'Bearer', 'X-GA': 'v1 1',
            'X-Ga-Sv': '1789534056',
            'ReleaseVersion': "OB55",
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Unity-Version': '2018.4.12f1',
        }, device=dev)

        enc_hex = encrypt_api(data.hex())

        resp = request_retry('POST', url, tag="MajorLogin",
                             headers=headers, data=bytes.fromhex(enc_hex))

        if resp and resp.status_code == 200 and len(resp.text) > 10:
            jwt_start = resp.text.find("eyJ")
            if jwt_start != -1:
                jwt_token = resp.text[jwt_start:]
                second_dot = jwt_token.find(".", jwt_token.find(".") + 1)
                if second_dot != -1:
                    jwt_token = jwt_token[:second_dot + 44]
                    try:
                        parts = jwt_token.split('.')
                        if len(parts) >= 2:
                            pp = parts[1]
                            padding = 4 - len(pp) % 4
                            if padding != 4:
                                pp += '=' * padding
                            claims = json.loads(base64.urlsafe_b64decode(pp))
                            account_id = claims.get('account_id') or claims.get('external_id')
                            if account_id:
                                return {"account_id": str(account_id), "jwt_token": jwt_token}
                    except Exception:
                        pass
        return {"account_id": "N/A", "jwt_token": ""}
    except Exception:
        return {"account_id": "N/A", "jwt_token": ""}

# ============================================================
# FORCE REGION BIND
# ============================================================
def force_region_bind(region, jwt_token):
    try:
        url = ("https://loginbp.common.ggbluefox.com/ChooseRegion"
               if region.upper() in ["ME","TH"]
               else "https://loginbp.ppmainecoonghj.com/ChooseRegion")
        region_code = "RU" if region.upper() == "CIS" else region.upper()
        proto_data = build_proto({1: region_code})
        encrypted = encrypt_api(proto_data.hex())
        dev = get_thread_device()
        headers = _merge_headers({
            "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
            "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
            "X-Ga-Sv": "1789534056",
            "Authorization": f"Bearer {jwt_token}",
            "X-Ga": "v1 1", "Releaseversion": "OB55",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.12f1"
        }, device=dev)
        request_retry('POST', url, tag="ForceRegionBind",
                      data=bytes.fromhex(encrypted), headers=headers)
    except Exception:
        pass

# ============================================================
# API GET ONE
# ============================================================
def api_get_one(region, name_prefix, is_ghost):
    global API_ACTIVE
    api_id = random.choice(list(SERVER.keys())) if API_ACTIVE == 0 else API_ACTIVE
    if api_id not in SERVER: api_id = 1
    try:
        params = {"count": 1, "name": name_prefix, "password": "BDI8363868367VS8FF9BSO648GVEKI6", "region": region.upper()}
        resp = _session.get(SERVER[api_id], params=params, timeout=HTTP_TIMEOUT, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("accounts"):
                acc = data["accounts"][0]
                with LOCK: API_OK[api_id] += 1
                return {
                    "uid": acc.get("uid","N/A"),
                    "password": acc.get("password",""),
                    "name": acc.get("name", name_prefix),
                    "account_id": acc.get("account_id","N/A"),
                    "jwt_token": acc.get("jwt_token",""),
                    "region": "GHOST" if is_ghost else region.upper(),
                    "api_used": api_id,
                }
            with LOCK: API_FAIL[api_id] += 1
        else:
            with LOCK: API_FAIL[api_id] += 1
    except:
        with LOCK: API_FAIL[api_id] += 1
    return None

# ============================================================
# PROCESS ACCOUNT & INSTANT SAVE
# ============================================================
def process_account(acc, region, is_ghost, thread_id):
    global COUNT_OK, RARE_CNT, LAST_PROGRESS
    with LOCK:
        if COUNT_OK >= TARGET: return
        COUNT_OK += 1
        current = COUNT_OK
        done = COUNT_OK >= TARGET

    is_rare, score = check_rarity(acc.get("account_id",""))

    # Instant File Saving
    save_normal(acc, "GHOST" if is_ghost else region, is_ghost)
    save_jwt(acc, "GHOST" if is_ghost else region, is_ghost)
    if is_rare:
        with LOCK: RARE_CNT += 1
        save_rare(acc, "GHOST" if is_ghost else region, is_ghost, score)

    print_account(
        current,
        acc.get("name","N/A"),
        acc.get("uid","N/A"),
        acc.get("account_id","N/A"),
        is_rare,
        score,
        acc.get("api_used", 0),
        acc.get("password",""),
        "GHOST" if is_ghost else region,
        thread_id
    )

    if done: STOP_EVENT.set()

# ============================================================
# WORKER LOOP
# ============================================================
def worker(region, name, is_ghost, thread_id):
    fails = 0
    while not EXIT and not STOP_EVENT.is_set():
        with LOCK:
            if COUNT_OK >= TARGET: return

        acc = api_get_one(region, name, is_ghost)

        if not acc:
            try:
                acc = create_account_direct(region, name, "FREXY")
            except:
                acc = None

        if acc and acc.get("account_id","N/A") != "N/A":
            fails = 0
            process_account(acc, region, is_ghost, thread_id)
        else:
            fails += 1
            if fails > 5:
                time.sleep(0.01)
                fails = 0

# ============================================================
# GENERATE FLOW
# ============================================================
def generate_flow():
    _verify_credit()
    global COUNT_OK, RARE_CNT, LAST_PROGRESS, THRESHOLD, API_OK, API_FAIL, EXIT, TARGET, START_TIME
    EXIT = False
    STOP_EVENT.clear()
    clear_screen(); show_banner()

    print(f"\n{INFO_B}  SELECT REGION{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    for n, label in [("1","ME"),("2","IND"),("3","ID"),("4","VN"),("5","TH"),
                     ("6","BD"),("7","PK"),("8","TW"),("9","CIS"),("10","SAC"),("11","👻 GHOST")]:
        print(f"  {OK_B}[{n}]{RST} {VALUE_WHITE}{label}{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")

    selected = None; is_ghost = False
    while True:
        try:
            c = input(f"{INFO_B}➤ Region Default [India]: {RST}").strip() or "2"
            rmap = {"1":"ME","2":"IND","3":"ID","4":"VN","5":"TH","6":"BD","7":"PK","8":"TW","9":"CIS","10":"SAC"}
            if c == "11": is_ghost = True; selected = "BD"; break
            if c in rmap: selected = rmap[c]; break
            print(f"{ERR_B}❌ Invalid{RST}")
        except KeyboardInterrupt: safe_exit()

    try:
        name = input(f"{INFO_B}➤ Name prefix Default [FREXY]: {RST}").strip() or "FREXY"
        ri = input(f"{INFO_B}➤ Rarity score Default [6]: {RST}").strip()
        THRESHOLD = 6 if not ri else max(0, int(ri))
        total = int(input(f"{INFO_B}➤ Total accounts: {RST}"))
        th = int(input(f"{INFO_B}➤ Threads (10-{MAX_WORKERS}) [{DEFAULT_WORKERS}]: {RST}").strip() or str(DEFAULT_WORKERS))
        th = max(1, min(th, MAX_WORKERS))
    except (ValueError, KeyboardInterrupt):
        return

    API_OK = {i: 0 for i in range(1, 39)}
    API_FAIL = {i: 0 for i in range(1, 39)}
    COUNT_OK = 0; RARE_CNT = 0; LAST_PROGRESS = 0; TARGET = total
    START_TIME = time.time()

    clear_screen(); show_banner()
    print(f"{OK_B}  STARTING FREXY ULTRA-FAST GENERATION{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    print(f"  {LABEL_CYAN}Name    :{RST} {VALUE_WHITE}{name}{RST}")
    print(f"  {LABEL_CYAN}Region  :{RST} {REGION_CLR}{'GHOST' if is_ghost else selected}{RST}")
    print(f"  {LABEL_CYAN}Target  :{RST} {VALUE_WHITE}{total}{RST}")
    print(f"  {LABEL_CYAN}Threads :{RST} {THREAD_CLR}{th}{RST}")
    print(f"  {LABEL_CYAN}Score   :{RST} {RARE_B}{THRESHOLD}{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}\n")

    start = time.time()
    actual = min(th, total)

    threads = []
    for i in range(actual):
        t = threading.Thread(target=worker, args=(selected, name, is_ghost, i+1), daemon=True)
        t.start()
        threads.append(t)

    try:
        while not STOP_EVENT.is_set():
            with LOCK:
                if COUNT_OK >= TARGET: break
            time.sleep(0.05)
    except KeyboardInterrupt:
        print(f"\n{WARN_B}⚠ Stopping...{RST}")

    EXIT = True
    STOP_EVENT.set()

    for t in threads:
        t.join(timeout=0.1)

    elapsed = time.time() - start
    speed = COUNT_OK / elapsed if elapsed > 0 else 0

    print(f"\n{DIM}──────────────────────────────────────────{RST}")
    if COUNT_OK >= total:
        print(f"{OK_B}  ✅ DONE — {COUNT_OK}/{total} accounts{RST}")
    else:
        print(f"{WARN_B}  ⚠ INCOMPLETE — {COUNT_OK}/{total} accounts{RST}")
    print(f"{INFO_B}  ⏱  {elapsed:.2f}s  |  ⚡ {speed:.1f} acc/s{RST}")
    if RARE_CNT > 0:
        print(f"{RARE_B}  💎 Rare: {RARE_CNT}{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}\n")
    input(f"{MENU}▶ Enter...{RST}")

# ============================================================
# VIEW / ABOUT / API
# ============================================================
def view_saved():
    clear_screen(); show_banner()
    print(f"{INFO_B}  SAVED ACCOUNTS{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    if os.path.exists(ACCOUNTS_FOLDER):
        for f in os.listdir(ACCOUNTS_FOLDER):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(ACCOUNTS_FOLDER, f), encoding="utf-8") as fh:
                        data = json.load(fh)
                        n = len(data) if isinstance(data, list) else 0
                    print(f"   {VALUE_WHITE}{f}: {OK_B}{n}{RST}")
                except: pass
    print(f"{DIM}──────────────────────────────────────────{RST}")
    input(f"{MENU}▶ Enter...{RST}")

def about():
    _verify_credit()
    clear_screen(); show_banner()
    print(f"{RARE_B}  ABOUT FREXY GENERATOR{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    print(f"  {LABEL_CYAN}Version  :{RST} {VALUE_WHITE}OB55 ULTRA FAST{RST}")
    print(f"  {LABEL_CYAN}Brand    :{RST} {RARE_B}FREXY{RST}")
    print(f"  {LABEL_CYAN}Owner    :{RST} {INFO_B}@FREXY{RST}")
    print(f"  {LABEL_CYAN}Channel  :{RST} {WARN_B}@FREXY_OFC{RST}")
    print(f"  {LABEL_CYAN}Engine   :{RST} {VALUE_WHITE}Target-Locked Worker Pool{RST}")
    print(f"  {LABEL_CYAN}Workers  :{RST} {VALUE_WHITE}default 200, max {MAX_WORKERS}{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    input(f"{MENU}▶ Enter...{RST}")

def api_settings():
    global API_ACTIVE
    clear_screen(); show_banner()
    mode = "RANDOM" if API_ACTIVE == 0 else f"API {API_ACTIVE}"
    print(f"{WARN_B}  API SETTINGS — FREXY{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    print(f"  Current: {OK_B}{mode}{RST}")
    print(f"{DIM}──────────────────────────────────────────{RST}")
    try:
        c = input(f"{MENU}➤ API number [0=random, 99=back]: {RST}").strip()
        if c == "99": return
        if c == "0": API_ACTIVE = 0
        elif c.isdigit() and int(c) in SERVER: API_ACTIVE = int(c)
    except KeyboardInterrupt: return

# ============================================================
# MAIN MENU
# ============================================================
def main():
    _verify_credit()
    while True:
        try:
            _verify_credit()
            clear_screen(); show_banner(); show_menu()
            c = input(f"{INFO_B}➤ Select: {RST}").strip()
            if c == "1": generate_flow()
            elif c == "2": view_saved()
            elif c == "3": about()
            elif c == "4": api_settings()
            elif c == "0": safe_exit()
        except KeyboardInterrupt:
            safe_exit()

if __name__ == "__main__":
    try:
        if install_requirements():
            main()
    except KeyboardInterrupt:
        safe_exit()
