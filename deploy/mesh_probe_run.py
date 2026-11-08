#!/usr/bin/env python3
"""Capture one production-mesh block at each node with local ZMQ probes.

Run on node1 only, after installing pyzmq and this repository on all active VMs.
This mines one block on the existing four-node regtest chain.
"""

import csv
import json
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid

import yaml


ROOT = Path(__file__).resolve().parent.parent
NODES = yaml.safe_load((ROOT / "deploy/addressing.yaml").read_text())["nodes"]
ACTIVE = {name: data for name, data in NODES.items() if data["status"] == "active"}
CLI = Path.home() / "btq-core/src/btq-cli"


def call(args, timeout=25):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}")
    return result.stdout.strip()


def remote(host, script, timeout=25):
    return call(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, script], timeout)


def rpc(method, *args):
    return call([str(CLI), "-regtest", method, *map(str, args)])


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def clock_quality(tracking):
    offset = re.search(r"^System time\s*:\s*([\d.]+) seconds", tracking, re.M)
    leap = re.search(r"^Leap status\s*:\s*(\w+)", tracking, re.M)
    dispersion = re.search(r"^Root dispersion\s*:\s*([\d.]+) seconds", tracking, re.M)
    values = {"offset_seconds": float(offset.group(1)) if offset else None,
              "root_dispersion_seconds": float(dispersion.group(1)) if dispersion else None,
              "leap_status": leap.group(1) if leap else None}
    values["within_5ms"] = (values["leap_status"] == "Normal" and
                            values["offset_seconds"] is not None and values["offset_seconds"] < .005 and
                            values["root_dispersion_seconds"] is not None and values["root_dispersion_seconds"] < .005)
    return values


def main():
    if len(ACTIVE) != 4:
        raise RuntimeError("this baseline requires exactly four active inventory nodes")
    run_id = "run-" + uuid.uuid4().hex[:12]
    root = Path.home() / "btq-mesh-probe-runs" / run_id
    root.mkdir(mode=0o700, parents=True)
    manifest = {"run_id": run_id, "status": "starting", "nodes": list(ACTIVE),
                "source_revision": call(["git", "-C", str(ROOT), "rev-parse", "HEAD"])}
    save(root / "manifest.json", manifest)
    pids = {}
    try:
        before = json.loads(call([str(ROOT / ".venv/bin/python"),
                                  str(ROOT / "deploy/mesh_check.py"), "--json"], timeout=120))
        if not before["pass"]:
            raise RuntimeError("production mesh checker failed before mining")
        manifest["mesh_before"] = before
        for name, node in ACTIVE.items():
            host = node["ssh_host"]
            remote_dir = f"/home/ubuntu/btq-mesh-probe-runs/{run_id}"
            remote(host, f"mkdir -p {shlex.quote(remote_dir)} && chmod 700 {shlex.quote(remote_dir)}")
            tracking = remote(host, "chronyc tracking")
            manifest.setdefault("clock_before", {})[name] = {"tracking": tracking,
                                                               "quality": clock_quality(tracking)}
            if not manifest["clock_before"][name]["quality"]["within_5ms"]:
                raise RuntimeError(f"clock quality on {name} is outside the 5 ms preflight threshold")
            out = f"{remote_dir}/blocks.jsonl"
            ready = f"{remote_dir}/probe.ready"
            log = f"{remote_dir}/probe.log"
            probe = "/home/ubuntu/btq-core/deploy/block_probe.py"
            python = "/home/ubuntu/btq-core/.venv/bin/python"
            argv = [python, probe, "--node", name, "--run-id", run_id,
                    "--endpoint", "tcp://127.0.0.1:28332", "--output", out, "--ready", ready]
            start = "nohup " + " ".join(shlex.quote(x) for x in argv)
            start += f" > {shlex.quote(log)} 2>&1 < /dev/null & echo $!"
            pids[name] = int(remote(host, start))
        for name, node in ACTIVE.items():
            ready = f"/home/ubuntu/btq-mesh-probe-runs/{run_id}/probe.ready"
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    remote(node["ssh_host"], f"test -f {shlex.quote(ready)}", timeout=15)
                    break
                except RuntimeError:
                    time.sleep(.3)
            else:
                raise RuntimeError(f"probe {name} did not become ready")
        manifest["status"] = "running"
        save(root / "manifest.json", manifest)
        wallets = json.loads(rpc("listwallets"))
        if "miner" not in wallets:
            rpc("loadwallet", "miner")
        address = call([str(CLI), "-regtest", "-rpcwallet=miner", "getnewaddress"])
        block_hash = json.loads(rpc("generatetoaddress", 1, address))[0]
        manifest["block_hash"] = block_hash
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if all(block_hash in remote(node["ssh_host"],
                                        f"cat /home/ubuntu/btq-mesh-probe-runs/{run_id}/blocks.jsonl")
                   for node in ACTIVE.values()):
                break
            time.sleep(.5)
        else:
            raise RuntimeError("not all probes observed the mined block within 30 seconds")
        manifest["status"] = "collecting"
        save(root / "manifest.json", manifest)
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        raise
    finally:
        for name, pid in pids.items():
            try:
                remote(ACTIVE[name]["ssh_host"], f"kill -TERM {pid}")
            except RuntimeError:
                pass
        for name, node in ACTIVE.items():
            if name in pids:
                try:
                    path = f"/home/ubuntu/btq-mesh-probe-runs/{run_id}/blocks.jsonl"
                    (root / f"{name}-blocks.jsonl").write_text(remote(node["ssh_host"], f"cat {shlex.quote(path)}") + "\n")
                    tracking = remote(node["ssh_host"], "chronyc tracking")
                    manifest.setdefault("clock_after", {})[name] = {"tracking": tracking,
                                                                      "quality": clock_quality(tracking)}
                except RuntimeError as exc:
                    manifest.setdefault("collection_errors", {})[name] = str(exc)
        save(root / "manifest.json", manifest)
    try:
        rows = {}
        for name in ACTIVE:
            records = [json.loads(line) for line in (root / f"{name}-blocks.jsonl").read_text().splitlines()]
            found = [row for row in records if row["hash"] == block_hash]
            if len(found) != 1 or any(row["gap"] for row in records):
                raise RuntimeError(f"probe {name} has missing, duplicate, or gapped block events")
            rows[name] = found[0]
        first = min(row["t_unix_ns"] for row in rows.values())
        with (root / "block_arrivals.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["block_hash", "node", "arrival_unix_ns", "delay_from_first_ms"])
            for name, row in rows.items():
                writer.writerow([block_hash, name, row["t_unix_ns"],
                                 round((row["t_unix_ns"] - first) / 1_000_000, 6)])
        after = json.loads(call([str(ROOT / ".venv/bin/python"),
                                 str(ROOT / "deploy/mesh_check.py"), "--json"], timeout=120))
        manifest["mesh_after"] = after
        manifest["clock_valid"] = all(value["quality"]["within_5ms"]
                                      for sample in ("clock_before", "clock_after")
                                      for value in manifest[sample].values())
        manifest["status"] = "complete" if after["pass"] and manifest["clock_valid"] else "invalid"
        save(root / "manifest.json", manifest)
        print(f"run_dir={root} status={manifest['status']} block_hash={block_hash}")
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        save(root / "manifest.json", manifest)
        raise


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, ValueError, OSError) as exc:
        raise SystemExit(f"mesh probe run failed: {exc}") from exc
