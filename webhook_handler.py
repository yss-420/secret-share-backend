#!/usr/bin/env python3
"""
RunPod Webhook Handler for Secret Share Bot
"""
import os
import json
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_telegram_update(update_data):
    """Process a Telegram update using the existing bot logic"""
    try:
        # Import the bot class
        from secret_share_bot import SecretShareBot
        
        # Get bot token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found")
        
        # Create Telegram objects
        bot = Bot(token=bot_token)
        application = Application.builder().token(bot_token).build()
        
        # Create Update object from webhook data
        update = Update.de_json(update_data, bot)
        if not update:
            return {"status": "error", "message": "Invalid update data"}
        
        # Initialize our bot handler
        secret_bot = SecretShareBot()
        
        # Process different types of updates
        if update.message:
            logger.info(f"Processing message: {update.message.text}")
            await secret_bot.handle_message(update, application)
        elif update.callback_query:
            logger.info("Processing callback query")
            await secret_bot.handle_callback_query(update, application)
        elif hasattr(update, 'web_app_data') and update.web_app_data:
            logger.info("Processing web app data")
            await secret_bot.handle_webapp_data(update, application)
        else:
            logger.info("Update type not handled")
        
        return {"status": "success", "message": "Update processed"}
        
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return {"status": "error", "message": str(e)}

def handler(event):
    """Main RunPod handler function"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Handle different event formats
        if isinstance(event, dict):
            # Check for RunPod API format
            if "input" in event:
                input_data = event["input"]
                logger.info("Processing RunPod API call")
                
                # If input contains Telegram update
                if any(key in input_data for key in ["message", "callback_query", "web_app_data"]):
                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(process_telegram_update(input_data))
                    loop.close()
                    return result
                else:
                    # Simple test/health check
                    return {"status": "success", "message": "Bot is running", "data": input_data}
            
            # Direct webhook format (Telegram sends update directly)
            elif any(key in event for key in ["message", "callback_query", "web_app_data"]):
                logger.info("Processing direct Telegram webhook")
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(process_telegram_update(event))
                loop.close()
                return result
        
        # Default response
        logger.info("No recognizable update format")
        return {"status": "success", "message": "Event received"}
        
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}

# For testing locally
if __name__ == "__main__":
    test_event = {
        "input": {
            "message": {
                "message_id": 1,
                "from": {"id": 123456, "first_name": "Test"},
                "chat": {"id": 123456, "type": "private"},
                "date": 1640995200,
                "text": "Hello bot"
            }
        }
    }
    result = handler(test_event)
    print(json.dumps(result, indent=2))
