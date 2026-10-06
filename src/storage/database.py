import sqlite3
import json
import os
from typing import Optional

DB_PATH = os.path.join("nexus_arbiter.db")

def get_connection():
    """اتصال محصن بوضع WAL ومهلة انتظار لمنع أخطاء قفل الجداول."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    return conn

def init_db():
    """تهيئة الجداول المشفرة والمالية لقاعدة البيانات."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # جدول الجلسات
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

        # جدول الرسائل والتواقيع الرقمية
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

        # جدول الفواتير الضريبية والمعاملات المالية
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

init_db()