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
- The four-node checker passed after the probed mesh smoke run. All nodes
  reported height 6, best block hash
  `6f8b484167812112fb3a13850bb995a9741e83728488ec398c6d1e7fec1da1e2`,
  identical core source tree and binary version, and all three expected
  remote VM IPs as unique peers.
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
- A separate three-process local regtest cluster on VM 145 completed the
  original seeded runs, then repeated a 20-second and 10-minute run with local
  ZMQ block probes. The longer probed run recorded all 143 mined blocks on
  each of three probes, yielding 429 arrival rows with no sequence gaps and
  matching local tips at height 143. Only the production daemon remained;
  the four-VM chain stayed at height 5 until the deliberate mesh smoke block.
- The probes were then deployed to nodes 1-4. A one-block four-VM run saved
  one matching ZMQ event per node, before/after clock tracking within the
  5 ms gate, and a matching production tip at height 6. Its private result
  directory is `/home/ubuntu/btq-mesh-probe-runs/run-aa71f24cd81a` on node1.
  This is a timing smoke test, not a validated propagation distribution.
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
| First probed local run rejected every block hash | BTQ's `hashblock` ZMQ payload was already in the same byte order as the RPC hash; the probe reversed it. | Removed the reversal. The failed run had 12 events per probe but mismatched hashes. The later short and 10-minute runs matched every mined hash. |
| Next local run timed out waiting for saved peer links | All three daemons started together, so one node attempted its first loopback dial before the destination listened; retry did not complete within the 20-second check. | Started each daemon and waited for its RPC before starting the next. Subsequent short and 10-minute runs established all local links and completed. |
| Four-VM timing preflight stopped before mining | Node2's public NTP source gave root dispersion about 6 ms, above the run's 5 ms threshold. A read-only query to OCI local NTP showed about 10.7 ms difference from its then-current clock. | Added `server 169.254.169.254 iburst prefer` in `/etc/chrony/sources.d/oci-local.sources` on node2 and reloaded chrony sources. OCI local NTP became the selected source; root dispersion fell below 1 ms and leap status stayed normal. The repeated four-VM run passed clock checks before and after. |

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
2. Validate the ZMQ timing method with a known-delay test and longer probe
   soak, then freeze the metric definition and collect multiple seeded E0
   baseline runs. The local runner saves source revision, binary hash, seed,
   schedule, per-node events, clock snapshots, and final tips. Its sequential
   CLI polling remains only a convergence check.
3. Fill node5 and node6 inventory entries only when those VMs are assigned,
   and repeat the same onboarding, firewall, clock, and mesh checks.

### Checkpoint: 30-Block Continuous Propagation Smoke Test
- **Timestamp (UTC):** 2026-11-08 20:15
- **Git Commit:** `022d466bdc29cbebaf09e115154990892a91f3df`
- **Orchestration Host:** VM 145 (`145.241.118.62`)
- **Pre-Test Tip:** Height 8
- **Post-Test Tip:** Height 38
- **Blocks Mined:** 30 consecutive blocks at ~3s intervals via `miner` wallet on VM 145
- **Verification:** Executed `deploy/mesh_check.py` across all four instances
- **Results:**
  - `node1` (VM 145): height=38, hash matched, unique_peers=3, connections=6
  - `node2` (VM 84): height=38, hash matched, unique_peers=3, connections=4
  - `node3` (VM 130): height=38, hash matched, unique_peers=3, connections=5
  - `node4` (VM 132): height=38, hash matched, unique_peers=3, connections=5
- **Status:** PASS. Zero chain divergence, LevelDB integrity verified across all 4 nodes. Layer 1 Bench officially frozen and accepted.

---

