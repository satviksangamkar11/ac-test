"""Send one command to the AbletonMCP Remote Script (localhost:9877). Usage: live_cmd.py <type> '<json params>'"""
import json
import socket
import sys


def cmd(kind, params=None):
    s = socket.create_connection(("localhost", 9877), timeout=15)
    s.sendall(json.dumps({"type": kind, "params": params or {}}).encode())
    buf = b""
    while True:
        buf += s.recv(65536)
        try:
            return json.loads(buf)
        except ValueError:
            continue


if __name__ == "__main__":
    print(json.dumps(cmd(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}), indent=1))
