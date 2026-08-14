"""
=============================================================================
Dual-Engine Crowdfunding Platform - Python Engine Backend (Flask + SQLite)
=============================================================================
This file implements the Python Engine for Donation & Reward funding models.
It uses a custom SHA-256 Hash-Chained Blockchain module and SQLite database.

Key Purpose for Project Thesis:
This engine demonstrates a CENTRALIZED pseudo-blockchain where a single admin
controls the database. Although blocks are hash-chained using SHA-256, an admin
can modify historical data and re-calculate hashes, proving that central control
lacks real immutability.
=============================================================================
"""

import os
import hashlib
import json
import sqlite3
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

# Initialize Flask Application
app = Flask(__name__)
# Enable CORS so our frontend HTML/JS can communicate with this API
CORS(app)

# Place SQLite database in /tmp when running on Vercel read-only filesystem
DB_FILE = "/tmp/database.db" if os.environ.get("VERCEL") else "database.db"


# =============================================================================
# 1. DATABASE INITIALIZATION
# =============================================================================

def get_db():
    """Helper function to open a connection to our SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects
    return conn

def init_db():
    """Creates SQLite tables if they do not exist already."""
    conn = get_db()
    cursor = conn.cursor()

    # Table for Campaigns (Donation & Reward models)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            funding_type TEXT NOT NULL,  -- 'Donation' or 'Reward'
            engine TEXT NOT NULL DEFAULT 'Python',
            funding_goal REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            deadline TEXT NOT NULL,
            is_closed INTEGER DEFAULT 0
        )
    """)

    # Table for Milestones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            target_percent REAL NOT NULL,
            status TEXT DEFAULT 'PENDING',  -- 'PENDING', 'APPROVED', 'REJECTED'
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        )
    """)

    # Table for Contributions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            contributor_name TEXT NOT NULL,
            amount REAL NOT NULL,
            reward_tier TEXT DEFAULT 'None',
            timestamp TEXT NOT NULL,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        )
    """)

    # Table for Python SHA-256 Blockchain Ledger
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            block_index INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            data_json TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        )
    """)

    conn.commit()

    # Create Genesis Block if blockchain table is empty
    cursor.execute("SELECT COUNT(*) as count FROM blocks")
    if cursor.fetchone()["count"] == 0:
        create_genesis_block(conn)

    conn.close()

# =============================================================================
# 2. SHA-256 BLOCKCHAIN MODULE
# =============================================================================

class Block:
    """
    Represents a single block in our Python SHA-256 ledger.
    Contains: index, timestamp, transaction data, previous_hash, and current block hash.
    """
    def __init__(self, index, timestamp, data, previous_hash, block_hash=None):
        self.index = index
        self.timestamp = timestamp
        self.data = data  # Dictionary containing transaction info
        self.previous_hash = previous_hash
        self.hash = block_hash or self.calculate_hash()

    def calculate_hash(self):
        """Calculates SHA-256 hash of the block contents."""
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data, sort_keys=True)}{self.previous_hash}"
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

def create_genesis_block(conn):
    """Creates the very first block (Genesis Block) in the ledger."""
    genesis_data = {"message": "Genesis Block - Dual Engine Python Ledger Initialized"}
    timestamp = str(int(time.time()))
    genesis_block = Block(0, timestamp, genesis_data, "0" * 64)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO blocks (block_index, timestamp, data_json, previous_hash, hash)
        VALUES (?, ?, ?, ?, ?)
    """, (genesis_block.index, genesis_block.timestamp, json.dumps(genesis_block.data), genesis_block.previous_hash, genesis_block.hash))
    conn.commit()

def add_block_to_ledger(data):
    """Adds a new transaction block to the SHA-256 blockchain ledger."""
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the latest block to get its index and hash
    cursor.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1")
    last_block_row = cursor.fetchone()

    new_index = last_block_row["block_index"] + 1
    new_timestamp = str(int(time.time()))
    previous_hash = last_block_row["hash"]

    # Instantiate new Block and calculate hash
    new_block = Block(new_index, new_timestamp, data, previous_hash)

    # Save new block into SQLite database
    cursor.execute("""
        INSERT INTO blocks (block_index, timestamp, data_json, previous_hash, hash)
        VALUES (?, ?, ?, ?, ?)
    """, (new_block.index, new_block.timestamp, json.dumps(new_block.data), new_block.previous_hash, new_block.hash))
    
    conn.commit()
    conn.close()
    return new_block

