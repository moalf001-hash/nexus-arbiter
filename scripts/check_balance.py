import sys
from web3 import Web3

WALLET_ADDRESS = "0x082b38aeA5D1bB7FEF3C16818f2E76809f2bA685"

# مزودات RPC سريعة ومجانية
NETWORKS = {
    "Base Sepolia (L2)": [
        "https://sepolia.base.org",
        "https://base-sepolia-rpc.publicnode.com"
    ],
    "Ethereum Sepolia (L1)": [
        "https://ethereum-sepolia-rpc.publicnode.com",
        "https://1rpc.io/sepolia",
        "https://rpc.ankr.com/eth_sepolia"
    ]
}

def get_active_connection(urls):
    for url in urls:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 7}))
            if w3.is_connected():
                return w3, url
        except Exception:
            continue
    return None, None

def run_check():
    print("=========================================================")
    print("           Multi-Network Balance Checker                 ")
    print("=========================================================")
    print(f"[*] Wallet Address: {WALLET_ADDRESS}\n")

    found_balance = False
    active_network = None

    for net_name, urls in NETWORKS.items():
        w3, active_url = get_active_connection(urls)
        if not w3:
            print(f"[-] {net_name:<22}: All RPC endpoints failed")
            continue

        try:
            checksum_addr = Web3.to_checksum_address(WALLET_ADDRESS)
            balance_wei = w3.eth.get_balance(checksum_addr)
            balance_eth = w3.from_wei(balance_wei, "ether")
            print(f"[+] {net_name:<22}: {balance_eth:.6f} ETH")

            if balance_eth > 0:
                found_balance = True
                active_network = net_name
        except Exception as e:
            print(f"[-] {net_name:<22}: Error reading balance ({e})")

    print("\n=========================================================")
    if found_balance:
        print(f"[+] SUCCESS: Funds detected on {active_network}!")
    else:
        print("[!] NOTICE: Balance is still 0.000000 ETH.")
        print("    If you just mined on pk910.de:")
        print("    1. Return to the browser tab.")
        print("    2. Click the 'Claim Rewards' button.")
        print("    3. Complete the queue until you see a green Transaction Hash.")
    print("=========================================================")

if __name__ == "__main__":
    run_check()