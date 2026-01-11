import os
import sys
from finnhub_mcp.server import mcp

def main():
    """Entry point for the finnhub-mcp CLI."""
    if not os.environ.get("FINNHUB_API_KEY"):
        print("Error: FINNHUB_API_KEY environment variable is not set.", file=sys.stderr)
        print("Please set it in your MCP client configuration.", file=sys.stderr)
        sys.exit(1)
    
    mcp.run()

if __name__ == "__main__":
    main()
