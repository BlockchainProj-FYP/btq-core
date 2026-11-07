#!/usr/bin/env python3
"""Render a private regtest config from the shared node inventory.

The output is a candidate file. This command never edits the live btq.conf.
"""

import argparse
import ipaddress
import os
from pathlib import Path
import secrets

import yaml


INVENTORY = Path(__file__).with_name("addressing.yaml")


def credentials_from(path):
    found = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if line.startswith(("#", ";")) or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in ("rpcuser", "rpcpassword"):
            continue
        if not value or (key in found and found[key] != value):
            raise ValueError(f"Missing or conflicting {key} in {path}")
        found[key] = value
    if set(found) != {"rpcuser", "rpcpassword"}:
        raise ValueError(f"Both RPC credentials are required in {path}")
    return found["rpcuser"], found["rpcpassword"]


def render(node_name, inventory, rpc_user, rpc_password):
    nodes = inventory["nodes"]
    if node_name not in nodes or nodes[node_name]["status"] != "active":
        raise ValueError(f"{node_name} is not an active inventory node")
    node = nodes[node_name]
    ipaddress.IPv4Address(node["public_ip"])
    if not rpc_user or not rpc_password or any(c in rpc_user + rpc_password for c in "\r\n#"):
        raise ValueError("RPC credentials contain an unsupported character")
    peers = []
    for name, peer in nodes.items():
        if name != node_name and peer["status"] == "active":
            peers.append(f'addnode={ipaddress.IPv4Address(peer["public_ip"])}:{int(peer["p2p_port"])}')
    return "\n".join([
        "# Generated from deploy/addressing.yaml. Keep this file private.",
        "regtest=1", "", "[regtest]", "server=1", "listen=1",
        f'port={int(node["p2p_port"])}', f'rpcport={int(node["rpc_port"])}',
        "rpcbind=127.0.0.1", "rpcallowip=127.0.0.1",
        f"rpcuser={rpc_user}", f"rpcpassword={rpc_password}", "",
        "txindex=1", "fallbackfee=0.0001", "logtimemicros=1", "debug=bench",
        "zmqpubhashblock=tcp://127.0.0.1:28332",
        "zmqpubhashtx=tcp://127.0.0.1:28333",
        "zmqpubrawblock=tcp://127.0.0.1:28334",
        "zmqpubrawtx=tcp://127.0.0.1:28335", "", *peers, "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True, help="node1, node2, and so on")
    parser.add_argument("--output", required=True, type=Path, help="new candidate path")
    parser.add_argument("--current", type=Path, help="existing config whose RPC credentials to preserve")
    args = parser.parse_args()
    inventory = yaml.safe_load(INVENTORY.read_text())
    if args.current:
        rpc_user, rpc_password = credentials_from(args.current.expanduser())
    else:
        rpc_user, rpc_password = "btqadmin", secrets.token_hex(24)
    content = render(args.node, inventory, rpc_user, rpc_password)
    output = args.output.expanduser()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    print(f"Wrote private candidate config to {output}; RPC credentials were not displayed")


if __name__ == "__main__":
    main()
