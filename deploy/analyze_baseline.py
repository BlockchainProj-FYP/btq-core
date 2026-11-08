#!/usr/bin/env python3
import math
import sqlite3
import sys

DB_PATH = "metrics.sqlite"

def percentile(data, pct):
    if not data:
        return 0.0
    k = (len(data) - 1) * pct
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    return data[f] * (c - k) + data[c] * (k - f)

def analyze(run_id="E0_baseline"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

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
        (b.t_ns - m.min_t) / 1e6 AS delta_ms
    FROM block_events b
    JOIN min_times m ON b.block_id = m.block_id
    WHERE b.run_id = ?
    ORDER BY delta_ms ASC;
    """
    rows = cur.execute(query, (run_id, run_id)).fetchall()
    conn.close()

    if not rows:
        print(f"No records found for run_id '{run_id}'.")
        return

    by_node = {}
    network_deltas = []

    for _, node, delta in rows:
        by_node.setdefault(node, []).append(delta)
        if delta > 0.05:  # Exclude origin mining node arrival
            network_deltas.append(delta)

    network_deltas.sort()

    print(f"\n=======================================================")
    print(f" BASELINE PROPAGATION REPORT: {run_id}")
    print(f" Total block events analyzed: {len(rows)}")
    print(f"=======================================================\n")

    print("--- Per-Node Propagation Delays (Mean ± Max) ---")
    for node, vals in sorted(by_node.items()):
        vals_sorted = sorted(vals)
        mean_v = sum(vals_sorted) / len(vals_sorted)
        p50_v = percentile(vals_sorted, 0.50)
        max_v = max(vals_sorted)
        print(f"  {node:5s} | Mean: {mean_v:6.2f} ms | p50: {p50_v:6.2f} ms | Max: {max_v:6.2f} ms (n={len(vals)})")

    if network_deltas:
        print("\n--- Network Wide Transit Latency (Excluding Origin) ---")
        print(f"  Samples (N) : {len(network_deltas)}")
        print(f"  Mean Delay  : {sum(network_deltas)/len(network_deltas):.3f} ms")
        print(f"  Median (p50): {percentile(network_deltas, 0.50):.3f} ms")
        print(f"  p90 Delay   : {percentile(network_deltas, 0.90):.3f} ms")
        print(f"  p95 Delay   : {percentile(network_deltas, 0.95):.3f} ms")
        print(f"  p99 Delay   : {percentile(network_deltas, 0.99):.3f} ms")
        print(f"  Max Delay   : {max(network_deltas):.3f} ms")
    print("\n=======================================================\n")

if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "E0_baseline"
    analyze(run)
