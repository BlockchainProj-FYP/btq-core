# BTQ testbed operations log

This log records the work and troubleshooting completed for the BIP-361 research
testbed. It describes observed outcomes rather than treating the build plan as
implemented. Update it whenever a configuration, topology, or experiment
procedure changes. Keep RPC credentials, private keys, wallet files, and raw
private configuration out of Git.

## Current verified state

- Four Oracle VMs run BTQ Core regtest: Hussain's nodes at `145.241.118.62`
  (node1) and `84.235.244.35` (node2), and Abyaan's nodes at
  `130.210.56.76` (node3) and `132.226.188.199` (node4).
- The four-node checker passed after the isolated 10-minute run. All nodes
  reported height 5, best block hash
  `667dae19063fd494b36fbca79b2da46431f0b116dd36a73ad0e0432d1cce5a0e`,
  identical core source tree and binary version, and all three expected
  remote VM IPs as unique peers. Documentation revisions differ across VMs.
- `btqd` and chrony are enabled as systemd services on all four VMs. Nodes
  have `txindex=1`, `fallbackfee=0.0001`, microsecond log timestamps,
  `debug=bench`, and loopback-only ZMQ publishers. RPC is loopback-only on
  port 18443, P2P uses port 19444, and the dashboard proxy uses loopback port
  4000 where running.
- Each node has persistent `addnode` entries for the other three VMs. The
  four-node checker verifies unique peer IPs, matching chain tips, and matching
  core source trees and binary version strings. `deploy/addressing.yaml` is
  the shared inventory.
- A block mined on node1 propagated to all four nodes (height 4). A block
  mined on node3 propagated to all four nodes (height 5). These are smoke
  tests, not research-grade propagation latency measurements.
- A separate three-process local regtest cluster on VM 145 completed both a
  short seeded run (12 planned and recorded blocks) and a 10-minute seeded
  run (143 planned and recorded blocks). In the longer run, all three local
  tips matched at height 143 and hash
  `7b01437650e36c600f387ae0dd608738756d6d59a01c781c923ca87b1637f744`.
  Only the production daemon remained afterward; the four-VM chain stayed at
  height 5.
- VM 84's dashboard source snapshot is installed at
  `~/Frontend/btq-dashboard`. Its proxy is now a boot-managed systemd service,
  bound to `127.0.0.1:4000`. It returned HTTP 200 and RPC height 5 after a
  reboot. The local laptop dashboard uses an SSH RPC tunnel to node1.
  Dashboard code and the VM 84 service template live in the separate private
  `BlockchainProj-FYP/Frontend` repository, with the service template added in
  commit `d7e89db`.

## Problems encountered and resolutions

