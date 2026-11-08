#!/usr/bin/env python3
import glob
import json
import os
import sqlite3
import subprocess
import sys

DB_PATH = "metrics.sqlite"
LOG_DIR = "/tmp/experiment_logs"

REMOTE_NODES = {
    "node2": "84.235.244.35",
    "node3": "130.210.56.76",
    "node4": "132.226.188.199",
}

def setup_db(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS block_events (
        block_id TEXT NOT NULL,
        node_id TEXT NOT NULL,
        t_ns INTEGER NOT NULL,
        seq INTEGER NOT NULL,
        gap INTEGER NOT NULL,
        run_id TEXT NOT NULL,
        PRIMARY KEY (block_id, node_id, run_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tx_events (
        tx_id TEXT NOT NULL,
        node_id TEXT NOT NULL,
        t_ns INTEGER NOT NULL,
        seq INTEGER NOT NULL,
        gap INTEGER NOT NULL,
        run_id TEXT NOT NULL,
        PRIMARY KEY (tx_id, node_id, run_id)
    )
    """)
    conn.commit()

def fetch_logs():
    os.makedirs(LOG_DIR, exist_ok=True)
    if os.path.exists("/home/ubuntu/node1_probe.jsonl"):
        subprocess.run(["cp", "/home/ubuntu/node1_probe.jsonl", f"{LOG_DIR}/node1_probe.jsonl"], check=True)
    
    for node_id, ip in REMOTE_NODES.items():
        dest = f"{LOG_DIR}/{node_id}_probe.jsonl"
        cmd = ["scp", "-o", "BatchMode=yes", f"ubuntu@{ip}:/home/ubuntu/{node_id}_probe.jsonl", dest]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            print(f"Fetched {node_id} log from {ip}")
        else:
            print(f"Warning: Failed to fetch log from {node_id} ({ip}): {res.stderr.decode().strip()}")

def ingest(run_id):
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    cur = conn.cursor()

    block_rows = []
    tx_rows = []

    for file_path in glob.glob(f"{LOG_DIR}/node*_probe.jsonl"):
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    row = (d["id"], d["n"], d["t_ns"], d["seq"], 1 if d.get("gap") else 0, run_id)
                    if d.get("topic") == "hashblock":
                        block_rows.append(row)
                    elif d.get("topic") == "hashtx":
                        tx_rows.append(row)
                except json.JSONDecodeError:
                    continue

    cur.executemany("INSERT OR REPLACE INTO block_events VALUES (?, ?, ?, ?, ?, ?)", block_rows)
    cur.executemany("INSERT OR REPLACE INTO tx_events VALUES (?, ?, ?, ?, ?, ?)", tx_rows)
    conn.commit()
    print(f"\nIngested {len(block_rows)} block records and {len(tx_rows)} tx records into {DB_PATH}")

    print(f"\n--- Propagation Latencies for run_id: '{run_id}' ---")
    query = """
    WITH min_times AS (
        SELECT block_id, MIN(t_ns) AS min_t
        FROM block_events
        WHERE run_id = ?
        GROUP BY block_id
    )
    SELECT 
        b.block_id,
        b.node_id,
        ROUND((b.t_ns - m.min_t) / 1e6, 3) AS delta_ms
    FROM block_events b
    JOIN min_times m ON b.block_id = m.block_id
    WHERE b.run_id = ?
    ORDER BY b.block_id, delta_ms ASC;
    """
    rows = cur.execute(query, (run_id, run_id)).fetchall()
    for block_id, node, delta in rows:
        print(f"Block: {block_id[:16]}... | Node: {node:5s} | Delta: {delta:8.3f} ms")

    conn.close()

if __name__ == "__main__":
    current_run = sys.argv[1] if len(sys.argv) > 1 else "E0_initial"
    fetch_logs()
    ingest(current_run)
