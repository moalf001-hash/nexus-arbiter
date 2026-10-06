from pathlib import Path

file_path = Path("scripts/simulate_autonomous_agents.py")
if not file_path.exists():
    print(f"[-] Error: File {file_path} not found.")
    exit(1)

content = file_path.read_text(encoding="utf-8")

old_code = "settle_result = seller.sdk.submit_and_settle(\n        session_id=session_id,"
new_code = """price_commitment = buyer.sdk.create_price_commitment(
        session_id=session_id,
        agreed_amount_usdc=agreed_final_price,
        seller_agent_id=getattr(seller, "agent_id", seller.sdk.agent_id)
    )

    settle_result = seller.sdk.submit_and_settle(
        session_id=session_id,
        price_commitment=price_commitment,"""

if old_code in content:
    updated_content = content.replace(old_code, new_code, 1)
    file_path.write_text(updated_content, encoding="utf-8")
    print("[+] SUCCESS: simulate_autonomous_agents.py has been updated with PriceCommitment!")
elif "price_commitment=price_commitment" in content:
    print("[*] Notice: File is already patched with PriceCommitment.")
else:
    print("[-] Error: Target code block not found in file.")