def validate_blockchain():
    """
    Validates the continuity and hashes of the Python SHA-256 chain.
    Returns (is_valid: bool, log_message: str).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return False, "Blockchain is empty"

    for i in range(len(rows)):
        current = rows[i]
        
        # Verify block's own SHA-256 hash calculation
        block_data = json.loads(current["data_json"])
        recalculated_hash = Block(current["block_index"], current["timestamp"], block_data, current["previous_hash"]).hash
        
        if recalculated_hash != current["hash"]:
            return False, f"Block #{current['block_index']} has invalid hash! Stored: {current['hash'][:10]}..., Recalculated: {recalculated_hash[:10]}..."

        # Verify hash link with previous block
        if i > 0:
            previous = rows[i - 1]
            if current["previous_hash"] != previous["hash"]:
                return False, f"Block #{current['block_index']} previous_hash mismatch with Block #{previous['block_index']}"

    return True, "Blockchain is VALID and hash continuity is intact."

# =============================================================================
# 3. REST API ENDPOINTS
# =============================================================================

@app.route("/api/campaigns", methods=["GET"])
def list_campaigns():
    """Returns a list of all Donation & Reward campaigns."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/api/campaigns/<int:campaign_id>", methods=["GET"])
def get_campaign(campaign_id):
    """Returns details for a single campaign along with its milestones and contributions."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = cursor.fetchone()
    if not campaign:
        conn.close()
        return jsonify({"error": "Campaign not found"}), 404

    cursor.execute("SELECT * FROM milestones WHERE campaign_id = ?", (campaign_id,))
    milestones = cursor.fetchall()

    cursor.execute("SELECT * FROM contributions WHERE campaign_id = ?", (campaign_id,))
    contributions = cursor.fetchall()

    conn.close()
    return jsonify({
        "campaign": dict(campaign),
        "milestones": [dict(m) for m in milestones],
        "contributions": [dict(c) for c in contributions]
    })

@app.route("/api/campaigns", methods=["POST"])
def create_campaign():
    """
    Creates a new Donation or Reward campaign.
    Expected JSON body: { title, description, owner, funding_type, funding_goal, deadline, milestones: [...] }
    """
    data = request.json
    if not data or "title" not in data or "funding_goal" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    funding_type = data.get("funding_type", "Donation") # Donation or Reward
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO campaigns (title, description, owner, funding_type, engine, funding_goal, deadline)
        VALUES (?, ?, ?, ?, 'Python', ?, ?)
    """, (data["title"], data.get("description", ""), data.get("owner", "Anonymous"), funding_type, float(data["funding_goal"]), data.get("deadline", "2026-12-31")))
    
    campaign_id = cursor.lastrowid

    # Insert Milestones if provided
    milestones = data.get("milestones", [])
    for m in milestones:
        cursor.execute("""
            INSERT INTO milestones (campaign_id, description, target_percent, status)
            VALUES (?, ?, ?, 'PENDING')
        """, (campaign_id, m.get("description", "Milestone"), float(m.get("target_percent", 50.0))))

    conn.commit()
    conn.close()

    # Log campaign creation as a new block on Python blockchain
    add_block_to_ledger({
        "event": "CAMPAIGN_CREATED",
        "campaign_id": campaign_id,
        "title": data["title"],
        "funding_type": funding_type,
        "funding_goal": float(data["funding_goal"])
    })

    return jsonify({"message": "Campaign created successfully", "campaign_id": campaign_id}), 201

