#!/usr/bin/env python3
"""Check regtest tip, source revision, and unique peer IPs via SSH.

Uses each VM's own btq.conf via btq-cli, so no RPC credentials are stored here.
"""

import argparse
import ipaddress
import json
from pathlib import Path
import subprocess
import sys

import yaml


INVENTORY = Path(__file__).with_name("addressing.yaml")


def remote(host, command):
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, command],
        capture_output=True, text=True, timeout=25, check=False,
    )
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"SSH exit {proc.returncode}")
    return proc.stdout.strip()


def inspect(name, node):
    host = node["ssh_host"]
    info = json.loads(remote(host, "~/btq-core/src/btq-cli -regtest getblockchaininfo"))
    peers = json.loads(remote(host, "~/btq-core/src/btq-cli -regtest getpeerinfo"))
    revision = remote(host, "git -C ~/btq-core rev-parse HEAD")
    source_tree = remote(host, "git -C ~/btq-core rev-parse HEAD:src")
    binary_version = remote(host, "~/btq-core/src/btqd --version").splitlines()[0]
    peer_ips = set()
    for peer in peers:
        address = peer.get("addr", "")
        try:
            peer_ips.add(str(ipaddress.ip_address(address.rsplit(":", 1)[0].strip("[]"))))
        except ValueError:
            pass
    return {"node": name, "ip": node["public_ip"], "height": info["blocks"],
            "hash": info["bestblockhash"], "revision": revision,
            "source_tree": source_tree, "binary_version": binary_version,
            "peer_ips": sorted(peer_ips), "connections": len(peers)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", help="Comma-separated node names; default is all active nodes")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results")
    args = parser.parse_args()
    inventory = yaml.safe_load(INVENTORY.read_text())
    nodes = inventory["nodes"]
    names = args.nodes.split(",") if args.nodes else [n for n, v in nodes.items() if v["status"] == "active"]
    if not names or any(n not in nodes or nodes[n]["status"] != "active" for n in names):
        parser.error("--nodes must name active inventory entries")

    results, errors = [], {}
    for name in names:
        try:
            results.append(inspect(name, nodes[name]))
        except (RuntimeError, subprocess.TimeoutExpired, KeyError, ValueError) as exc:
            errors[name] = str(exc)

    failures = []
    if errors:
        failures.append("unreachable or invalid nodes: " + ", ".join(errors))
    if len({(r["height"], r["hash"]) for r in results}) > 1:
        failures.append("best chain tips differ")
    if len({r["source_tree"] for r in results}) > 1:
        failures.append("core source trees differ")
    if len({r["binary_version"] for r in results}) > 1:
        failures.append("binary version strings differ")
    for result in results:
        missing = {nodes[n]["public_ip"] for n in names if n != result["node"]} - set(result["peer_ips"])
        if missing:
            failures.append(f'{result["node"]} lacks direct peers: {", ".join(sorted(missing))}')

    report = {"nodes": results, "errors": errors, "failures": failures, "pass": not failures}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for result in results:
            print(f'{result["node"]}: height={result["height"]} hash={result["hash"]} '
                  f'revision={result["revision"][:12]} unique_peers={len(result["peer_ips"])} '
                  f'connections={result["connections"]} source_tree={result["source_tree"][:12]} '
                  f'binary={result["binary_version"]}')
        for name, error in errors.items():
            print(f"{name}: ERROR {error}", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
