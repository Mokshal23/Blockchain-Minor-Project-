"""
=============================================================================
Vercel Serverless Entry Point - Python Engine (Flask + SQLite)
=============================================================================
"""

import os
import sys
import hashlib
import json
import sqlite3
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Use /tmp for SQLite database in Vercel serverless environment
DB_FILE = "/tmp/database.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            funding_type TEXT NOT NULL,
            engine TEXT NOT NULL DEFAULT 'Python',
            funding_goal REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            deadline TEXT NOT NULL,
            is_closed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            target_percent REAL NOT NULL,
            status TEXT DEFAULT 'PENDING',
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        )
    """)

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

    cursor.execute("SELECT COUNT(*) as count FROM blocks")
    if cursor.fetchone()["count"] == 0:
        create_genesis_block(conn)

    conn.close()

class Block:
    def __init__(self, index, timestamp, data, previous_hash, block_hash=None):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = block_hash or self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data, sort_keys=True)}{self.previous_hash}"
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

def create_genesis_block(conn):
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
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1")
    last_block_row = cursor.fetchone()

    new_index = last_block_row["block_index"] + 1 if last_block_row else 0
    new_timestamp = str(int(time.time()))
    previous_hash = last_block_row["hash"] if last_block_row else "0" * 64

    new_block = Block(new_index, new_timestamp, data, previous_hash)

    cursor.execute("""
        INSERT INTO blocks (block_index, timestamp, data_json, previous_hash, hash)
        VALUES (?, ?, ?, ?, ?)
    """, (new_block.index, new_block.timestamp, json.dumps(new_block.data), new_block.previous_hash, new_block.hash))
    
    conn.commit()
    conn.close()
    return new_block

def validate_blockchain():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return False, "Blockchain is empty"

    for i in range(len(rows)):
        current = rows[i]
        block_data = json.loads(current["data_json"])
        recalculated_hash = Block(current["block_index"], current["timestamp"], block_data, current["previous_hash"]).hash
        
        if recalculated_hash != current["hash"]:
            return False, f"Block #{current['block_index']} has invalid hash! Stored: {current['hash'][:10]}..., Recalculated: {recalculated_hash[:10]}..."

        if i > 0:
            previous = rows[i - 1]
            if current["previous_hash"] != previous["hash"]:
                return False, f"Block #{current['block_index']} previous_hash mismatch with Block #{previous['block_index']}"

    return True, "Blockchain is VALID and hash continuity is intact."

# Ensure DB initialized on cold start
try:
    init_db()
except Exception as e:
    pass

@app.route("/api/campaigns", methods=["GET"])
def list_campaigns():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/api/campaigns/<int:campaign_id>", methods=["GET"])
def get_campaign(campaign_id):
    init_db()
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
    init_db()
    data = request.json
    if not data or "title" not in data or "funding_goal" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    funding_type = data.get("funding_type", "Donation")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO campaigns (title, description, owner, funding_type, engine, funding_goal, deadline)
        VALUES (?, ?, ?, ?, 'Python', ?, ?)
    """, (data["title"], data.get("description", ""), data.get("owner", "Anonymous"), funding_type, float(data["funding_goal"]), data.get("deadline", "2026-12-31")))
    
    campaign_id = cursor.lastrowid

    milestones = data.get("milestones", [])
    if not milestones:
        milestones = [{"description": "Milestone 1: Prototype & Initial Setup (50% Funds)", "target_percent": 50.0}]

    for m in milestones:
        cursor.execute("""
            INSERT INTO milestones (campaign_id, description, target_percent, status)
            VALUES (?, ?, ?, 'PENDING')
        """, (campaign_id, m.get("description", "Milestone 1"), float(m.get("target_percent", 50.0))))


    conn.commit()
    conn.close()

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
    init_db()
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
    init_db()
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

    reward_tier = "None"
    if campaign["funding_type"] == "Reward":
        if amount >= 1000:
            reward_tier = "Gold Tier Sponsor"
        elif amount >= 500:
            reward_tier = "Silver Tier Supporter"
        else:
            reward_tier = "Bronze Tier Backer"

    timestamp = str(int(time.time()))

    cursor.execute("""
        INSERT INTO contributions (campaign_id, contributor_name, amount, reward_tier, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (campaign_id, contributor_name, amount, reward_tier, timestamp))

    new_amount = campaign["current_amount"] + amount
    cursor.execute("UPDATE campaigns SET current_amount = ? WHERE id = ?", (new_amount, campaign_id))
    conn.commit()
    conn.close()

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
    init_db()
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
    init_db()
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
    is_valid, message = validate_blockchain()
    return jsonify({
        "is_valid": is_valid,
        "message": message
    })

@app.route("/api/tamper", methods=["POST"])
def tamper_blockchain_endpoint():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
    rows = cursor.fetchall()

    if len(rows) < 2:
        conn.close()
        return jsonify({"error": "Need at least 2 blocks to demonstrate tampering. Please create a campaign and make a contribution first!"}), 400

    target_block = dict(rows[1])
    target_data = json.loads(target_block["data_json"])

    original_data_summary = str(target_data)
    target_data["tampered"] = True
    target_data["amount"] = target_data.get("amount", 100) * 10
    target_data["tampered_note"] = "Altered by Central Admin secretly"

    prev_hash = target_block["previous_hash"]

    for i in range(1, len(rows)):
        r = dict(rows[i])
        b_data = target_data if i == 1 else json.loads(r["data_json"])
        
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
        "message": "ADMIN TAMPER SUCCESSFUL! Block #1 was modified and downstream hashes recalculated.",
        "original_data": original_data_summary,
        "tampered_data": str(target_data),
        "chain_validation_after_tampering": {
            "is_valid": is_valid,
            "status": val_msg
        },
        "thesis_lesson": "Notice that the chain STILL VALIDATES as 'True' because one central admin holds all DB keys and recalculated all hashes. Real decentralization (Solidity engine) prevents this!"
    })

if __name__ == "__main__":
    app.run()
