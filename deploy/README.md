# Phase 1 node inventory and mesh check

This directory belongs to the BTQ Core fork because the checker verifies the exact
core revision running on every node. It does not contain RPC credentials, SSH keys,
wallet files, or node data. The dashboard remains in the separate `Frontend` repo.
See [OPERATIONS_LOG.md](OPERATIONS_LOG.md) for the setup history, fixes, and
remaining limitations.
See [CHECKPOINTS.md](CHECKPOINTS.md) for the latest completed task and next task.
See [LOCAL_RUN.md](LOCAL_RUN.md) for the first isolated three-node schedule.

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
hash, core `src` tree, and binary version string. Repository revisions are
reported for provenance but may differ after documentation-only commits.
Duplicate inbound/outbound sessions do not count as
additional peers. Save JSON output with an experiment run if desired.

`ssh_host` can be an SSH config alias instead of `ubuntu@IP`. For the Abyaan-owned
VMs, first establish trusted SSH access and verify their host keys with their
operator. Do not disable host-key checking. The checker runs each VM's local
`btq-cli`, which reads that VM's own private `btq.conf`; no RPC password is shared.

## Reproducible node configuration

`render_conf.py` renders the measured regtest settings and persistent peer list
from `addressing.yaml`. It creates a new candidate with mode `0600` and never
overwrites the live config. On an existing node, preserve that node's credentials:

```bash
cd ~/btq-core
.venv/bin/python deploy/render_conf.py --node node1 \
  --current ~/.btq/btq.conf --output ~/.btq/btq.conf.candidate
grep -Ev '^(rpcuser|rpcpassword)=' ~/.btq/btq.conf.candidate
```

Replace `node1` with the inventory name of the VM. Do not print, commit, or send
the full candidate: it contains the RPC password. For a new node with no config,
omit `--current`; the renderer generates a unique 48-character hex password.
Review the nonsecret settings before installing the candidate.

The tested service unit is `deploy/systemd/btqd.service`. On the four existing
VMs, systemd and `btq.conf` were already configured manually. To check the
installed unit without changing it, run:

```bash
cmp -s deploy/systemd/btqd.service /etc/systemd/system/btqd.service && echo 'unit matches'
systemctl is-enabled btqd chrony
```

For a *new* node, after the binary is built and the candidate is reviewed,
stop any manually started `btqd`, back up any existing config, install the
candidate as `~/.btq/btq.conf` with mode `0600`, then install the service unit
as `/etc/systemd/system/btqd.service` with mode `0644`. Run `sudo systemctl
daemon-reload` and `sudo systemctl enable --now btqd`. Verify the service,
loopback RPC and ZMQ bindings, clock, peer list, and full mesh before changing
another node. Do not run `btqd -daemon` while systemd manages the data directory.

### Network and reboot checks

Each active node's host and OCI firewalls must allow TCP 19444 from the other
active public IPs. Keep TCP 18443, 4000, and ZMQ ports private. Save host
firewall rules with `netfilter-persistent save` and verify the cloud ingress
rules separately. A reboot may briefly produce a checker failure while saved
peers reconnect; record the time to a stable `PASS`. Confirm `chronyc tracking`
is settled before any cross-node timing measurement.

The four-node bench has passed a block-propagation smoke test and reboot checks.
Time-synchronized propagation probes, automated scenarios, and BIP-361
enforcement are separate later tasks.
