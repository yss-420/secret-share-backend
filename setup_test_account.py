#!/usr/bin/env python3
"""
Test Account Setup Script for TrafficJunky Compliance Review
Run this after the test Telegram account starts your bot for the first time.
"""

import os
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# Initialize Supabase (same as your main bot)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

def setup_test_account(telegram_id: int):
    """Setup test account with premium access and gems for TrafficJunky review."""
    
    print(f"Setting up test account for Telegram ID: {telegram_id}")
    
    try:
        # 1. Update user with premium subscription and gems
        now = datetime.now(timezone.utc)
        subscription_end = now + timedelta(days=365)  # 1 year premium
        
        update_data = {
            'gems': 1000,  # Plenty of gems for testing all features
            'subscription_type': 'Premium',  # Premium subscription
            'subscription_end': subscription_end.isoformat(),
            'age_verified': True,  # Skip age verification for testing
            'username': 'trafficjunky_test',
            'user_name': 'Test Reviewer',
            'messages_today': 0,  # Reset daily limits
            'last_message_date': now.isoformat(),
            'last_seen': now.isoformat()
        }
        
        result = supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
        
        if result.data:
            print("✅ Test account updated successfully!")
            print(f"   - Premium subscription until: {subscription_end.strftime('%Y-%m-%d')}")
            print(f"   - Gems: 1000")
            print(f"   - Age verified: True")
            print(f"   - Username: trafficjunky_test")
        else:
            print("❌ No user found with that Telegram ID. Make sure they've started the bot first.")
            
    except Exception as e:
        print(f"❌ Error setting up test account: {e}")

def verify_test_account(telegram_id: int):
    """Verify the test account setup."""
    try:
        result = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        
        if result.data:
            user = result.data[0]
            print("\n📋 Test Account Status:")
            print(f"   - Telegram ID: {user.get('telegram_id')}")
            print(f"   - Username: {user.get('username')}")
            print(f"   - Gems: {user.get('gems')}")
            print(f"   - Subscription: {user.get('subscription_type')}")
            print(f"   - Subscription End: {user.get('subscription_end')}")
            print(f"   - Age Verified: {user.get('age_verified')}")
        else:
            print("❌ User not found")
            
    except Exception as e:
        print(f"❌ Error verifying account: {e}")

if __name__ == "__main__":
    print("TrafficJunky Test Account Setup")
    print("=" * 40)
    
    # Replace with the actual Telegram ID from your logs
    telegram_id = input("Enter the Telegram ID from your bot logs: ")
    
    try:
        telegram_id = int(telegram_id)
        setup_test_account(telegram_id)
        verify_test_account(telegram_id)
        
        print("\n🎯 Ready for TrafficJunky Review!")
        print("Provide these credentials:")
        print(f"Target URL: https://t.me/your_bot_username")
        print(f"Test Email: trafficjunky.test@gmail.com") 
        print(f"Test Email Password: [The password you set for the Gmail]")
        print(f"Additional Info: Telegram-based platform, use /start to begin")
        
    except ValueError:
        print("❌ Please enter a valid Telegram ID number")