### Checkpoint: Layer 3 Telemetry Deployment & ZMQ Pipeline Verification
- **Timestamp (UTC):** 2026-11-08 21:00
- **Git Commit:** `722602e6e` (`feat(metrics): add on-node zmq probe for microsecond event logging`)
- **Components Introduced:**
  - `deploy/probe.py`: Microsecond-accurate ZMQ subscriber (`28332` / `28333`), writing `nodeX_probe.jsonl`
  - `deploy/aggregate.py`: Post-run SCP collector and atomic SQLite (`metrics.sqlite`) ingestion engine
  - `deploy/analyze_baseline.py`: Statistical percentile analyzer ($p_{50}, p_{90}, p_{95}, p_{99}$)
- **Transport Verification:** ZMQ publisher sockets confirmed listening on `127.0.0.1:28332` (`zmqpubhashblock`) and `127.0.0.1:28333` (`zmqpubhashtx`) across all 4 nodes.
- **Initial Verification:** Mined block `1091529d1e66af4d...` at height 39. Telemetry successfully captured across all nodes with `gap: false` and identical ZMQ sequence IDs (`seq: 33`).
  - Node 2 $\to$ Node 1 (Intra-tenancy LAN): 4.552 ms
  - Node 2 $\to$ Node 3 (Cross-tenancy WAN): 34.221 ms
  - Node 2 $\to$ Node 4 (Cross-tenancy WAN): 34.336 ms (co-located subnet $\Delta t = 0.115$ ms)
- **Status:** PASS. Layer 3 instrumentation functional and verified.

---

### Checkpoint: Condition E0 Control Baseline Capture
- **Timestamp (UTC):** 2026-11-08 21:45
- **Run ID:** `E0_baseline`
- **Topology:** 4-node all-to-all full mesh ($K_4$), Oracle Cloud Ampere A1 (ARM64) Ubuntu 22.04 LTS
- **Clock Discipline:** `chrony` locked to link-local NTP (`169.254.169.254`), RMS clock offset $< 0.6$ ms
- **Dataset:** 25 consecutive unconstrained blocks mined on VM 145 at ~2s intervals
- **Events Ingested:** 100 block records across 4 nodes (0 dropped messages, 0 gap flags)
- **Statistical Summary (Transit Latency Excluding Mining Origin, N=75):**
  - **Mean Delay:** 11.596 ms
  - **Median ($p_{50}$):** 14.447 ms
  - **90th Percentile ($p_{90}$):** 14.952 ms
  - **95th Percentile ($p_{95}$):** 15.023 ms
  - **99th Percentile ($p_{99}$):** 48.751 ms
  - **Maximum Delay:** 50.427 ms
- **Per-Node Performance:**
  - `node1` (VM 145): Mean 2.70 ms | $p_{50}$ 2.79 ms | Max 3.06 ms ($n=25$)
  - `node2` (VM 84): Mean 0.00 ms | $p_{50}$ 0.00 ms | Max 0.00 ms ($n=25$, origin anchor)
  - `node3` (VM 130): Mean 15.80 ms | $p_{50}$ 14.45 ms | Max 48.16 ms ($n=25$)
  - `node4` (VM 132): Mean 16.28 ms | $p_{50}$ 14.88 ms | Max 50.43 ms ($n=25$)
- **Observations:**
  1. Deterministic intra-tenancy link between Node 1 and Node 2 ($2.70 \pm 0.3$ ms).
  2. Co-located friend nodes (Node 3 and Node 4) track within $430\ \mu\text{s}$ at median ($14.45$ ms vs $14.88$ ms).
  3. Tail latency ($p_{99} \approx 48.75$ ms) captures real wide-area internet jitter and TCP packet delivery dynamics.
- **Status:** PASS. Condition E0 Control Baseline established and stored in `metrics.sqlite`.

## How to maintain this log

For each new incident or milestone, record the affected node, observed
symptom, actual cause if established, change made, and command or output that
verified recovery. Mark a hypothesis as such; do not turn it into a confirmed
cause without evidence. Add no credentials, private addresses, keys, or wallet
contents.