| Problem | Cause or evidence | Resolution and verification |
|---|---|---|
| BTQ daemon rejected `port`, `rpcport`, and `rpcbind` on regtest | Network-specific options were outside `[regtest]` in `btq.conf`. | Moved network-specific options under `[regtest]`; RPC and P2P started successfully. |
| RPC CLI timed out after credentials changed | Config was rewritten while the running daemon still used its old RPC credentials. | Stopped the daemon before editing, preserved each node's credentials, and restarted cleanly. Never regenerate a password under a running daemon. |
| Early peer lists were empty or incomplete | Peer port access and host firewall rules were not uniform. | Scoped TCP 19444 rules and peer connections were added. Matching block height and hash later confirmed propagation. |
| Duplicate inbound and outbound connections inflated connection counts | Multiple sessions to the same public IP appeared in `getpeerinfo`. | Checker counts unique remote IPs; three expected addresses per node constitute the current full mesh. |
| Dashboard deployment using SSH deploy keys was blocked | The GitHub organization disables repository deploy keys. | Distinct public/private keypairs were prepared on Hussain's VMs, but they do not grant repository access under current policy. VM 84 received a committed source snapshot over SSH. Never add a VM key to a personal GitHub account for broad access. |
| A proposed mesh checker embedded a literal RPC password | The pasted plan assumed one shared credential for all nodes and exposed a password-shaped value in the proposal. | Replaced it with SSH-based checks that read each VM's existing local config. Whether the pasted value matches any live credential has not been established; rotate it on any VM where it does. |
| Friend dashboard clone failed with `Permission denied (publickey)` | Private Frontend repository access was not granted by an active deploy key. | Stop after `git ls-remote` fails; do not run `npm` from `~/btq-core` or place dashboard `.env` there. Use an approved repository access method or a committed source snapshot. |
| VM 84 had Node 12, too old for the dashboard | The VM is ARM64 and its system Node package was old. | Installed a checksum-verified official Node 22 ARM64 build under the ubuntu user's home, installed dependencies, built the frontend, and verified HTTP 200 and RPC height 3. |
| Local dashboard tunnel could not bind port 18443 | That laptop port was already in use. | Used local port 18444 for the SSH RPC tunnel and set the private dashboard `.env` to that port. |
| Local dashboard processes initially could not bind loopback ports in the tool sandbox | Starting the API and Vite in the restricted environment returned `EPERM`. | Started them with the required local execution permission, then verified API height 3 and frontend HTTP 200. |
| `deploy/requirements.txt` was reported missing | Commands were run from `/home/ubuntu` instead of `~/btq-core`. | Changed to `~/btq-core` before running `deploy/mesh_check.py`. The checker needs to run on only one machine with authorized SSH to all targets. |
| Python virtual environment could not bootstrap pip | `python3-venv` was absent on node1. | Installed `python3-venv`, recreated `.venv`, installed PyYAML, and ran the checker. |
| The node1 repository showed `.venv/` as untracked | The core fork's root `.gitignore` did not exclude local Python virtual environments. | Added `.venv/` to `.gitignore` so a future broad `git add` cannot include the environment. The separate untracked `nodesource_setup.sh` still requires operator review and must not be committed blindly. |
| Re-running the config renderer on node2 raised `FileExistsError` | A private `btq.conf.candidate` already existed; the renderer intentionally refuses to overwrite an existing file. | Reviewed the existing candidate instead. Its mode was `0600`, nonsecret settings and peers were correct, credentials matched the live config in a comparison that printed no secret, and the installed service matched the committed template. |
| Node3's renderer initially failed with `ModuleNotFoundError: yaml` | PyYAML was absent from that VM's `.venv`, even though the renderer existed. | Installed the pinned major range from `deploy/requirements.txt` into the VM's virtual environment, then rendered and reviewed the candidate. Its mode, peers, nonsecret flags, private credential comparison, and service unit all passed. The live config was not replaced. |
| Node4 candidate review completed | The last VM needed a renderer and service-template check. | Its candidate mode was `0600`, the expected nonsecret flags and three peers were present, a private comparison confirmed RPC credentials matched the live config, and the installed service matched the template. Node1's credentials were also compared privately; all four candidates now pass. No live config was replaced. |
| Node1 could not SSH into node2 | First, the node2 SSH host key was unknown; then public-key authentication was missing. | Verified node2's ED25519 host fingerprint with its operator, created a dedicated `btq_mesh_check` key on node1, authorized its public half on node1 and node2, and configured SSH to use it. The private half remained on node1. |
| Node1 could not inspect Abyaan's VMs | Their host keys and authorization had not been established. | Abyaan supplied host fingerprints and authorized the public checker key. After verification, node1 could SSH into nodes 3 and 4 and the full checker passed. |
| Initial GitHub push methods failed | Shell HTTPS had no usable credentials; the connected GitHub integration could read the repository but returned `403` for a write. | Used the operator's existing authenticated GitHub SSH identity and verified the remote branch matched the local parent before pushing deployment commit `869926f`. |
| Chrony initially reported large skew and root dispersion | Readings were taken immediately after service installation. | Waited for synchronization. Later readings showed active sources, normal leap status, and substantially reduced offsets/dispersion. Check clock quality again before each timing run. |
| Normal `btqd -help` did not list `logtimemicros` | It is a debug-only option. | Confirmed it in `btqd -help-debug` and in this core revision's source before enabling it. |
| VM 84 lost direct peer links when the daemon restarted | Runtime `addnode` calls do not survive daemon restart. | Added the other three addresses to VM 84's `[regtest]` config. Then added persistent peer entries on the other VMs and reran the checker after each restart. |
| RPC briefly timed out immediately after `systemctl restart btqd` | The daemon had not finished startup when the CLI ran. | Waited for readiness; subsequent RPC calls and full mesh checks passed. Treat a lasting error or failed service state as a real fault. |
| Reboot of node3 broke its direct link to node4 | Both friend-owned host firewalls rejected new inbound P2P connections from one another. | Abyaan added and saved scoped TCP 19444 rules with `netfilter-persistent`; after reboot, the rule survived and the link returned. |
| Reboot of node2 temporarily broke its direct links to nodes 3 and 4 | Saved peers were retrying, and node2-initiated TCP 19444 connections toward those VMs timed out even when host firewall rules were present. The opposite direction connected. | Abyaan added saved host firewall rules for the Hussain VM IPs. The friend-owned nodes' outbound connections eventually re-established the full mesh. Cloud ingress for node2-initiated connections remains to be reviewed if both initiation directions are required. |
| Reboot of node1 removed its previous broad P2P host rule | The original TCP 19444 rule had not been saved. | Replaced it with three `/32` peer-specific rules, ran `netfilter-persistent save`, rebooted again, and confirmed the rules and full mesh persisted. |
| VM 84 dashboard stopped after VM reboot | Its server was launched as a process, not a boot-managed service. | Added `btq-dashboard.service` to the private Frontend repository and installed it on VM 84. After a reboot, the service was active, API and RPC reported height 5, frontend returned HTTP 200, and port 4000 listened only on 127.0.0.1. |
| Checker rejected documentation-only repository drift | Nodes had pulled successive operations-log commits, so `git rev-parse HEAD` differed even though BTQ core source and binary version were unchanged. | Changed the checker to report each revision but compare the core `src` tree and binary version string. A live four-node check passed with matching height 5, hash, source tree, version string, and three expected peers per node despite differing repository revisions. This is not a binary attestation. |
| First isolated local run did not establish all saved peer links | Configuring every local node to dial every other node created duplicate inbound/outbound sessions; `getaddednodeinfo` could report one redundant dial disconnected although other links were active. | Configured only one dial per node pair and disabled onion listening. A subsequent short run completed with 12 blocks and matching tips. |
| A 10-minute run initially failed its port preflight | TCP sockets from the short run temporarily made some fixed loopback ports appear busy, although no extra daemon remained. | Set `SO_REUSEADDR` in the preflight check and moved port validation before creation of a run directory. The next 10-minute run started. |
| The 10-minute run's SSH session ended before verification | The SSH client reported that VM 145 was not responding. The run's private directory had been observed with a running manifest and recorded events, but completion was not observed through that session. | A later SSH check found manifest `complete`, 143 of 143 event records, three matching local tips at height 143, no remaining local daemons, and a production four-node checker `PASS` at height 5. |

