# BTQ Testbed Coding Session Playbook

This workflow assumes you have four active SSH sessions open
simultaneously: - **Terminal 1:** VM 145 (`node1` --- Miner /
Orchestrator / SQLite host) - **Terminal 2:** VM 84 (`node2` --- Peer
validator, LAN) - **Terminal 3:** VM 130 (`node3` --- Peer validator,
WAN) - **Terminal 4:** VM 132 (`node4` --- Commit station / Git push
host)

------------------------------------------------------------------------

## Part 1: Starting a Coding Session (Spin-Up & Pre-Flight)

### 1. Check Clock Discipline (Run on ALL Terminals)

Microsecond-accurate propagation metrics require sub-millisecond clock
drift. Run on **VM 145, VM 84, VM 130, and VM 132**:

``` bash
chronyc tracking | grep -E "Reference|System time|RMS offset"
```

*Verification:* Ensure `RMS offset` is under `0.005000` seconds (5 ms).

------------------------------------------------------------------------

### 2. Verify Daemons & Socket Bindings (Run on ALL Terminals)

Verify that `btqd` is active and listening on the designated ports on
**VM 145, VM 84, VM 130, and VM 132**:

``` bash
sudo ss -tulpn | grep -E "19444|18443|28332|28333"
```

*Ports:*

-   `19444`: P2P v2 encrypted mesh transport
-   `18443`: Local JSON-RPC (`127.0.0.1`)
-   `28332`: ZMQ `hashblock` (`127.0.0.1`)
-   `28333`: ZMQ `hashtx` (`127.0.0.1`)

*(If the daemon is stopped on any node, start it immediately:)*

``` bash
~/btq-core/src/btqd -regtest -daemon
```

------------------------------------------------------------------------

### 3. Assert Cluster Consensus Health (Run on VM 145)

Run the automated consensus monitor to verify peer count, tip parity,
and Git revision across the mesh:

``` bash
cd ~/btq-core
.venv/bin/python deploy/mesh_check.py
```

*Verification:* Must print `ALL CHECKS PASSED (PASS)` with all 4 nodes
reporting identical `height`, matching `bestblockhash`, and
`unique_peers >= 3`.

------------------------------------------------------------------------

### 4. Sync Working Tree on Commit Station (Run on VM 132)

Ensure the commit station is clean and up to date before making changes:

``` bash
cd ~/btq-core
git status
git pull origin master
```

------------------------------------------------------------------------

## Part 2: Testing Procedures During the Session

### Test Suite A: Mesh Consensus Sanity Check

Whenever you produce blocks, modify peer settings, or restart daemons,
run this on **VM 145**:

``` bash
cd ~/btq-core
.venv/bin/python deploy/mesh_check.py
```

------------------------------------------------------------------------

### Test Suite B: C++ Code Build & Unit Tests (Run on VM 132)

When modifying consensus validation or mempool rules (e.g., BIP-361 C++
patches):

1.  **Compile with all available ARM64 cores:**

``` bash
cd ~/btq-core/build
ninja -j$(nproc)
```

*(Or if using GNU Make: `make -j$(nproc)`)*

2.  **Execute Bitcoin/BTQ unit test binary:**

``` bash
./src/test/test_btq
```

3.  **Run specific functional tests:**

``` bash
test/functional/test_runner.py p2p_invalid_block.py
```

------------------------------------------------------------------------

### Test Suite C: Live Telemetry Run (Condition Profiling)

#### 1. Clean previous logs and start `probe.py` in background

**On VM 145 (Node 1):**

``` bash
pkill -f probe.py 2>/dev/null || true
> /home/ubuntu/node1_probe.jsonl
nohup python3 ~/btq-core/deploy/probe.py node1 /home/ubuntu/node1_probe.jsonl > /dev/null 2>&1 &
pgrep -fa probe.py
```

**On VM 84 (Node 2):**

``` bash
pkill -f probe.py 2>/dev/null || true
> /home/ubuntu/node2_probe.jsonl
nohup python3 ~/btq-core/deploy/probe.py node2 /home/ubuntu/node2_probe.jsonl > /dev/null 2>&1 &
pgrep -fa probe.py
```

