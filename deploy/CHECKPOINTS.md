# BTQ testbed checkpoints

This is the short handoff for the next work session. Update it after every
completed task. Put detailed failures and fixes in [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
Do not include credentials, private keys, wallet data, or raw node config.

## Current checkpoint

**Completed task:** On-node ZMQ block probes were added to the isolated runner
and deployed to all four VMs. The 20-second and 10-minute isolated runs on VM
145 completed with every block recorded by all three probes. A controlled
one-block four-VM timing smoke run then passed its mesh, probe, and clock gates.

**Evidence:** VM 145's private isolated run
`/home/ubuntu/btq-local-runs/run-de7bcbbf4f10` has manifest `complete`, 143
mined blocks, 143 ZMQ records per local node, 429 arrival rows, no sequence
gaps, and three matching tips at height 143. Its before/after chrony readings
had normal leap status. The four-VM run
`/home/ubuntu/btq-mesh-probe-runs/run-aa71f24cd81a` has manifest `complete`,
one matching block event per VM, no probe gaps, before/after clock checks
within the 5 ms gate, and mesh checker `PASS` before and after mining. All four
production nodes now report height `6` and hash
`6f8b484167812112fb3a13850bb995a9741e83728488ec398c6d1e7fec1da1e2`.
All temporary probes exited.

**Scope of this result:** These are timing smoke tests. The real-mesh table has
only one block and has not been validated with known delay, probe soak, or
multiple seeds. The current bench has four of the six planned VMs. The local
cluster is process-based, not Docker Compose. The mesh checker confirms
connectivity and chain consistency; matching source tree and version strings
are not a binary attestation.

**Next task:** Validate timing accuracy with a controlled known-delay test and
a longer probe soak, then freeze the metric definition and run several seeded
E0 baseline replicates. Keep the four-VM result labelled preliminary.

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
| Probed isolated runs | Added one loopback ZMQ probe per local node and chrony snapshots to the manifest. Repeated a 20-second run and a 10-minute run on VM 145. | Short run: 12 events per probe. Long run: 143 events per probe, 429 arrival rows, matching local tips, no sequence gaps; production mesh unchanged at height 5. |
| Four-VM probe deployment and smoke run | Installed probe code and pyzmq on nodes 1-4. Added OCI local NTP as a preferred chrony source on node2 after its public source failed the clock gate. Ran one production regtest block from node1. | Four matching ZMQ events, normal leap status and under 5 ms offset/dispersion before and after, no sequence gaps, temporary probes stopped, all nodes at height 6 with the same hash and mesh checker `PASS`. |

## Update after the next task

1. Replace **Current checkpoint** with the new completed task, its command or
   artifact evidence, the next single task, and any open issue.
2. Add one concise row to **Completed checkpoints**. Preserve prior rows.
3. Put the full problem, diagnosis, fix, and verification in
   [OPERATIONS_LOG.md](OPERATIONS_LOG.md).
4. Commit both Markdown files with the code or configuration change they
   describe. Never claim an experiment is reproducible until its inputs,
   outputs, and source revisions have been saved.
