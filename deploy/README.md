# Phase 1 node inventory and mesh check

This directory belongs to the BTQ Core fork because the checker verifies the exact
core revision running on every node. It does not contain RPC credentials, SSH keys,
wallet files, or node data. The dashboard remains in the separate `Frontend` repo.

## Run the checker

Install `deploy/requirements.txt` in a local virtual environment, ensure SSH access
to the VMs, and run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r deploy/requirements.txt
.venv/bin/python deploy/mesh_check.py --nodes node1,node2
.venv/bin/python deploy/mesh_check.py --json
```

The two-node command is useful while only Hussain's VMs are SSH-accessible. The
default checks all active nodes. A full-mesh pass requires every active node to
see each other active node's public IP, plus matching block height, best block
hash, and source commit. Duplicate inbound/outbound sessions do not count as
additional peers. Save JSON output with an experiment run if desired.

`ssh_host` can be an SSH config alias instead of `ubuntu@IP`. For the Abyaan-owned
VMs, first establish trusted SSH access and verify their host keys with their
operator. Do not disable host-key checking. The checker runs each VM's local
`btq-cli`, which reads that VM's own private `btq.conf`; no RPC password is shared.

## Next node setup tasks

1. Confirm reserved public IPs, owner, VM shape, tenancy, and core commit for all
   active nodes. Fill node5 and node6 only after those VMs exist.
2. Check `chronyc tracking` and `chronyc sources -v` on each VM. Install chrony
   where missing. Add a cloud NTP source only after confirming the endpoint is
   reachable and avoiding duplicate configuration lines.
3. Back up each VM's `~/.btq/btq.conf`. Preserve its own RPC credentials. Stop
   `btqd` cleanly before changing config; only enable `txindex`, `logtimemicros`,
   `debug=bench`, `fallbackfee`, and loopback ZMQ publishers after checking the
   flags against this core build. Restart once, then verify RPC and port bindings.
4. Choose one daemon lifecycle method per VM. A systemd unit may replace manual
   `btqd -daemon` startup, but never run both against the same data directory.
5. Use persistent peer configuration or `addnode ... add` for links meant to
   survive the session. `onetry` is a one-off connection attempt. Verify unique
   remote IPs, not just `getconnectioncount`.
6. Mine with an existing loaded wallet, record the resulting block hash, and
   rerun the checker. A same-height check alone cannot detect a chain split.

The current four-node network is a working bench, not yet a complete research
instrument. Time-synchronized propagation probes, automated scenarios, and
BIP-361 enforcement are separate later tasks.
