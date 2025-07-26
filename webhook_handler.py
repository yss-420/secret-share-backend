#!/usr/bin/env python3
"""
Simple webhook handler for RunPod
"""
import json
import os
import sys

def handler(event):
    """
    Simple handler for Telegram webhooks
    """
    try:
        print(f"Webhook received: {json.dumps(event)}")
        
        # Return success for all webhook calls
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "success", "message": "Webhook received"})
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500, 
            "body": json.dumps({"status": "error", "message": str(e)})
        }

if __name__ == "__main__":
    # Test the handler
    test_event = {"message": {"text": "test"}}
    result = handler(test_event)
    print(result)