## Repository and configuration decisions

- Public team fork: `BlockchainProj-FYP/btq-core`, default branch `master`.
  The first deployment commit, `869926f`, added `deploy/addressing.yaml`,
  `deploy/mesh_check.py`, and instructions. The newer configuration renderer
  and unit template are in this directory.
- Private dashboard repository: `BlockchainProj-FYP/Frontend`, `main` at
  least through `d7e89db` when the VM 84 service template was added. Keep
  dashboard code there; keep BTQ node configuration, mesh checks, and
  experiment infrastructure with the core fork until a separate testbed
  repository is created.
- Do not push `~/.btq/btq.conf`, `server/.env`, SSH keys, wallet directories,
  node data, or RPC history. The committed renderer makes a private candidate
  config and preserves each node's own credentials.
- P2P requires one working connection per pair; both inbound and outbound
  sessions are not required. The checker requires all expected unique remote
  IPs. Identical height alone is insufficient; compare best-block hashes.
- `onetry` makes a one-off attempt. `addnode ... add` is runtime state;
  `addnode=` in `btq.conf` persists across daemon restart.
- Node1 rendered a mode `0600` candidate from its live config. The reviewed
  nonsecret settings and peers were correct, and its installed service matched
  the committed template. The live config and service were not replaced.

## Next work

1. Review the OCI ingress rules for TCP 19444 and document the remaining
   direction-dependent connection behavior. Keep RPC and ZMQ private.
2. Add on-node event probes and clock-quality records for actual timing
   metrics. The completed local runner saves source revision, binary hash,
   seed, schedule, block events, and final tips, but its sequential CLI
   polling is not a propagation-latency measurement.
3. Fill node5 and node6 inventory entries only when those VMs are assigned,
   and repeat the same onboarding, firewall, clock, and mesh checks.

## How to maintain this log

For each new incident or milestone, record the affected node, observed
symptom, actual cause if established, change made, and command or output that
verified recovery. Mark a hypothesis as such; do not turn it into a confirmed
cause without evidence. Add no credentials, private addresses, keys, or wallet
contents.
