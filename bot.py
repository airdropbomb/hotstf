import httpx
import asyncio
import random
import os
from datetime import datetime
from eth_account import Account
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import pyfiglet

# Console initialization for beautiful output
console = Console()

class StyledLogger:
    def timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def info(self, msg, context="System"):
        console.print(f"[bold grey37][{self.timestamp()}][/] [bold green]INFO[/]    [cyan][{context:<12}][/] {msg}")

    def warn(self, msg, context="System"):
        console.print(f"[bold grey37][{self.timestamp()}][/] [bold yellow]WARN[/]    [cyan][{context:<12}][/] {msg}")

    def error(self, msg, context="System"):
        console.print(f"[bold grey37][{self.timestamp()}][/] [bold red]ERROR[/]   [cyan][{context:<12}][/] {msg}")

log = StyledLogger()

def get_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
    ]
    return {
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://www.testnet.hotstuff.trade',
        'referer': 'https://www.testnet.hotstuff.trade/',
        'user-agent': random.choice(user_agents)
    }

async def process_account(pk, index, total, proxy=None):
    context = f"Acc {index + 1}/{total}"
    try:
        account = Account.from_key(pk)
        address = account.address
        masked = f"{address[:6]}...{address[-4:]}"
    except Exception as e:
        log.error(f"Invalid Private Key: {str(e)}", context)
        return

    # Account Display Header
    console.print(Panel(f"🚀 Processing: [bold yellow]{masked}[/]", border_style="magenta", expand=False))

    proxies = {"http://": proxy, "https://": proxy} if proxy else None
    
    async with httpx.AsyncClient(proxies=proxies, timeout=30.0, verify=False) as client:
        # 1. Check-in (GM Claim)
        log.info("[white]Executing check-in...[/]", context)
        try:
            res = await client.post(
                'https://testnet-api.hotstuff.trade/info', 
                json={"method": "claimGM", "params": {"user": address}},
                headers=get_headers()
            )
            if res.status_code == 200:
                log.info(f"[bold green]Check-In Success! GM: {res.json().get('gm_count')}[/]", context)
            else:
                log.warn("[yellow]Already checked in today[/]", context)
        except Exception:
            log.error("Check-in request failed", context)

        await asyncio.sleep(2)

        # 2. Faucet Claims (USDT & USDC)
        for cid, name in [(2, "USDT"), (1, "USDC")]:
            log.info(f"[white]Claiming {name} faucet...[/]", context)
            try:
                f_res = await client.post(
                    'https://testnet-api.hotstuff.target/faucet',
                    json={"collateral_id": cid, "address": address, "amount": "1000", "is_spot": cid==2},
                    headers=get_headers()
                )
                data = f_res.json()
                if data.get('status') == 'success':
                    log.info(f"[bold spring_green3]{name} Claimed Successfully! ✅[/]", context)
                else:
                    log.warn(f"{name} skip (Already claimed or limit)", context)
            except Exception:
                log.error(f"{name} faucet request failed", context)
            await asyncio.sleep(2)

    console.print("[dim magenta]" + "━"*60 + "[/]\n")

async def main():
    # Clear screen for fresh start
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Show Banner
    banner_text = pyfiglet.figlet_format("ADB NODE", font="slant")
    console.print(Panel(Text(banner_text, style="bold cyan"), subtitle="[bold yellow]HotStuff Auto Bot v2.0", border_style="blue"))
    console.print("[bold magenta]Channel: @airdropbombnode[/] | [bold green]Status: Active[/]\n")

    # Configuration
    use_proxy = console.input("[bold cyan]🔌 Use Proxy? (y/n): [/]").lower() == 'y'
    proxies = []
    if use_proxy:
        if os.path.exists('proxy.txt'):
            with open('proxy.txt', 'r') as f:
                proxies = [l.strip() for l in f if l.strip()]
            log.info(f"Loaded {len(proxies)} proxies.")
        else:
            log.warn("proxy.txt not found! Proceeding without proxy.")
            use_proxy = False

    while True:
        if not os.path.exists('pk.txt'):
            log.error("pk.txt not found! Please create it and add private keys.")
            break
        
        with open('pk.txt', 'r') as f:
            pks = [l.strip() for l in f if l.strip()]

        if not pks:
            log.error("No private keys found in pk.txt")
            break

        for i, pk in enumerate(pks):
            p = proxies[i % len(proxies)] if use_proxy and proxies else None
            await process_account(pk, i, len(pks), p)
            # Small delay between accounts
            if i < len(pks) - 1:
                delay = random.randint(5, 10)
                log.info(f"Waiting {delay}s for next account...", "Break")
                await asyncio.sleep(delay)

        log.info("[bold reverse yellow] All accounts processed. Waiting 24 hours for next cycle... [/]", "Cycle")
        await asyncio.sleep(86400)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold red]Bot stopped by user.[/]")
