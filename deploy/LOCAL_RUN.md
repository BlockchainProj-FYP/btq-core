# First isolated block run

`local_run.py` is the first repeatable Layer 2 smoke-run tool. It starts three
BTQ Core regtest processes on one host, each with a fresh private data
directory. P2P and RPC ports bind to loopback and do not touch the existing
four-VM chain. It saves the seed, planned schedule, source identity, binary
hash, individual block events, and final chain tips under `~/btq-local-runs`.
Each of the three local node pairs has one configured dial direction, avoiding
duplicate sessions while retaining a complete three-node mesh.

This is a process-based local cluster on one VM, not the planned Docker
cluster. Its `poll_convergence_ms` field includes sequential CLI polling and
must not be used as a scientific propagation measurement. On-node event
probes and clock validation come later. The exponential schedule is a
provisional workload choice; freeze the experiment spec before reporting
comparative results.

## On VM 145

Pull the latest team fork, then inspect a plan without starting nodes:

```bash
cd ~/btq-core
git pull --ff-only origin master
python3 deploy/local_run.py --seed 7 --duration 20 --mean-interval 4
```

Run a short isolated smoke test:

```bash
python3 deploy/local_run.py --seed 7 --duration 20 --mean-interval 4 --execute
```

The command prints the run directory. Inspect its `manifest.json`,
`schedule.json`, and `events.jsonl`; the node directories also contain each
node's logs and wallet. Keep the entire run directory private because node
configs contain credentials. Confirm `status` is `complete` and all three
`final_tips` match.

After the short run works, the proposed first 10-minute baseline is:

```bash
python3 deploy/local_run.py --seed 7 --duration 600 --mean-interval 5 --execute
```

Run the production four-node mesh checker separately before and after the
local run to confirm that chain remains unchanged. The local tool uses P2P
ports 19550-19552 and RPC ports 18550-18552 on 127.0.0.1. It checks that
these ports are free before execution and stops all three local nodes at the
end, including after a normal error or Ctrl+C. If the process is forcibly
killed, inspect any remaining `btqd` processes and stop only those using the
run directory; do not stop the production `btqd.service`.

Do not commit `~/btq-local-runs` or copy its private node configs to GitHub.
After review, publish a redacted manifest and any nonsecret derived results
as an experiment artifact if the team chooses.
