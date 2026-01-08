import httpx
import time
import asyncio
import random
import os
from datetime import datetime
from eth_account import Account
from loguru import logger
from colorama import Fore, Style, init
import pyfiglet

# Initialize Colorama
init(autoreset=True)

# Logger Configuration
logger.remove()
logger.add(lambda msg: print(msg, end=""), format="{message}")

class CryptoLogger:
    @staticmethod
    def _format(level, msg, emoji, context):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ctx = f"[{context:<20}] " if context else ""
        colors = {"INFO": Fore.GREEN, "WARN": Fore.YELLOW, "ERROR": Fore.RED, "DEBUG": Fore.BLUE}
        color = colors.get(level, Fore.WHITE)
        return f"[ {Fore.LIGHTBLACK_EX}{timestamp}{Style.RESET_ALL} ] {emoji}{color}{level}{Style.RESET_ALL} {Fore.WHITE}{ctx}{msg}"

    def info(self, msg, context=None, emoji="ℹ️  "):
        logger.info(self._format("INFO", msg, emoji, context))

    def warn(self, msg, context=None, emoji="⚠️  "):
        logger.warning(self._format("WARN", msg, emoji, context))

    def error(self, msg, context=None, emoji="❌ "):
        logger.error(self._format("ERROR", msg, emoji, context))

log = CryptoLogger()

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
]

def get_headers():
    return {
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://www.testnet.hotstuff.trade',
        'referer': 'https://www.testnet.hotstuff.trade/',
        'user-agent': random.choice(USER_AGENTS)
    }

async def request_with_retry(client, method, url, payload=None, context=None):
    for i in range(3):
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=get_headers())
            else:
                response = await client.post(url, json=payload, headers=get_headers())
            return response
        except Exception as e:
            log.error(f"Request failed: {str(e)} (Attempt {i+1}/3)", context)
            await asyncio.sleep(2)
    return None

def mask_address(address):
    return f"{address[:6]}******{address[-6:]}" if address else "N/A"

async def execute_check_in(client, address, context):
    url = 'https://testnet-api.hotstuff.trade/info'
    payload = {"method": "claimGM", "params": {"user": address}}
    
    log.info("Executing check-in...", context, "🛎️ ")
    response = await request_with_retry(client, "POST", url, payload, context)
    
    if response:
        if response.status_code == 500:
            log.warn("Already checked in today", context)
            return False
        elif response.status_code == 200:
            data = response.json()
            log.info(f"Check-In Successful! GM Count: {data.get('gm_count')}", context, "✅ ")
            return True
    return False

async def claim_faucet(client, address, collateral_id, context):
    url = 'https://testnet-api.hotstuff.trade/faucet'
    token_name = "USDT" if collateral_id == 2 else "USDC"
    payload = {"collateral_id": collateral_id, "address": address, "amount": "1000", "is_spot": collateral_id == 2}
    
    log.info(f"Claiming {token_name} faucet...", context, "💰 ")
    response = await request_with_retry(client, "POST", url, payload, context)
    
    if response:
        data = response.json()
        if response.status_code == 400 and "insufficient" in str(data):
            log.warn(f"Insufficient balance for {token_name}", context)
        elif data.get('status') == 'success':
            log.info(f"{token_name} Faucet Claimed! Tx: {data['tx_hash'][:10]}...", context, "✅ ")
            return True
    return False

async def process_account(pk, index, total, proxy=None):
    context = f"Account {index + 1}/{total}"
    try:
        account = Account.from_key(pk)
        address = account.address
    except Exception:
        log.error("Invalid Private Key", context)
        return

    log.info(f"Starting: {mask_address(address)}", context, "🚀 ")

    proxies = {"http://": proxy, "https://": proxy} if proxy else None
    
    async with httpx.AsyncClient(proxies=proxies, timeout=60.0) as client:
        # Get IP info
        ip_res = await request_with_retry(client, "GET", "https://api.ipify.org?format=json", context=context)
        ip = ip_res.json().get('ip', 'Unknown') if ip_res else "Unknown"
        log.info(f"IP: {ip}", context, "📍 ")

        await execute_check_in(client, address, context)
        await asyncio.sleep(2)
        
        await claim_faucet(client, address, 2, context) # USDT
        await asyncio.sleep(2)
        await claim_faucet(client, address, 1, context) # USDC
        
        log.info("Completed account processing", context, "🎉 ")

async def run_cycle(use_proxy, proxies):
    if not os.path.exists('pk.txt'):
        log.error("pk.txt not found!")
        return

    with open('pk.txt', 'r') as f:
        pks = [line.strip() for line in f if line.strip()]

    for i, pk in enumerate(pks):
        proxy = proxies[i % len(proxies)] if use_proxy and proxies else None
        await process_account(pk, i, len(pks), proxy)
        if i < len(pks) - 1:
            await asyncio.sleep(random.randint(5, 10))

async def main():
    print(Fore.CYAN + pyfiglet.figlet_format("NT EXHAUST", font="slant"))
    print(Fore.YELLOW + "=== Telegram: @NTExhaust | HotStuff Auto Bot ===\n")

    use_proxy = input("🔌 Do You Want to Use Proxy? (y/n): ").lower() == 'y'
    proxies = []
    if use_proxy and os.path.exists('proxy.txt'):
        with open('proxy.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]

    while True:
        await run_cycle(use_proxy, proxies)
        log.info("Cycle completed. Waiting 24 hours...", emoji="🔄 ")
        await asyncio.sleep(86400)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
