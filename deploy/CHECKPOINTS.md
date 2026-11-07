# BTQ testbed checkpoints

This is the short handoff for the next work session. Update it after every
completed task. Put detailed failures and fixes in [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
Do not include credentials, private keys, wallet data, or raw node config.

## Current checkpoint

**Completed task:** VM 84's dashboard proxy now runs as a boot-managed,
loopback-only systemd service. It survived a reboot and returned frontend
HTTP 200 and RPC height 5. The dashboard service template was committed to
the private Frontend repository. All four core config candidates were reviewed
without replacing the working configs. The mesh checker was corrected to
distinguish core source changes from documentation-only repository commits.

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

**Next task:** Build a seeded, 10-minute block schedule with a saved run
manifest. The corrected checker passed on the live four-node network even
while the VMs had different documentation revisions.

**Open issue:** VM 84-initiated TCP 19444 connections toward Abyaan's VMs
timed out after reboot, although Abyaan's saved outbound connections restored
the full mesh. Review OCI ingress rules and record any topology or cloud rule
change before a controlled experiment. A planning draft contained a literal RPC password; verify
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
| Node3 candidate review | Rendered a private candidate after installing PyYAML in its virtual environment. | Candidate mode `0600`, expected nonsecret settings and three peers, RPC credentials matched live config in a private comparison, and service unit matched. |
| Four-node candidate review | Reviewed node4 and completed private credential comparisons on all four nodes. No live config was replaced. | All candidates mode `0600`, expected nonsecret settings and three peers, credentials matching live configs, and service units matching the committed template. |
| VM 84 dashboard boot service | Installed a loopback-only dashboard unit from the private Frontend repository and rebooted VM 84. | Service active after reboot; API and RPC height 5, frontend HTTP 200, port 4000 on 127.0.0.1. |
| Checker source identity fix | Compared core `src` tree and binary version instead of requiring equal documentation revisions. | Live four-node check passed: identical height 5, best hash, source tree, binary version, and three expected peer IPs each. |

## Update after the next task

1. Replace **Current checkpoint** with the new completed task, its command or
   artifact evidence, the next single task, and any open issue.
2. Add one concise row to **Completed checkpoints**. Preserve prior rows.
3. Put the full problem, diagnosis, fix, and verification in
   [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
4. Commit both Markdown files with the code or configuration change they
   describe. Never claim an experiment is reproducible until its inputs,
   outputs, and source revisions have been saved.