**On VM 130 (Node 3):**

``` bash
pkill -f probe.py 2>/dev/null || true
> /home/ubuntu/node3_probe.jsonl
nohup python3 ~/btq-core/deploy/probe.py node3 /home/ubuntu/node3_probe.jsonl > /dev/null 2>&1 &
pgrep -fa probe.py
```

**On VM 132 (Node 4):**

``` bash
pkill -f probe.py 2>/dev/null || true
> /home/ubuntu/node4_probe.jsonl
nohup python3 ~/btq-core/deploy/probe.py node4 /home/ubuntu/node4_probe.jsonl > /dev/null 2>&1 &
pgrep -fa probe.py
```

------------------------------------------------------------------------

#### 2. Mine experimental batch (Run on VM 145)

Mine a controlled batch of blocks (adjust `COUNT` and `INTERVAL_SEC` as
needed):

``` bash
python3 -c '
import subprocess, time

addr = "mvPv5KhwPGk8sTP97VgBhCSHkcwcbGW5BK"
COUNT = 25
INTERVAL_SEC = 2

print(f"Mining {COUNT} blocks...")
for i in range(1, COUNT + 1):
    subprocess.check_output([
        "/home/ubuntu/btq-core/src/btq-cli", "-regtest",
        "-rpcwallet=miner", "generatetoaddress", "1", addr
    ])
    print(f"[{i:02d}/{COUNT}] Block mined")
    time.sleep(INTERVAL_SEC)
print("Finished.")
'
```

------------------------------------------------------------------------

#### 3. Ingest logs into SQLite (Run on VM 145)

Pull remote JSONL logs and ingest them under a unique run tag:

``` bash
cd ~/btq-core
python3 deploy/aggregate.py <RUN_TAG>
```

\*Example: `python3 deploy/aggregate.py E1_phaseA_test*`

------------------------------------------------------------------------

#### 4. Compute statistical propagation report (Run on VM 145)

Calculate $p_{50}, p_{90}, p_{95}, p_{99}$ percentiles:

``` bash
python3 deploy/analyze_baseline.py <RUN_TAG>
```

------------------------------------------------------------------------

## Part 3: Ending a Coding Session (Wrap-Up & Clean Teardown)

### 1. Stop Background Probes (Run on ALL Terminals)

Terminate running probe listeners so background logging halts on **VM
145, VM 84, VM 130, and VM 132**:

``` bash
pkill -f probe.py 2>/dev/null || true
```

*(Leave `btqd` running in the background).*

------------------------------------------------------------------------

### 2. Snapshot the Telemetry Database (Run on VM 145)

Create a timestamped backup of the SQLite metrics database:

``` bash
cd ~/btq-core
cp metrics.sqlite "metrics_backup_$(date +%Y%m%d_%H%M%S).sqlite"
ls -lh metrics*.sqlite
```

------------------------------------------------------------------------

### 3. Stage, Commit, and Push Code (Run on VM 132)

Review changes, commit, and push from your designated commit host:

``` bash
cd ~/btq-core
git status
git diff

# Stage specific files (or git add .)
git add deploy/
git commit -m "feat(scope): detailed description of changes"
git push origin master
```

------------------------------------------------------------------------

### 4. Sync Remote Nodes (Run on VM 145, VM 84, and VM 130)

Update all other nodes to the new commit hash:

**On VM 145:**

``` bash
cd ~/btq-core && git pull origin master
```

**On VM 84:**

``` bash
cd ~/btq-core && git pull origin master
```

**On VM 130:**

``` bash
cd ~/btq-core && git pull origin master
```

------------------------------------------------------------------------

### 5. Final Consensus Sanity Verification (Run on VM 145)

Confirm all nodes are in sync and ready for the next session:

``` bash
cd ~/btq-core
.venv/bin/python deploy/mesh_check.py
```

*Verification:* Must exit with `ALL CHECKS PASSED (PASS)`. The session
is cleanly closed.