@app.route("/api/campaigns/<int:campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = cursor.fetchone()
    if not campaign:
        conn.close()
        return jsonify({"error": "Campaign not found"}), 404

    cursor.execute("DELETE FROM milestones WHERE campaign_id = ?", (campaign_id,))
    cursor.execute("DELETE FROM contributions WHERE campaign_id = ?", (campaign_id,))
    cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()

    add_block_to_ledger({
        "event": "CAMPAIGN_DELETED",
        "campaign_id": campaign_id,
        "title": campaign["title"]
    })

    return jsonify({"message": f"Campaign #{campaign_id} deleted successfully."})

@app.route("/api/campaigns/<int:campaign_id>/contribute", methods=["POST"])

def contribute(campaign_id):
    """
    Adds a contribution to a Donation/Reward campaign and appends a block to Python blockchain.
    Expected JSON body: { contributor_name, amount }
    """
    data = request.json
    if not data or "amount" not in data:
        return jsonify({"error": "Amount is required"}), 400

    amount = float(data["amount"])
    contributor_name = data.get("contributor_name", "Anonymous Contributor")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = cursor.fetchone()
    if not campaign:
        conn.close()
        return jsonify({"error": "Campaign not found"}), 404

    # Determine Reward Tier if campaign type is Reward
    reward_tier = "None"
    if campaign["funding_type"] == "Reward":
        if amount >= 1000:
            reward_tier = "Gold Tier Sponsor"
        elif amount >= 500:
            reward_tier = "Silver Tier Supporter"
        else:
            reward_tier = "Bronze Tier Backer"

    timestamp = str(int(time.time()))

    # Insert contribution record
    cursor.execute("""
        INSERT INTO contributions (campaign_id, contributor_name, amount, reward_tier, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (campaign_id, contributor_name, amount, reward_tier, timestamp))

    # Update campaign current amount
    new_amount = campaign["current_amount"] + amount
    cursor.execute("UPDATE campaigns SET current_amount = ? WHERE id = ?", (new_amount, campaign_id))
    conn.commit()
    conn.close()

    # Log contribution block on SHA-256 Python ledger
    new_block = add_block_to_ledger({
        "event": "CONTRIBUTION",
        "campaign_id": campaign_id,
        "contributor": contributor_name,
        "amount": amount,
        "reward_tier": reward_tier
    })

    return jsonify({
        "message": "Contribution successful",
        "reward_tier": reward_tier,
        "new_total": new_amount,
        "block_index": new_block.index,
        "block_hash": new_block.hash
    })

@app.route("/api/campaigns/<int:campaign_id>/milestones/<int:milestone_id>/approve", methods=["POST"])
def approve_milestone(campaign_id, milestone_id):
    """
    ADMIN ENDPOINT: Approves a campaign milestone and releases funds.
    Demonstrates centralized control where platform admin alone releases funds.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM milestones WHERE id = ? AND campaign_id = ?", (milestone_id, campaign_id))
    milestone = cursor.fetchone()
    if not milestone:
        conn.close()
        return jsonify({"error": "Milestone not found"}), 404

    cursor.execute("UPDATE milestones SET status = 'APPROVED' WHERE id = ?", (milestone_id,))
    conn.commit()
    conn.close()

    # Log milestone approval on Python SHA-256 ledger
    new_block = add_block_to_ledger({
        "event": "MILESTONE_APPROVED_BY_ADMIN",
        "campaign_id": campaign_id,
        "milestone_id": milestone_id,
        "approved_by": "Central Platform Admin"
    })

    return jsonify({
        "message": "Milestone approved by Admin. Funds released.",
        "block_index": new_block.index,
        "block_hash": new_block.hash
    })

@app.route("/api/blockchain", methods=["GET"])
def get_blockchain():
    """Returns the full Python SHA-256 blockchain ledger."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "block_index": r["block_index"],
            "timestamp": r["timestamp"],
            "data": json.loads(r["data_json"]),
            "previous_hash": r["previous_hash"],
            "hash": r["hash"]
        })
    return jsonify(result)

@app.route("/api/blockchain/validate", methods=["GET"])
def validate_chain_endpoint():
    """Endpoint to check if the SHA-256 blockchain hash continuity is valid."""
    is_valid, message = validate_blockchain()
    return jsonify({
        "is_valid": is_valid,
        "message": message
    })

@app.route("/api/tamper", methods=["POST"])
def tamper_blockchain_endpoint():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
    rows = cursor.fetchall()

    if len(rows) < 2:
        conn.close()
        return jsonify({"error": "Need at least 2 blocks to demonstrate tampering. Please create a Donation/Reward campaign and make a contribution first!"}), 400

    target_block = None
    target_idx = 1
    for r in rows[1:]:
        b_dict = dict(r)
        d_json = json.loads(b_dict["data_json"])
        if d_json.get("event") == "CONTRIBUTION_RECEIVED" or "amount" in d_json:
            target_block = b_dict
            target_idx = b_dict["block_index"]
            break

    if not target_block:
        target_block = dict(rows[1])
        target_idx = 1

    target_data = json.loads(target_block["data_json"])
    original_data_summary = json.dumps(target_data, indent=2)

    original_amount = target_data.get("amount", 25.0)

    target_data["tampered"] = True
    target_data["amount"] = 0.0
    target_data["contributor_name"] = "[DELETED BY ADMIN]"
    target_data["tampered_note"] = f"Original ${original_amount} contribution entry removed and reset to $0 secretly by Central Admin"
    tampered_data_summary = json.dumps(target_data, indent=2)

    if "campaign_id" in target_data:
        cursor.execute("UPDATE campaigns SET current_amount = MAX(0, current_amount - ?) WHERE id = ?",
                       (original_amount, target_data["campaign_id"]))

    prev_hash = target_block["previous_hash"]

    for i in range(1, len(rows)):
        r = dict(rows[i])
        b_data = target_data if r["block_index"] == target_idx else json.loads(r["data_json"])
        
        new_b = Block(r["block_index"], r["timestamp"], b_data, prev_hash)
        
        cursor.execute("""
            UPDATE blocks
            SET data_json = ?, previous_hash = ?, hash = ?
            WHERE block_index = ?
        """, (json.dumps(b_data), prev_hash, new_b.hash, r["block_index"]))

        prev_hash = new_b.hash

    conn.commit()
    conn.close()

    is_valid, val_msg = validate_blockchain()

    return jsonify({
        "message": f"ADMIN TAMPER EXECUTED: Removed ${original_amount} contribution entry and reset campaign total!",
        "block_index": target_idx,
        "removed_amount": original_amount,
        "original_data": original_data_summary,
        "tampered_data": tampered_data_summary,
        "chain_validation_after_tampering": {
            "is_valid": is_valid,
            "status": val_msg
        },
        "thesis_lesson": f"Notice that the ${original_amount} contribution entry was deleted and reset to $0, yet the chain STILL VALIDATES as 'True' because one central admin recalculated all hashes. Real decentralization (Solidity engine) prevents this!"
    })


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    print("Initializing SQLite Database for Python Engine...")
    init_db()
    print("Starting Flask Server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
