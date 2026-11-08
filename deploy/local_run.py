#!/usr/bin/env python3
"""Plan or execute an isolated three-node regtest block run on one host."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import socket
import subprocess
import sys
import time
import uuid


P2P_BASE = 19550
RPC_BASE = 18550
ZMQ_BASE = 28550
NODE_COUNT = 3


def command(args, *, timeout=20):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, args[:2]))}: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def cli(binary, datadir, method, *params):
    return command([str(binary), f"-datadir={datadir}", "-regtest", method, *map(str, params)])


def rpc_json(binary, datadir, method, *params):
    return json.loads(cli(binary, datadir, method, *params))


def available(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def schedule(seed, duration, mean_interval):
    rng = random.Random(seed)
    at = 0.0
    result = []
    while True:
        at += rng.expovariate(1.0 / mean_interval)
        if at >= duration:
            return result
        result.append({"index": len(result) + 1, "offset_seconds": round(at, 6)})


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def clock_tracking():
    try:
        result = subprocess.run(["chronyc", "tracking"], capture_output=True,
                                text=True, timeout=5, check=False)
        return {"exit_code": result.returncode,
                "output": result.stdout.strip() if result.returncode == 0 else result.stderr.strip(),
                "observed_at_unix_ns": time.time_ns()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc), "observed_at_unix_ns": time.time_ns()}


def wait_ready(paths, processes, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(proc.poll() is not None for proc in processes):
            raise RuntimeError("block probe exited before becoming ready")
        if all(path.exists() for path in paths):
            return
        time.sleep(0.1)
    raise TimeoutError("block probes did not become ready")


def verify_probes(run_dir, events_path):
    mined = [json.loads(line)["block_hash"] for line in events_path.read_text().splitlines()]
    rows = []
    for index in range(NODE_COUNT):
        path = run_dir / f"node{index+1}-blocks.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()]
        if any(row["gap"] for row in records):
            raise RuntimeError(f"ZMQ sequence gap on node{index+1}")
        observed = [row["hash"] for row in records]
        if observed != mined:
            raise RuntimeError(f"block probe on node{index+1} did not record every mined hash in order")
        rows.append(records)
    delays = []
    with (run_dir / "block_arrivals.csv").open("w") as stream:
        stream.write("block_hash,node,arrival_unix_ns,delay_from_first_ms\n")
        for events in zip(*rows):
            first = min(row["t_unix_ns"] for row in events)
            for row in events:
                delay_ms = (row["t_unix_ns"] - first) / 1_000_000
                delays.append(delay_ms)
                stream.write(f'{row["hash"]},{row["node"]},{row["t_unix_ns"]},{delay_ms:.6f}\n')
    return {"blocks_per_node": len(mined), "nodes": NODE_COUNT,
            "arrival_rows": len(delays), "max_delay_from_first_ms": max(delays, default=0)}


def wait_rpc(cli_bin, datadir, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"btqd exited early for {datadir.name}")
        try:
            cli(cli_bin, datadir, "getblockcount")
            return
        except (RuntimeError, subprocess.TimeoutExpired):
            time.sleep(0.3)
    raise TimeoutError(f"RPC did not start for {datadir.name}")


def wait_tip(cli_bin, datadirs, expected_hash, timeout=15):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            hashes = [cli(cli_bin, d, "getbestblockhash") for d in datadirs]
            if all(h == expected_hash for h in hashes):
                return round((time.monotonic() - start) * 1000, 3)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
        time.sleep(0.1)
    raise TimeoutError(f"nodes did not converge on {expected_hash}")


def wait_peers(cli_bin, datadirs, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if all(all(peer["connected"] for peer in rpc_json(cli_bin, d, "getaddednodeinfo"))
                   for d in datadirs):
                return
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
        time.sleep(0.3)
    raise TimeoutError("local nodes did not establish their saved peer links")


def make_config(datadir, index):
    # One dial per pair avoids duplicate inbound/outbound sessions.
    peers = [f"addnode=127.0.0.1:{P2P_BASE+j}" for j in range(index)]
    content = "\n".join([
        "regtest=1", "", "[regtest]", "server=1", "listen=1", "listenonion=0", "discover=0",
        "dnsseed=0", f"bind=127.0.0.1:{P2P_BASE+index}",
        f"port={P2P_BASE+index}", f"rpcport={RPC_BASE+index}",
        "rpcbind=127.0.0.1", "rpcallowip=127.0.0.1", "rpcuser=localrun",
        f"rpcpassword={secrets.token_hex(24)}", "fallbackfee=0.0001",
        f"zmqpubhashblock=tcp://127.0.0.1:{ZMQ_BASE+index}", *peers, "",
    ])
    path = datadir / "btq.conf"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)


def execute(run_dir, manifest, schedule_items, btqd, btqcli):
    processes = []
    probes = []
    logs = []
    probe_logs = []
    datadirs = []
    events_path = run_dir / "events.jsonl"
    try:
        manifest["status"] = "running"
        manifest["started_at_unix_ns"] = time.time_ns()
        manifest["clock_before"] = clock_tracking()
        write_json(run_dir / "manifest.json", manifest)
        for index in range(NODE_COUNT):
            datadir = run_dir / f"node{index+1}"
            datadir.mkdir(mode=0o700)
            make_config(datadir, index)
            log = (run_dir / f"node{index+1}-console.log").open("w")
            logs.append(log)
            process = subprocess.Popen(
                [str(btqd), f"-datadir={datadir}", f"-conf={datadir/'btq.conf'}", "-regtest"],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            processes.append(process)
            datadirs.append(datadir)
            wait_rpc(btqcli, datadir, process)
        wait_peers(btqcli, datadirs)
        ready_paths = []
        for index in range(NODE_COUNT):
            node = f"node{index+1}"
            ready = run_dir / f"{node}-probe.ready"
            ready_paths.append(ready)
            probe_log = (run_dir / f"{node}-probe.log").open("w")
            probe_logs.append(probe_log)
            probes.append(subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name("block_probe.py")),
                 "--node", node, "--run-id", run_dir.name,
                 "--endpoint", f"tcp://127.0.0.1:{ZMQ_BASE+index}",
                 "--output", str(run_dir / f"{node}-blocks.jsonl"),
                 "--ready", str(ready)],
                stdout=probe_log, stderr=subprocess.STDOUT, start_new_session=True,
            ))
        wait_ready(ready_paths, probes)
        rpc_json(btqcli, datadirs[0], "createwallet", "miner")
        address = cli(btqcli, datadirs[0], "-rpcwallet=miner", "getnewaddress")
        # The first node mines. The other two must receive each block through P2P.
        start = time.monotonic()
        with events_path.open("w") as events:
            for item in schedule_items:
                delay = start + item["offset_seconds"] - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                block_hash = rpc_json(btqcli, datadirs[0], "generatetoaddress", 1, address)[0]
                convergence_ms = wait_tip(btqcli, datadirs, block_hash)
                event = {**item, "observed_at_unix_ns": time.time_ns(),
                         "block_hash": block_hash, "poll_convergence_ms": convergence_ms}
                events.write(json.dumps(event) + "\n")
                events.flush()
        time.sleep(0.5)
        for probe in probes:
            probe.terminate()
            if probe.wait(timeout=5) != 0:
                raise RuntimeError("block probe exited with an error")
        manifest["probe_summary"] = verify_probes(run_dir, events_path)
        tips = [rpc_json(btqcli, d, "getblockchaininfo") for d in datadirs]
        manifest["final_tips"] = [{"height": t["blocks"], "hash": t["bestblockhash"]} for t in tips]
        manifest["status"] = "complete"
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        raise
    finally:
        manifest["finished_at_unix_ns"] = time.time_ns()
        manifest["clock_after"] = clock_tracking()
        for probe in probes:
            if probe.poll() is None:
                probe.terminate()
                try:
                    probe.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    probe.kill()
                    probe.wait()
        for datadir in datadirs:
            try:
                cli(btqcli, datadir, "stop")
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for log in logs:
            log.close()
        for log in probe_logs:
            log.close()
        write_json(run_dir / "manifest.json", manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=600, help="run length in seconds")
    parser.add_argument("--mean-interval", type=float, default=5, help="mean seconds between blocks")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-root", type=Path, default=Path.home() / "btq-local-runs")
    parser.add_argument("--execute", action="store_true", help="start isolated nodes and mine blocks")
    args = parser.parse_args()
    if args.duration <= 0 or args.mean_interval <= 0:
        parser.error("duration and mean interval must be positive")
    source_root = Path(__file__).resolve().parent.parent
    btqd = source_root / "src/btqd"
    btqcli = source_root / "src/btq-cli"
    if args.execute:
        if not btqd.is_file() or not btqcli.is_file():
            parser.error("built src/btqd and src/btq-cli are required for --execute")
        busy = [p for p in (*range(P2P_BASE, P2P_BASE+NODE_COUNT),
                            *range(RPC_BASE, RPC_BASE+NODE_COUNT),
                            *range(ZMQ_BASE, ZMQ_BASE+NODE_COUNT)) if not available(p)]
        if busy:
            parser.error(f"local ports are busy: {busy}")
    root = args.output_root.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    run_dir = root / f"run-{uuid.uuid4().hex[:12]}"
    run_dir.mkdir(mode=0o700)
    items = schedule(args.seed, args.duration, args.mean_interval)
    manifest = {
        "format": 1, "backend": "isolated-local-processes", "network": "regtest",
        "nodes": NODE_COUNT, "seed": args.seed, "duration_seconds": args.duration,
        "mean_interval_seconds": args.mean_interval, "distribution": "seeded-exponential",
        "planned_blocks": len(items), "p2p_ports": list(range(P2P_BASE, P2P_BASE+NODE_COUNT)),
        "rpc_ports": list(range(RPC_BASE, RPC_BASE+NODE_COUNT)),
        "zmq_ports": list(range(ZMQ_BASE, ZMQ_BASE+NODE_COUNT)),
        "source_revision": command(["git", "-C", str(source_root), "rev-parse", "HEAD"]),
        "source_tree": command(["git", "-C", str(source_root), "rev-parse", "HEAD:src"]),
        "status": "planned",
    }
    write_json(run_dir / "schedule.json", items)
    write_json(run_dir / "manifest.json", manifest)
    print(f"run_dir={run_dir} planned_blocks={len(items)}")
    if not args.execute:
        return
    manifest["binary_sha256"] = hashlib.sha256(btqd.read_bytes()).hexdigest()
    write_json(run_dir / "manifest.json", manifest)
    execute(run_dir, manifest, items, btqd, btqcli)
    print(f"status={manifest['status']} final_height={manifest['final_tips'][0]['height']}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
        print(f"local run failed: {exc}", file=sys.stderr)
        sys.exit(1)
