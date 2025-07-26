#!/usr/bin/env python3
"""
Simple bot runner using polling instead of webhooks
"""
import asyncio
import logging
from secret_share_bot import SecretShareBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run the bot with polling"""
    try:
        logger.info("Starting Secret Share Bot with polling...")
        
        # Create bot instance
        bot = SecretShareBot()
        
        # Start the bot with polling
        await bot.run_polling()
        
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
