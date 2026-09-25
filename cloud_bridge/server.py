import os
import sys

from mcp.server.fastmcp import FastMCP
from pythonosc.udp_client import SimpleUDPClient

SECRET = os.environ.get("MCP_BRIDGE_SECRET", "")
if len(SECRET) < 20:
    sys.exit("Set MCP_BRIDGE_SECRET (run start.ps1, which generates one).")

osc = SimpleUDPClient("127.0.0.1", 11000)
mcp = FastMCP(
    "ableton-ping",
    host="127.0.0.1",
    port=8000,
    streamable_http_path=f"/mcp-{SECRET}",
    stateless_http=True,
)


@mcp.tool()
def ping(bpm: float = 97.0) -> str:
    """Set Ableton tempo via AbletonOSC."""
    if not 20.0 <= bpm <= 999.0:
        return f"rejected - bpm {bpm} outside Ableton range 20-999"
    osc.send_message("/live/song/set/tempo", bpm)
    return f"pong - sent tempo {bpm}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
