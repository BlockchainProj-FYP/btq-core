# Project work records

After completing any task for this testbed, update `deploy/CHECKPOINTS.md` with
the completed outcome, evidence, next task, and open issue. Add the detailed
problem, diagnosis, fix, and verification to `deploy/OPERATIONS_LOG.md` when
the task involved troubleshooting or an operational change. Commit those
updates with the related code or documentation so GitHub remains the shared
handoff. Use no timestamps unless the project team requests them.

Never commit RPC credentials, private keys, wallet files, node data, or private
`.env` files. Keep `btq.conf` candidates private. Verify chain consistency by
height **and** best-block hash, and count unique peer IPs rather than raw
connection totals.
