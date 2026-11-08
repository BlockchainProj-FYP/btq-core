# BTQ testbed checkpoints

This is the short handoff for the next work session. Update it after every
completed task. Put detailed failures and fixes in [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
Do not include credentials, private keys, wallet data, or raw node config.

## Current checkpoint

**Completed task:** The seeded, isolated 10-minute regtest run on VM 145
completed. Its manifest reports `complete`, all 143 planned blocks have event
records, and all three local nodes ended at height 143 with the same tip. The
local nodes stopped; the production four-VM chain remained at height 5.

**Evidence:** Private run directory
`/home/ubuntu/btq-local-runs/run-21d08b1395a6` contains 143 block events and
three final tips at hash
`7b01437650e36c600f387ae0dd608738756d6d59a01c781c923ca87b1637f744`.
Only the production `btqd` process remained. The four-node checker returned
`PASS`: all nodes reported height `5`, hash
`667dae19063fd494b36fbca79b2da46431f0b116dd36a73ad0e0432d1cce5a0e`,
the same core source tree and binary version, and three expected peer IPs.

**Scope of this result:** The current bench has four nodes. The BIP-361 plan
calls for six, plus a local cluster, orchestration, metrics, and enforcement.
The checker is a connectivity and chain-consistency check, not a propagation
latency measurement. Repository revision is not a binary attestation.

**Next task:** Add on-node block event probes and clock-quality records, then
define the timing metric and freeze the experiment protocol before comparing
propagation results. The current sequential CLI polling is only a smoke test.

**Open issue:** VM 84-initiated TCP 19444 connections toward Abyaan's VMs
timed out after reboot, although Abyaan's saved outbound connections restored
the full mesh. Review OCI ingress rules and record any topology or cloud rule
change before a controlled experiment. A planning draft contained a literal
RPC password; verify whether it matches any live VM and rotate it there if it
does.

## Completed checkpoints

| Checkpoint | Outcome | Evidence |
|---|---|---|
| Team repositories | Public `btq-core` fork and private `Frontend` repository established; dashboard code on `Frontend/main`. | Core fork and dashboard repository available to the team. |
| Two Hussain nodes | Matching BTQ Core build, regtest RPC, mining wallet, and P2P. | Same core source commit and block hash on both nodes. |
| Four-node connectivity | Hussain and Abyaan nodes peered with three expected unique peers each. | `deploy/mesh_check.py` returned `PASS` on all four. |
| Dashboard on VM 84 | Source snapshot deployed, Node 22 installed, frontend built, API returned height 3 through an SSH tunnel. | HTTP 200 and RPC result 3 at setup; later boot startup was completed. |
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
| Isolated short run | Ran three new local regtest nodes on VM 145 with seed 7, a 20-second window, and four-second mean block interval. | 12 planned and 12 recorded blocks; matching local height 12 and tips; private run directory mode `0700`; no extra `btqd` left running; production four-node checker `PASS` at height 5. |
| Isolated 10-minute run | Ran the three-node local cluster on VM 145 with seed 7, a 600-second window, and five-second mean block interval. | Manifest `complete`; 143 planned and recorded blocks; all local tips match at height 143; only production `btqd` remains; four-node mesh checker `PASS` at height 5. |

## Update after the next task

1. Replace **Current checkpoint** with the new completed task, its command or
   artifact evidence, the next single task, and any open issue.
2. Add one concise row to **Completed checkpoints**. Preserve prior rows.
3. Put the full problem, diagnosis, fix, and verification in
   [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
4. Commit both Markdown files with the code or configuration change they
   describe. Never claim an experiment is reproducible until its inputs,
   outputs, and source revisions have been saved.
