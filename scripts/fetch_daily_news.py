import os
import sys
import json
import time
import logging
from datetime import datetime, date, timezone
from typing import Any, List

import finnhub

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fetch_daily_news")

def get_client() -> finnhub.Client:
    """Get the Finnhub client instance."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        logger.error("FINNHUB_API_KEY environment variable is not set")
        sys.exit(1)
    return finnhub.Client(api_key=api_key)

def fetch_general_news(client: finnhub.Client, category: str = "general") -> List[dict]:
    """Fetch general news with basic error handling."""
    try:
        # Finnhub python client's general_news returns a list of dictionaries
        return client.general_news(category, min_id=0)
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        sys.exit(1)

def main():
    # 1. Initialize Client
    client = get_client()
    
    # 2. Fetch News (Category: general)
    logger.info("Fetching general news...")
    news_items = fetch_general_news(client, "general")
    
    # 3. Process News
    # Requirement: "count为30条" (Check top 30 items)
    # Requirement: "日期是当天" (Filter out older news from those 30)
    
    # Get start of current day in UTC to compare with news timestamp
    # Finnhub returns 'datetime' as unix timestamp
    now = datetime.now(timezone.utc)
    # Start of today (00:00:00 UTC)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_today_ts = start_of_today.timestamp()
    
    processed_news = []
    
    # Slice first 30 items
    subset = news_items[:30]
    
    for item in subset:
        item_ts = item.get("datetime", 0)
        
        # Filter: Only keep news from today
        if item_ts >= start_of_today_ts:
            # Format Date: Unix -> YYYYMMDD
            # We add a new field 'formatted_date' or replace existing? 
            # Request says "date needs to change from unix format to YYYYMMDD"
            # server.py replaces 'datetime' with string.
            # We will create a formatted string for the 'datetime' field.
            
            dt_object = datetime.fromtimestamp(item_ts, tz=timezone.utc)
            item["datetime"] = dt_object.strftime("%Y%m%d")
            
            processed_news.append(item)
    
    logger.info(f"Processed {len(processed_news)} news items from the top 30.")

    # 4. Save to JSON
    # Use today's date in the filename
    today_str = now.strftime("%Y%m%d")
    output_file = f"news_output_{today_str}.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_news, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved news to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
