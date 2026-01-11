from fastmcp import FastMCP, Context
from finnhub import Client
import logging
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Any

MCP_SERVER_NAME = "mcp-finnhub"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(MCP_SERVER_NAME)

mcp = FastMCP(MCP_SERVER_NAME)

# Rate limiting configuration
_last_request_time = 0.0
_request_lock = threading.Lock()
# Conservative interval of 1.1 seconds to avoid rate limits (60/min)
RATE_LIMIT_INTERVAL = 1.1

# Request counting for progress tracking
_total_requests_served = 0
_count_lock = threading.Lock()

# Singleton client instance
_client: Client | None = None
_client_lock = threading.Lock()

def wait_for_rate_limit():
    """Ensure that we don't exceed the API rate limit."""
    global _last_request_time
    with _request_lock:
        current_time = time.time()
        time_since_last = current_time - _last_request_time
        if time_since_last < RATE_LIMIT_INTERVAL:
            sleep_time = RATE_LIMIT_INTERVAL - time_since_last
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        _last_request_time = time.time()

async def execute_with_retry(func, *args, ctx: Context | None = None, **kwargs):
    """Execute API call with retry logic for 429 Too Many Requests.
    
    Args:
        func: The API function to call
        *args: Positional arguments for the function
        ctx: Optional FastMCP Context for progress reporting to client
        **kwargs: Keyword arguments for the function
    """
    global _total_requests_served
    max_retries = 3
    base_wait = 5  # Minimum wait time for 429

    for attempt in range(max_retries + 1):
        wait_for_rate_limit()
        try:
            result = func(*args, **kwargs)
            with _count_lock:
                _total_requests_served += 1
            return result
        except Exception as e:
            # Check for 429 status code in common exception patterns
            status = getattr(e, "status", None) or getattr(e, "status_code", None) or getattr(e, "code", None)
            
            if str(status) == "429":
                if attempt == max_retries:
                    logger.error("Max retries exceeded for 429 Too Many Requests")
                    raise e
                
                # Wait time increases: 5s, 10s, 15s...
                wait_time = base_wait * (attempt + 1)
                msg = (
                    f"Rate limited (429). Waiting {wait_time}s before retry "
                    f"(Attempt {attempt + 1}/{max_retries})..."
                )
                logger.warning(msg)
                
                # Report progress to MCP client if context available
                if ctx:
                    await ctx.report_progress(
                        progress=attempt,
                        total=max_retries,
                        message=msg
                    )
                
                time.sleep(wait_time)
            else:
                raise e

def get_client() -> Client:
    """Get or create the singleton Finnhub client instance."""
    global _client
    with _client_lock:
        if _client is None:
            api_key = os.environ.get("FINNHUB_API_KEY")
            if not api_key:
                raise ValueError("FINNHUB_API_KEY environment variable is not set")
            _client = Client(api_key=api_key)
            logger.info("Finnhub client initialized")
        return _client


def validate_stock_symbol(stock: str) -> str:
    """Validate and normalize stock symbol."""
    if not stock or not stock.strip():
        raise ValueError("Stock symbol is required and cannot be empty")
    symbol = stock.strip().upper()
    if not symbol.isalnum() and '.' not in symbol and '-' not in symbol:
        raise ValueError(f"Invalid stock symbol format: {stock}")
    if len(symbol) > 10:
        raise ValueError(f"Stock symbol too long: {stock}")
    return symbol


@mcp.tool(
    name="list_news",
    description="""Fetch latest financial market news from Finnhub.

Parameters:
- category: News category. Valid values: 'general', 'forex', 'crypto', 'merger'. Default: 'general'
- count: Maximum number of articles to return. Default: 10
- days: Only return news from the past N days. Optional.

Returns: List of news articles with headline, source, summary, url, and publication date."""
)
async def list_news(category: str = "general", count: int = 10, days: int | None = None, ctx: Context | None = None) -> list[dict[str, Any]]:
    """Fetch latest market news."""
    valid_categories = {"general", "forex", "crypto", "merger"}
    if category not in valid_categories:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}")
    if count < 1 or count > 100:
        raise ValueError("Count must be between 1 and 100")
    if days is not None and days < 1:
        raise ValueError("Days must be a positive integer")

    logger.info(f"Fetching {category} news (count={count}, days={days})")
    if ctx:
        await ctx.info(f"Fetching {category} news...")
    
    news = await execute_with_retry(get_client().general_news, category, ctx=ctx)

    if days:
        min_ts = (datetime.now() - timedelta(days=days)).timestamp()
        news = [n for n in news if n.get("datetime", 0) > min_ts]

    for n in news:
        if "datetime" in n:
            n["datetime"] = datetime.fromtimestamp(n["datetime"]).strftime("%Y-%m-%d")

    return news[:count]


@mcp.tool(
    name="get_market_data",
    description="""Get real-time market quote data for a specific stock.

Parameters:
- stock: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')

Returns: Quote data including:
- c: Current price
- h: High price of the day
- l: Low price of the day
- o: Open price of the day
- pc: Previous close price
- t: Timestamp
- d: Change (current - previous close)
- dp: Percent change"""
)
async def get_market_data(stock: str, ctx: Context | None = None) -> dict[str, Any]:
    """Get real-time market quote for a stock."""
    symbol = validate_stock_symbol(stock)
    logger.info(f"Fetching market data for {symbol}")
    if ctx:
        await ctx.info(f"Fetching market data for {symbol}...")
    return await execute_with_retry(get_client().quote, symbol, ctx=ctx)


@mcp.tool(
    name="get_basic_financials",
    description="""Get comprehensive financial metrics for a company.

Parameters:
- stock: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')
- metric: Type of metrics to retrieve. Valid values: 'all', 'price', 'valuation', 'margin'. Default: 'all'

Returns: Financial metrics including:
- 52-week high/low
- Beta
- Market capitalization
- P/E ratio
- EPS
- Dividend yield
- Revenue/profit margins
- And many more fundamental indicators"""
)
async def get_basic_financials(stock: str, metric: str = "all", ctx: Context | None = None) -> dict[str, Any]:
    """Get basic financial metrics for a company."""
    symbol = validate_stock_symbol(stock)
    valid_metrics = {"all", "price", "valuation", "margin"}
    if metric not in valid_metrics:
        raise ValueError(f"Invalid metric '{metric}'. Must be one of: {', '.join(valid_metrics)}")
    
    logger.info(f"Fetching basic financials for {symbol} (metric={metric})")
    if ctx:
        await ctx.info(f"Fetching basic financials for {symbol}...")
    return await execute_with_retry(get_client().company_basic_financials, symbol, metric, ctx=ctx)


@mcp.tool(
    name="get_recommendation_trends",
    description="""Get analyst recommendation trends for a stock over time.

Parameters:
- stock: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')

Returns: Monthly breakdown of analyst recommendations including:
- buy: Number of buy recommendations
- hold: Number of hold recommendations  
- sell: Number of sell recommendations
- strongBuy: Number of strong buy recommendations
- strongSell: Number of strong sell recommendations
- period: The month of the recommendation data

Useful for understanding market sentiment and analyst consensus on a stock."""
)
async def get_recommendation_trends(stock: str, ctx: Context | None = None) -> list[dict[str, Any]]:
    """Get analyst recommendation trends for a stock."""
    symbol = validate_stock_symbol(stock)
    logger.info(f"Fetching recommendation trends for {symbol}")
    if ctx:
        await ctx.info(f"Fetching recommendation trends for {symbol}...")
    return await execute_with_retry(get_client().recommendation_trends, symbol, ctx=ctx)
