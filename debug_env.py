#!/usr/bin/env python3
"""Debug environment variables in Railway"""
import os

print("=== ENVIRONMENT VARIABLES DEBUG ===")
env_vars = [
    "TELEGRAM_BOT_TOKEN",
    "SUPABASE_URL", 
    "SUPABASE_KEY",
    "REPLICATE_API_TOKEN",
    "WAVESPEED_API_TOKEN",
    "ADMIN_CHAT_ID",
    "ELEVENLABS_API_KEY"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: SET (length: {len(value)})")
    else:
        print(f"❌ {var}: NOT SET")

print("\n=== ALL ENVIRONMENT VARIABLES ===")
all_vars = dict(os.environ)
for key in sorted(all_vars.keys()):
    if any(x in key.lower() for x in ['token', 'key', 'secret', 'url']):
        print(f"{key}: {'SET' if all_vars[key] else 'EMPTY'}")
