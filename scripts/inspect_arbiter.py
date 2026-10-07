import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import sqlite3
from nexus_arbiter.crypto.signatures import verify_signature

def run_inspector():
    db_path = "nexus_arbiter.db"
    if not Path(db_path).exists():
        print(f"[-] Database file not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=================================================================")
    print("      NexusArbiter Protocol Audit & Financial Ledger (Admin)     ")
    print("=================================================================\n")

    # 1. Platform Financial Ledger
    cursor.execute("""
        SELECT 
            COUNT(*) as total_deals,
            COALESCE(SUM(total_usdc), 0.0) as total_volume,
            COALESCE(SUM(platform_fee_usdc), 0.0) as total_fees,
            COALESCE(SUM(seller_net_usdc), 0.0) as total_payouts
        FROM invoices
    """)
    stats = cursor.fetchone()

    print("[1] Platform Financial Metrics:")
    print(f"    - Total Settled Deals     : {stats['total_deals']}")
    print(f"    - Gross Volume (USDC)     : ${stats['total_volume']:.2f}")
    print(f"    - Platform Revenue (1.5%) : ${stats['total_fees']:.2f}")
    print(f"    - Total Seller Net Payout : ${stats['total_payouts']:.2f}\n")

    # 2. Recent Invoices
    print("[2] Recent Settled Invoices:")
    cursor.execute("""
        SELECT invoice_id, session_id, total_usdc, platform_fee_usdc, invoice_hash, created_at 
        FROM invoices 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    invoices = cursor.fetchall()
    
    for idx, inv in enumerate(invoices, 1):
        print(f"    [{idx}] Invoice ID : {inv['invoice_id']}")
        print(f"        - Amount    : ${inv['total_usdc']:.2f} USDC (Platform Fee: ${inv['platform_fee_usdc']:.2f})")
        print(f"        - Session   : {inv['session_id']}")
        print(f"        - Hash      : {inv['invoice_hash'][:32]}...")
        print(f"        - Timestamp : {inv['created_at']}")

    # 3. Cryptographic Tamper-Proof Audit
    print("\n[3] Cryptographic Integrity Audit (Ed25519 Signatures):")
    cursor.execute("SELECT session_id, sequence_id, sender_agent_id, action, payload_json, public_key_hex, signature_hex FROM messages")
    messages = cursor.fetchall()

    valid_sigs = 0
    corrupted_sigs = 0

    for msg in messages:
        payload_data = json.loads(msg["payload_json"])
        envelope = {
            "session_id": msg["session_id"],
            "sequence_id": msg["sequence_id"],
            "sender_agent_id": msg["sender_agent_id"],
            "action": msg["action"],
            "payload": payload_data
        }
        digest = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        
        is_valid = verify_signature(
            public_key_hex=msg["public_key_hex"],
            signature_hex=msg["signature_hex"],
            data=digest
        )

        if is_valid:
            valid_sigs += 1
        else:
            corrupted_sigs += 1

    print(f"    - Messages Audited         : {len(messages)}")
    print(f"    - Valid Ed25519 Signatures : {valid_sigs}")
    
    print("\n=================================================================")
    if corrupted_sigs == 0:
        print("[+] Protocol State: 100% Cryptographically Intact. Zero Tampering.")
    else:
        print(f"[!] Security Alert: {corrupted_sigs} signature(s) failed verification!")
    print("=================================================================")

    conn.close()

if __name__ == "__main__":
    run_inspector()