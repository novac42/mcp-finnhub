# Finnhub MCP Server

An MCP server to interface with Finnhub API.

### Tools

- `list_news`

  - List latest market news from Finnhub [market news endpoint](https://finnhub.io/docs/api/market-news)

- `get_market_data`

  - Get market data for a particular stock from [quote endpoint](https://finnhub.io/docs/api/quote)

- `get_basic_financials`

  - Get basic financials for a particular stock from [basic financials endpoint](https://finnhub.io/docs/api/company-basic-financials)

- `get_recommendation_trends`
  - Get recommendation trends for a particular stock from [recommendation trend endpoint](https://finnhub.io/docs/api/recommendation-trends)

## Configuration

This MCP server is designed to be run with `uvx` (part of the [uv](https://docs.astral.sh/uv/) toolkit).

### Quickstart (Claude Desktop)

Add the following to your Claude Desktop configuration file:

- On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "finnhub": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/<YOUR_USERNAME>/mcp-finnhub.git", "finnhub-mcp"],
      "env": {
        "FINNHUB_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

Replace `YOUR_API_KEY` with your actual [Finnhub API Key](https://finnhub.io/).
Replace `<YOUR_USERNAME>` with your GitHub username (or the owner of the fork you are using).

### Environment Variables

- `FINNHUB_API_KEY`: **Required**. Your Finnhub API key. This must be passed via the `env` configuration in your MCP client or set in the environment where `finnhub-mcp` runs.

## Troubleshooting

- **Error: FINNHUB_API_KEY environment variable is not set**: Ensure you have added the `"env"` section to your MCP config with the correct key.
- **Command not found (uvx)**: Ensure you have `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

## Development

To develop or run locally from source:

1. Clone the repository.
2. Run `uv sync` to create a virtual environment and install dependencies.
3. Run `fastmcp dev src/finnhub_mcp/server.py` to start the inspector.

To run the server locally (stdio) via the installed console script:

`FINNHUB_API_KEY=YOUR_API_KEY uv run finnhub-mcp`

