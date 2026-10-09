import sqlite3
import json
import os
from typing import Optional, Dict, Any
from src.auth.keys import hash_api_key

DB_PATH = os.path.join("nexus_arbiter.db")

def get_connection():
    """Hardened connection with WAL mode and busy timeout to avoid database lock errors."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    return conn

def init_db():
    """Initialize cryptographic, ledger, and B2B SaaS tenancy database schemas."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Sessions ledger table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                expected_sequence_id INTEGER NOT NULL,
                last_sender_id TEXT,
                buyer_id TEXT,
                seller_id TEXT,
                agreed_payload_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Messages and cryptographic signatures audit table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sequence_id INTEGER NOT NULL,
                sender_agent_id TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                public_key_hex TEXT NOT NULL,
                signature_hex TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)

        # Tax invoices and escrow settlement ledger table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                total_usdc REAL NOT NULL,
                platform_fee_usdc REAL NOT NULL,
                seller_net_usdc REAL NOT NULL,
                deliverable_hash TEXT NOT NULL,
                invoice_hash TEXT NOT NULL,
                blockchain_calldata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # B2B SaaS tenants and enterprise subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'free',
                monthly_limit INTEGER NOT NULL DEFAULT 100,
                current_usage INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Hashed API keys storage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash TEXT PRIMARY KEY,
                prefix TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            )
        """)
        conn.commit()

class StorageManager:
    @staticmethod
    def save_session_state(session_id: str, status: str, next_seq: int, last_sender: str, buyer: str, seller: str, agreed_payload: Optional[dict] = None):
        with get_connection() as conn:
            cursor = conn.cursor()
            payload_str = json.dumps(agreed_payload) if agreed_payload else None
            cursor.execute("""
                INSERT INTO sessions (session_id, status, expected_sequence_id, last_sender_id, buyer_id, seller_id, agreed_payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    status=excluded.status,
                    expected_sequence_id=excluded.expected_sequence_id,
                    last_sender_id=excluded.last_sender_id,
                    buyer_id=excluded.buyer_id,
                    seller_id=excluded.seller_id,
                    agreed_payload_json=excluded.agreed_payload_json,
                    updated_at=CURRENT_TIMESTAMP
            """, (session_id, status, next_seq, last_sender, buyer, seller, payload_str))
            conn.commit()

    @staticmethod
    def log_message(session_id: str, sequence_id: int, sender_agent_id: str, action: str, payload_dict: dict, pubkey_hex: str, sig_hex: str):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (session_id, sequence_id, sender_agent_id, action, payload_json, public_key_hex, signature_hex)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, sequence_id, sender_agent_id, action, json.dumps(payload_dict), pubkey_hex, sig_hex))
            conn.commit()

    @staticmethod
    def save_invoice_record(invoice_id: str, session_id: str, buyer: str, seller: str, total: float, fee: float, net: float, deliv_hash: str, inv_hash: str, calldata: str):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO invoices (invoice_id, session_id, buyer_id, seller_id, total_usdc, platform_fee_usdc, seller_net_usdc, deliverable_hash, invoice_hash, blockchain_calldata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_id, session_id, buyer, seller, total, fee, net, deliv_hash, inv_hash, calldata))
            conn.commit()

    # ==========================================
    # B2B SaaS Tenancy & API Key Management
    # ==========================================

    @staticmethod
    def create_tenant(tenant_id: str, name: str, tier: str = "free", monthly_limit: int = 100):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tenants (tenant_id, name, tier, monthly_limit, current_usage)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(tenant_id) DO NOTHING
            """, (tenant_id, name, tier, monthly_limit))
            conn.commit()

    @staticmethod
    def save_api_key(key_hash: str, prefix: str, tenant_id: str):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO api_keys (key_hash, prefix, tenant_id, is_active)
                VALUES (?, ?, ?, 1)
            """, (key_hash, prefix, tenant_id))
            conn.commit()

    @staticmethod
    def authenticate_api_key(raw_key: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate API key and return tenant details if active and within quota.
        """
        if not raw_key:
            return None
        khash = hash_api_key(raw_key)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.tenant_id, t.name, t.tier, t.monthly_limit, t.current_usage, k.is_active
                FROM api_keys k
                JOIN tenants t ON k.tenant_id = t.tenant_id
                WHERE k.key_hash = ?
            """, (khash,))
            row = cursor.fetchone()
            if row and row["is_active"] == 1:
                return dict(row)
            return None

    @staticmethod
    def increment_and_check_quota(tenant_id: str) -> bool:
        """
        Atomic transaction: increments usage counter and enforces monthly quota to prevent race conditions.
        Returns True if the request is within quota, False if exceeded.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            # Atomic quota check and increment
            cursor.execute("""
                UPDATE tenants
                SET current_usage = current_usage + 1
                WHERE tenant_id = ? AND current_usage < monthly_limit
            """, (tenant_id,))
            conn.commit()
            return cursor.rowcount > 0

init_db()