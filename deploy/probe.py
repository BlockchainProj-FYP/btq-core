import json
import sys
import time
import zmq

node_id = sys.argv[1] if len(sys.argv) > 1 else "node1"
out_file = sys.argv[2] if len(sys.argv) > 2 else f"/home/ubuntu/{node_id}_probe.jsonl"

ctx = zmq.Context()
sock = ctx.socket(zmq.SUB)
sock.connect("tcp://127.0.0.1:28332")
sock.connect("tcp://127.0.0.1:28333")

sock.setsockopt(zmq.SUBSCRIBE, b"hashblock")
sock.setsockopt(zmq.SUBSCRIBE, b"hashtx")

last_seq = {}

with open(out_file, "a", buffering=1) as f:
    while True:
        topic, body, seq = sock.recv_multipart()
        s = int.from_bytes(seq, "little")
        t_str = topic.decode("utf-8")
        gap = t_str in last_seq and s != last_seq[t_str] + 1
        last_seq[t_str] = s

        record = {
            "n": node_id,
            "t_ns": time.time_ns(),
            "topic": t_str,
            "id": body.hex(),
            "seq": s,
            "gap": gap
        }
        f.write(json.dumps(record) + "\n")