# BTQ testbed checkpoints

This is the short handoff for the next work session. Update it after every
completed task. Put detailed failures and fixes in [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
Do not include credentials, private keys, wallet data, or raw node config.

## Current checkpoint

**Completed task:** Four-node regtest bench restored and verified after node
restarts and reboot tests. Repository templates for the measured config and
systemd service have been prepared. The four-node mesh checker last returned
`PASS` after VM 84 and VM 145 rebooted.

**Evidence:** Nodes 1-4 reported height `5`, best-block hash
`667dae19063fd494b36fbca79b2da46431f0b116dd36a73ad0e0432d1cce5a0e`,
repository revision `869926f64c61d428b69d35d833da7f1d71893f02`, and all
three expected public VM IPs as unique peers. Services `btqd` and `chrony`
were active on the rebooted Hussain VMs; scoped host P2P firewall rules
survived subsequent reboots. Node1 and node3 each mined one block that
reached all four nodes.

**Scope of this result:** The current bench has four nodes. The BIP-361 plan
calls for six, plus a local cluster, orchestration, metrics, and enforcement.
The checker is a connectivity and chain-consistency check, not a propagation
latency measurement. Repository revision is not a binary attestation.

**Next task:** Verify the committed config renderer on nodes 3 and 4 without
replacing their working configs. Nodes 1 and 2 have mode `0600` candidates
with the expected nonsecret settings and exact service-unit matches. Node2's
candidate RPC credentials were privately confirmed to match its live config.
Then add a boot-managed,
loopback-only dashboard service for VM 84 if that dashboard should come back
automatically after a reboot. The first research coding milestone after that
is a seeded, 10-minute block schedule with a saved run manifest.

**Open issue:** VM 84-initiated TCP 19444 connections toward Abyaan's VMs
timed out after reboot, although Abyaan's saved outbound connections restored
the full mesh. Review OCI ingress rules and record any topology or cloud rule
change before a controlled experiment. VM 84's dashboard server did not
restart on boot. A planning draft contained a literal RPC password; verify
whether it matches any live VM and rotate it there if it does.

## Completed checkpoints

| Checkpoint | Outcome | Evidence |
|---|---|---|
| Team repositories | Public `btq-core` fork and private `Frontend` repository established; dashboard code on `Frontend/main`. | Core fork and dashboard repository available to the team. |
| Two Hussain nodes | Matching BTQ Core build, regtest RPC, mining wallet, and P2P. | Same core source commit and block hash on both nodes. |
| Four-node connectivity | Hussain and Abyaan nodes peered with three expected unique peers each. | `deploy/mesh_check.py` returned `PASS` on all four. |
| Dashboard on VM 84 | Source snapshot deployed, Node 22 installed, frontend built, API returned height 3 through an SSH tunnel. | HTTP 200 and RPC result 3 at setup. Boot startup remains open. |
| Time synchronization | Chrony installed and active on all four VMs. | Later tracking readings had normal leap status and reduced clock uncertainty. Recheck before every timed run. |
| First block propagation smoke tests | Node1 mined block 4; node3 mined block 5; each reached all four nodes. | Matching height and best-block hash in saved checker output. |
| Deployment inventory and checker | `addressing.yaml`, `mesh_check.py`, and requirements committed to the core fork. | Commit `869926f`; checker passed. |
| Node service conversion | All four nodes use systemd `btqd`, telemetry flags, loopback RPC/ZMQ, and saved peers. | Service checks, port bindings, and subsequent mesh checks passed. |
| Reboot recovery | All four nodes were reboot-tested; missing P2P host rules were corrected and saved. | Final checker `PASS` after Hussain VM reboot tests; firewall rules survived reboot. |
| Configuration source | Secret-free renderer and exact tested service unit prepared in `deploy/`. | Renderer checks cover credential preservation, peer lists, output mode, and no overwrite; service template hash matched installed units on nodes 1 and 2. |
| Node1 candidate review | Rendered node1's private candidate from its live config without replacing it. | Candidate mode `0600`, expected nonsecret settings and three peers, and service unit matched. |
| Node2 candidate review | Reviewed a previously rendered private candidate without overwriting it or changing the live config. | Candidate mode `0600`, expected nonsecret settings and three peers, RPC credentials matched live config in a private comparison, and service unit matched. |

## Update after the next task

1. Replace **Current checkpoint** with the new completed task, its command or
   artifact evidence, the next single task, and any open issue.
2. Add one concise row to **Completed checkpoints**. Preserve prior rows.
3. Put the full problem, diagnosis, fix, and verification in
   [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
4. Commit both Markdown files with the code or configuration change they
   describe. Never claim an experiment is reproducible until its inputs,
   outputs, and source revisions have been saved.
