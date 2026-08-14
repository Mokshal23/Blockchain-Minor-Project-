"""
=============================================================================
Dual-Engine Crowdfunding Platform - Admin Tamper Script (CLI Tool)
=============================================================================
This script allows an admin to tamper with historical blocks in the Python
SHA-256 SQLite database and recompute downstream hashes.

Run this script directly from the terminal:
    python backend/tamper.py
=============================================================================
"""

import sqlite3
import json
import hashlib
import time

DB_FILE = "database.db"

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data, sort_keys=True)}{self.previous_hash}"
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

def run_tamper_demo():
    print("=" * 70)
    print("PYTHON ENGINE ADMIN TAMPER DEMO")
    print("=" * 70)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch blocks
    cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
    rows = cursor.fetchall()

    if len(rows) < 2:
        print("[!] Need at least 2 blocks in database to run tamper script.")
        print("[!] Please run app.py, create a campaign, and add a contribution first.")
        conn.close()
        return

    print(f"Total blocks currently in chain: {len(rows)}")
    target_block = dict(rows[1])
    print(f"\nTargeting Block #{target_block['block_index']} for tampering...")
    print(f"Original Hash: {target_block['hash']}")
    
    target_data = json.loads(target_block["data_json"])
    print(f"Original Data: {target_data}")

    # Alter data
    target_data["tampered_by"] = "Admin CLI Tamper Script"
    if "amount" in target_data:
        target_data["amount"] = target_data["amount"] * 10
        print(f"--> TAMPERED: Multiplied contribution amount by 10x to {target_data['amount']}")
    else:
        target_data["tampered_note"] = "Altered title/description secretly"

    # Re-calculate hashes for target block and all downstream blocks
    prev_hash = target_block["previous_hash"]

    for i in range(1, len(rows)):
        r = dict(rows[i])
        b_data = target_data if i == 1 else json.loads(r["data_json"])
        
        # Instantiate block and compute new hash
        new_block = Block(r["block_index"], r["timestamp"], b_data, prev_hash)
        
        cursor.execute("""
            UPDATE blocks
            SET data_json = ?, previous_hash = ?, hash = ?
            WHERE block_index = ?
        """, (json.dumps(b_data), prev_hash, new_block.hash, r["block_index"]))

        prev_hash = new_block.hash

    conn.commit()
    conn.close()

    print("\n[+] Tampering completed! All downstream hashes recalculated.")
    print("=" * 70)
    print("THESIS LESSON: The chain still passes hash-validation checks because")
    print("the central admin holds the database write permissions.")
    print("This demonstrates why Equity & Lending models must use Solidity smart contracts!")
    print("=" * 70)

if __name__ == "__main__":
    run_tamper_demo()
