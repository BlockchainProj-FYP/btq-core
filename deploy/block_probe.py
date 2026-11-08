#!/usr/bin/env python3
"""Timestamp local ZMQ hashblock notifications into private JSONL."""

import argparse
import json
from pathlib import Path
import signal
import time

import zmq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    args = parser.parse_args()
    context = zmq.Context()
    sock = context.socket(zmq.SUB)
    sock.setsockopt(zmq.SUBSCRIBE, b"hashblock")
    sock.setsockopt(zmq.RCVTIMEO, 500)
    sock.connect(args.endpoint)
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last_seq = None
    try:
        # PUB/SUB has no subscription acknowledgement. Allow the local link to
        # settle before telling the scheduler it may generate its first block.
        time.sleep(0.5)
        with args.output.open("x", buffering=1) as stream:
            args.ready.write_text("ready\n")
            while not stopping:
                try:
                    frames = sock.recv_multipart()
                except zmq.Again:
                    continue
                if len(frames) != 3 or frames[0] != b"hashblock" or len(frames[1]) != 32 or len(frames[2]) != 4:
                    raise ValueError("unexpected hashblock ZMQ frame")
                seq = int.from_bytes(frames[2], "little")
                record = {
                    "run_id": args.run_id, "node": args.node,
                    "topic": "hashblock", "hash": frames[1].hex(),
                    "t_unix_ns": time.time_ns(), "t_monotonic_ns": time.monotonic_ns(),
                    "seq": seq, "gap": last_seq is not None and seq != (last_seq + 1) % (2**32),
                }
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                last_seq = seq
    finally:
        sock.close(linger=0)
        context.term()


if __name__ == "__main__":
    main()
