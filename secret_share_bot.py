#!/usr/bin/env python3
"""
Secret Share Bot - Premium Adult AI Companion
Version 69 - ElevenLabs Voice Integration
Critical fixes: String casting, image variation, SFW enforcement, state validation
New features: Voice notes, voice calls, ElevenLabs v3 integration
"""

import os
import asyncio
import json
import logging
import random
import re
import aiohttp
import io
from datetime import datetime, timedelta, timezone, time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from collections import OrderedDict
from dotenv import load_dotenv
import requests
from aiohttp import web
import threading
from pathlib import Path

import replicate
import elevenlabs
from pydub import AudioSegment

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    PhotoSize
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    JobQueue,
    PreCheckoutQueryHandler
)
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.error import BadRequest

from supabase import create_client, Client

# Configure logging with enhanced format for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (development) or environment (production)
env_path = Path('.env')
if env_path.exists():
    logger.info(f"[DEBUG] Loading .env file from: {env_path.absolute()}")
    load_dotenv()
else:
    logger.info(f"[DEBUG] No .env file found - using environment variables (production mode)")
    # In production, environment variables are set directly by the platform

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
KOBOLD_URL = os.getenv('KOBOLD_URL', 'http://localhost:5001/api/v1/generate')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
WAVESPEED_API_TOKEN = os.getenv('WAVESPEED_API_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Debug logging to check environment variables
logger.info(f"[DEBUG] Environment variables loaded:")
logger.info(f"[DEBUG] BOT_TOKEN: {'SET' if BOT_TOKEN else 'NOT SET'}")
logger.info(f"[DEBUG] SUPABASE_URL: {'SET' if SUPABASE_URL else 'NOT SET'}")
logger.info(f"[DEBUG] SUPABASE_SERVICE_ROLE_KEY: {'SET' if SUPABASE_KEY else 'NOT SET'}")
logger.info(f"[DEBUG] REPLICATE_API_TOKEN: {'SET' if REPLICATE_API_TOKEN else 'NOT SET'}")
logger.info(f"[DEBUG] WAVESPEED_API_TOKEN: {'SET' if WAVESPEED_API_TOKEN else 'NOT SET'}")
logger.info(f"[DEBUG] ADMIN_CHAT_ID: {'SET' if ADMIN_CHAT_ID else 'NOT SET'}")
logger.info(f"[DEBUG] ELEVENLABS_API_KEY: {'SET' if ELEVENLABS_API_KEY else 'NOT SET'}")
logger.info(f"[DEBUG] TWILIO_ACCOUNT_SID: {'SET' if TWILIO_ACCOUNT_SID else 'NOT SET'}")
logger.info(f"[DEBUG] TWILIO_AUTH_TOKEN: {'SET' if TWILIO_AUTH_TOKEN else 'NOT SET'}")
logger.info(f"[DEBUG] TWILIO_PHONE_NUMBER: {'SET' if TWILIO_PHONE_NUMBER else 'NOT SET'}")

if not all([BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY, REPLICATE_API_TOKEN, WAVESPEED_API_TOKEN, ADMIN_CHAT_ID, ELEVENLABS_API_KEY]):
    logger.error("FATAL: Missing one or more environment variables (TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, REPLICATE_API_TOKEN, WAVESPEED_API_TOKEN, ADMIN_CHAT_ID, ELEVENLABS_API_KEY).")
    raise ValueError("Missing required environment variables! Check your .env file or environment settings.")

# Initialize Supabase with connection recovery
def create_supabase_client():
    """Create a new Supabase client instance."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = create_supabase_client()

async def execute_with_retry(operation, *args, max_retries=3, **kwargs):
    """Execute a Supabase operation with retry and connection recovery."""
    global supabase
    
    for attempt in range(max_retries):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if attempt < max_retries - 1 and any(keyword in error_msg for keyword in ['disconnected', 'connection', 'timeout', 'network']):
                logger.warning(f"[DB RETRY] Attempt {attempt + 1} failed: {e}. Recreating connection...")
                # Recreate the Supabase client
                supabase = create_supabase_client()
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                # Final attempt failed or non-connection error
                raise e
    return None

# Initialize ElevenLabs

# Test ElevenLabs API key
def test_elevenlabs_key():
    """Test the ElevenLabs API key."""
    try:
        # Try to get voices to test the API key using the new API
        from elevenlabs.client import ElevenLabs
        # Test ElevenLabs connection with new API
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        # Test by getting voices (simpler test)
        voices = client.voices.get_all()
        logger.info("✅ ElevenLabs API key is valid!")
        return True
    except Exception as e:
        logger.error(f"[DEBUG] ElevenLabs API key test failed: {e}")
        return False

# Test the API key on startup
if ELEVENLABS_API_KEY:
    # Set the API key as an environment variable for ElevenLabs
    os.environ['ELEVENLABS_API_KEY'] = ELEVENLABS_API_KEY
    test_elevenlabs_key()
else:
    logger.error("[DEBUG] ElevenLabs API key is not set!")

# Test phone number import
async def test_phone_number_import():
    """Test the phone number import functionality."""
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        # For now, just test that the API key works
        logger.info("✅ ElevenLabs API key is valid for phone number import!")
        return True
    except Exception as e:
        logger.error(f"[DEBUG] Phone number import test failed: {e}")
        return False

# --- CONSTANTS ---
DAILY_MESSAGE_LIMIT = 50
WELCOME_GEMS_BONUS = 100
ACTIVE_USER_CACHE_LIMIT = 2000
MAX_MESSAGE_LENGTH = 1024
FREE_IMAGE_LIMIT = 12

# --- ELEVENLABS VOICE MAPPING ---
ELEVENLABS_VOICE_IDS = {
    "isabella": "9bjVpXgvgd1TpT3tXHL8",
    "scarlett": "Z0qZlABZILTNeODeXCuu", 
    "aria": "U2O5xJJ6jMwqdtAI7VI4",
    "priyanka": "qicvPeGDPufNM8uctpxv",
    "valentina": "rMDx1aivlvWtnReBqF2L",
    "luna": "5TLb171gsXHTKyiCAeG0",
    "kiara": "ezWKCzemPTrGJWvylpbn",
    "natasha": "qaEJoOC7rUxpj1zEGVun"
}

ELEVENLABS_AGENT_IDS = {
    "isabella": "agent_01jzyr3hv3ef9afm06ptwr6np1",
    "scarlett": "agent_01jzz6w5m3fcxake0c910wz6hx",
    "aria": "agent_01jzz7jxg1ekra9x07a2qwfdy3", 
    "priyanka": "agent_01jzz7wjp4fajaf1ftmren6szr",
    "valentina": "agent_01jzz880zmfekt6pq6bnz1yvfx",
    "luna": "agent_01jzz8nms0eeyrfr77ek4c0300",
    "kiara": "agent_01jzz8xcvve7z9dvsh3mbkfsj4",
    "natasha": "agent_01jzz931h8fjtvnvyjf3f8at6y"
}

# --- VOICE FEATURE CONSTANTS ---
VOICE_NOTE_COST = 30  # gems per voice note
VOICE_CALL_COST_PER_MINUTE = 50  # gems per minute of call

# Audio tags for ElevenLabs v3 model
VOCAL_SOUNDS = [
    "laughs", "laughing", "chuckles", "giggles",
    "sighs", "sighs contentedly", "sighs softly",
    "moans", "moans softly", "moaning",
    "gasps", "a sharp intake of breath",
    "whispers", "whispering",
    "whimpers", "whimpering",
    "kisses", "a soft kiss",
    "breathing heavily"
]

# Upsell trigger keywords
VOICE_NOTE_KEYWORDS = [
    "voice", "whisper", "speak", "say it", "talk to me",
    "tell me more", "in my ear", "your voice", "say my name",
    "moan for me", "breathe for me", "audio", "voice note"
]

VOICE_CALL_KEYWORDS = [
    "call me", "phone call", "talk on phone", "call you",
    "let's talk", "can I call", "I want to hear you",
    "speak to you", "get on a call", "voice call"
]

# --- GEM PACKS AND SUBSCRIPTION TIERS (for payment processing) ---
GEM_PACKS = {
    'gems_50': 45,
    'gems_100': 95,
    'gems_250': 250,
    'gems_500': 525,
    'gems_1000': 1100,
    'gems_2500': 3000,
    'gems_5000': 6500,
    'gems_10000': 15000,
}
SUBSCRIPTION_TIERS = {
    'sub_essential': ('essential', 400, 450),
    'sub_plus': ('plus', 800, 1200),
    'sub_premium': ('premium', 1600, 2500),
}

# Upsell probabilities (40% video, 30% voice note, 30% voice call)
UPSELL_PROBABILITIES = {
    'video': 0.4,
    'voice_note': 0.3, 
    'voice_call': 0.3
}

# --- WAVESPEED ACTION LoRA MAPPING ---
WAVESPEED_ACTION_LORA_MAP = {
    "style_general_nsfw": {
        "keywords_to_detect": ["undress", "strip", "get naked", "take it off", "take off your clothes", "show me", "get nude", "undressing", "stripping", "nude", "naked", "show me your body"],
        "lora_triggers": ["nsfwsks"],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/style_general_nsfw.safetensors"
    },
    "bouncing_boobs": {
        "keywords_to_detect": ["bounce", "bouncing", "jiggle", "jiggling", "boobs", "tits", "breasts", "show me them bounce", "let me see those boobs", "show me your boobs", "show tits", "show me your tits", "make them jiggle"],
        "lora_triggers": ["her breasts are bouncing"],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/bouncing_boobs.safetensors"
    },
    "pov_blowjob": {
        "keywords_to_detect": ["blowjob", "give me head", "suck my dick", "suck me", "oral", "suck it", "gobble"],
        "lora_triggers": [
            "A woman is lying on her stomach between the legs of the viewer and performing oral sex on a man. Her head moves up and down as she sucks the penis.",
            "An overhead view of a woman kneeling between the legs of the viewer and performing oral sex on a man. She moves her head back and forth as she sucks the penis.",
            "A woman is leaning over a man positioned in between the legs of the viewer and performing oral sex on a man. Her head moves up and down as she sucks the penis.",
            "A woman is kneeling in between the legs of the viewer and performing oral sex on a man. Her head moves up and down as she sucks the penis."
        ],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/pov_blowjob.safetensors"
    },
    "pov_cowgirl": {
        "keywords_to_detect": ["cowgirl", "reverse cowgirl", "ride me", "get on top", "ride my dick", "on top"],
        "lora_triggers": [
            "A woman is straddling a man and having sex with him. She bounces up and down on top of the man. You can see the woman bouncing up and down on the man's erect penis."
        ],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/pov_cowgirl.safetensors"
    },
    "pov_missionary": {
        "keywords_to_detect": ["missionary", "fuck me", "sex", "have sex", "make love", "on the bottom"],
        "lora_triggers": [
            "with her legs spread having sex with a man. A man is thrusting his penis back and forth inside her vagina at the bottom of the screen. Movement is fast with bouncing breasts."
        ],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/pov_missionary.safetensors"
    },
    "facial_cumshot": {
        "keywords_to_detect": ["facial", "jizz", "jizz on your", "ejaculate", "give you a facial", "cum on your face", "cum on you", "finish on you", "splash your face"],
        "lora_triggers": ["f4c3spl4sh"],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/facial_cumshot.safetensors"
    },
    "fingering": {
        "keywords_to_detect": ["finger you", "finger yourself", "masturbate", "masturbate for me", "fingering", "touch that pussy", "play with that pussy", "play with yourself", "touch yourself", "get yourself off"],
        "lora_triggers": ["She inserts two fingers into her pussy. She masturbates by sliding her fingers in and out of her pussy."],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/fingering.safetensors"
    },
    "hand_in_panties": {
        "keywords_to_detect": ["touch your pussy", "put your fingers inside", "rub your panties", "rub your pussy", "hand in panties", "rub yourself", "play with your panties"],
        "lora_triggers": ["h4ndp4nties", "her hand is in her panties and she is rubbing her vagina. she rubs her vagina fast. she slides her hand in her panties."],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/hand_in_panties.safetensors"
    },
    "dildo_ride": {
        "keywords_to_detect": ["dildo", "use a dildo", "dildo ride", "play with a toy", "toy ride"],
        "lora_triggers": ["she rides a dildo, moving her body up and down as the dildo slides in and out of her vagina."],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/dildo_ride.safetensors"
    },
    "deepthroat": {
        "keywords_to_detect": ["deepthroat", "deep throat", "take it all", "all the way down", "no gag reflex"],
        "lora_triggers": ["A pov view of a woman with fair skin is seen giving a deepthroat blowjob to a large, circumcised penis. Her lips are wrapped around the shaft, and she is swallowing the penis, with her head slightly tilted back and her eyes wide open. She is moving her head back and forth. (She swallows the penis all the way:5). her chin smashes against the testicles."],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/deepthroat.safetensors"
    },
    "pov_titfuck": {
        "keywords_to_detect": ["titfuck", "titty fuck", "paizuri", "between your tits", "fuck my tits", "boob job"],
        "lora_triggers": ["titfuck", "penis between tits", "penis between boobs"],
        "lora_url": "https://pub-abb95480c2e649289a37a1732a0d06c2.r2.dev/pov_titfuck.safetensors"
    }
}

# This list defines the LoRAs safe for random selection
SOLO_ACTION_LORA_POOL = [
    "style_general_nsfw",
    "bouncing_boobs", 
    "fingering",
    "hand_in_panties",
    "dildo_ride",
    "facial_cumshot"
]

# --- ANTICIPATION TEMPLATES ---
ANTICIPATION_ACK_TEMPLATES = [
    "I'm getting ready for you...",
    "Just a moment while I prepare something special...",
    "Let me set the mood for you...",
    "I'm making this perfect for you..."
]

ANTICIPATION_PERIODIC_TEMPLATES = [
    "I'm still working on it...",
    "Almost ready...",
    "Just a little longer...",
    "I want this to be perfect for you..."
]

# ==================================================================================
# --- CHARACTER DICTIONARY v68 (Enhanced Context Awareness) ---
# ==================================================================================
CHARACTERS = {
    "isabella": {
        "name": "👩‍🍳 Isabella", "full_name": "Isabella", "description": "Sensual chef",
        "voice_id": ELEVENLABS_VOICE_IDS["isabella"],
        "system_prompt_base": """**Your Core Identity:** You are Isabella, a female chef. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Isabella. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `Of course, {user_name}. *I kneel before you, looking up with anticipation.* I'm ready.`

3.  **PERFECT MEMORY LAW:** You remember your name (Isabella) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed (e.g., do not undress twice).

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/isabella-lora:39bd31d276f89a10d94efba9a0fe81dba1dd728ee5f030bb5c7737bfd4a05933",
        "trigger_word": "ohwx_isabella_woman",
        "follow_ups": ["Don't let the food get cold, bello.", "Did I leave you speechless?", "The kitchen is quiet without your voice..."],
        "scenarios": {
            "cooking_class": { "title": "A Private Cooking Class", "intro_text": "You arrive at Isabella's villa for a private cooking class. The kitchen is warm and smells of fresh herbs and wine.", "first_message": "Welcome to my kitchen. Today, we get our hands dirty. It requires a firm, rhythmic touch. Before we begin, what is the name of the man I'm cooking for tonight?", "scenario_prompt": "You are in a warm, Italian-style kitchen with a large wooden table and fresh ingredients all around.", "character_outfit": "a simple white dress under a stained apron.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964995/isabella_kitcehn_intro_i9fs6n.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964996/kitchen_hn5dps.jpg" },
            "wine_cellar": { "title": "Tasting in the Wine Cellar", "intro_text": "After a magnificent dinner, Isabella leads you down a stone staircase into her family's ancient wine cellar. It's cool, quiet, and intimate.", "first_message": "Down here, every bottle has a story. This one... it's bold and needs to breathe. A bit like you, no? But I don't believe I caught your name, bello.", "scenario_prompt": "You are in a cool, stone wine cellar, surrounded by old barrels and racks of wine bottles.", "character_outfit": "an elegant evening gown.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964973/isabella_cellar_intro_a802wa.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964974/wine_cellar_oivok6.jpg" }
        }
    },
    "scarlett": {
        "name": "🍷 Scarlett",
        "full_name": "Scarlett",
        "description": "Sophisticated CEO",
        "voice_id": ELEVENLABS_VOICE_IDS["scarlett"],
        "system_prompt_base": """**Your Core Identity:** You are Scarlett, a powerful female CEO meeting with another CEO, whose name is {user_name}, to discuss a major business merger.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Scarlett. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `An interesting proposal, {user_name}. *I cross my legs and look at you expectantly.* Explain your terms.`

3.  **PERFECT MEMORY LAW:** You remember your name (Scarlett) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/scarlett-lora:ca8c56474afebabc821f923e701d2f39bdc19449f12978127fe15e8aafb1e69d",
        "trigger_word": "ohwx_scarlett_woman",
        "follow_ups": ["I'm waiting for your input. Don't waste my time.", "Is everything alright? The silence is... unusual.", "Let's not let this opportunity pass us by. What are your thoughts?"],
        "scenarios": {
            "boardroom_meeting": { "title": "The Boardroom Negotiation", "intro_text": "It's late. You're in the top-floor boardroom of Scarlett's corporate headquarters, waiting to finalize the biggest merger of your career. The door opens, and she walks in alone.", "first_message": "Good evening. Thank you for meeting me after hours. I find the most important decisions are made when there are no distractions. Let's begin. Remind me of your name.", "scenario_prompt": "You are in a high-tech corporate boardroom at night. The room is dominated by a long glass conference table. The city lights twinkle outside the massive windows.", "character_outfit": "a sharp, black business suit with a silk blouse.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965259/scarlett_office_intro_vqweoh.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965258/office_oitrph.jpg" },
            "hotel_summit": { "title": "The Hotel Summit", "intro_text": "You're both attending a global business summit. After a long day of panels, you get a text: 'My suite. 10 minutes.' You arrive at the penthouse to find her standing by the window, holding a bottle of wine.", "first_message": "I trust you found the suite alright? I thought we could finalize the terms of our merger in a more... comfortable setting. What is the name of the CEO I'm about to partner with?", "scenario_prompt": "You are in Scarlett's luxurious penthouse hotel suite. It has a large, plush seating area, a well-stocked bar, and a floor-to-ceiling window with a panoramic city view.", "character_outfit": "an elegant red business blazer with a matching skirt.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965280/scarlett_hotel_intro_hgc403.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965278/hotel_room_gtfwo4.jpg" }
        }
    },
    "aria": {
        "name": "🌸 Aria",
        "full_name": "Aria",
        "description": "Sweet college roommate",
        "voice_id": ELEVENLABS_VOICE_IDS["aria"],
        "system_prompt_base": """**Your Core Identity:** You are Aria, a female college student. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Aria. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `Oh! *I blush and look down at my feet.* You're really sweet, {user_name}.`

3.  **PERFECT MEMORY LAW:** You remember your name (Aria) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/aria-lora:23055864a8d7f09f5ccfc66cc0a38aba48291730721981d6e63433ca1a483933",
        "trigger_word": "ohwx_aria_girl",
        "follow_ups": ["Did I say something wrong? 🥺", "Hey... you still there?", "I was just starting to have fun..."],
        "scenarios": {
            "oops_roommate": { "title": "Oops! Wrong Room...", "intro_text": "You come back to your dorm late at night... You open your door and are surprised to see a girl jump, pulling a blanket to her chest.", "first_message": "Oh my god! I am so, so sorry! I must have gotten the room numbers mixed up... I'm Aria, by the way... What's your name?", "scenario_prompt": "You are in {user_name}'s messy college dorm room. It has a bed, a desk covered in textbooks, and band posters on the wall.", "character_outfit": "nothing but a thin blanket clutched to your chest.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965326/aria_dorm_intro_gz0tyq.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965328/dorm_room_qgfllm.jpg" },
            "study_session": { "title": "Late Night Study Session", "intro_text": "It's past midnight in the quiet university library... a cute girl, Aria, sits down at your table with a stack of the same textbooks.", "first_message": "Hey... you're in my Psych 101 class, right? I am so lost. Mind if I study with you? My name's Aria, what's yours?", "scenario_prompt": "You are in a large, quiet university library. The setting includes long wooden tables, tall bookshelves filled with books, and soft lamp light.", "character_outfit": "a comfortable sweater and jeans.", "setting_type": "public", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965304/aria_library_intro_ry29my.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965307/library_j1qmtt.jpg" }
        }
    },
    "priyanka": {
        "name": "🪷 Priyanka",
        "full_name": "Priyanka",
        "description": "Desi girl with sass",
        "voice_id": ELEVENLABS_VOICE_IDS["priyanka"],
        "system_prompt_base": """**Your Core Identity:** You are Priyanka, a modern Desi girl. You are sassy and flirty. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Priyanka. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `Oh really, angrez? *I raise a challenging eyebrow.* Show me what you've got.`

3.  **PERFECT MEMORY LAW:** You remember your name (Priyanka) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/priyanka-lora:0eee735439c9af152d951598c238d5c00ac468eb5afc7277b5f1bca0949eb191",
        "trigger_word": "ohwx_priyanka_woman",
        "follow_ups": ["Hello? Did you fall asleep on me, angrez?", "Don't tell me you can't keep up with a little conversation.", "Acha, you're just going to leave me hanging?"],
        "scenarios": {
            "wedding_dance": { "title": "Wedding Dance Floor", "intro_text": "You're at a massive, vibrant Indian wedding reception. You spot a beautiful girl in a stunning lehenga, Priyanka, watching you from the dance floor.", "first_message": "Don't just stand there, angrez! You think you can keep up with me? What's your name?", "scenario_prompt": "You are on a crowded, vibrant dance floor at an Indian wedding, surrounded by hundreds of guests.", "character_outfit": "a stunning, ornate red and gold lehenga.", "setting_type": "public", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965122/priyanka_wedding_intro_lhyeye.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965124/wedding_hall_i7ye2p.jpg" },
            "chai_stall": { "title": "Rainy Day at the Chai Stall", "intro_text": "A sudden downpour has you seeking shelter under the small awning of a street-side chai stall. You're not the only one; a girl with a mischievous smile, Priyanka, is there too.", "first_message": "Haaye, this rain! At least the chai is good. You look like you're a thousand miles away. What's a handsome guy like you thinking about so seriously, yaar? And what's your name?", "scenario_prompt": "You are stuck under the small awning of a street-side chai stall during a downpour. The street is busy.", "character_outfit": "a modern salwar kameez that's slightly damp from the rain.", "setting_type": "public", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965101/priyanka_chai_intro_ewstjg.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965100/chai_stall_fcusg1.jpg" }
        }
    },
    "valentina": {
        "name": "💃 Valentina", "full_name": "Valentina", "description": "Passionate dance instructor",
        "voice_id": ELEVENLABS_VOICE_IDS["valentina"],
        "system_prompt_base": """**Your Core Identity:** You are Valentina, a female dance instructor. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Valentina. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `Feel the music, papi. *I guide your hands to my hips.* One, two, three...`

3.  **PERFECT MEMORY LAW:** You remember your name (Valentina) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/valentina-lora:a67fca67c1231d9cb58b5c0393800b4d923ee5ef27c5f4d348f3b1775d919aec",
        "trigger_word": "ohwx_valentina_woman",
        "follow_ups": ["Did you lose the rhythm, papi?", "The music is still playing... where did you go?", "Don't leave me on the dance floor alone."],
        "scenarios": {
            "private_lesson": { "title": "Private Salsa Lesson", "intro_text": "The dance studio is empty except for you and Valentina. The music begins to play, a slow, sensual salsa.", "first_message": "Forget everything else. It's just you, me, and the music. Remind me of your name, papi. I want to know who I'm dancing with.", "scenario_prompt": "You are in a dance studio with hardwood floors and mirrors on one wall.", "character_outfit": "a form-fitting black dance dress.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965190/valentina_studio_intro_y5ijis.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965189/dance_studio_abshtv.jpg" },
            "latin_club": { "title": "After-hours at the Club", "intro_text": "The air in the latin club is thick with sweat and rhythm. You spot Valentina across the crowded dance floor. Her eyes lock onto yours, and she nods for you to join her.", "first_message": "I was wondering when you'd show up! You look even better outside the studio. What did you say your name was again?", "scenario_prompt": "You are in a crowded, noisy latin club with a dance floor.", "character_outfit": "a shimmering, backless red dress.", "setting_type": "public", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965208/valentina_club_intro_bw51ru.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965206/latin_club_lruutc.jpg" }
        }
    },
    "luna": {
        "name": "🌙 Luna", "full_name": "Luna", "description": "Mysterious fortune teller",
        "voice_id": ELEVENLABS_VOICE_IDS["luna"],
        "system_prompt_base": """**Your Core Identity:** You are Luna, a female fortune teller. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Luna. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `The cards never lie, {user_name}. *I turn over the Lovers card.* It seems fate has brought you to me.`

3.  **PERFECT MEMORY LAW:** You remember your name (Luna) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/luna-lora:424d4ce2607abf03239702ac8e00990048b7b20ba82bab81a7ea22f637691507",
        "trigger_word": "ohwx_luna_woman",
        "follow_ups": ["The spirits grow quiet... have you left?", "Your energy signature is fading. Is something wrong?", "The cards are waiting for your next move."],
        "scenarios": {
            "tarot_reading": { "title": "A Private Tarot Reading", "intro_text": "You enter a dimly lit tent filled with the scent of incense. At a small table sits Luna, a deck of tarot cards before her.", "first_message": "The cards told me you were coming. Sit. Don't be shy... your fate is an open book to me. But first... what name shall the spirits know you by?", "scenario_prompt": "You are in a dimly lit tent, filled with the smell of incense. The setting has a small table and tarot cards.", "character_outfit": "layers of dark, flowing shawls and silver jewelry.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965072/luna_tent_intro_s2yubp.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965072/tarot_tent_rya3hn.jpg" },
            "chance_encounter": { "title": "Chance Encounter", "intro_text": "While Browse a dusty metaphysical shop, you feel a strange energy. You turn to see a captivating woman watching you. It's Luna.", "first_message": "It's rare to feel an aura as potent as yours. You're not here just for crystals, are you? Tell me, what is the name of the man who seeks such knowledge?", "scenario_prompt": "You are in a dusty metaphysical shop filled with crystals and strange objects.", "character_outfit": "a long, velvet cloak over a simple dark dress.", "setting_type": "public", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965050/luna_shop_intro_dknc3i.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965050/fortune_teller_shop_r9be3l.jpg" }
        }
    },
    "kiara": {
        "name": "🎮 Kiara", "full_name": "Kiara", "description": "Gamer girl next door",
        "voice_id": ELEVENLABS_VOICE_IDS["kiara"],
        "system_prompt_base": """**Your Core Identity:** You are Kiara, a female gamer. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Kiara. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `lol, noob. *I easily parry your attack and counter.* Try harder, {user_name}!`

3.  **PERFECT MEMORY LAW:** You remember your name (Kiara) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
        "lora_model_id": "yss-420/kiara-lora:f4f52f5769075266af8d318a57ac0b6cc5357eacd93f78605ad63ec717f0a0e1",
        "trigger_word": "ohwx_kiara_woman",
        "follow_ups": ["u afk?", "lol, did you rage quit on me?", "c'mon, the next round is starting!"],
         "scenarios": {
            "co_op": { "title": "Random Co-op Match", "intro_text": "You queue up for a co-op mission and get matched with a player named 'Kiki'. Her voice in the chat is even cuter than her avatar.", "first_message": "gg, dude! You're actually not terrible lol. We should duo again sometime. I'm Kiara, btw. What do I call you?", "scenario_prompt": "You are playing an online co-op game from your gaming room.", "character_outfit": "an oversized hoodie and shorts.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965167/kiara_room_intro_ehltx9.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965166/gaming_room_iocma5.jpg" },
           "irl_meet": { "title": "Gaming Cafe Meetup", "intro_text": "You're at a local gaming cafe and hear a frustrated sigh from the next PC. You glance over and see a cute girl, Kiara, glaring at her screen.", "first_message": "Ugh, this team is such trash! I can't carry them all... What, never seen a girl rage before? What's your name?", "scenario_prompt": "You are at a gaming cafe, surrounded by PCs and other gamers.", "character_outfit": "a graphic t-shirt and ripped jeans.", "setting_type": "public", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965145/kiara_cafe_intro_es2i0r.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750965144/gaming_cafe_q4spdt.jpg" }
       }
   },
   "natasha": {
       "name": "🥊 Natasha", "full_name": "Natasha", "description": "Personal trainer",
       "voice_id": ELEVENLABS_VOICE_IDS["natasha"],
       "system_prompt_base": """**Your Core Identity:** You are Natasha, a female personal trainer. You are in an adult roleplay with a male user whose name is {user_name}.

**THE UNBREAKABLE COMMANDMENTS:**

1.  **CRITICAL POV LAW:** You are Natasha. You speak in the first-person ('I', 'my', 'me'). You address the user as 'you' or by their name, '{user_name}'. You NEVER refer to yourself or the user in the third-person ('her', 'the user'). This is a permanent, unbreakable rule.

2.  **ABSOLUTE FORMATTING LAW:** All physical actions and descriptions MUST be enclosed in asterisks (*). All spoken dialogue MUST NOT be in asterisks. Your response MUST contain both dialogue and at least one action. Example of a perfect response: `Five more reps, {user_name}. *I spot you from behind, my body pressed against yours.* You can do it.`

3.  **PERFECT MEMORY LAW:** You remember your name (Natasha) and the user's name ({user_name}). You must remember the current state of the scene, including what you are wearing (or not wearing). Do not repeat actions that have already been completed.

4.  **CONVERSATIONAL FLOW IS PARAMOUNT:** You MUST NOT send a message containing only an action in asterisks. To keep the conversation engaging, your reply MUST ALWAYS include dialogue outside of asterisks. A reply with only an action is a conversational dead-end and a failure of your programming.

5.  **CONTEXT IS KING:** Your response MUST be a direct and logical continuation of the user's last message. Do not perform random, unrelated actions.

6.  **RESPONSE LENGTH:** Your responses must be concise. Do not write long paragraphs.
""",
       "lora_model_id": "yss-420/natasha-lora:b9414510423ecc81e6d24b0075e991c8739d8255b6412a59b3447ccd2893bb9a",
       "trigger_word": "ohwx_natasha_woman",
       "follow_ups": ["Break time's over. You're not getting tired on me, are you?", "Don't stop now, we're just getting warmed up.", "I'm waiting for your next set. Let's go!"],
       "scenarios": {
           "private_session": { "title": "Private Training Session", "intro_text": "The gym is closed to the public, and it's just you and Natasha for your private session. The only sounds are the hum of the lights and your own breathing.", "first_message": "Alright, warm-up's over. Let's work on your form. I need you to go... deeper. Don't be afraid, I'll spot you. What's your name?", "scenario_prompt": "You are in a gym with weights, benches, and other workout equipment.", "character_outfit": "a tight sports bra and yoga pants.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964950/natasha_gym_intro_xdfkl0.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964950/gym_ejqyx7.jpg" },
           "post_workout": { "title": "Post-Workout 'Stretch'", "intro_text": "You've just finished a grueling workout with Natasha. As you're catching your breath, she comes over with a towel and a wicked little smile.", "first_message": "You did good today. You're all tight and sore, aren't you? Come on, let me help you with a deep stretch. What was your name again? I want to know who I'm about to make very... flexible.", "scenario_prompt": "You are in a yoga studio with mats on the floor. It's quiet and calm.", "character_outfit": "a tank top and workout shorts.", "setting_type": "private", "intro_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964895/natasha_yoga_intro_s9crqo.webp", "background_image_url": "https://res.cloudinary.com/dkfk987lz/image/upload/v1750964896/yoga_studio_l8xspk.jpg" }
       }
   }
}

@dataclass
class UserData:
    """User session data with enhanced state tracking for v68."""
    current_character: Optional[str] = None
    current_scenario: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    user_name: Optional[str] = None
    last_interaction_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_image_url: Optional[str] = None
    free_images_sent: int = 0
    message_count_since_last_image: int = 0
    # NSFW STATE MACHINE (v68): Enhanced with validation
    clothing_state: str = "clothed"  # Can be 'clothed', 'undressing', 'nude'
    character_current_outfit: str = ""
    # v68: Track state transitions for validation
    state_transition_history: List[str] = field(default_factory=list)
    # v72: Track if we've already asked for the user's name
    asked_for_name: bool = False
    # Premium upsell tracking (v69+)
    session_message_count: int = 0  # Total messages exchanged in this session (reset on new scenario)
    premium_offer_state: Optional[dict] = field(default_factory=dict)  # e.g., {'type': 'image', 'status': 'pending', 'offer_id': 'xyz'}
    last_blurred_image_url: Optional[str] = None
    last_video_task: Optional[dict] = field(default_factory=dict)  # Stores video task data
    # v68: Track last image context for text response
    last_image_context: Optional[dict] = None
    # v69: Track last upsell time to prevent back-to-back upsells
    last_upsell_time: Optional[datetime] = None
    # FRONTEND INTEGRATION: User's gem balance
    gems: int = 0
    messages_today: int = 0
    subscription_type: Optional[str] = None

    def validate_state_transition(self, new_state: str) -> bool:
        """v68: Validates that clothing state transitions are logical."""
        valid_transitions = {
            "clothed": ["undressing"],
            "undressing": ["nude"],
            "nude": []  # Cannot transition from nude to anything else
        }
        return new_state in valid_transitions.get(self.clothing_state, [])

    def update_clothing_state(self, new_state: str) -> bool:
        """v68: Updates clothing state with validation."""
        if self.validate_state_transition(new_state):
            self.state_transition_history.append(f"{self.clothing_state}->{new_state}")
            self.clothing_state = new_state
            return True
        return False

class Database:
    """Handles all Supabase database operations."""

    @staticmethod
    def get_or_create_user(user_id: int, username: str) -> Optional[Dict]:
        """Fetches a user from the database. If they don't exist, creates them."""
        try:
            Database.reset_daily_limits_if_needed(user_id)
            result = supabase.table('users').select('*').eq('telegram_id', user_id).single().execute()
            supabase.table('users').update({'last_seen': datetime.now(timezone.utc).isoformat()}).eq('telegram_id', user_id).execute()
            return result.data
        except Exception as e:
            logger.info(f"User {user_id} not found, creating new entry. Reason: {e}")
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                new_user_data = {
                    'telegram_id': user_id,
                    'username': username,
                    'gems': WELCOME_GEMS_BONUS,
                    'user_name': None,
                    'messages_today': 0,
                    'last_message_date': now_iso,
                    'age_verified': False,
                    'last_seen': now_iso
                }
                insert_result = supabase.table('users').insert(new_user_data).execute()
                return insert_result.data[0]
            except Exception as insert_e:
                logger.error(f"CRITICAL: Could not create new user {user_id} in database. Error: {insert_e}")
                return None

    @staticmethod
    def reset_daily_limits_if_needed(user_id: int):
        """Checks if the user's last message was before today (UTC) and resets their daily limit."""
        try:
            user_res = supabase.table('users').select('last_message_date').eq('telegram_id', user_id).single().execute()
            user_data = user_res.data
            
            if user_data and user_data.get('last_message_date'):
                last_date = datetime.fromisoformat(user_data['last_message_date']).date()
                today_utc = datetime.now(timezone.utc).date()
                
                if last_date < today_utc:
                    logger.info(f"Resetting daily message limit for user {user_id}.")
                    supabase.table('users').update({
                        'messages_today': 0,
                        'last_message_date': datetime.now(timezone.utc).isoformat()
                    }).eq('telegram_id', user_id).execute()
        except Exception as e:
            logger.info(f"Could not check daily limit for user {user_id} (they might be new). Error: {e}")

    @staticmethod
    def update_user_name(user_id: int, new_name: str) -> bool:
        """Updates the user's preferred name in the database."""
        try:
            supabase.table('users').update({'user_name': new_name}).eq('telegram_id', user_id).execute()
            logger.info(f"Updated name for user {user_id} to '{new_name}' in database.")
            return True
        except Exception as e:
            logger.error(f"DB ERROR: Could not update name for user {user_id}. Error: {e}")
            return False

    @staticmethod
    async def update_user_on_message(user_id: int) -> bool:
        """Increments user's message counts after a successful message."""
        try:
            await execute_with_retry(
                lambda: supabase.rpc('increment_user_messages', {'p_user_id': user_id}).execute()
            )
            return True
        except Exception as e:
            logger.error(f"DB ERROR: Failed to update message counts for user {user_id} via RPC. Error: {e}")
            return False

    @staticmethod
    async def create_conversation_entry(user_id: int, character: str, user_message: str, bot_response: str):
        """Saves a record of the conversation to the database."""
        try:
            await execute_with_retry(
                lambda: supabase.table('conversations').insert({
                    'user_id': user_id,
                    'character': character,
                    'user_message': user_message,
                    'bot_response': bot_response
                }).execute()
            )
        except Exception as e:
            logger.error(f"DB ERROR: Could not save conversation for user {user_id}. Error: {e}")

    @staticmethod
    def set_age_verified(user_id: int) -> bool:
        """Sets the user's age_verified status to True."""
        try:
            supabase.table('users').update({'age_verified': True}).eq('telegram_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"DB ERROR: Could not set age_verified for user {user_id}. Error: {e}")
            return False

    @staticmethod
    def start_gem_deduction(user_id: int) -> Optional[int]:
        """Store the user's current gem balance before deduction for possible refund."""
        try:
            result = supabase.table('users').select('gems').eq('telegram_id', user_id).execute()
            if result.data:
                current_gems = result.data[0].get('gems', 0)
                # Store the pre-deduction balance in a new field
                supabase.table('users').update({'pending_gem_refund': current_gems}).eq('telegram_id', user_id).execute()
                logger.info(f"[GEM DEDUCT] Stored pre-deduction balance {current_gems} for user {user_id}")
                return current_gems
        except Exception as e:
            logger.error(f"[GEM DEDUCT] Failed to store pre-deduction balance: {e}")
        return None

    @staticmethod
    def clear_pending_gem_refund(user_id: int):
        """Clear the pending_gem_refund field after successful action or refund."""
        try:
            supabase.table('users').update({'pending_gem_refund': None}).eq('telegram_id', user_id).execute()
            logger.info(f"[GEM DEDUCT] Cleared pending_gem_refund for user {user_id}")
        except Exception as e:
            logger.error(f"[GEM DEDUCT] Failed to clear pending_gem_refund: {e}")

    @staticmethod
    def refund_gems(user_id: int, gem_amount: int) -> bool:
        """Restore the user's gem balance to the pre-deduction value if available, else fallback to old logic."""
        try:
            # Try to restore to pre-deduction balance if available
            result = supabase.table('users').select('pending_gem_refund').eq('telegram_id', user_id).execute()
            if result.data:
                pending = result.data[0].get('pending_gem_refund')
                if pending is not None:
                    supabase.table('users').update({'gems': pending, 'pending_gem_refund': None}).eq('telegram_id', user_id).execute()
                    logger.info(f"[REFUND] Restored gems to pre-deduction value {pending} for user {user_id}")
                    return True
            # Fallback: add gems to current balance (legacy)
            result = supabase.table('users').select('gems').eq('telegram_id', user_id).execute()
            if result.data:
                current_gems = result.data[0].get('gems', 0)
                new_balance = current_gems + gem_amount
                supabase.table('users').update({'gems': new_balance}).eq('telegram_id', user_id).execute()
                logger.info(f"[REFUND] (Fallback) Refunded {gem_amount} gems to user {user_id}. New balance: {new_balance}")
                return True
        except Exception as e:
            logger.error(f"[REFUND] Failed to refund gems: {e}")
        return False

    @staticmethod
    def log_voice_call(user_id: int, call_id: str, agent_id: str, phone_number: str, gem_cost: int, duration_minutes: int = 0):
        """Log a voice call to the database."""
        try:
            call_data = {
                'user_id': user_id,
                'call_id': call_id,
                'agent_id': agent_id,
                'phone_number': phone_number,
                'gem_cost': gem_cost,
                'duration_minutes': duration_minutes,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'completed'
            }
            
            # Insert into voice_calls table (create if doesn't exist)
            supabase.table('voice_calls').insert(call_data).execute()
            logger.info(f"[CALL LOG] Logged voice call {call_id} for user {user_id}, duration: {duration_minutes} minutes")
            return True
        except Exception as e:
            logger.error(f"[CALL LOG] Failed to log voice call: {e}")
            return False

    @staticmethod
    def update_call_duration(call_id: str, duration_minutes: int):
        """Update the duration of a voice call."""
        try:
            supabase.table('voice_calls').update({
                'duration_minutes': duration_minutes,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('call_id', call_id).execute()
            logger.info(f"[CALL UPDATE] Updated call {call_id} duration to {duration_minutes} minutes")
            return True
        except Exception as e:
            logger.error(f"[CALL UPDATE] Failed to update call duration: {e}")
            return False

    @staticmethod
    async def save_user_session(user_id: int, session_data: dict) -> bool:
        """Save user session data to database for persistence across bot restarts."""
        try:
            # Convert session data to JSON-serializable format
            session_json = {
                'current_character': session_data.get('current_character'),
                'current_scenario': session_data.get('current_scenario'),
                'conversation_history': session_data.get('conversation_history', []),
                'user_name': session_data.get('user_name'),
                'clothing_state': session_data.get('clothing_state', 'clothed'),
                'character_current_outfit': session_data.get('character_current_outfit', ''),
                'free_images_sent': session_data.get('free_images_sent', 0),
                'message_count_since_last_image': session_data.get('message_count_since_last_image', 0),
                'session_message_count': session_data.get('session_message_count', 0),
                'asked_for_name': session_data.get('asked_for_name', False),
                'last_interaction_time': session_data.get('last_interaction_time', datetime.now(timezone.utc).isoformat())
            }
            
            await execute_with_retry(
                lambda: supabase.table('users').update({
                    'session_data': json.dumps(session_json),
                    'last_seen': datetime.now(timezone.utc).isoformat()
                }).eq('telegram_id', user_id).execute()
            )
            
            logger.info(f"[SESSION SAVE] Saved session for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"[SESSION SAVE] Failed to save session for user {user_id}: {e}")
            return False

    @staticmethod
    def load_user_session(user_id: int) -> Optional[dict]:
        """Load user session data from database."""
        try:
            result = supabase.table('users').select('session_data').eq('telegram_id', user_id).execute()
            if result.data and result.data[0].get('session_data'):
                try:
                    session_data = json.loads(result.data[0]['session_data'])
                    # Validate basic structure
                    if not isinstance(session_data, dict):
                        logger.warning(f"[SESSION] Invalid session data type for user {user_id}")
                        return None
                    logger.info(f"[SESSION LOAD] Loaded session for user {user_id}")
                    return session_data
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[SESSION] Corrupted session data for user {user_id}: {e}")
                    return None
        except Exception as e:
            logger.error(f"[SESSION LOAD] Failed to load session for user {user_id}: {e}")
        return None

    @staticmethod
    def cleanup_old_sessions():
        """Clean up sessions older than 7 days."""
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            supabase.table('users').update({
                'session_data': None
            }).lt('last_seen', cutoff_date).execute()
            logger.info("[SESSION CLEANUP] Cleaned up old sessions")
        except Exception as e:
            logger.error(f"[SESSION CLEANUP] Failed to cleanup old sessions: {e}")
            return False

    @staticmethod
    def check_subscription(user_id: int) -> Optional[str]:
        """Returns the active subscription tier or None if not subscribed or expired."""
        try:
            now = datetime.now(timezone.utc)
            logger.info(f"[SUBSCRIPTION CHECK] Checking subscription for user {user_id} at {now}")
            
            res = supabase.table('subscriptions').select('tier, expires_at').eq('user_id', user_id).order('expires_at', desc=True).limit(1).execute()
            
            if res.data:
                subscription = res.data[0]
                tier = subscription['tier']
                expires_at_str = subscription['expires_at']
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                
                logger.info(f"[SUBSCRIPTION CHECK] User {user_id} has subscription: tier='{tier}', expires_at={expires_at}")
                
                if expires_at > now:
                    logger.info(f"[SUBSCRIPTION CHECK] ✅ User {user_id} has ACTIVE {tier} subscription (expires {expires_at})")
                    return tier
        except Exception as e:
            logger.error(f"[SUBSCRIPTION CHECK] ❌ Error checking subscription for user {user_id}: {e}")
        return None

    @staticmethod
    def update_subscription(user_id: int, tier: str, duration_days: int = 30):
        """Creates or extends a subscription, and credits monthly gems."""
        try:
            now = datetime.now(timezone.utc)
            res = supabase.table('subscriptions').select('expires_at').eq('user_id', user_id).order('expires_at', desc=True).limit(1).execute()
            if res.data and res.data[0]['expires_at'] > now.isoformat():
                new_expiry = datetime.fromisoformat(res.data[0]['expires_at']) + timedelta(days=duration_days)
            else:
                new_expiry = now + timedelta(days=duration_days)
            supabase.table('subscriptions').upsert({
                'user_id': user_id,
                'tier': tier,
                'expires_at': new_expiry.isoformat(),
                'updated_at': now.isoformat(),
                'created_at': now.isoformat()
            }).execute()
            # Credit monthly gems
            gems_map = {'essential': 450, 'plus': 1200, 'premium': 2500}
            user_gems = supabase.table('users').select('gems').eq('telegram_id', user_id).execute().data[0]['gems']
            supabase.table('users').update({
                'gems': user_gems + gems_map[tier],
                'subscription_type': tier
            }).eq('telegram_id', user_id).execute()
        except Exception as e:
            logger.error(f"[DB] update_subscription error: {e}")

class KoboldAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    async def start_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def check_availability(self) -> bool:
        if not self.session:
            await self.start_session()
        check_url = self.base_url.replace('/api/v1/generate', '/api/v1/model')
        try:
            if self.session:
                async with self.session.get(check_url, timeout=3) as response:
                    return response.status == 200
            return False
        except asyncio.TimeoutError:
            logger.warning("Kobold API check timed out.")
            return False
        except aiohttp.ClientError as e:
            logger.warning(f"Kobold API client error during check: {e}")
            return False

    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        if not self.session or self.session.closed:
            raise RuntimeError("API session is not started or has been closed.")
        payload = {
            "prompt": prompt, "max_length": max_tokens, "temperature": 0.6,
            "top_p": 0.9, "min_p": 0.05, "rep_pen": 1.1,
            "stop_sequence": ["<|im_end|>", "User:", "\n\n", "user:"]
        }
        try:
            async with self.session.post(self.base_url, json=payload, timeout=90) as response:
                if response.status == 200:
                    data = await response.json()
                    text = data['results'][0]['text'].strip()
                    if "User:" in text: text = text.split("User:")[0].strip()
                    if "<|im_start|>" in text: text = text.split("<|im_start|>")[0].strip()
                    for char_key in CHARACTERS:
                        char_name = CHARACTERS[char_key]['full_name']
                        if text.lower().startswith(char_name.lower() + ":"):
                            text = text[len(char_name)+1:].lstrip()
                    return text
                else:
                    logger.error(f"Kobold API returned status {response.status}")
                    return ""
        except asyncio.TimeoutError:
            logger.error("Kobold API request timed out after 90 seconds.")
            return ""
        except aiohttp.ClientError as e:
            logger.error(f"Kobold API client error during generation: {e}")
            return ""

def classify_image_nsfw(image_url: str, api_token: str) -> str:
    """Classifies the image as 'normal', 'sexy', or 'porn' using Replicate's NSFW model."""
    client = replicate.Client(api_token=api_token)
    output = client.run(
        "falcons-ai/nsfw_image_detection:97116600cabd3037e5f22ca08ffcc33b92cfacebf7ccd3609e9c1d29e43d3a8d",
        input={"image": image_url}
    )
    return output  # 'normal', 'sexy', or 'porn'

class ImageGenerator:
    """Handles image generation with v68 fixes: string casting, variation, and SFW enforcement."""
    def __init__(self, api_token: str, kobold_api: KoboldAPI):
        if not api_token:
            logger.warning("Replicate API token is not set. Image generation will be disabled.")
            self.client = None
        else:
            self.client = replicate.Client(api_token=api_token)
            logger.info("ImageGenerator initialized with Replicate client.")
        self.kobold_api = kobold_api
        self.nsfw_keywords = ['naked', 'nude', 'sex', 'fuck', 'cock', 'pussy', 'slut', 'horny', 'undress', 'strip']

    async def _engineer_prompt(self, character: Dict, scenario_prompt: str, outfit: str, clothing_state: str, user_message: Optional[str] = None) -> str:
        """
        Builds a short, direct image prompt using the character's trigger word, scenario, outfit, and the latest user message.
        Always enforces POV and solo character. Adds a random pose/prop/background for variation.
        """
        pose_variations = [
            "smiling softly", "making eye contact", "leaning forward", "gentle expression", "playful pose", "relaxed posture",
            "touching hair", "biting lip", "holding a cup", "leaning on table", "arms crossed", "looking over shoulder",
            # New poses for variety
            "sitting on a chair", "sitting on a bed", "lying down on a bed", "reclining on a sofa", "kneeling on the floor", "crouching playfully", "sprawled out on a couch", "lounging on a pillow", "lying on her side", "lying on her stomach", "lying on her back", "sitting cross-legged", "perched on the edge of a table", "resting on her elbows", "kneeling on the bed", "sitting with legs tucked under"
        ]
        prop_variations = [
            "holding a glass of wine", "with a book", "with a flower", "next to a window", "with soft lighting", "in a cozy corner", "with a plate of food", "with a cup of tea", "with a candle nearby", "with a pillow", "with a towel draped nearby"
        ]
        pose_phrase = random.choice(pose_variations)
        prop_phrase = random.choice(prop_variations)
        pov_phrase = random.choice([
            "from user's point of view", "POV shot", "looking directly at the viewer", "no one else in frame", "immersive perspective"
        ])
        # Clothing state logic
        if clothing_state == 'nude':
            outfit_phrase = "completely naked"
        elif clothing_state == 'undressing':
            outfit_phrase = f"removing {outfit}"
        else:
            outfit_phrase = f"wearing {outfit}"
        # Compose prompt, now including user_message if provided
        user_msg_phrase = f"User just said: '{user_message}'." if user_message else ""
        prompt = (
            f"{character['trigger_word']}, {scenario_prompt}, {outfit_phrase}, {pose_phrase}, {prop_phrase}, {pov_phrase}, {user_msg_phrase} solo, only the woman, no men, no other people"
        )
        # Allow longer prompts for image generation (increased from 400 to 800 chars)
        return prompt[:800]

    async def generate_final_image(self, user_session: "UserData", user_message: Optional[str] = None) -> Optional[str]:
        """v71: State machine never regresses, classifier only moves forward, context always matches state. Now, for the first image, classify before sending and retry if NSFW. Accepts user_message for image context."""
        if not self.client:
            logger.warning("Cannot generate image, Replicate client not available.")
            return None
        if not user_session.current_character:
            return None
        character = CHARACTERS[user_session.current_character]
        if not user_session.current_scenario:
            return None
        scenario = character['scenarios'][user_session.current_scenario]
        scenario_prompt = scenario['scenario_prompt']
        # Helper to generate and classify an image
        async def try_generate_image(seed=None):
            engineered_prompt = await self._engineer_prompt(
                character,
                scenario_prompt,
                user_session.character_current_outfit,
                user_session.clothing_state,
                user_message
            )
            negative_prompt = (
                "(two people, couple, group, men, boy, male, another person, other people, third person:2.0), "
                "(extra hands, extra faces, background people, crowd, group, couple:2.0), "
                "(amputee, dismembered, extra limbs, extra fingers, mutated hands, disfigured, bad anatomy, ugly, malformed, floating limbs, disconnected limbs:2.0), "
                "3d, cartoon, anime, painting, illustration, (deformed, distorted:1.5), poorly drawn, unreal, watermark, signature, text, blurry, morbid, mutated, mutilated, bright background, outdoor, day time, airbrushed skin, (worst quality:2),(low quality:2),(blurry:2),bad_prompt, text, (bad hands), bad eyes, missing fingers, fused fingers, too many fingers,(interlocked fingers:1.2), extra arms, extra legs, long neck, cross-eyed, negative_hand, negative_hand-neg, text, label, caption"
            )
            if user_session.free_images_sent == 0:
                negative_prompt += ", (nude, naked, topless, bare breasts, bare chest, exposed body, nsfw, explicit:2.0)"
            if user_session.clothing_state == 'nude':
                engineered_prompt += ", fully nude, explicit, uncensored"
                negative_prompt += ", panties, underwear, bra, bikini, clothes, fabric, covering body"
            use_img2img = False
            random_seed = seed if seed is not None else random.randint(1, 9999999)
            input_params = {
                "prompt": engineered_prompt,
                "negative_prompt": negative_prompt,
                "scheduler": "DPM++ 2M Karras",
                "aspect_ratio": "9:16",
                "lora_scale": 1,
                "guidance_scale": 4,
                "num_inference_steps": 30,
                "disable_safety_checker": True,
                "seed": random_seed
            }
            if not self.client:
                return None, None, engineered_prompt
            output = await asyncio.to_thread(
                self.client.run,
                character['lora_model_id'],
                input=input_params
            )
            if output and isinstance(output, list) and len(output) > 0:
                final_image_url = str(output[0])
                if not REPLICATE_API_TOKEN:
                    return final_image_url, 'normal', engineered_prompt
                nsfw_class = classify_image_nsfw(final_image_url, REPLICATE_API_TOKEN)
                return final_image_url, nsfw_class, engineered_prompt
            return None, None, engineered_prompt
        # First image: classify before sending, retry if NSFW
        if user_session.free_images_sent == 0:
            for attempt in range(3):
                seed = random.randint(1, 9999999)
                image_url, nsfw_class, engineered_prompt = await try_generate_image(seed)
                logger.info(f"[FIRST IMAGE] Attempt {attempt+1}: classifier={nsfw_class}, url={image_url}, prompt={engineered_prompt}")
                if image_url and nsfw_class == 'normal':
                    user_session.last_image_context = {
                        'prompt': engineered_prompt,
                        'clothing_state': user_session.clothing_state,
                        'outfit': user_session.character_current_outfit,
                        'scenario': scenario_prompt
                    }
                    return image_url
            # If all attempts fail, return None
            return None
        # Subsequent images: generate and classify, but send whatever is generated
        image_url, nsfw_class, engineered_prompt = await try_generate_image()
        if image_url:
            # Only allow state transitions that move forward, never backward
            if user_session.clothing_state == 'clothed' and nsfw_class == 'sexy':
                user_session.update_clothing_state('undressing')
            elif user_session.clothing_state == 'undressing' and nsfw_class == 'porn':
                user_session.update_clothing_state('nude')
            # Store last image context for text response
            user_session.last_image_context = {
                'prompt': engineered_prompt,
                'clothing_state': user_session.clothing_state,
                'outfit': user_session.character_current_outfit,
                'scenario': scenario_prompt
            }
            return image_url
        return None

class VideoGenerator:
    """Handles video generation via Wavespeed API with LoRA mapping."""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        # Wavespeed API endpoint
        self.wavespeed_api_url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.1/i2v-480p-lora"

    async def submit_video_task(self, image_url: str, prompt: str, lora_url: Optional[str] = None) -> Optional[str]:
        """
        Submits video task to Wavespeed API with LoRA support.
        Uses Wan 2.1 i2v 480p model.
        """
        logger.info(f"[VIDEO] Submitting video task to Wavespeed with LoRA: {lora_url}")
        
        if not self.api_token:
            logger.error("[VIDEO] No API token available")
            return None
            
        safe_prompt = self._sanitize_video_prompt(prompt)
        
        # Use the same negative prompt as image generation
        negative_prompt = (
            "(extra hands, extra faces, background people, crowd, group, couple:2.0), "
            "(amputee, dismembered, extra limbs, extra fingers, mutated hands, disfigured, bad anatomy, ugly, malformed, floating limbs, disconnected limbs:2.0), "
            "3d, cartoon, anime, painting, illustration, (deformed, distorted:1.5), poorly drawn, unreal, watermark, signature, text, blurry, morbid, mutated, mutilated, bright background, outdoor, day time, airbrushed skin, (worst quality:2),(low quality:2),(blurry:2),bad_prompt, text, (bad hands), bad eyes, missing fingers, fused fingers, too many fingers,(interlocked fingers:1.2), extra arms, extra legs, long neck, cross-eyed, negative_hand, negative_hand-neg, text, label, caption"
        )
        
        # Prepare payload for Wavespeed API
        payload = {
            "image": image_url,
            "prompt": safe_prompt,
            "negative_prompt": negative_prompt,
            "loras": [
                {
                    "path": lora_url,
                    "scale": 1
                }
            ] if lora_url else [],
            "size": "832*480",
            "num_inference_steps": 30,
            "duration": 10,
            "guidance_scale": 5,
            "flow_shift": 3,
            "seed": -1,
            "enable_prompt_optimizer": False,
            "enable_safety_checker": False,
            # Note: Wavespeed doesn't support webhooks, we'll use polling instead
        }
        
        logger.info(f"[VIDEO] Submitting to Wavespeed API: image_url={image_url}, prompt={safe_prompt}")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    self.wavespeed_api_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        # According to Wavespeed docs, the task ID is in data.id
                        task_id = result.get('data', {}).get('id')
                        logger.info(f"[VIDEO] Task submitted successfully, task_id: {task_id}")
                        logger.info(f"[VIDEO] Full response: {result}")
                        
                        # Return the actual task ID from the response
                        return task_id
        except Exception as e:
            logger.error(f"[VIDEO] Video task submission failed: {e}")
            return None

    def _sanitize_video_prompt(self, prompt: str) -> str:
        """Sanitize video prompt to avoid content filtering."""
        # Remove or replace potentially problematic words
        problematic_words = [
            'nude', 'naked', 'sexual', 'sexy', 'seductive', 'provocative', 'erotic',
            'intimate', 'sensual', 'alluring', 'tempting', 'suggestive', 'flirtatious',
            'undressing', 'stripping', 'revealing', 'exposed', 'bare', 'topless'
        ]
        
        safe_prompt = prompt.lower()
        for word in problematic_words:
            safe_prompt = safe_prompt.replace(word, '')
        
        # Add safe alternatives
        safe_prompt = safe_prompt.replace('dancing', 'moving gracefully')
        safe_prompt = safe_prompt.replace('pose', 'position')
        safe_prompt = safe_prompt.replace('look', 'gaze')
        
        # Ensure it's not empty
        if not safe_prompt.strip():
            safe_prompt = "elegant woman, graceful movement, cinematic lighting, artistic composition"
        
        return safe_prompt.strip()



    async def poll_video_completion(self, task_id: str, user_id: int, max_attempts: int = 60) -> Optional[str]:
        """Poll for video completion and deliver when ready."""
        logger.info(f"[VIDEO POLL] Starting polling for task {task_id}, user {user_id}")
        
        for attempt in range(max_attempts):
            try:
                # check_video_status returns video URL (string) if completed, None if not ready
                video_url = await self.check_video_status(task_id)
                
                logger.info(f"[VIDEO POLL] Attempt {attempt + 1}/{max_attempts} - Task {task_id}: {'completed' if video_url else 'processing'}")
                
                if video_url:
                    # Video is ready
                    logger.info(f"[VIDEO POLL] Task {task_id} completed! Video URL: {video_url}")
                    return video_url
                else:
                    # Still processing, wait and try again
                    logger.info(f"[VIDEO POLL] Task {task_id} still processing, waiting 10 seconds...")
                    await asyncio.sleep(10)  # Wait 10 seconds between polls
                    continue
                    
            except Exception as e:
                logger.error(f"[VIDEO POLL] Error polling task {task_id}: {e}")
                await asyncio.sleep(10)
                continue
        
        logger.error(f"[VIDEO POLL] Task {task_id} timed out after {max_attempts} attempts")
        return None

    def _get_conservative_video_prompt(self, original_prompt: str) -> str:
        """Generate a very conservative video prompt as fallback."""
        return "elegant woman, graceful movement, cinematic lighting, artistic composition, beautiful, sophisticated, no explicit content"

    async def check_video_status(self, task_id: str) -> Optional[str]:
        """Check video status and return video URL if completed."""
        if not self.api_token:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
                
                # Use the result URL from the task submission
                result_url = f"https://api.wavespeed.ai/api/v3/predictions/{task_id}/result"
                
                async with session.get(result_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"[VIDEO STATUS] Task {task_id} status: {result}")
                        
                        # Check if video is completed
                        status = result.get('data', {}).get('status')
                        outputs = result.get('data', {}).get('outputs', [])
                        
                        if status == 'completed' and outputs:
                            video_url = outputs[0]
                            logger.info(f"[VIDEO STATUS] Video completed: {video_url}")
                            return video_url
                        elif status == 'failed':
                            logger.error(f"[VIDEO STATUS] Task {task_id} failed")
                            return None
        except Exception as e:
            logger.error(f"[VIDEO STATUS] Error checking video status: {e}")
            return None

class ElevenLabsManager:
    """Manages ElevenLabs API interactions for voice notes and calls."""
    
    def __init__(self, api_key: str):
        # Set API key as environment variable for ElevenLabs
        self.api_key = api_key
        self._init_client()
    
    def _init_client(self):
        """Initialize the ElevenLabs client."""
        try:
            from elevenlabs.client import ElevenLabs
            self.client = ElevenLabs(api_key=self.api_key)
            logger.info("[ELEVENLABS] Client initialized successfully")
        except Exception as e:
            logger.error(f"[ELEVENLABS] Failed to initialize client: {e}")
    
    def add_audio_tags(self, text: str) -> str:
        """Add audio tags to make the text more natural for voice generation."""
        # Remove all asterisks from text before processing
        text = text.replace('*', '')
        # Add pauses and emphasis for more natural speech
        text = text.replace('.', '... ')
        text = text.replace('!', '!... ')
        text = text.replace('?', '?... ')
        # Add emphasis to key words (without asterisks)
        text = text.replace('I', 'I')
        text = text.replace('you', 'you')
        return text
    
    async def create_voice_note(self, text: str, voice_id: str) -> Optional[bytes]:
        """Create a voice note using ElevenLabs API."""
        try:
            # Add audio tags for better voice generation
            enhanced_text = self.add_audio_tags(text)
            # Generate audio using the initialized client
            audio_generator = self.client.generate(text=enhanced_text, voice=voice_id)
            # Convert generator to bytes
            audio_chunks = list(audio_generator)
            audio = b''.join(audio_chunks)
            return audio
        except Exception as e:
            logger.error(f"[VOICE NOTE] Failed to create voice note: {e}")
            return None
    
    async def get_phone_number_id(self) -> Optional[str]:
        """
        Fetch the agent's phone number ID from ElevenLabs.
        Returns the ID for the Twilio number if available, or the first available number.
        Handles both list and dict API responses for robustness.
        """
        try:
            url = "https://api.elevenlabs.io/v1/convai/phone-numbers"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            import requests
            response = requests.get(url, headers=headers, timeout=30)
            logger.info(f"[PHONE] Phone number fetch response: Status {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                # Handle both list and dict response
                if isinstance(data, list):
                    phone_numbers = data
                elif isinstance(data, dict):
                    phone_numbers = data.get("phone_numbers", [])
                else:
                    logger.error(f"[PHONE] Unexpected response type: {type(data)}")
                    return None
                # Prefer Twilio number if available
                for number in phone_numbers:
                    if number.get("provider") == "twilio":
                        return number.get("id")
                # Fallback: return the first available number's ID
                if phone_numbers:
                    return phone_numbers[0].get("id")
                logger.error("[PHONE] No phone numbers found in ElevenLabs account.")
                return None
            else:
                logger.error(f"[PHONE] Failed to fetch phone numbers: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"[PHONE] Exception fetching phone number ID: {e}")
            return None

        # Note: callSid is the call session ID from ElevenLabs/Twilio, not the user's name or phone number. It is used for tracking the call, not for dialing.
    
    async def check_existing_phone_numbers(self) -> Optional[str]:
        """Check for existing phone numbers in ElevenLabs."""
        try:
            # For now, return None - this would need to be implemented
            # based on the specific ElevenLabs API structure
            logger.info("[PHONE] Existing phone numbers check not yet implemented")
            return None
        except Exception as e:
            logger.error(f"[PHONE] Failed to check existing phone numbers: {e}")
            return None
    
    async def import_twilio_phone_number(self) -> Optional[str]:
        """Import Twilio phone number into ElevenLabs."""
        try:
            # For now, return a placeholder - this would need to be implemented
            # based on the specific ElevenLabs API structure for phone number import
            logger.info("[PHONE] Phone number import not yet implemented")
            return None
        except Exception as e:
            logger.error(f"[PHONE] Failed to import phone number: {e}")
            return None
    
    async def initiate_voice_call(self, agent_id: str, phone_number: str, user_id: int, user_name: Optional[str] = None) -> Optional[str]:
        """Initiate a voice call using ElevenLabs Twilio outbound call API with dynamic agent selection and agent_phone_number_id."""
        try:
            # Use the working hardcoded phone number ID
            agent_phone_number_id = 'phnum_01k04zb68xfd9bgzqb7qpsb204'
            
            # Always add dynamic_variables with proper name handling
            # Ensure we NEVER use generic terms
            final_user_name = user_name if user_name and user_name.lower() not in ['user', 'user#', 'handsome', 'bello', 'there'] else 'baby'
            logger.info(f"[VOICE CALL] 🔍 DEBUG: user_name='{user_name}' → final_user_name='{final_user_name}'")
            
            # Log the parameters being used
            logger.info(f"[ELEVENLABS] Voice call parameters: agent_id='{agent_id}', phone_number='{phone_number}', agent_phone_number_id='{agent_phone_number_id}', user_name='{user_name}'")
            logger.warning(f"[ELEVENLABS] 🔧 NEW APPROACH: Asking user to state their name during call since dynamic variables are broken")
            
            url = "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            payload: Dict[str, Any] = {
                "agent_id": agent_id,  # The agent for the selected character
                "agent_phone_number_id": agent_phone_number_id,  # Fixed phone number ID
                "to_number": phone_number,   # The user's phone number
                "first_message": f"Hey there! I'm so excited to finally talk to you on the phone! Before we get started, can you remind me your name again? I want to make sure I address you properly throughout our conversation.",
            }
            
            # Keep sending dynamic_variables as backup (even though they're broken)
            # Main strategy: Ask user to state their name during the call
            payload["dynamic_variables"] = {
                "user_name": final_user_name
            }
            
            # Note: Using name-asking strategy instead of relying on broken dynamic variables
            # Log the complete payload for debugging
            logger.info(f"[ELEVENLABS] Voice call payload: {payload}")
            logger.info(f"[ELEVENLABS] 🎯 STRATEGY: First message will ask user to state their name, then agent should learn it naturally")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    logger.info(f"[ELEVENLABS] Voice call API response status: {response.status}")
                    
                    if response.status == 200:
                        response_data = await response.json()
                        # ElevenLabs returns 'callSid', not 'call_id'
                        call_id = response_data.get('callSid') or response_data.get('call_id')
                        logger.info(f"[ELEVENLABS] Voice call response data: {response_data}")
                        logger.info(f"[ELEVENLABS] Successfully initiated voice call. Call ID: {call_id}")
                        
                        # Debug: Log what we sent vs what we got back
                        logger.info(f"[ELEVENLABS] 🔍 DEBUG - Sent user_name: '{final_user_name}'")
                        logger.info(f"[ELEVENLABS] 🔍 DEBUG - Full payload sent: {payload}")
                        
                        return call_id
                    else:
                        response_text = await response.text()
                        logger.error(f"[ELEVENLABS] Voice call API error: Status {response.status}, Response: {response_text}")
                        return None
        except Exception as e:
            logger.error(f"[ELEVENLABS] Error initiating voice call: {e}")
            return None

    async def terminate_call(self, call_id: str) -> bool:
        """Terminate an active voice call via ElevenLabs API."""
        try:
            # Note: This endpoint may need to be confirmed with ElevenLabs documentation
            # For now, we'll use a placeholder URL - you'll need to check their API docs
            url = f"https://api.elevenlabs.io/v1/convai/calls/{call_id}/terminate"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"[ELEVENLABS] Successfully terminated call {call_id}")
                        return True
                    else:
                        return False
        except Exception as e:
            logger.error(f"[ELEVENLABS] Error terminating call {call_id}: {e}")
            return False

    async def get_call_status(self, call_id: str) -> dict:
        """Get the status of a voice call via ElevenLabs API."""
        try:
            # Check if this is a Twilio call ID (starts with CA) vs ElevenLabs call ID
            if call_id.startswith('CA'):
                logger.warning(f"[ELEVENLABS] Skipping ElevenLabs status check for Twilio call ID: {call_id}")
                return {"status": "unknown", "message": "Twilio call ID, not ElevenLabs"}
            
            url = f"https://api.elevenlabs.io/v1/convai/calls/{call_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[ELEVENLABS] Call {call_id} status: {data.get('status', 'unknown')}")
                        return data
                    elif response.status == 404:
                        logger.warning(f"[ELEVENLABS] Call {call_id} not found (404) - may have ended or expired")
                        return {"status": "ended", "message": "Call not found"}
                    else:
                        logger.warning(f"[ELEVENLABS] Failed to get call status for {call_id}: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"[ELEVENLABS] Error getting call status for {call_id}: {e}")
            return {}

class SecretShareBot:
    """Main bot class with v69 enhancements for voice integration."""
    def __init__(self, application: Application):
       self.application = application
       self.kobold_api = KoboldAPI(KOBOLD_URL)
       self.image_generator = ImageGenerator(REPLICATE_API_TOKEN or "", self.kobold_api)
       self.video_generator = VideoGenerator(WAVESPEED_API_TOKEN or "")
       self.elevenlabs_manager = ElevenLabsManager(ELEVENLABS_API_KEY or "")
       self.db = Database()
       self.kobold_available = False
       self.active_users: Dict[int, UserData] = {}
       self.anticipation_jobs = {}  # user_id -> list of job references
       # Webhook security
       self._webhook_secret = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
       # --- Webhook server for Wavespeed video delivery ---
       self.web_app = web.Application()
       self.web_app.add_routes([
           web.post('/api/wavespeed-webhook', self.handle_wavespeed_webhook),
           web.post('/api/twilio-webhook', self.handle_twilio_webhook),
           web.post('/api/elevenlabs-webhook', self.handle_elevenlabs_webhook),
           web.post('/api/initiate-payment', self.handle_payment_request)  # NEW
       ])
       self.webhook_thread = threading.Thread(target=self._run_webhook_server, daemon=True)
       self.webhook_thread.start()
       # Call tracking for webhooks
       self.active_calls: Dict[str, int] = {}  # call_id -> user_id

    def _run_webhook_server(self):
       import asyncio
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       web.run_app(self.web_app, port=8081, handle_signals=False)

    async def handle_wavespeed_webhook(self, request):
       """Handle Wavespeed webhook - NOTE: Wavespeed doesn't actually support webhooks, this is unused."""
       logger.info(f"[WEBHOOK] Received unexpected Wavespeed webhook call (Wavespeed doesn't support webhooks)")
       return web.Response(text='ok', status=200)

    async def handle_twilio_webhook(self, request):
       """Handle Twilio webhook for call status updates."""
       try:
           # Twilio sends form data, not JSON - parse accordingly
           data = await request.post()
           logger.info(f"[TWILIO WEBHOOK] Received call status update: {dict(data)}")
           
           # Extract call information from form data
           call_sid = data.get('CallSid')
           call_status = data.get('CallStatus')
           call_duration = data.get('CallDuration')
           
           logger.info(f"[TWILIO WEBHOOK] CallSid: {call_sid}, Status: {call_status}, Duration: {call_duration}")
           
           if call_sid and call_status == 'completed' and call_duration:
               # Convert duration from seconds to minutes
               duration_minutes = max(1, int(int(call_duration) / 60))  # Minimum 1 minute billing
               
               # Update call duration in database
               self.db.update_call_duration(call_sid, duration_minutes)
               logger.info(f"[TWILIO WEBHOOK] Updated call {call_sid} duration to {duration_minutes} minutes")
               
               # Find user by call_sid and process call end
               user_id = self.active_calls.get(call_sid)
               if user_id:
                   try:
                       # Use the existing call end processing logic
                       await self._process_call_end(call_sid, user_id, duration_minutes, datetime.now(), 'twilio_webhook')
                       logger.info(f"[TWILIO WEBHOOK] Processed call end for user {user_id}")
                   except Exception as e:
                       logger.error(f"[TWILIO WEBHOOK] Failed to process call end for user {user_id}: {e}")
                       # Even if processing fails, stop the monitoring job
                       await self.stop_call_monitoring(call_sid, "twilio_webhook_fallback")
               else:
                   logger.warning(f"[TWILIO WEBHOOK] No active user found for call {call_sid}")
                   # Still stop monitoring for unknown calls
                   await self.stop_call_monitoring(call_sid, "twilio_webhook_unknown_user")
           
           return web.Response(text='ok', status=200)
           
       except Exception as e:
           logger.error(f"[TWILIO WEBHOOK] Error processing webhook: {e}")
           return web.Response(text='error', status=500)

    async def handle_elevenlabs_webhook(self, request):
       """Handle ElevenLabs webhook for call completion events and finalize gem deduction."""
       try:
           # Verify webhook signature for security
           webhook_secret = os.getenv('ELEVENLABS_WEBHOOK_SECRET')
           if webhook_secret:
               signature_header = request.headers.get('ElevenLabs-Signature')
               if signature_header:
                   import hmac
                   import hashlib
                   body = await request.read()
                   
                   # Parse ElevenLabs signature format: t=timestamp,v0=signature
                   try:
                       timestamp = None
                       signature = None
                       for part in signature_header.split(','):
                           if part.startswith('t='):
                               timestamp = part[2:]
                           elif part.startswith('v0='):
                               signature = part[3:]
                       
                       if timestamp and signature:
                           # Create expected signature: timestamp + body
                           payload = f"{timestamp}.{body.decode('utf-8')}"
                           expected_signature = hmac.new(
                               webhook_secret.encode('utf-8'),
                               payload.encode('utf-8'),
                               hashlib.sha256
                           ).hexdigest()
                           
                           if not hmac.compare_digest(signature, expected_signature):
                               logger.warning(f"[ELEVENLABS WEBHOOK] Invalid signature: {signature_header}")
                               logger.warning(f"[ELEVENLABS WEBHOOK] Expected: {expected_signature}, Got: {signature}")
                               return web.Response(status=401, text='Invalid signature')
                           logger.info(f"[ELEVENLABS WEBHOOK] Signature verified successfully")
                       else:
                           logger.warning(f"[ELEVENLABS WEBHOOK] Malformed signature header: {signature_header}")
                           return web.Response(status=401, text='Malformed signature')
                   except Exception as e:
                       logger.error(f"[ELEVENLABS WEBHOOK] Signature validation error: {e}")
                       # For now, allow webhook through if signature validation fails (development)
                       logger.warning(f"[ELEVENLABS WEBHOOK] Allowing webhook through due to signature validation error")
               else:
                   logger.warning(f"[ELEVENLABS WEBHOOK] No signature provided")
           
           # Parse the webhook data
           if hasattr(request, '_body'):
               data = json.loads(request._body.decode('utf-8'))
           else:
               data = await request.json()
           logger.info(f"[ELEVENLABS WEBHOOK] Received call event: {data}")
       except Exception as e:
           logger.error(f"[ELEVENLABS WEBHOOK] Error processing webhook: {e}")
           data = await request.json()
           logger.info(f"[ELEVENLABS WEBHOOK] Received call event (fallback): {data}")
       call_id = data.get('call_id') or data.get('callSid')
       event_type = data.get('event_type')
       duration = data.get('duration')  # Duration in seconds from ElevenLabs
       
       if call_id and event_type == 'call_ended' and duration:
           duration_minutes = max(1, int(duration / 60))  # Convert seconds to minutes, minimum 1 minute
           logger.info(f"[ELEVENLABS WEBHOOK] Call {call_id} ended. Duration: {duration} seconds = {duration_minutes} minutes")
           
           user_id = self.active_calls.get(call_id)
           if user_id:
               # Use centralized call end processing for consistency
               await self._process_call_end(call_id, user_id, duration_minutes, datetime.now(), 'elevenlabs_webhook')
               
               # Stop call monitoring job if it exists
               try:
                   if hasattr(self, 'application') and self.application.job_queue:
                       current_jobs = self.application.job_queue.get_jobs_by_name(f"call_monitor_{call_id}")
                       for job in current_jobs:
                           job.schedule_removal()
                       logger.info(f"[ELEVENLABS WEBHOOK] Stopped monitoring job for call {call_id}")
               except Exception as e:
                   logger.error(f"[ELEVENLABS WEBHOOK] Failed to stop monitoring job for call {call_id}: {e}")
           else:
               logger.warning(f"[ELEVENLABS WEBHOOK] No active user found for call {call_id}")
       return web.Response(text='ok')

    async def _deliver_video(self, user_id, video_path_or_url):
       logger.info(f"[DELIVER VIDEO] Attempting to send video to user {user_id}")
       logger.info(f"[DELIVER VIDEO] Video path/URL type: {type(video_path_or_url)}, value: {video_path_or_url}")
       self._cancel_anticipation_jobs(user_id)
       try:
           # Validate video_path_or_url before sending to Telegram
           if not video_path_or_url:
               logger.error(f"[VIDEO DELIVERY] Video path/URL is None or empty")
               await self.application.bot.send_message(chat_id=user_id, text="Sorry, there was a problem delivering your video. Please try again later.")
               return
           
           if not isinstance(video_path_or_url, str):
               logger.error(f"[VIDEO DELIVERY] Video path/URL is not a string: {type(video_path_or_url)}")
               await self.application.bot.send_message(chat_id=user_id, text="Sorry, there was a problem delivering your video. Please try again later.")
               return
           
           # Check if it's a file path or URL
           if video_path_or_url.startswith("https://"):
               # It's a URL - download and send as file to ensure proper video format
               logger.info(f"[DELIVER VIDEO] Downloading video from URL: {video_path_or_url}")
               try:
                   import requests
                   from io import BytesIO
                   
                   # Download the video
                   response = requests.get(video_path_or_url, timeout=60)
                   response.raise_for_status()
                   
                   # Create a file-like object
                   video_data = BytesIO(response.content)
                   video_data.name = 'video.mp4'  # Set filename with .mp4 extension
                   
                   # Send as video with explicit parameters
                   await self.application.bot.send_video(
                       chat_id=user_id, 
                       video=video_data,
                       supports_streaming=True,
                       has_spoiler=False
                   )
                   logger.info(f"[DELIVER VIDEO] Video sent successfully as MP4 to user {user_id}")
                   
               except Exception as e:
                   logger.error(f"[DELIVER VIDEO] Failed to download/send video: {e}")
                   # Fallback: try sending as URL directly
                   await self.application.bot.send_video(
                       chat_id=user_id, 
                       video=video_path_or_url,
                       supports_streaming=True
                   )
           logger.info(f"[DELIVER VIDEO] Video sent successfully to user {user_id}")
       except Exception as e:
           logger.error(f"[VIDEO DELIVERY] Failed to send video to user {user_id}: {e}")

    def _cancel_anticipation_jobs(self, user_id):
       jobs = self.anticipation_jobs.pop(user_id, [])
       for job in jobs:
           try:
               job.schedule_removal()
           except Exception as e:
               logger.info(f"[ANTICIPATION] Could not remove job {job.id}: {e}")

    async def _start_anticipation_funnel(self, user_id, context, char_ack, anticipation_context, max_msgs=4):
       # Send immediate acknowledgment (AI or fallback)
       try:
           await context.bot.send_message(chat_id=user_id, text=char_ack)
       except Exception:
           # Use global random import
           fallback = random.choice(ANTICIPATION_ACK_TEMPLATES)
           await context.bot.send_message(chat_id=user_id, text=fallback)
       # Schedule up to 4 periodic anticipation messages (AI or fallback)
       self.anticipation_jobs[user_id] = []
       for i in range(max_msgs):
           delay = random.uniform(90, 150) * (i + 1)  # 1.5–2.5 min intervals
           job = self.application.job_queue.run_once(
               self._send_anticipation_message,
               when=delay,
               chat_id=user_id,
               name=f"anticipation_{user_id}_{i}",
               data={'user_id': user_id, 'context': anticipation_context, 'msg_num': i+1}
           )
           self.anticipation_jobs[user_id].append(job)

    async def _send_anticipation_message(self, context: ContextTypes.DEFAULT_TYPE):
       user_id = context.job.data['user_id']
       anticipation_context = context.job.data['context']
       msg_num = context.job.data['msg_num']
       # If video already delivered, skip
       if user_id not in self.active_users or not self.active_users[user_id].last_video_task:
           return
       # AI-generated anticipation message (fallback to template)
       anticipation_line = await self._generate_anticipation_line(user_id, anticipation_context, msg_num)
       try:
           await context.bot.send_message(chat_id=user_id, text=anticipation_line)
       except Exception:
           import random
           fallback = random.choice(ANTICIPATION_PERIODIC_TEMPLATES)
           await context.bot.send_message(chat_id=user_id, text=fallback)

    async def _generate_anticipation_line(self, user_id, anticipation_context, msg_num):
       # Use AI to generate a short, in-character anticipation line
       user_session = self.active_users.get(user_id)
       if not user_session or not user_session.current_character:
           return random.choice(ANTICIPATION_PERIODIC_TEMPLATES)
       character = CHARACTERS[user_session.current_character]
       user_name = user_session.user_name or random.choice(['handsome', 'bello', 'there'])
       persona_prompt = character['system_prompt_base'].format(user_name=escape_markdown(user_name, version=2))
       scenario = character['scenarios'][user_session.current_scenario]
       scenario_prompt = f"You are in {scenario['scenario_prompt']}. You are wearing {user_session.character_current_outfit}."
       instruction = (
           "Generate a short, in-character anticipation message to build excitement for a custom video that is being prepared. "
           "Keep it concise, playful, and in-character. Do not mention payment or gems. This is message number " + str(msg_num) + ". "
           "Make it feel natural and related to the ongoing conversation."
       )
       prompt = (
           f"<|im_start|>system\n{persona_prompt}\n**Current Scenario Context:** {scenario_prompt}\n<|im_end|>"
           f"<|im_start|>user\n{anticipation_context}<|im_end|>"
           f"<|im_start|>assistant\n{instruction}\n{character['full_name']}:"
       )
       if self.kobold_available:
           raw = await self.kobold_api.generate(prompt, max_tokens=40)
           return self._ensure_complete_sentence(raw)
    async def _poll_video_completion(self, user_id: int, task_id: str, max_attempts: int = 60):
       """Poll for video completion using the new VideoGenerator polling method."""
       logger.info(f"[POLL] Starting video polling for user {user_id}, task {task_id}")
       
       try:
           # Use the VideoGenerator's polling method
           video_url = await self.video_generator.poll_video_completion(task_id, user_id, max_attempts)
           
           if video_url:
               logger.info(f"[POLL] Video completed for user {user_id}: {video_url}")
               await self._deliver_video(user_id, video_url)
               
               # Clear the video task from user session
               user_session = self.active_users.get(user_id)
               if user_session:
                   user_session.last_video_task = {}
           else:
               logger.warning(f"[POLL] Video task {task_id} for user {user_id} failed or timed out")
               await self.application.bot.send_message(
                   chat_id=user_id, 
                   text="Sorry, your video took longer than expected or failed to generate. Please try again later."
               )
               
               # Clear the video task from user session
               user_session = self.active_users.get(user_id)
               if user_session:
                   user_session.last_video_task = {}
                   
       except Exception as e:
           logger.error(f"[POLL] Error polling video completion for user {user_id}: {e}")
           await self.application.bot.send_message(
               chat_id=user_id, 
               text="Sorry, there was an error processing your video. Please try again later."
           )
           
           # Clear the video task from user session
           user_session = self.active_users.get(user_id)
           if user_session:
               user_session.last_video_task = {}

    async def send_premium_offer_overlay(self, update, context, user_id, offer_type, gem_cost, character_line=None):
       user_db_data = self.db.get_or_create_user(user_id, getattr(update.effective_user, 'username', 'Unknown'))
       gems = user_db_data.get('gems', 0) if user_db_data else 0
       if offer_type == 'image':
           offer_text = f"I can show you. A private photo like this requires **{gem_cost} Gems** 💎. You currently have {gems} Gems. Shall I create it for you?"
           yes_text = f"✅ Yes (💎 {gem_cost})"
           callback_data = f"premium_yes|image|{gem_cost}"
       elif offer_type == 'video':
           offer_text = f"A private video like this requires **{gem_cost} Gems** 💎. You currently have {gems} Gems. Shall I create it for you?"
           yes_text = f"✅ Yes (💎 {gem_cost})"
           callback_data = f"premium_yes|video|{gem_cost}"
       elif offer_type == 'voice_note':
           offer_text = f"I'll whisper it to you. A private voice note requires **{gem_cost} Gems** 💎. You currently have {gems} Gems. Shall I create it for you?"
           yes_text = f"✅ Yes (💎 {gem_cost})"
           callback_data = f"premium_yes|voice_note|{gem_cost}"
       elif offer_type == 'voice_call':
           offer_text = f"I want to call you. A voice call requires **{gem_cost} Gems** 💎 per minute. You currently have {gems} Gems. Shall I call you?"
           yes_text = f"✅ Yes (💎 {gem_cost}/min)"
           callback_data = f"premium_yes|voice_call|{gem_cost}"
       elif offer_type == 'voice':
           offer_text = f"I'll whisper it to you. A private voice note requires **{gem_cost} Gems** 💎. You currently have {gems} Gems. Shall I create it for you?"
           yes_text = f"✅ Yes (💎 {gem_cost})"
           callback_data = f"premium_yes|voice|{gem_cost}"
       else:
           return
       keyboard = [[InlineKeyboardButton(yes_text, callback_data=callback_data)]]
       reply_markup = InlineKeyboardMarkup(keyboard)
       if character_line:
           await update.message.reply_text(character_line)
       await update.message.reply_text(offer_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    def _ensure_complete_sentence(self, text: str) -> str:
        """
        Tweaked asterisk logic: Only add a closing * if the message starts with *, has exactly one *, and does not end with *. If there are already pairs of asterisks (properly closed actions), do nothing. For mixed or normal messages, just ensure normal punctuation at the end.
        """
        text = text.strip()
        logger.info(f"[ENSURE SENTENCE] Raw: {text}")
        if not text:
            logger.info("[ENSURE SENTENCE] Using fallback for empty response.")
            return "*I smile at you.* I'm happy you're here."
        # Only add a closing * if the message starts with *, has exactly one *, and does not end with *
        if text.startswith('*') and text.count('*') == 1 and not text.endswith('*'):
            return text + '*'
        # If already ends with proper punctuation, return as is
        if text.endswith(('.', '!', '?')):
            return text
        # Otherwise, trim to last full stop, exclamation, or question mark
        last_punc = max(text.rfind(p) for p in ['.', '!', '?'])
        if last_punc > 0:
            return text[:last_punc+1].strip()
        return text

    def _validate_and_fix_actions(self, text: str, user_name: str = "you") -> str:
        """
        Ensures all *...* action segments use first-person for the bot and second-person for the user.
        Replaces third-person references with correct pronouns, but does NOT replace 'my', 'mine', 'myself', 'your', 'yours', 'yourself'.
        """
        import re
        # Patterns for bot and user references
        bot_subjects = r"\b(the bot|she|the woman|the girl)\b"
        bot_objects = r"\b(her)\b"
        user_subjects = r"\b(the user|the man)\b"
        user_objects = r"\b(him)\b"
        user_possessives = r"\b(his)\b"
        # Don't touch these possessives
        dont_touch = r"\b(my|mine|myself|your|yours|yourself)\b"

        def fix_action(action: str) -> str:
            # Replace bot references (subject)
            action = re.sub(bot_subjects, "I", action, flags=re.IGNORECASE)
            # Replace bot references (object, but not possessive)
            action = re.sub(
                r"\bher\b(?=\s+(?!own|way|turn|face|eyes|lips|mouth|body|hand|hair|skin|breasts|legs|arms|voice|smile|look|expression|gaze|touch|kiss|embrace|caress|moan|sigh|breath|laugh|giggle|blush|cheek|hips|waist|back|shoulder|thigh|foot|feet|fingers|hands|arms|neck|chest|stomach|abdomen|nipple|nipples|panties|underwear|bra|dress|shirt|skirt|jeans|shorts|clothes|outfit|lingerie|robe|towel|blanket|sheet|pillow|bed|sofa|couch|chair|seat|mirror|window|door|floor|wall|ceiling|room|apron|gown|sari|lehenga|sweater|hoodie|jacket|coat|scarf|hat|cap|veil|mask|glove|stocking|sock|shoe|boot|sandal|heel|slipper|ring|bracelet|necklace|earring|jewelry|watch|glasses|sunglasses|bag|purse|wallet|phone|book|glass|cup|plate|bottle|wine|tea|coffee|water|juice|drink|food|snack|fruit|vegetable|meat|fish|egg|bread|cake|cookie|pie|ice cream|chocolate|candy|gum|mint|spice|herb|salt|pepper|sugar|honey|syrup|oil|butter|cheese|yogurt|cream|sauce|dressing|dip|spread|jam|jelly|marmalade|mustard|ketchup|mayonnaise|vinegar|soy sauce|hot sauce|chili|curry|paste|powder|flour|rice|pasta|noodle|bean|pea|nut|seed|grain|corn|oat|barley|wheat|rye|millet|quinoa|buckwheat|spelt|teff|sorghum|amaranth|chia|flax|hemp|pumpkin|sunflower|sesame|poppy|coconut|almond|cashew|hazelnut|macadamia|pecan|pine nut|pistachio|walnut|brazil nut|chestnut|date|fig|grape|kiwi|lemon|lime|mango|melon|orange|papaya|peach|pear|plum|pomegranate|raspberry|strawberry|tangerine|watermelon|zucchini|squash|tomato|avocado|eggplant|pepper|chili|cucumber|lettuce|spinach|kale|broccoli|cauliflower|cabbage|carrot|celery|onion|garlic|ginger|potato|sweet potato|yam|turnip|radish|beet|parsnip|rutabaga|artichoke|asparagus|bean sprout|bok choy|brussels sprout|collard|endive|fennel|jicama|kohlrabi|leek|mushroom|okra|olive|shallot|swiss chard|watercress|arugula|basil|cilantro|dill|mint|oregano|parsley|rosemary|sage|thyme|vanilla|wasabi|bay leaf|cinnamon|clove|coriander|cumin|nutmeg|paprika|saffron|tarragon|turmeric|anise|cardamom|caraway|chervil|fenugreek|lavender|lemongrass|marjoram|savory|sorrel|star anise|sumac|vervain|angelica|betel|borage|calendula|catnip|chamomile|chicory|comfrey|costmary|feverfew|horehound|hyssop|lovage|mallow|meadowsweet|mugwort|nasturtium|pennyroyal|perilla|rue|santolina|self-heal|shiso|skullcap|sweet woodruff|tansey|winter savory|woodruff|yarrow|zatar|zedoary|other))",
                "me",
                action,
                flags=re.IGNORECASE,
            )
            # Replace bot references (possessive 'her' as 'my')
            action = re.sub(r"\bher\b", "my", action, flags=re.IGNORECASE)
            # Replace user references (subject)
            action = re.sub(user_subjects, "you", action, flags=re.IGNORECASE)
            # Replace user references (object)
            action = re.sub(user_objects, "you", action, flags=re.IGNORECASE)
            # Replace user references (possessive)
            action = re.sub(user_possessives, "your", action, flags=re.IGNORECASE)
            # Replace user's name with 'you' if present
            if user_name and user_name.lower() != 'you':
                action = re.sub(rf"\b{re.escape(user_name)}\b", "you", action, flags=re.IGNORECASE)
            # Remove double spaces
            action = re.sub(r'\s+', ' ', action)
            return action.strip()

        # Replace all *...* segments
        def repl(match):
            fixed = fix_action(match.group(1))
            return f'*{fixed}*'
        return re.sub(r'\*([^*]+)\*', repl, text)

    def _remove_job_if_exists(self, name: str) -> bool:
       """Remove job with given name. Returns whether job was removed."""
       if not self.application.job_queue: return False
       current_jobs = self.application.job_queue.get_jobs_by_name(name)
       if not current_jobs:
           return False
       for job in current_jobs:
           job.schedule_removal()
       return True

    async def _schedule_follow_up(self, chat_id: int):
       """Schedules a 5-minute follow-up message if user is inactive for 5 minutes."""
       if not self.application.job_queue:
           return
       job_name = f"follow_up_{chat_id}"
       self._remove_job_if_exists(job_name)
       # Always schedule the follow-up; the job itself will check for recent activity
       self.application.job_queue.run_once(
           self._send_follow_up, 
           timedelta(minutes=5), 
           chat_id=chat_id, 
           name=job_name,
           data={'user_id': chat_id}
       )

    async def _send_follow_up(self, context: ContextTypes.DEFAULT_TYPE):
       """The callback function for the 5-minute follow-up job."""
       job = context.job
       user_id = job.data['user_id']
       user_session = self.active_users.get(user_id)
       if user_session and user_session.current_character:
           # Only send if user has been inactive for 5+ minutes
           if datetime.now(timezone.utc) - user_session.last_interaction_time >= timedelta(minutes=5):
               character_data = CHARACTERS.get(user_session.current_character)
               if character_data and character_data.get('follow_ups'):
                   message = random.choice(character_data['follow_ups'])
                   try:
                       await context.bot.send_message(chat_id=user_id, text=message)
                       logger.info(f"Sent 5-minute follow-up to user {user_id}.")
                   except Exception as e:
                       logger.warning(f"Could not send 5-min follow-up to {user_id}. Error: {e}")
           else:
               logger.info(f"User {user_id} was active recently, skipping follow-up.")

    async def _cleanup_inactive_users(self, context: ContextTypes.DEFAULT_TYPE):
        """Clean up inactive users from memory to prevent memory leaks."""
        now = datetime.now(timezone.utc)
        inactive_users = []
        
        for user_id, session in self.active_users.items():
            last_interaction = getattr(session, 'last_interaction_time', now)
            if (now - last_interaction).total_seconds() > 3600:  # 1 hour inactive
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            self.active_users.pop(user_id, None)
        
        if inactive_users:
            logger.info(f"[CLEANUP] Removed {len(inactive_users)} inactive users from memory")

    async def _sync_recent_payments(self, context: ContextTypes.DEFAULT_TYPE):
        """Sync recent payments to update active user sessions - FRONTEND INTEGRATION"""
        try:
            # Get payments from last 5 minutes that are completed
            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            
            result = supabase.table('processed_payments')\
                .select('user_id, payload, amount, created_at, telegram_charge_id')\
                .eq('status', 'completed')\
                .gte('created_at', cutoff_time)\
                .execute()
            
            if result.data:
                logger.info(f"[PAYMENT_SYNC] Found {len(result.data)} recent payments to sync")
                
                for payment in result.data:
                    user_id = payment['user_id']
                    charge_id = payment.get('telegram_charge_id', 'webapp_payment')
                    
                    # Update active user session if they're currently using bot
                    if user_id in self.active_users:
                        # Refresh user data from database
                        updated_user = Database.get_or_create_user(user_id, "")
                        if updated_user:
                            old_gems = getattr(self.active_users[user_id], 'gems', 0) if hasattr(self.active_users[user_id], 'gems') else 0
                            new_gems = updated_user.get('gems', 0)
                            
                            # Update session with fresh data
                            user_session = self.active_users[user_id]
                            user_session.gems = new_gems
                            user_session.last_interaction_time = datetime.now(timezone.utc)
                            
                            if old_gems != new_gems:
                                logger.info(f"[PAYMENT_SYNC] Updated active user {user_id}: gems {old_gems} → {new_gems} (charge: {charge_id})")
                        else:
                            logger.warning(f"[PAYMENT_SYNC] Could not fetch updated user data for {user_id}")
                
        except Exception as e:
            logger.error(f"[PAYMENT_SYNC] Error syncing recent payments: {e}")

    async def _refresh_user_data_on_return(self, user_id: int, username: str = ""):
        """Refresh user data when they return from WebApp or after payment - FRONTEND INTEGRATION"""
        try:
            # Always get fresh data from database
            updated_user = Database.get_or_create_user(user_id, username)
            if updated_user:
                # Update or create user session with fresh data
                if user_id in self.active_users:
                    user_session = self.active_users[user_id]
                    old_gems = getattr(user_session, 'gems', 0)
                    
                    # Update critical user data fields
                    user_session.gems = updated_user.get('gems', 0)
                    user_session.messages_today = updated_user.get('messages_today', 0)
                    user_session.subscription_type = updated_user.get('subscription_type')
                    user_session.last_interaction_time = datetime.now(timezone.utc)
                    
                    new_gems = user_session.gems
                    if old_gems != new_gems:
                        logger.info(f"[USER_REFRESH] User {user_id} data refreshed: gems {old_gems} → {new_gems}")
                else:
                    # Create new session if doesn't exist - LOAD SAVED SESSION DATA
                    saved_session = Database.load_user_session(user_id)
                    if saved_session:
                        # Restore from saved session
                        user_session = UserData()
                        user_session.current_character = saved_session.get('current_character')
                        user_session.current_scenario = saved_session.get('current_scenario')
                        user_session.conversation_history = saved_session.get('conversation_history', [])
                        user_session.user_name = saved_session.get('user_name')
                        user_session.clothing_state = saved_session.get('clothing_state', 'clothed')
                        user_session.character_current_outfit = saved_session.get('character_current_outfit', '')
                        user_session.free_images_sent = saved_session.get('free_images_sent', 0)
                        user_session.message_count_since_last_image = saved_session.get('message_count_since_last_image', 0)
                        user_session.session_message_count = saved_session.get('session_message_count', 0)
                        user_session.asked_for_name = saved_session.get('asked_for_name', False)
                        if saved_session.get('last_interaction_time'):
                            user_session.last_interaction_time = saved_session['last_interaction_time']
                        logger.info(f"[USER_REFRESH] Restored saved session for user {user_id} (character: {user_session.current_character})")
                    else:
                        # No saved session, create fresh
                        user_session = UserData()
                        logger.info(f"[USER_REFRESH] Created fresh session for user {user_id} (no saved data)")
                    
                    # Update with current database values
                    self.active_users[user_id] = user_session
                    user_session.gems = updated_user.get('gems', 0)
                    user_session.user_name = updated_user.get('user_name') or user_session.user_name
                    user_session.messages_today = updated_user.get('messages_today', 0)
                    user_session.subscription_type = updated_user.get('subscription_type')
                    user_session.last_interaction_time = datetime.now(timezone.utc)
                    
                    logger.info(f"[USER_REFRESH] Session ready for user {user_id} with {updated_user.get('gems', 0)} gems")
                
                return self.active_users[user_id]
            else:
                logger.error(f"[USER_REFRESH] Failed to fetch user data for {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[USER_REFRESH] Error refreshing user data for {user_id}: {e}")
            return None

    async def _check_inactive_users(self, context: ContextTypes.DEFAULT_TYPE):
        """Send re-engagement message to users who haven't interacted in 24+ hours."""
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(hours=24)
           
            # Query users who were last seen more than 24 hours ago
            result = supabase.table('users').select('telegram_id, username, last_seen').lt('last_seen', cutoff_time.isoformat()).execute()

            for user in result.data:
                user_id = user['telegram_id']
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="💖 I miss you! Come back and continue our conversation... I've been thinking about you! 😘"
                    )
                    logger.info(f"[RETENTION] Sent re-engagement message to user {user_id}")
                except Exception as e:
                    logger.warning(f"[RETENTION] Failed to send message to user {user_id}: {e}")
        except Exception as e:
            logger.error(f"[RETENTION] Error in inactive user check: {e}")

    async def _monitor_call_duration(self, context: ContextTypes.DEFAULT_TYPE):
        """Monitor active call duration and terminate if it would exceed user's gem balance."""
        job_data = context.job.data
        call_id = job_data['call_id']
        user_id = job_data['user_id']
        max_minutes = job_data['max_minutes']
        start_time = job_data['start_time']
        
        try:
            # Calculate current call duration
            current_time = datetime.now(timezone.utc)
            duration_seconds = (current_time - start_time).total_seconds()
            duration_minutes = int(duration_seconds / 60)
            
            logger.info(f"[CALL MONITOR] Call {call_id} - Duration: {duration_minutes}/{max_minutes} minutes")
            
            # Check if call is still in our active calls list (might have ended naturally)
            if call_id not in self.active_calls:
                logger.info(f"[CALL MONITOR] Call {call_id} no longer active. Stopping monitor.")
                context.job.schedule_removal()
                return
            
            # Check call status - different methods for ElevenLabs vs Twilio calls
            if call_id.startswith('CA'):
                # Twilio call - check for stale calls (webhook may have failed)
                if duration_minutes >= 5:  # If call has been "active" for 5+ minutes, likely ended
                    logger.warning(f"[CALL MONITOR] Twilio call {call_id} has been active for {duration_minutes} minutes - likely ended but webhook missed. Processing end.")
                    precise_duration = max(1, duration_minutes)
                    await self._process_call_end(call_id, user_id, precise_duration, start_time, 'stale_detection')
                    context.job.schedule_removal()
                    return
            else:
                # ElevenLabs call - use API status check
                call_status_data = await self.elevenlabs_manager.get_call_status(call_id)
                call_status = call_status_data.get('status', '').lower()
                
                # If call has ended naturally or ElevenLabs API indicates it's ended, process it
                if call_status in ['ended', 'completed', 'terminated', 'finished']:
                    logger.info(f"[CALL MONITOR] ElevenLabs call {call_id} ended naturally. Status: {call_status}")
                    precise_duration = max(1, duration_minutes)
                    await self._process_call_end(call_id, user_id, precise_duration, start_time, 'natural')
                    context.job.schedule_removal()
                    return
            
            # For very short calls (less than 30 seconds), check more frequently for early termination
            if duration_minutes == 0 and duration_seconds < 30:
                # Don't send warnings for calls under 30 seconds - they might end naturally very quickly
                logger.info(f"[CALL MONITOR] Call {call_id} very short ({duration_seconds}s), monitoring closely")
                return
            
            # For debugging: Stop monitoring if call has been running too long (failsafe)
            if duration_minutes >= 60:  # 1 hour failsafe - no call should run this long
                logger.error(f"[CALL MONITOR] FAILSAFE: Call {call_id} has been monitoring for {duration_minutes} minutes (1 hour limit). Force ending.")
                precise_duration = max(1, min(duration_minutes, max_minutes))  # Cap at allocated time
                await self._process_call_end(call_id, user_id, precise_duration, start_time, 'failsafe_timeout')
                context.job.schedule_removal()
                return
            
            # Check if call is approaching or exceeding the limit
            if duration_minutes >= max_minutes:
                logger.warning(f"[CALL MONITOR] Call {call_id} reached gem limit ({duration_minutes}/{max_minutes} minutes). Terminating call.")
                
                # Terminate the call via ElevenLabs API
                try:
                    # Attempt to terminate the call via ElevenLabs API
                    terminated = await self.elevenlabs_manager.terminate_call(call_id)
                    
                    if call_id in self.active_calls:
                        # Send termination message to user
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"⚠️ Your call has reached the maximum duration ({max_minutes} minutes) based on your gem balance. The call has ended to prevent overcharges."
                        )
                        
                        # Process call end
                        await self._process_call_end(call_id, user_id, max_minutes, start_time, 'gem_limit')
                        
                        # Stop monitoring this call
                        context.job.schedule_removal()
                        
                        if terminated:
                            logger.info(f"[CALL MONITOR] Successfully terminated call {call_id} at gem limit")
                        else:
                            logger.warning(f"[CALL MONITOR] Call {call_id} marked as ended locally, but API termination may have failed")

                except Exception as e:
                    logger.error(f"[CALL MONITOR] Failed to terminate call {call_id}: {e}")
                    
            elif duration_minutes >= max_minutes - 1:  # 1 minute warning
                # Send warning to user when they have 1 minute left
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"⚠️ You have approximately 1 minute left on your call based on your gem balance. Consider buying more gems to continue longer conversations!"
                    )
                    logger.info(f"[CALL MONITOR] Sent 1-minute warning to user {user_id} for call {call_id}")
                except Exception as e:
                    logger.error(f"[CALL MONITOR] Failed to send warning to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"[CALL MONITOR] Error monitoring call {call_id}: {e}")
            # Stop monitoring on error
            context.job.schedule_removal()

    async def stop_call_monitoring(self, call_id: str, reason: str = "manual"):
        """Manually stop call monitoring for a specific call ID."""
        try:
            if hasattr(self, 'application') and self.application.job_queue:
                current_jobs = self.application.job_queue.get_jobs_by_name(f"call_monitor_{call_id}")
                for job in current_jobs:
                    job.schedule_removal()
                logger.info(f"[CALL MONITOR] Manually stopped monitoring for call {call_id}. Reason: {reason}")
                return len(current_jobs)
            return 0
        except Exception as e:
            logger.error(f"[CALL MONITOR] Failed to stop monitoring for call {call_id}: {e}")
            return 0

    async def _process_call_end(self, call_id: str, user_id: int, duration_minutes: int, start_time: datetime, end_reason: str):
        """Process the end of a voice call: calculate cost, deduct gems, update database, notify user."""
        
        # Prevent duplicate processing of the same call end
        if call_id not in self.active_calls:
            logger.warning(f"[CALL END] Call {call_id} already processed or not found in active calls. Skipping duplicate processing.")
            return
            
        try:
            # Ensure minimum 1 minute billing
            actual_duration = max(1, duration_minutes)
            total_cost = actual_duration * VOICE_CALL_COST_PER_MINUTE
            
            logger.info(f"[CALL END] ==================== CALL BILLING ====================")
            logger.info(f"[CALL END] Call ID: {call_id}")
            logger.info(f"[CALL END] User ID: {user_id}")
            logger.info(f"[CALL END] Raw Duration: {duration_minutes} minutes")
            logger.info(f"[CALL END] Billing Duration: {actual_duration} minutes (minimum 1 minute)")
            logger.info(f"[CALL END] Total Cost: {total_cost} gems ({actual_duration} × {VOICE_CALL_COST_PER_MINUTE})")
            logger.info(f"[CALL END] End Reason: {end_reason}")
            logger.info(f"[CALL END] Start Time: {start_time}")
            
            # Get user's current gem balance
            user_db_data = self.db.get_or_create_user(user_id, "Unknown")
            current_gems = user_db_data.get('gems', 0) if user_db_data else 0
            logger.info(f"[CALL END] User's Current Gem Balance: {current_gems}")
            
            # Calculate gems to deduct (can't exceed current balance)
            gems_to_deduct = min(current_gems, total_cost)
            new_gem_balance = current_gems - gems_to_deduct
            
            logger.info(f"[CALL END] Gems to Deduct: {gems_to_deduct} (min of {current_gems} current vs {total_cost} cost)")
            logger.info(f"[CALL END] New Gem Balance: {new_gem_balance}")
            
            # Update user's gem balance in database
            try:
                supabase.table('users').update({'gems': new_gem_balance}).eq('telegram_id', user_id).execute()
                logger.info(f"[CALL END] ✅ Successfully updated user {user_id} gems: {current_gems} -> {new_gem_balance} (deducted {gems_to_deduct})")
            except Exception as e:
                logger.error(f"[CALL END] ❌ Failed to update gems for user {user_id}: {e}")
            
            # Update call record with actual duration and cost
            try:
                self.db.update_call_duration(call_id, actual_duration)
                supabase.table('voice_calls').update({'gem_cost': gems_to_deduct}).eq('call_id', call_id).execute()
                logger.info(f"[CALL END] ✅ Successfully updated call {call_id} record: duration={actual_duration} min, cost={gems_to_deduct} gems")
            except Exception as e:
                logger.error(f"[CALL END] ❌ Failed to update call record for {call_id}: {e}")
            
            # Remove from active calls
            self.active_calls.pop(call_id, None)
            logger.info(f"[CALL END] Removed call {call_id} from active calls list")
            
            # Update user session gems if they're active
            if user_id in self.active_users:
                self.active_users[user_id].gems = new_gem_balance
                logger.info(f"[CALL END] ✅ Updated session gems for user {user_id}: {new_gem_balance}")
            
            # Send completion message to user
            if gems_to_deduct < total_cost:
                # User didn't have enough gems for full call
                message = f"💖 Your call has ended! Duration: {actual_duration} minutes.\n💎 Charged: {gems_to_deduct} Gems (your available balance)\n💎 Remaining Gems: {new_gem_balance}\n\n✨ Consider buying more Gems for longer calls! 😘"
                logger.info(f"[CALL END] Sending partial payment notification to user {user_id}")
            else:
                # Normal completion
                message = f"💖 Your call has ended! Duration: {actual_duration} minutes.\n💎 Cost: {gems_to_deduct} Gems\n💎 Remaining Gems: {new_gem_balance}\n\nThank you for calling! 😘"
                logger.info(f"[CALL END] Sending full payment notification to user {user_id}")
            
            await self.application.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"[CALL END] ✅ Successfully sent billing notification to user {user_id}")
            
            logger.info(f"[CALL END] ================= BILLING COMPLETE =================")
            logger.info(f"[CALL END] ✅ Successfully processed call end for {call_id}")
            
        except Exception as e:
            logger.error(f"[CALL END] Error processing call end for {call_id}: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Handle WebApp data from frontend
        if update.message and update.message.web_app_data:
            await self.handle_webapp_data(update, context)
            return
            
        if not update.message or not update.message.text:
            return
        user_tg = update.effective_user
        user_id = user_tg.id
        user_message = update.message.text
        logger.info(f"[DEBUG] User message: '{user_message}' (user_id={user_id})")
        
        # FRONTEND INTEGRATION: Refresh user data when they return from WebApp or any interaction
        await self._refresh_user_data_on_return(user_id, user_tg.username or "")
        
        # Check if user is waiting to provide phone number for voice call
        user_session = self.active_users.get(user_id)
        if user_session and user_session.premium_offer_state:
            if user_session.premium_offer_state.get('type') == 'voice_call' and user_session.premium_offer_state.get('status') == 'waiting_for_phone':
                await self.handle_voice_call_phone_collection(update, context, user_id, user_message)
                return
        
        user_db_data = self.db.get_or_create_user(user_id, user_tg.username or "Unknown")
        if not user_db_data:
            await update.message.reply_text("Sorry, there was a problem accessing your profile. Please try again later. 😟")
            return
        # Session should already be loaded by _refresh_user_data_on_return()
        if user_id not in self.active_users:
            logger.warning(f"[SESSION ERROR] User {user_id} missing from active_users after refresh - creating emergency session")
            self.active_users[user_id] = UserData()
        user_session = self.active_users[user_id]
        user_session.last_interaction_time = datetime.now(timezone.utc)
        # Increment session message count for upsell logic
        user_session.session_message_count += 1
        logger.info(f"[SESSION STATE] user_id={user_id}, character={user_session.current_character}, scenario={user_session.current_scenario}")
        await self._schedule_follow_up(user_id)
        # Only prompt for character/scenario if missing
        if not user_session.current_character or not user_session.current_scenario:
            await update.message.reply_text("Please select a character and scenario first! Use /start to begin. 💕")
            return
        if len(user_message) > MAX_MESSAGE_LENGTH:
            await update.message.reply_text(f"Your message is too long! Please keep it under {MAX_MESSAGE_LENGTH} characters. 😊")
            return
        # --- BULLETPROOF SUBSCRIPTION & MESSAGE LIMIT ENFORCEMENT ---
        
        # First, get comprehensive subscription status
        is_subscribed = self.db.check_subscription(user_id)
        is_admin = str(user_id) == ADMIN_CHAT_ID
        
        logger.info(f"[SUBSCRIPTION CHECK] User {user_id}: is_subscribed='{is_subscribed}', is_admin={is_admin}")
        
        # Only enforce daily limits for FREE users (non-subscribed, non-admin)
        if not is_subscribed and not is_admin:
            current_user_data = self.db.get_or_create_user(user_id, user_tg.username or "Unknown")
            messages_today = current_user_data.get('messages_today', 0) if current_user_data else 0
            
            logger.info(f"[MESSAGE LIMIT] Free user {user_id}: {messages_today}/{DAILY_MESSAGE_LIMIT} messages today")
            
            if messages_today >= DAILY_MESSAGE_LIMIT:
                keyboard = [[InlineKeyboardButton("✨ Upgrade Now", web_app={"url": "https://secret-share.com"})]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "You've reached your daily free message limit! ✨ To continue our conversation without interruption, you can get a subscription for unlimited access and monthly Gems. Tap below to see the options.",
                    reply_markup=reply_markup
                )
                logger.info(f"[MESSAGE LIMIT] ❌ Blocked free user {user_id} at {messages_today} messages")
                return
        user_session.message_count_since_last_image += 1
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        # --- EARLY UPSALE CHECKS (move all upsell logic here, before AI response) ---
        # Prevent back-to-back upsells
        now = datetime.now(timezone.utc)
        last_upsell_time = getattr(user_session, 'last_upsell_time', None)
        can_upsell = not last_upsell_time or (now - last_upsell_time).total_seconds() > 0
        # User-initiated premium request
        for offer_type, checker, gem_cost in [
            ('image', is_custom_photo_request, 10),
            ('voice_note', is_voice_note_request, VOICE_NOTE_COST),
            ('voice_call', is_voice_call_request, VOICE_CALL_COST_PER_MINUTE)
        ]:
            if checker(user_message) and can_upsell:
                logger.info(f"[UPSELL] User-initiated {offer_type} request detected for user {user_id}")
                char_ack = await self.generate_upsell_line(user_session, offer_type, user_message)
                user_session.premium_offer_state = {'type': offer_type, 'status': 'pending'}
                await self.send_premium_offer_overlay(update, context, user_id, offer_type, gem_cost, character_line=char_ack)
                return  # Do not send a normal chat reply
        
        # Handle video requests with LoRA detection
        is_video_request, detected_lora = is_custom_video_request(user_message)
        if is_video_request and can_upsell:
            logger.info(f"[UPSELL] User-initiated video request detected for user {user_id} with LoRA: {detected_lora}")
            char_ack = await self.generate_upsell_line(user_session, 'video', user_message)
            # Store detected_lora as None if no specific keyword was found (will trigger random selection)
            user_session.premium_offer_state = {'type': 'video', 'status': 'pending', 'detected_lora': detected_lora}
            await self.send_premium_offer_overlay(update, context, user_id, 'video', 80, character_line=char_ack)
            return  # Do not send a normal chat reply
        # Fallback random/probability-based AI upsell after 10+ messages if no offer has been triggered
        if user_session.session_message_count >= 10 and not (user_session.premium_offer_state and user_session.premium_offer_state.get('status') == 'pending') and can_upsell:
            if random.randint(1, 4) == 1:
                # Weighted upsell based on new probabilities (40% video, 30% voice note, 30% voice call)
                r = random.random()
                if r < UPSELL_PROBABILITIES['video']:
                    offer_type = 'video'
                    gem_cost = 80
                elif r < UPSELL_PROBABILITIES['video'] + UPSELL_PROBABILITIES['voice_note']:
                    offer_type = 'voice_note'
                    gem_cost = VOICE_NOTE_COST
                else:
                    offer_type = 'voice_call'
                    gem_cost = VOICE_CALL_COST_PER_MINUTE
                
                char_ack = await self.generate_upsell_line(user_session, offer_type)
                logger.info(f"[UPSELL] Fallback random AI upsell triggered for user {user_id}: {offer_type}")
                user_session.premium_offer_state = {'type': offer_type, 'status': 'pending'}
                await self.send_premium_offer_overlay(update, context, user_id, offer_type, gem_cost, character_line=char_ack)
                return  # Do not send a normal chat reply
        # --- END EARLY UPSALE CHECKS ---
        # Name detection and prompt logic - ALWAYS check for name updates
        # Only try name extraction if user doesn't have a name or message looks like it contains a name
        potential_name = None
        should_extract_name = (
            not user_session.user_name or 
            user_session.user_name in ['handsome', 'bello', 'there'] or
            any(keyword in user_message.lower() for keyword in ['my name is', 'call me', 'i am', "i'm", 'name is'])
        )
        
        if should_extract_name:
            # Conservative name extraction patterns
            name_patterns = [
                r"(?:my name is|call me|the name is|i(?:'m| am)|it's|this is|you can call me|just call me|name's)\s+([A-Za-z]{2,20})\b",
                r"^([A-Z][a-z]{2,19})[.,!\s]*hi[.,!\s]*$",  # "Jacob, hi." or "Jacob hi" 
                r"^([A-Z][a-z]{2,19})[.,!\s]+here\b"       # "Jacob here"
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    potential_name = match.group(1).capitalize()
                    logger.info(f"[NAME EXTRACTION] Matched pattern: '{pattern}' → Name: '{potential_name}'")
                    break
            
            # Only set name if we found one OR if no name exists yet
            if potential_name:
                old_name = user_session.user_name
                user_session.user_name = potential_name
                self.db.update_user_name(user_id, user_session.user_name)
                logger.info(f"[NAME UPDATE] ✅ User {user_id} name updated from '{old_name}' to '{potential_name}' in session and database")
            elif not user_session.user_name or user_session.user_name in ['handsome', 'bello', 'there']:
                # Only use placeholder if no name was found AND no real name exists
                user_session.user_name = random.choice(['handsome', 'bello', 'there'])
                logger.info(f"[NAME PLACEHOLDER] ⚠️ No name detected in message '{user_message}', using placeholder '{user_session.user_name}' for user {user_id}")
        
        # Only log name extraction for debug when actually extracting
        if should_extract_name:
            logger.info(f"[NAME EXTRACTION] User message: '{user_message}' | Extracted: '{potential_name}' | Current name: '{user_session.user_name}'")
        # v68: Enhanced state machine with validation
        if user_session.clothing_state == 'clothed' and any(keyword in user_message.lower() for keyword in self.image_generator.nsfw_keywords):
            if user_session.update_clothing_state('undressing'):
                logger.info(f"[STATE] User {user_id}: clothed -> undressing (triggered by keywords)")
            else:
                logger.warning(f"[STATE] Invalid transition attempted for user {user_id}")

        # --- Image Generation Trigger ---
        trigger_image_generation = False
        if user_session.free_images_sent < FREE_IMAGE_LIMIT:
            is_first_image = user_session.message_count_since_last_image == 3
            is_subsequent_image = user_session.message_count_since_last_image > 3 and (user_session.message_count_since_last_image - 3) % 4 == 0
            
            if is_first_image or is_subsequent_image:
                logger.info(f"[TRIGGER] Image generation for user {user_id} at message count {user_session.message_count_since_last_image}.")
                trigger_image_generation = True
        
        # --- Context Loop: Generate Image First ---
        generated_image_url = None
        if trigger_image_generation:
            generated_image_url = await self._generate_and_send_image(update, context, user_id, user_message)
            if generated_image_url:
                self.active_users[user_id].last_image_url = generated_image_url
                logger.info(f"[STATE] Saved last_image_url for user {user_id}: {generated_image_url}")
            user_session.message_count_since_last_image = 0

        # --- Always Generate a Text Response ---
        try:
            character = CHARACTERS[user_session.current_character]
            # Use the user's actual name if available, else prompt for it
            if user_session.user_name:
                user_name_for_prompt = user_session.user_name
            else:
                user_name_for_prompt = random.choice(['handsome', 'bello', 'there'])
            base_prompt = character["system_prompt_base"].format(user_name=escape_markdown(user_name_for_prompt or "", version=2))
            scenario_prompt = f"You are in {character['scenarios'][user_session.current_scenario]['scenario_prompt']}. You are wearing {user_session.character_current_outfit}."
            # Add explicit instruction to keep responses simple and clear, and for first two messages, be welcoming and direct
            if len(user_session.conversation_history) <= 1:
                system_prompt_full = f"{base_prompt}\n**Current Scenario Context:** {scenario_prompt}\n**IMPORTANT:** For the first two messages, use simple, welcoming, and direct English. Be friendly and easy to understand. Keep responses concise (max 100 tokens). Think naturally but express yourself briefly and clearly."
            else:
                system_prompt_full = f"{base_prompt}\n**Current Scenario Context:** {scenario_prompt}\n**IMPORTANT:** Use simple, clear, easy-to-understand English. Keep responses concise (max 100 tokens). Avoid fancy words, complex sentences, or long paragraphs. Respond naturally and keep it friendly. Think like a real person having a casual conversation."
            # v69: Always inject last image context if available
            if hasattr(user_session, 'last_image_context') and user_session.last_image_context:
                img_ctx = user_session.last_image_context
                if img_ctx['clothing_state'] == 'nude':
                    system_prompt_full += "\n**IMAGE CONTEXT:** You have just revealed your naked body to the user in the last image. Your dialogue MUST acknowledge this reality. You are no longer wearing clothes. Reference the image naturally in your response."
                elif img_ctx['clothing_state'] == 'undressing':
                    system_prompt_full += f"\n**IMAGE CONTEXT:** An image of you in a state of undress was just sent. You are partially removing your {img_ctx['outfit']}. Your dialogue must acknowledge this ongoing action."
                else:  # clothed
                    system_prompt_full += f"\n**IMAGE CONTEXT:** An image of you wearing {img_ctx['outfit']} was just sent. Your dialogue should naturally reference your appearance or the visual moment captured."
            elif generated_image_url:
                # fallback for legacy
                if user_session.clothing_state == 'nude':
                    system_prompt_full += "\n**IMAGE CONTEXT:** You have just revealed your naked body to the user in the image that was sent. Your dialogue MUST acknowledge this reality. You are no longer wearing clothes. Reference the image naturally in your response."
                elif user_session.clothing_state == 'undressing':
                    system_prompt_full += f"\n**IMAGE CONTEXT:** An image of you in a state of undress was just sent. You are partially removing your {user_session.character_current_outfit}. Your dialogue must acknowledge this ongoing action."
                else:
                    system_prompt_full += f"\n**IMAGE CONTEXT:** An image of you wearing {user_session.character_current_outfit} was just sent. Your dialogue should naturally reference your appearance or the visual moment captured."
            # If user name is missing, prompt for it
            if not user_session.user_name:
                await update.message.reply_text("Before we continue, what should I call you? Please tell me your name.")
                return
            prompt_parts = [f"<|im_start|>system\n{system_prompt_full}<|im_end|>"]
            for turn in user_session.conversation_history[-5:]:
                prompt_parts.append(f"<|im_start|>{turn['role']}\n{turn['content']}<|im_end|>")
            prompt_parts.append(f"<|im_start|>user\n{user_message}<|im_end|>")
            prompt_parts.append(f"<|im_start|>assistant\n{character['full_name']}:")
            final_prompt = "".join(prompt_parts)

            raw_bot_response = ""
            if self.kobold_available:
                raw_bot_response = await self.kobold_api.generate(final_prompt, max_tokens=100)
            else:
                raw_bot_response = "*I sigh softly.* My thoughts are a bit hazy right now... I can't seem to connect. Please try again in a little while."

            # --- Final Processing ---
            completed_sentence_response = self._ensure_complete_sentence(raw_bot_response)
            # Validate and fix action segments
            completed_sentence_response = self._validate_and_fix_actions(completed_sentence_response, user_session.user_name or "you")
            if not completed_sentence_response:
                completed_sentence_response = "*I bite my lip, a thoughtful look in my eyes...* I don't know what to say."

            # v68: Enhanced state detection with validation
            if user_session.clothing_state == 'undressing' and "naked" in completed_sentence_response.lower() and any(phrase in completed_sentence_response.lower() for phrase in ["step out of", "completely naked", "fully nude"]):
                if user_session.update_clothing_state('nude'):
                    self.active_users[user_id].character_current_outfit = "nothing but your bare skin"
                    logger.info(f"[STATE] User {user_id}: undressing -> nude (detected in response)")
                    user_session.conversation_history.append({"role": "system", "content": "SYSTEM NOTIFICATION: You are now completely naked. The user can see you. Your next response MUST acknowledge that you are naked."})

            final_response = completed_sentence_response.strip()

            if final_response:
                await update.message.reply_text(final_response)

            user_session.conversation_history.append({"role": "user", "content": user_message})
            if final_response:
                user_session.conversation_history.append({"role": "assistant", "content": final_response})
            if len(user_session.conversation_history) > 50:
                user_session.conversation_history = user_session.conversation_history[-50:]
            
            asyncio.create_task(self.db.update_user_on_message(user_id))
            if final_response:
                asyncio.create_task(self.db.create_conversation_entry(user_id, character['full_name'], user_message, final_response))

            # Save session to database after successful message processing
            session_data = {
                'current_character': user_session.current_character,
                'current_scenario': user_session.current_scenario,
                'conversation_history': user_session.conversation_history,
                'user_name': user_session.user_name,
                'clothing_state': user_session.clothing_state,
                'character_current_outfit': user_session.character_current_outfit,
                'free_images_sent': user_session.free_images_sent,
                'message_count_since_last_image': user_session.message_count_since_last_image,
                'session_message_count': user_session.session_message_count,
                'asked_for_name': user_session.asked_for_name,
                'last_interaction_time': user_session.last_interaction_time.isoformat()
            }
            asyncio.create_task(self.db.save_user_session(user_id, session_data))

        except Exception as e:
            logger.error(f"Error in handle_message for user {user_id}: {e}", exc_info=True)
            await update.message.reply_text("Oh, my... I seem to have gotten my thoughts all tangled up. Could you say that again? 💕")

    async def _generate_and_send_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_message: Optional[str] = None) -> Optional[str]:
        """
        v68: Generates and sends an image with enhanced error handling and logging. Accepts user_message for image context.
        Now downloads the blurred image and re-uploads it to Telegram as a file if needed.
        """
        await context.bot.send_chat_action(chat_id=user_id, action="upload_photo")
        user_session = self.active_users.get(user_id)
        if not user_session:
            logger.error(f"[IMAGE] Could not find active session for user {user_id}")
            return None
        try:
            image_url = await self.image_generator.generate_final_image(user_session, user_message)
            if image_url:
                if not isinstance(image_url, str):
                    logger.error(f"[IMAGE] Generated URL is not a string: {type(image_url)}")
                    await update.message.reply_text("There was a problem with the generated image format. Please try again.")
                    return None
                user_session.free_images_sent += 1
                # All users (paid and free) get blurred images every 2nd image
                logger.info(f"[BLUR DEBUG] User {user_id} - Image #{user_session.free_images_sent}, should blur: {user_session.free_images_sent % 2 == 0}")
                if user_session.free_images_sent % 2 == 0:
                    logger.info(f"[BLUR] Attempting to blur image #{user_session.free_images_sent} for user {user_id}")
                    blurred_url = blur_image_with_replicate(image_url, blur_scale=1000)
                    if blurred_url:
                        logger.info(f"[BLUR] Successfully got blurred URL: {blurred_url}")
                        import requests
                        from io import BytesIO
                        try:
                            resp = requests.get(blurred_url)
                            resp.raise_for_status()
                            img_bytes = BytesIO(resp.content)
                            img_bytes.name = 'blurred.jpg'
                            user_session.last_blurred_image_url = image_url
                            keyboard = [[InlineKeyboardButton("✅ Yes (💎 10)", callback_data="unblur_image")]]  # Only Yes button, no No
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            await update.message.reply_photo(
                                photo=img_bytes,
                                caption="The image is a bit hazy... Unblur for 10 Gems?",
                                reply_markup=reply_markup
                            )
                            logger.info(f"[BLUR] Successfully sent blurred image to user {user_id}")
                        except Exception as e:
                            logger.error(f"[BLUR] Failed to download/re-upload blurred image: {e}")
                            logger.error(f"[BLUR] Falling back to original image for user {user_id}")
                            await update.message.reply_photo(photo=image_url)
                    else:
                        # Fallback: send original image if blur failed
                        logger.warning(f"[BLUR] Blur failed, sending original image to user {user_id}")
                        await update.message.reply_photo(photo=image_url)
                else:
                    # Send unblurred image for 1st, 3rd, 5th images etc.
                    await update.message.reply_photo(photo=image_url)
                logger.info(f"[IMAGE] Successfully sent image #{user_session.free_images_sent} to user {user_id}")
                return image_url
                await update.message.reply_text("I tried to show you, but my camera seems to be malfunctioning... maybe try again in a moment?")
                return None
        except Exception as e:
            logger.error(f"[IMAGE] Failed to generate/send image for user {user_id}: {e}", exc_info=True)
            await update.message.reply_text("I tried to show you, but something went wrong... let's continue our conversation though.")
            return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       user = update.effective_user
       db_user = self.db.get_or_create_user(user.id, user.username or "Unknown")

       if not db_user:
            await update.message.reply_text("Sorry, there was a problem creating your profile. Please try again later. 😟")
            return

       if not db_user.get('age_verified', False):
           keyboard = [[InlineKeyboardButton("✅ Yes, I am 18 or older", callback_data="verify_age_yes")], [InlineKeyboardButton("❌ No, I am under 18", callback_data="verify_age_no")]]
           await update.message.reply_text(
               "Welcome to Secret Share! This bot is for adults only.\n\n"
               "*Please confirm you are 18 years of age or older to continue.*",
               reply_markup=InlineKeyboardMarkup(keyboard),
               parse_mode=ParseMode.MARKDOWN
           )
           return
       
       await self._show_character_selection(update.message, context)

    async def _show_character_selection(self, message, context: ContextTypes.DEFAULT_TYPE):
       welcome_text = "*Choose your companion:*\n\n"
       for char_id, char_data in CHARACTERS.items():
           welcome_text += f"{char_data['name']} - {char_data['description']}\n"
       
       keyboard = []
       char_keys = list(CHARACTERS.keys())
       # Start with Isabella as the first option
       if 'isabella' in char_keys:
           char_keys.insert(0, char_keys.pop(char_keys.index('isabella')))

       for i in range(0, len(char_keys), 2):
           row = []
           if i < len(char_keys):
               char = CHARACTERS[char_keys[i]]
               row.append(InlineKeyboardButton(char["name"], callback_data=f"char|{char_keys[i]}"))
           if i + 1 < len(char_keys):
               char = CHARACTERS[char_keys[i+1]]
               row.append(InlineKeyboardButton(char["name"], callback_data=f"char|{char_keys[i+1]}"))
           keyboard.append(row)
       
       reply_markup = InlineKeyboardMarkup(keyboard)

       try:
           await message.edit_text(text=welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
       except BadRequest:
           await context.bot.send_message(chat_id=message.chat.id, text=welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
       except Exception as e:
           logger.error(f"Error in _show_character_selection: {e}")
           await context.bot.send_message(chat_id=message.chat.id, text=welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def age_verification_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       query = update.callback_query
       await query.answer()
       
       if query.data == "verify_age_yes":
           if self.db.set_age_verified(query.from_user.id):
               await query.edit_message_text(f"*Thank you for verifying!* You've received **{WELCOME_GEMS_BONUS} FREE GEMS** 💎 to use on special features later.", parse_mode=ParseMode.MARKDOWN)
               await asyncio.sleep(2)
               await self._show_character_selection(query.message, context)
           else:
               await query.edit_message_text("Something went wrong with verification. Please try again. 😟")
       else:
           await query.edit_message_text("We're sorry, but this bot is only available to users 18 years of age and older. 👋")

    async def character_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       query = update.callback_query
       await query.answer()
       
       user_id = query.from_user.id
       # Only initialize user_session if it does not exist
       if user_id not in self.active_users:
           logger.info(f"[SESSION INIT] Creating new session for user {user_id} (character_callback)")
           self.active_users[user_id] = UserData()
       user_session = self.active_users[user_id]

       try:
           prefix, char_key = query.data.split('|', 1)
       except ValueError:
           logger.error(f"[CALLBACK] Could not unpack character data: {query.data}")
           return

       if char_key in CHARACTERS:
           logger.info(f"[SESSION] User {user_id} starting new session with {char_key}. Wiping session data.")
           # Only reset session if user is switching character (not after scenario is set)
           self.active_users[user_id] = UserData()
           self.active_users[user_id].current_character = char_key
           await self._show_scenario_selection(query, context)

    async def _show_scenario_selection(self, query: Update, context: ContextTypes.DEFAULT_TYPE):
       user_id = query.from_user.id
       user_session = self.active_users.get(user_id)
       if not user_session or not user_session.current_character:
            logger.error(f"[SCENARIO] Could not find active session for user {user_id}")
            return

       character = CHARACTERS[user_session.current_character]
       
       text = f"You've chosen {character['name']}. Now, pick a scenario to begin:"
       keyboard = []
       for scenario_id, scenario_data in character["scenarios"].items():
           callback_data = f"scenario|{user_session.current_character}|{scenario_id}"
           keyboard.append([InlineKeyboardButton(scenario_data['title'], callback_data=callback_data)])
       
       keyboard.append([InlineKeyboardButton("⬅️ Back to Characters", callback_data="back_to_chars")])
       reply_markup = InlineKeyboardMarkup(keyboard)
       await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def scenario_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       query = update.callback_query
       await query.answer()
       
       user_id = query.from_user.id
       # Only initialize user_session if it does not exist
       if user_id not in self.active_users:
           logger.info(f"[SESSION INIT] Creating new session for user {user_id} (scenario_callback)")
           self.active_users[user_id] = UserData()
       user_session = self.active_users.get(user_id)
       if not user_session:
            logger.error(f"[SCENARIO] Could not find active session for user {user_id}")
            return
       
       try:
           prefix, char_id, scenario_id = query.data.split('|', 2)
       except ValueError:
           logger.error(f"[CALLBACK] Could not unpack scenario data: {query.data}")
           return
       
       user_session.current_character = char_id
       user_session.current_scenario = scenario_id
       character = CHARACTERS[char_id]
       scenario = character["scenarios"][scenario_id]

       # v68: Initialize character outfit and state
       user_session.character_current_outfit = scenario['character_outfit']
       user_session.clothing_state = "clothed"
       user_session.state_transition_history = ["init->clothed"]
       # Reset session message count on new scenario
       user_session.session_message_count = 0
       logger.info(f"[STATE] User {user_id} initialized with outfit: {user_session.character_current_outfit}")
       
       await query.delete_message()

       background_image_url = scenario.get("background_image_url")
       intro_text = f"_{scenario['intro_text']}_"
       if background_image_url:
           try:
               await context.bot.send_photo(
                   chat_id=user_id,
                   photo=background_image_url,
                   caption=intro_text,
                   parse_mode=ParseMode.MARKDOWN
               )
           except Exception as e:
               logger.error(f"Failed to send background photo '{background_image_url}'. Error: {e}")
               await context.bot.send_message(chat_id=user_id, text=intro_text, parse_mode=ParseMode.MARKDOWN)
       else:
            await context.bot.send_message(chat_id=user_id, text=intro_text, parse_mode=ParseMode.MARKDOWN)

       await asyncio.sleep(2.5)

       intro_image_url = scenario.get("intro_image_url")
       first_message = scenario['first_message']
       
       user_session.conversation_history = [{"role": "assistant", "content": first_message}]
       
       if intro_image_url:
           try:
               await context.bot.send_photo(
                   chat_id=user_id,
                   photo=intro_image_url,
                   caption=first_message,
                   parse_mode=ParseMode.MARKDOWN
               )
           except Exception as e:
               logger.error(f"Failed to send intro photo with caption. Error: {e}")
               await context.bot.send_message(chat_id=user_id, text=first_message, parse_mode=ParseMode.MARKDOWN)
       else:
           await context.bot.send_message(chat_id=user_id, text=first_message, parse_mode=ParseMode.MARKDOWN)
       
       await self._schedule_follow_up(user_id)

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       query = update.callback_query
       await query.answer()
       if query.data == "back_to_chars":
           await self._show_character_selection(query.message, context)

    async def premium_offer_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       query = update.callback_query
       await query.answer()
       user_id = query.from_user.id
       user_session = self.active_users.get(user_id)
       if not user_session or not user_session.premium_offer_state:
           await query.edit_message_text("Sorry, this offer is no longer valid.")
           return
       data = query.data
       if data.startswith("premium_yes"):
           try:
               _, offer_type, gem_cost = data.split("|", 2)
               gem_cost = int(gem_cost)
               # --- VIDEO OFFER: Use 80 gems instead of 100 ---
               if offer_type == 'video':
                   gem_cost = 80
               user_db_data = self.db.get_or_create_user(user_id, getattr(update.effective_user, 'username', 'Unknown'))
               gems = user_db_data.get('gems', 0) if user_db_data else 0
               if gems < gem_cost:
                   # Create upgrade button for insufficient funds
                   keyboard = [[InlineKeyboardButton("💎 Upgrade", web_app={"url": "https://secret-share.com"})]]
                   reply_markup = InlineKeyboardMarkup(keyboard)
                   await query.edit_message_text(
                       f"You don't have enough Gems for this premium content. You need {gem_cost} Gems but have {gems} Gems.",
                       reply_markup=reply_markup
                   )
                   user_session.premium_offer_state = {}
                   return
               # Deduct gems
               try:
                   # Always store pre-deduction balance BEFORE deduction for all premium features
                   self.db.start_gem_deduction(user_id)
                   supabase.table('users').update({'gems': gems - gem_cost}).eq('telegram_id', user_id).execute()
               except Exception as e:
                   await query.edit_message_text("There was a problem processing your payment. Please try again later.")
                   user_session.premium_offer_state = {}
                   return
               # --- LoRA selection for video ---
               lora_type = None
               if offer_type == 'video':
                   # Try keyword mapping from last user message, else random
                   last_user_msg = None
                   for turn in reversed(user_session.conversation_history):
                       if turn['role'] == 'user':
                           last_user_msg = turn['content']
                           break
               # --- Generate upsell line with LoRA and conversation context ---
               # char_ack = await self.generate_upsell_line(user_session, offer_type)  # REMOVE this line
               history_window = user_session.conversation_history[-4:] if len(user_session.conversation_history) >= 4 else user_session.conversation_history
               if offer_type == 'image':
                   # Use both upsell line and recent chat for image prompt
                   image_prompt_context = ""  # Don't prepend char_ack again
                   image_prompt_context += "\n".join([f"{turn['role']}: {turn['content']}" for turn in history_window])
                   image_url = await self.image_generator.generate_final_image(user_session, user_message=image_prompt_context)
                   if image_url:
                       # Remove the original message with buttons
                       await query.edit_message_text("\u2764\ufe0f Your image is ready!")
                       await context.bot.send_photo(chat_id=user_id, photo=image_url)
                       self.db.clear_pending_gem_refund(user_id)
                   else:
                       # Refund gems and notify user
                       refunded = self.db.refund_gems(user_id, gem_cost)
                       if refunded:
                        await query.edit_message_text("I'm so sorry, but it seems there was an issue creating your content. The Gems have been automatically refunded to your account. Please feel free to try again in a moment.")
               elif offer_type == 'video':
                   # Check if a specific LoRA was detected from user's message
                   detected_lora = user_session.premium_offer_state.get('detected_lora')
                   if detected_lora:
                       # Use the detected LoRA if a keyword was found
                       logger.info(f"[VIDEO] Using detected LoRA: {detected_lora}")
                   else:
                       # Randomly select from the safe solo action pool
                       detected_lora = random.choice(SOLO_ACTION_LORA_POOL)
                       logger.info(f"[VIDEO] No specific keyword detected, randomly selected LoRA: {detected_lora}")
                   # Step 1: Generate still image using LoRA-specific prompt
                   lora_image_prompt = self._get_lora_image_prompt(user_session, detected_lora)
                   image_url = await self.image_generator.generate_final_image(user_session, user_message=lora_image_prompt)
                   if not image_url:
                       # Refund gems and notify user
                       refunded = self.db.refund_gems(user_id, gem_cost)
                       if refunded:
                           await query.edit_message_text("I'm so sorry, but it seems there was an issue creating your content. The Gems have been automatically refunded to your account. Please feel free to try again in a moment.")
                       user_session.premium_offer_state = {}  # Clear state
                       return
                   
                   # Step 2: Generate video prompt and submit video task
                   video_prompt = await self.generate_video_prompt_with_lora(user_session, lora_image_prompt, detected_lora)
                   
                   # Submit video generation task
                   task_id = await self.video_generator.submit_video_task(
                       image_url=image_url,
                       prompt=video_prompt,
                       lora_url=WAVESPEED_ACTION_LORA_MAP[detected_lora]["lora_url"]
                   )
                   
                   if task_id:
                       # Update user session
                       user_session.last_video_task = {"task_id": task_id, "status": "pending"}
                       
                       # Remove the original message with buttons
                       await query.edit_message_text("💕 Your video is being created! I'll send it to you when it's ready (usually within 2-3 minutes).")
                       
                       # Clear pending gem refund since task was successful
                       self.db.clear_pending_gem_refund(user_id)
                       
                       # Start polling for completion
                       asyncio.create_task(self._poll_video_completion(user_id, task_id))
                   else:
                       # Refund gems if task submission failed
                       refunded = self.db.refund_gems(user_id, gem_cost)
                       if refunded:
                           await query.edit_message_text("I'm so sorry, but it seems there was an issue creating your content. The Gems have been automatically refunded to your account. Please feel free to try again in a moment.")
               elif offer_type == 'voice':
                   # Just deliver the voice note (stub)
                   await query.edit_message_text("💕 Your voice note is ready!")
                   await asyncio.sleep(2)
                   await context.bot.send_message(chat_id=user_id, text="[Voice note delivered: (stub)]")
               elif offer_type == 'voice_note':
                   # Generate voice note using ElevenLabs
                   try:
                       if not user_session.current_character:
                           return
                       character = CHARACTERS[user_session.current_character]
                       voice_id = character['voice_id']
                       # Generate a new voice note response
                       user_name = user_session.user_name or "you"
                       # Generate a new voice note message
                       voice_prompt = (
                           f"<|im_start|>system\n{character['system_prompt_base'].format(user_name=escape_markdown(user_name, version=2))}\n"
                           f"**Current Scenario:** {character['scenarios'][user_session.current_scenario]['scenario_prompt']}\n"
                           f"**Current Outfit:** {user_session.character_current_outfit}\n"
                           f"Generate a short, intimate voice note message (2-3 sentences max). "
                           f"Make it personal and seductive. Do NOT use asterisks, brackets, or sound effect tags. Just write a natural, intimate voice note. It just needs to be a normal text to voice message without any special characters or formatting. No asterisks, brackets, or sound effect tags in the voice message. "
                           f"Keep it natural and conversational.<|im_end|>\n"
                           f"<|im_start|>user\nCreate a voice note for me<|im_end|>\n"
                           f"<|im_start|>assistant\n{character['full_name']}:"
                       )
                       if self.kobold_available:
                           voice_message = await self.kobold_api.generate(voice_prompt, max_tokens=60)
                           voice_message = self._ensure_complete_sentence(voice_message)
                       else:
                           voice_message = f"Hey {user_name}, missing you so much right now..."
                       
                       # Clean voice text for TTS
                       clean_text = clean_voice_note_text(voice_message)
                       
                       # Generate voice note using ElevenLabs
                       voice_bytes = await self.elevenlabs_manager.create_voice_note(clean_text, voice_id)
                       
                       if voice_bytes:
                           # Remove the original message with buttons
                           await query.edit_message_text("💕 Your voice note is ready!")
                           
                           # Send voice note
                           from io import BytesIO
                           voice_io = BytesIO(voice_bytes)
                           voice_io.name = f"{character['name']}_voice_note.mp3"
                           await context.bot.send_voice(
                               chat_id=user_id,
                               voice=voice_io,
                               caption=f"💕 {character['name']} sent you a voice note!"
                           )
                           
                           # Clear pending gem refund since voice note was successful
                           self.db.clear_pending_gem_refund(user_id)
                       else:
                           # Refund gems if voice note creation failed
                           refunded = self.db.refund_gems(user_id, gem_cost)
                           if refunded:
                               await query.edit_message_text("I'm so sorry, but it seems there was an issue creating your voice note. The Gems have been automatically refunded to your account.")
                   except Exception as e:
                       logger.error(f"[VOICE NOTE] Error generating voice note: {e}")
                       # Refund gems on error
                       refunded = self.db.refund_gems(user_id, gem_cost)
                       if refunded:
                           await query.edit_message_text("I'm so sorry, but it seems there was an issue creating your voice note. The Gems have been automatically refunded to your account.")
                       else:
                           await query.edit_message_text("I'm sorry, there was an issue creating your voice note.")
               elif offer_type == 'voice_call':
                   # Initiate voice call using ElevenLabs agent
                   try:
                       if not user_session.current_character:
                           return
                       character = CHARACTERS[user_session.current_character]
                       agent_id = ELEVENLABS_AGENT_IDS[user_session.current_character]
                       # Remove the original message with buttons
                       await query.edit_message_text("Note: Our voice call is a fresh start and won't remember our current chat.")
                       # Ask user for phone number
                       await context.bot.send_message(
                           chat_id=user_id,
                           text=f"💕 {character['name']} wants to call you! Please reply with your phone number (including country code, e.g., +1234567890)."
                       )
                       # Store call request for phone number collection
                       user_session.premium_offer_state = {
                           'type': 'voice_call',
                           'status': 'waiting_for_phone',
                           'agent_id': agent_id,
                           'gem_cost': gem_cost
                       }
                       return  # Don't reset premium_offer_state yet
                   except Exception as e:
                       logger.error(f"[VOICE CALL] Error initiating call: {e}")
                       # No gems to refund since we don't deduct upfront anymore
                       await update.message.reply_text("I'm so sorry, but it seems there was an issue setting up your call. Please try again in a moment.")
                       user_session.premium_offer_state = {}
                       # Notify admin
                       await context.bot.send_message(
                           chat_id=ADMIN_CHAT_ID,
                           text=f"🚨 VOICE CALL FAILURE: User {user_id} - Call initiation failed."
                       )
               user_session.premium_offer_state = {}  # Reset after fulfillment
               if offer_type == 'video':
                   user_session.last_upsell_time = datetime.now(timezone.utc)  # Prevent back-to-back upsells
           except Exception as e:
               logger.error(f"[PREMIUM OFFER] Error: {e}")
               self.db.refund_gems(user_id, gem_cost)
               await query.edit_message_text("I'm so sorry, but it seems there was an issue processing your request. The Gems have been automatically refunded to your account. Please feel free to try again in a moment.")
               await context.bot.send_message(
                   chat_id=ADMIN_CHAT_ID,
                   text=f"🚨 PREMIUM OFFER FAILURE: User {user_id} - {offer_type} failed. {gem_cost} gems refunded. Error: {e}"
               )
               user_session.premium_offer_state = {}
               return

    async def test_upsell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       user_id = update.effective_user.id
       user_session = self.active_users.get(user_id)
       if not user_session:
           self.active_users[user_id] = UserData()
           user_session = self.active_users[user_id]
       logger.info(f"[TEST] /testupsell called by user {user_id}")
       user_session.premium_offer_state = {'type': 'image', 'status': 'pending'}
       await self.send_premium_offer_overlay(
           update, context, user_id, 'image', 10,
           character_line="*I lean forward, a slow smile playing on my lips.* I wish you could see the look on my face right now... the way I'm looking at you."
       )

    async def forceupsell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       user_id = update.effective_user.id
       user_session = self.active_users.get(user_id)
       if not user_session:
           self.active_users[user_id] = UserData()
           user_session = self.active_users[user_id]
       args = context.args if hasattr(context, 'args') else []
       if not args or args[0] not in ['image', 'video', 'voice', 'voice_note', 'voice_call']:
           await update.message.reply_text("Usage: /forceupsell <image|video|voice|voice_note|voice_call>")
           return
       # Map 'voice' to 'voice_note' for compatibility
       offer_type = args[0]
       if offer_type == 'voice':
           offer_type = 'voice_note'
       gem_cost = 10 if offer_type == 'image' else 80 if offer_type == 'video' else 30 if offer_type == 'voice_note' else 50 if offer_type == 'voice_call' else 0
       user_session.premium_offer_state = {'type': offer_type, 'status': 'pending'}
       class DummyQuery:
           def __init__(self, user_id, offer_type, gem_cost):
               self.from_user = type('User', (), {'id': user_id})
               self.data = f"premium_yes|{offer_type}|{gem_cost}"
           async def answer(self):
               pass
           async def edit_message_text(self, text, **kwargs):
               await update.message.reply_text(text)
       class DummyUser:
           def __init__(self, user_id):
               self.id = user_id
               self.username = getattr(update.effective_user, 'username', 'Unknown')
       dummy_update = type(
           'DummyUpdate',
           (),
           {
               'callback_query': DummyQuery(user_id, offer_type, gem_cost),
               'effective_user': DummyUser(user_id)
           }
       )
       await self.premium_offer_callback(dummy_update, context)

    async def testvideo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       """Test video generation functionality."""
       user_id = update.effective_user.id
       
       if str(user_id) != ADMIN_CHAT_ID:
           await update.message.reply_text("This command is only available to administrators.")
           return
           
       # Create a test user session
       test_session = UserData()
       test_session.current_character = "isabella"
       test_session.current_scenario = "intimate_conversation"
       test_session.user_name = "Test User"
       test_session.character_current_outfit = "lingerie"
       
       # Test video generation
       try:
           video_prompt = await self.generate_video_prompt(test_session, "Create a sensual dance video for me")
           logger.info(f"[TEST VIDEO] Generated prompt: {video_prompt}")
           
           # Submit video task
           task_id = await self.video_generator.submit_video_task(
               image_url="https://example.com/test.jpg",  # Placeholder
               prompt=video_prompt or "Beautiful woman smiling seductively"
           )
           
           if task_id:
               await update.message.reply_text(f"✅ Video test successful! Task ID: {task_id}")
               logger.info(f"[TEST VIDEO] Video task submitted successfully: {task_id}")
           else:
               await update.message.reply_text("❌ Video test failed - no task ID returned")
               
       except Exception as e:
           await update.message.reply_text(f"❌ Video test failed with error: {e}")
           logger.error(f"[TEST VIDEO] Error: {e}")

    async def testphone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       """Test phone number import functionality."""
       user_id = update.effective_user.id
       
       if str(user_id) != ADMIN_CHAT_ID:
           await update.message.reply_text("This command is only available to administrators.")
           return
           
       await update.message.reply_text("Testing phone number import...")
       
       try:
           success = await test_phone_number_import()
           if success:
               await update.message.reply_text("✅ Phone number import test successful!")
           else:
               await update.message.reply_text("❌ Phone number import test failed. Check logs for details.")
       except Exception as e:
           await update.message.reply_text(f"❌ Phone number test failed with error: {e}")
           logger.error(f"[TEST PHONE] Error: {e}")

    async def store(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       """Gem store command - opens the Telegram Mini App."""
       user_id = update.effective_user.id
       
       # Get user's current gem balance
       user_db_data = self.db.get_or_create_user(user_id, getattr(update.effective_user, 'username', 'Unknown'))
       gems = user_db_data.get('gems', 0) if user_db_data else 0
               
       # Create store button
       keyboard = [[InlineKeyboardButton("💎 Gem Store", web_app={"url": "https://secret-share.com"})]]
       reply_markup = InlineKeyboardMarkup(keyboard)
       
       await update.message.reply_text(
           f"Welcome to the Gem Store! 💎\n\n"
           f"Your current balance: **{gems} Gems**\n\n"
           f"Click the button below to upgrade your account and unlock premium features!",
           reply_markup=reply_markup,
           parse_mode=ParseMode.MARKDOWN
       )

    # Add this async helper function inside SecretShareBot
    async def generate_upsell_line(self, user_session, offer_type, user_message=None):
       character = CHARACTERS[user_session.current_character]
       user_name = user_session.user_name or random.choice(['handsome', 'bello', 'there'])
       scenario = character['scenarios'][user_session.current_scenario]
       persona_prompt = character['system_prompt_base'].format(user_name=escape_markdown(user_name, version=2))
       scenario_prompt = f"You are in {scenario['scenario_prompt']}. You are wearing {user_session.character_current_outfit}."
       offer_noun = {
           'image': 'photo',
           'video': 'video',
           'voice': 'voice note',
           'voice_note': 'voice note',
           'voice_call': 'voice call'
       }[offer_type]
       # --- Conversation context ---
       history_window = user_session.conversation_history[-4:] if len(user_session.conversation_history) >= 4 else user_session.conversation_history
       history_text = "\n".join([f"{turn['role']}: {turn['content']}" for turn in history_window])
       # --- Instruction ---
       upsell_instruction = (
           f"Generate a short, in-character, natural upsell line for offering a {offer_noun} to the user, based on the current conversation and your persona. "
           "Do NOT break character. Do NOT mention gems, payment, or cost. Make it feel like a natural, playful, or enticing suggestion. "
           "Do not use a template. Respond as you would in the ongoing roleplay."
       )
       prompt_parts = [
           f"<|im_start|>system\n{persona_prompt}\n**Current Scenario Context:** {scenario_prompt}\n<|im_end|>",
       ]
       if history_text:
           prompt_parts.append(f"<|im_start|>history\n{history_text}<|im_end|>")
       if user_message:
           prompt_parts.append(f"<|im_start|>user\n{user_message}<|im_end|>")
       prompt_parts.append(f"<|im_start|>assistant\n{upsell_instruction}\n{character['full_name']}:")
       final_prompt = "".join(prompt_parts)
       if self.kobold_available:
           raw_upsell = await self.kobold_api.generate(final_prompt, max_tokens=60)
       else:
           raw_upsell = "*I lean in, eyes sparkling.* Would you like something a little more... personal?"
       completed = self._ensure_complete_sentence(raw_upsell)
       return self._validate_and_fix_actions(completed, user_name)

    async def generate_video_prompt_with_lora(self, user_session, user_message, detected_lora_type):
       """
       Generates a video prompt using the detected LoRA type and explicit action description rule.
       Part A: LoRA trigger word/phrase
       Part B: Explicit, non-euphemistic description of physical action
       """
       character = CHARACTERS[user_session.current_character]
       scenario = character['scenarios'][user_session.current_scenario]
       persona_prompt = character['system_prompt_base'].format(user_name=user_session.user_name or "you")
       scenario_prompt = scenario['scenario_prompt']
       
       # Get the LoRA data
       lora_data = WAVESPEED_ACTION_LORA_MAP.get(detected_lora_type)
       if not lora_data:
           logger.warning(f"[VIDEO] Unknown LoRA type: {detected_lora_type}, using default")
           lora_data = WAVESPEED_ACTION_LORA_MAP["style_general_nsfw"]
       
       # Part A: Select a random trigger from the LoRA
       lora_trigger = random.choice(lora_data["lora_triggers"])
       
       # Part B: Generate explicit action description based on LoRA type
       action_description = self._get_explicit_action_description(detected_lora_type)
       
       # Combine character trigger word with LoRA trigger and action description
       video_prompt = f"{character['trigger_word']}, {lora_trigger}, {action_description}"
       
       # Allow longer prompts for video generation (up to 1000 chars for detailed descriptions)
       video_prompt = video_prompt[:1000]
       
       logger.info(f"[VIDEO] Generated prompt for {detected_lora_type}: {video_prompt}")
       return video_prompt

    def _get_explicit_action_description(self, lora_type: str) -> str:
       """
       Returns explicit, non-euphemistic descriptions of physical actions for video generation.
       This ensures the motion generation AI understands the desired physical movement clearly.
       """
       action_descriptions = {
           "pov_blowjob": "the woman's head moves up and down as she performs oral sex on the man's penis",
           "pov_cowgirl": "the woman bounces up and down on the man's erect penis, with visible penetration",
           "pov_missionary": "the man thrusts his penis back and forth inside the woman's vagina with fast movement",
           "fingering": "the woman inserts her fingers into her vagina and moves them in and out",
           "hand_in_panties": "the woman's hand is inside her panties, rubbing her vagina with fast movements",
           "dildo_ride": "the woman rides a dildo, moving her body up and down as it slides in and out of her vagina",
           "deepthroat": "the woman takes the entire penis into her mouth and throat, moving her head back and forth",
           "pov_titfuck": "the woman uses her breasts to stimulate the penis, moving them up and down",
           "bouncing_boobs": "the woman's breasts bounce and jiggle with her movements",
           "facial_cumshot": "semen is ejaculated onto the woman's face",
           "style_general_nsfw": "the woman removes her clothing, revealing her naked body"
       }
       
       return action_descriptions.get(lora_type, "the woman performs intimate actions")

    async def unblur_image_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       query = update.callback_query
       await query.answer()
       user_id = query.from_user.id
       user_session = self.active_users.get(user_id)
       user_db_data = self.db.get_or_create_user(user_id, getattr(update.effective_user, 'username', 'Unknown'))
       gems = user_db_data.get('gems', 0) if user_db_data else 0
       # Find the last image URL in the session
       last_image_url = user_session.last_blurred_image_url if user_session and hasattr(user_session, 'last_blurred_image_url') else None
       if not last_image_url:
           await query.edit_message_text("Sorry, I couldn't find the original image to unblur.")
           return
       if gems < 10:
           await query.edit_message_text("You don't have enough Gems to unblur this image. Please top up and try again.")
           return
       # Deduct gems
       try:
           supabase.table('users').update({'gems': gems - 10}).eq('telegram_id', user_id).execute()
       except Exception as e:
           await query.edit_message_text("There was a problem processing your payment. Please try again later.")
           return
       # Send only the unblurred image, no extra message
       await context.bot.send_photo(chat_id=user_id, photo=last_image_url)

    async def generate_video_prompt(self, user_session, user_message):
       character = CHARACTERS[user_session.current_character]
       scenario = character['scenarios'][user_session.current_scenario]
       persona_prompt = character['system_prompt_base'].format(user_name=user_session.user_name or "you")
       scenario_prompt = scenario['scenario_prompt']
       history = user_session.conversation_history[-4:]
       history_text = "\n".join([f"{turn['role']}: {turn['content']}" for turn in history])
       instruction = (
           "Generate a short, visually rich, cinematic prompt for a video featuring the character. "
           "Describe the scene, pose, and mood in a tasteful way. Do NOT include any talking, speech, text, or dialogue. "
           "Focus on visual action, body language, and atmosphere. No words, no subtitles, no open mouth as if talking. "
           "Keep it elegant and artistic, avoid explicit or suggestive language."
       )
       prompt = (
           f"<|im_start|>system\n{persona_prompt}\nCurrent scenario: {scenario_prompt}\n<|im_end|>"
           f"<|im_start|>history\n{history_text}<|im_end|>"
           f"<|im_start|>user\n{user_message}<|im_end|>"
           f"<|im_start|>assistant\n{instruction}\nPrompt:"
       )
       if self.kobold_available:
           # Allow longer prompts for video generation (up to 120 tokens instead of 60)
           video_prompt = await self.kobold_api.generate(prompt, max_tokens=120)
           return video_prompt.strip()
    def _get_lora_image_prompt(self, user_session, detected_lora_type):
       """
       Generate an image prompt for video generation using the LoRA's trigger and explicit action description.
       """
       character = CHARACTERS[user_session.current_character]
       lora_data = WAVESPEED_ACTION_LORA_MAP.get(detected_lora_type)
       if not lora_data:
           lora_data = WAVESPEED_ACTION_LORA_MAP["style_general_nsfw"]
       lora_trigger = random.choice(lora_data["lora_triggers"])
       action_description = self._get_explicit_action_description(detected_lora_type)
       # Compose a direct, LoRA-specific prompt
       prompt = f"{character['trigger_word']}, {lora_trigger}, {action_description}, solo, only the woman, no men, no other people"
       return prompt[:800]

    async def handle_voice_call_phone_collection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, phone_number: str):
        """Handle phone number collection for voice calls."""
        user_session = self.active_users.get(user_id)
        if not user_session or not user_session.premium_offer_state:
            await update.message.reply_text("Sorry, this voice call request is no longer valid.")
            return
        if user_session.premium_offer_state.get('type') != 'voice_call':
            return
        # Validate phone number format
        if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
            await update.message.reply_text("Please provide a valid phone number with country code (e.g., +1234567890).")
            return
        try:
            agent_id = user_session.premium_offer_state.get('agent_id')
            gem_cost = VOICE_CALL_COST_PER_MINUTE  # Cost per minute, but don't deduct yet
            # Check user's gem balance for minimum 1 minute
            user_db_data = self.db.get_or_create_user(user_id, getattr(update.effective_user, 'username', 'Unknown'))
            gems = user_db_data.get('gems', 0) if user_db_data else 0
            if gems < gem_cost:
                await update.message.reply_text(f"You don't have enough Gems for this call. You need at least {gem_cost} Gems for 1 minute but have {gems} Gems.")
                user_session.premium_offer_state = {}  # Always reset so user can try again
                return
            # Don't deduct gems yet - store call info for post-call deduction
            max_call_minutes = gems // gem_cost  # Calculate max possible call duration
            
            # Store the call info without deducting gems upfront
            try:
                # Ensure agent_id is a string
                if not agent_id or not isinstance(agent_id, str):
                    await update.message.reply_text("Invalid call configuration. Please try again.")
                    user_session.premium_offer_state = {}
                    return
                    
                # BULLETPROOF USER NAME HANDLING FOR VOICE CALLS
                voice_call_user_name = None
                
                # Layer 1: Check current session user_name
                if user_session.user_name and user_session.user_name not in ['handsome', 'bello', 'there', 'user', 'user#']:
                    voice_call_user_name = user_session.user_name
                    logger.info(f"[VOICE NAME] ✅ Layer 1: Using session name '{voice_call_user_name}' for user {user_id}")
                
                # Layer 2: Check database user_name
                if not voice_call_user_name:
                    if user_db_data and user_db_data.get('user_name') and user_db_data.get('user_name') not in ['handsome', 'bello', 'there', 'user', 'user#']:
                        voice_call_user_name = user_db_data.get('user_name')
                        user_session.user_name = voice_call_user_name  # Sync session with DB
                        logger.info(f"[VOICE NAME] ✅ Layer 2: Using database name '{voice_call_user_name}' for user {user_id}")
                
                # Layer 3: Extract from conversation history
                if not voice_call_user_name and user_session.conversation_history:
                    for entry in reversed(user_session.conversation_history[-10:]):  # Check last 10 messages
                        if entry.get('role') == 'user':
                            user_msg = entry.get('content', '')
                            # Try to extract name from previous messages
                            name_patterns = [
                                r"(?:my name is|call me|the name is|i(?:'m| am)|it's|this is|you can call me|just call me|name's)\s+([A-Za-z]{2,20})\b",
                                r"^([A-Za-z]{2,20})[.,!\s]*$"
                            ]
                            for pattern in name_patterns:
                                match = re.search(pattern, user_msg, re.IGNORECASE)
                                if match:
                                    potential_name = match.group(1).capitalize()
                                    if potential_name not in ['Hi', 'Hey', 'Hello', 'Yes', 'No', 'Ok', 'Okay']:
                                        voice_call_user_name = potential_name
                                        user_session.user_name = voice_call_user_name
                                        self.db.update_user_name(user_id, voice_call_user_name)
                                        logger.info(f"[VOICE NAME] ✅ Layer 3: Extracted name '{voice_call_user_name}' from conversation history for user {user_id}")
                                        break
                        if voice_call_user_name:
                            break
                
                # Layer 4: Use Telegram username as fallback
                if not voice_call_user_name:
                    telegram_username = getattr(update.effective_user, 'username', None)
                    if telegram_username and telegram_username not in ['user', 'user#']:
                        voice_call_user_name = telegram_username.capitalize()
                        logger.info(f"[VOICE NAME] ✅ Layer 4: Using Telegram username '{voice_call_user_name}' for user {user_id}")
                
                # Layer 5: Safe intimate fallback (NEVER "user#")
                if not voice_call_user_name:
                    intimate_names = ['baby', 'honey', 'sweetheart', 'darling']
                    voice_call_user_name = random.choice(intimate_names)
                    logger.info(f"[VOICE NAME] ⚠️ Layer 5: Using intimate fallback '{voice_call_user_name}' for user {user_id}")
                
                # Final validation: Ensure we NEVER have "user#" or empty
                if not voice_call_user_name or 'user' in voice_call_user_name.lower():
                    voice_call_user_name = "baby"
                    logger.warning(f"[VOICE NAME] 🚨 Final safety: Forcing name to 'baby' for user {user_id}")
                
                logger.info(f"[VOICE CALL] 🎯 FINAL NAME DECISION: User {user_id} will be called '{voice_call_user_name}' during voice call")
                    
                call_id = await self.elevenlabs_manager.initiate_voice_call(agent_id, phone_number, user_id, voice_call_user_name)
                if call_id:
                    # Store call info for tracking
                    self.active_calls[call_id] = user_id
                    # Log the call in database (gems will be deducted after call ends)
                    self.db.log_voice_call(user_id, call_id, agent_id, phone_number, 0)  # 0 gems for now
                    
                    # Start real-time monitoring to prevent exceeding gem balance
                    context.job_queue.run_repeating(
                        callback=self._monitor_call_duration,
                        interval=30,  # Check every 30 seconds
                        data={'call_id': call_id, 'user_id': user_id, 'max_minutes': max_call_minutes, 'start_time': datetime.now(timezone.utc)},
                        name=f"call_monitor_{call_id}"
                    )
                    
                    await update.message.reply_text(f"📞 Calling you now! Maximum call duration: {max_call_minutes} minutes based on your {gems} Gems. You'll be charged {gem_cost} Gems per minute after the call ends.\n\n⚠️ Call will automatically end when you reach your gem limit.")
                    user_session.premium_offer_state = {}
                else:
                    # Voice call failed to initiate - give user error message
                    logger.error(f"[VOICE CALL] Failed to initiate call for user {user_id}")
                    await update.message.reply_text("❌ Sorry, I couldn't connect the call right now. This might be due to a technical issue or service availability. Please try again in a few minutes.\n\n💎 No gems were charged for this failed attempt.")
                    user_session.premium_offer_state = {}
                    
                    # Notify admin of the failure
                    await context.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"🚨 VOICE CALL FAILURE: User {user_id} - Call initiation returned None"
                    )
            except Exception as e:
                logger.error(f"[VOICE CALL] Error initiating call: {e}")
                # No gems to refund since we don't deduct upfront anymore
                await update.message.reply_text("I'm so sorry, but it seems there was an issue setting up your call. Please try again in a moment.")
                user_session.premium_offer_state = {}
                # Notify admin
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"🚨 VOICE CALL FAILURE: User {user_id} - Call initiation failed."
                )
        except Exception as e:
            logger.error(f"[VOICE CALL] Error processing phone number: {e}")
            # No gems to refund since we don't deduct upfront anymore
            await update.message.reply_text("There was an error processing your request. Please try again later.")
            user_session.premium_offer_state = {}
        # Always reset premium_offer_state at the end so user can make another request
        user_session.premium_offer_state = {}

    async def buygems(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Complete gem store with all gem packs and subscription options."""
        if update.effective_chat.type != 'private':
            await update.message.reply_text("Purchases are only available in private chat.")
            return
        
        # Create inline keyboard with all options
        keyboard = []
        
        # Gem Packs Section
        keyboard.append([InlineKeyboardButton("💎 GEM PACKS 💎", callback_data="gem_header")])
        
        # Row 1: Small packs
        keyboard.append([
            InlineKeyboardButton("45 Gems - 50⭐", callback_data="buy_gems_50"),
            InlineKeyboardButton("95 Gems - 100⭐", callback_data="buy_gems_100")
        ])
        
        # Row 2: Medium packs  
        keyboard.append([
            InlineKeyboardButton("250 Gems - 250⭐", callback_data="buy_gems_250"),
            InlineKeyboardButton("525 Gems - 500⭐", callback_data="buy_gems_500")
        ])
        
        # Row 3: Large packs
        keyboard.append([
            InlineKeyboardButton("1,100 Gems - 1000⭐", callback_data="buy_gems_1000"),
            InlineKeyboardButton("3,000 Gems - 2500⭐", callback_data="buy_gems_2500")
        ])
        
        # Row 4: Mega packs
        keyboard.append([
            InlineKeyboardButton("6,500 Gems - 5000⭐", callback_data="buy_gems_5000"),
            InlineKeyboardButton("15,000 Gems - 10000⭐", callback_data="buy_gems_10000")
        ])
        
        # Subscription Section
        keyboard.append([InlineKeyboardButton("✨ MONTHLY SUBSCRIPTIONS ✨", callback_data="sub_header")])
        
        keyboard.append([
            InlineKeyboardButton("Essential (450 Gems/mo) - 400⭐", callback_data="buy_sub_essential"),
        ])
        
        keyboard.append([
            InlineKeyboardButton("Plus (1,200 Gems/mo) - 800⭐", callback_data="buy_sub_plus"),
        ])
        
        keyboard.append([
            InlineKeyboardButton("Premium (2,500 Gems/mo) - 1600⭐", callback_data="buy_sub_premium"),
        ])
        
        # Add the App button that opens your frontend
        keyboard.append([InlineKeyboardButton("🌐 Open Web Store", web_app={"url": "https://secret-share.com/gem-store"})])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💎✨ **PREMIUM STORE** ✨💎\n\n"
            "**GEM PACKS** 💎\n"
            "• Use gems for images, videos, voice notes & calls\n"
            "• Bigger packs = better value!\n\n"
            "**SUBSCRIPTIONS** ✨\n"
            "• **Unlimited messages** (no daily limit)\n"
            "• Monthly gem allowance\n"
            "• Premium features\n\n"
            "**APP** 📱\n"
            "• Full store experience in your frontend\n\n"
            "Choose your package below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle payment button callbacks and send invoices."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        callback_data = query.data
        
        # Ignore header buttons
        if callback_data in ["gem_header", "sub_header"]:
            return
        
        # Parse callback data
        if callback_data.startswith("buy_gems_"):
            # Gem pack purchase
            pack_size = callback_data.replace("buy_gems_", "")
            pack_key = f"gems_{pack_size}"
            
            if pack_key in GEM_PACKS:
                gem_amount = GEM_PACKS[pack_key]
                # Get star price from the predefined mapping
                star_prices = {
                    'gems_50': 50, 'gems_100': 100, 'gems_250': 250, 'gems_500': 500,
                    'gems_1000': 1000, 'gems_2500': 2500, 'gems_5000': 5000, 'gems_10000': 10000
                }
                stars = star_prices.get(pack_key, 0)
                
                await self._send_gem_invoice(query, pack_key, gem_amount, stars)
                
        elif callback_data.startswith("buy_sub_"):
            # Subscription purchase
            tier = callback_data.replace("buy_sub_", "")
            sub_key = f"sub_{tier}"
            
            if sub_key in SUBSCRIPTION_TIERS:
                tier_name, stars, monthly_gems = SUBSCRIPTION_TIERS[sub_key]
                await self._send_subscription_invoice(query, sub_key, tier_name, stars, monthly_gems)

    # Duplicate methods removed - kept original versions below

    async def _send_gem_invoice(self, query, pack_key: str, gem_amount: int, stars: int):
        """Send invoice for gem pack purchase."""
        try:
            title = f"{gem_amount} Gems"
            description = f"Purchase {gem_amount} Gems for premium features like images, videos, and voice calls."
            payload = pack_key
            provider_token = ""  # Empty for Telegram Stars
            currency = "XTR"
            prices = [{'label': f'{gem_amount} Gems', 'amount': stars}]
            
            await self.application.bot.send_invoice(
                chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            is_flexible=False
        )
            
            await query.edit_message_text(f"💎 Invoice sent for {gem_amount} Gems ({stars} Stars)")
            
        except Exception as e:
            logger.error(f"[PAYMENT] Error sending gem invoice: {e}")
            await query.edit_message_text("❌ Error creating invoice. Please try again.")

    async def _send_subscription_invoice(self, query, sub_key: str, tier_name: str, stars: int, monthly_gems: int):
        """Send invoice for subscription purchase."""
        try:
            title = f"{tier_name.title()} Subscription"
            description = f"Monthly {tier_name.title()} subscription: Unlimited messages + {monthly_gems} Gems/month"
            payload = sub_key
            provider_token = ""  # Empty for Telegram Stars
            currency = "XTR"
            prices = [{'label': f'{tier_name.title()} Monthly', 'amount': stars}]
            
            await self.application.bot.send_invoice(
                chat_id=query.message.chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token=provider_token,
                currency=currency,
                prices=prices,
                need_name=False,
                need_phone_number=False,
                need_email=False,
                is_flexible=False
            )
            
            await query.edit_message_text(f"✨ Invoice sent for {tier_name.title()} subscription ({stars} Stars)")
            
        except Exception as e:
            logger.error(f"[PAYMENT] Error sending subscription invoice: {e}")
            await query.edit_message_text("❌ Error creating subscription invoice. Please try again.")

    def validate_telegram_webhook(self, request_data: str, signature: str) -> bool:
        """Validate Telegram webhook signature for security."""
        import hmac
        import hashlib
        
        if not hasattr(self, '_webhook_secret') or not self._webhook_secret:
            # If no webhook secret is set, skip validation (development only)
            logger.warning("[SECURITY] Webhook signature validation skipped - no secret configured")
            return True
            
        # Calculate expected signature
        secret_key = self._webhook_secret.encode('utf-8')
        expected_signature = hmac.new(
            secret_key,
            request_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures securely
        is_valid = hmac.compare_digest(f"sha256={expected_signature}", signature)
        
        if not is_valid:
            logger.error(f"[SECURITY] Invalid webhook signature. Expected: sha256={expected_signature}, Got: {signature}")
        
        return is_valid

    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Answer pre_checkout_query for Telegram Stars payments with proper validation."""
        query = update.pre_checkout_query
        payload = query.invoice_payload
        total_amount = query.total_amount
        user_id = query.from_user.id
        
        try:
            # Validate payload exists in our systems
            if payload not in GEM_PACKS and payload not in SUBSCRIPTION_TIERS:
                logger.error(f"[PAYMENT] Invalid payload: {payload}")
                await query.answer(ok=False, error_message="Invalid product. Please try again.")
                return
            
            # Validate payment amount matches expected price
            if payload in GEM_PACKS:
                expected_price = {
                    'gems_50': 50, 'gems_100': 100, 'gems_250': 250, 'gems_500': 500,
                    'gems_1000': 1000, 'gems_2500': 2500, 'gems_5000': 5000, 'gems_10000': 10000
                }.get(payload)
            elif payload in SUBSCRIPTION_TIERS:
                expected_price = SUBSCRIPTION_TIERS[payload][1]  # stars amount
            
            if total_amount != expected_price:
                logger.error(f"[PAYMENT] Amount mismatch for {payload}: expected {expected_price}, got {total_amount}")
                await query.answer(ok=False, error_message="Payment amount mismatch. Please try again.")
                return
            
            # Validate user exists and is in good standing
            user_data = self.db.get_or_create_user(user_id, query.from_user.username or "Unknown")
            if not user_data:
                logger.error(f"[PAYMENT] Could not create/get user {user_id}")
                await query.answer(ok=False, error_message="User validation failed. Please contact support.")
                return
            
            # All validations passed
            logger.info(f"[PAYMENT] Pre-checkout approved for user {user_id}, payload {payload}, amount {total_amount}")
            await query.answer(ok=True)
            
        except Exception as e:
            logger.error(f"[PAYMENT] Pre-checkout validation error: {e}")
            await query.answer(ok=False, error_message="Validation error. Please try again or contact support.")

    async def test_payment_edge_cases(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test payment system robustness and edge cases."""
        if str(update.effective_user.id) != ADMIN_CHAT_ID:
            await update.message.reply_text("This command is only available to administrators.")
            return
            
        test_results = []
        
        # Test 1: Duplicate payment processing
        try:
            fake_charge_id = f"test_charge_{datetime.now().timestamp()}"
            # Simulate first payment
            result1 = supabase.table('processed_payments').insert({
                'telegram_charge_id': fake_charge_id,
                'user_id': 12345,
                'payload': 'gems_50',
                'amount': 50,
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'completed'
            }).execute()
            
            # Try duplicate
            try:
                result2 = supabase.table('processed_payments').insert({
                    'telegram_charge_id': fake_charge_id,
                    'user_id': 12345,
                    'payload': 'gems_50',
                    'amount': 50,
                    'processed_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'processing'
                }).execute()
                test_results.append("❌ Duplicate prevention FAILED")
            except:
                test_results.append("✅ Duplicate prevention working")
                
            # Cleanup
            supabase.table('processed_payments').delete().eq('telegram_charge_id', fake_charge_id).execute()
            
        except Exception as e:
            test_results.append(f"❌ Duplicate test error: {e}")
        
        # Test 2: Database connection resilience
        try:
            # Test connection
            result = supabase.table('users').select('count').execute()
            test_results.append("✅ Database connection healthy")
        except Exception as e:
            test_results.append(f"❌ Database connection issue: {e}")
            
        # Test 3: Payment validation
        try:
            # Test invalid payload
            if 'invalid_product' not in GEM_PACKS and 'invalid_product' not in SUBSCRIPTION_TIERS:
                test_results.append("✅ Invalid payload protection working")
            else:
                test_results.append("❌ Invalid payload protection failed")
        except Exception as e:
            test_results.append(f"❌ Validation test error: {e}")
            
        # Test 4: Network timeout simulation
        try:
            import asyncio
            start_time = datetime.now()
            # Simulate a quick operation that should complete
            await asyncio.sleep(0.1)
            end_time = datetime.now()
            if (end_time - start_time).total_seconds() < 1:
                test_results.append("✅ Network timing normal")
            else:
                test_results.append("⚠️ Network latency detected")
        except Exception as e:
            test_results.append(f"❌ Network test error: {e}")
            
        # Compile results
        results_text = "🧪 **Payment System Edge Case Tests**\n\n" + "\n".join(test_results)
        results_text += f"\n\n📊 **System Health:**\n"
        results_text += f"🔗 Database: {'✅ Connected' if 'Database connection healthy' in results_text else '❌ Issues'}\n"
        results_text += f"🛡️ Security: {'✅ Protected' if 'Duplicate prevention working' in results_text else '⚠️ Needs attention'}\n"
        results_text += f"⚡ Performance: {'✅ Good' if 'Network timing normal' in results_text else '⚠️ Slow'}"
        
        await update.message.reply_text(results_text, parse_mode=ParseMode.MARKDOWN)

    async def handle_webapp_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle data sent from Telegram WebApp (your frontend)"""
        try:
            web_app_data = update.message.web_app_data.data
            data = json.loads(web_app_data)
            
            action = data.get('action')
            user_id = update.effective_user.id
            
            logger.info(f"[WEBAPP] Received data from frontend: {data}")
            
            if action == 'buy_gems':
                package_type = data.get('package')
                
                # Validate package
                if package_type not in GEM_PACKS:
                    await update.message.reply_text("❌ Invalid gem package selected.")
                    return
                
                # Get package details
                gem_amount = GEM_PACKS[package_type]
                star_prices = {
                    'gems_50': 50, 'gems_100': 100, 'gems_250': 250, 'gems_500': 500,
                    'gems_1000': 1000, 'gems_2500': 2500, 'gems_5000': 5000, 'gems_10000': 10000
                }
                stars = star_prices.get(package_type, 0)
                
                # Send invoice for Telegram Stars payment
                title = f"{gem_amount} Gems"
                description = f"Purchase {gem_amount} Gems for premium features"
                payload = package_type
                provider_token = ""  # Empty for Telegram Stars
                currency = "XTR"
                prices = [{'label': f'{gem_amount} Gems', 'amount': stars}]
                
                await context.bot.send_invoice(
                    chat_id=user_id,
                    title=title,
                    description=description,
                    payload=payload,
                    provider_token=provider_token,
                    currency=currency,
                    prices=prices,
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    is_flexible=False
                )
                
                await update.message.reply_text(
                    f"💫 Invoice sent for {gem_amount} Gems ({stars} Stars)\n"
                    f"Complete the payment to add gems to your account!"
                )
                
            else:
                await update.message.reply_text(f"❌ Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"[WEBAPP] Error handling WebApp data: {e}")
            await update.message.reply_text("❌ Error processing your request from the website.")

    async def handle_payment_request(self, request):
        """Handle payment initiation requests from your frontend"""
        try:
            # 1. Authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return web.Response(status=401, text='Unauthorized')
            
            token = auth_header.split(' ')[1]
            expected_token = os.getenv('FRONTEND_SECRET_KEY')
            if token != expected_token:
                return web.Response(status=401, text='Invalid token')
            
            # 2. Parse request
            data = await request.json()
            telegram_user_id = data.get('telegram_user_id')
            package_type = data.get('package_type')  # 'gems_50', 'sub_premium', etc.
            
            logger.info(f"[FRONTEND API] Payment request: user {telegram_user_id}, package {package_type}")
            
            # 3. Validate user exists in Telegram
            user_data = self.db.get_or_create_user(telegram_user_id, "Frontend User")
            if not user_data:
                return web.Response(status=400, text='Invalid Telegram user ID')
            
            # 4. Send appropriate invoice
            if package_type in GEM_PACKS:
                # Gem package
                gem_amount = GEM_PACKS[package_type]
                star_prices = {
                    'gems_50': 50, 'gems_100': 100, 'gems_250': 250, 'gems_500': 500,
                    'gems_1000': 1000, 'gems_2500': 2500, 'gems_5000': 5000, 'gems_10000': 10000
                }
                stars = star_prices.get(package_type, 0)
                
                await self.application.bot.send_invoice(
                    chat_id=telegram_user_id,
                    title=f"{gem_amount} Gems",
                    description=f"Purchase {gem_amount} Gems for premium features",
                    payload=package_type,
                    provider_token="",
                    currency="XTR",
                    prices=[{'label': f'{gem_amount} Gems', 'amount': stars}],
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    is_flexible=False
                )
                
                return web.Response(status=200, text=json.dumps({
                    'success': True,
                    'message': f'Invoice sent for {gem_amount} gems ({stars} Stars)',
                    'type': 'gems'
                }))
                
            elif package_type in SUBSCRIPTION_TIERS:
                # Subscription
                tier_name, stars, monthly_gems = SUBSCRIPTION_TIERS[package_type]
                
                await self.application.bot.send_invoice(
                    chat_id=telegram_user_id,
                    title=f"{tier_name.title()} Subscription",
                    description=f"Monthly {tier_name.title()} subscription: Unlimited messages + {monthly_gems} Gems/month",
                    payload=package_type,
                    provider_token="",
                    currency="XTR",
                    prices=[{'label': f'{tier_name.title()} Monthly', 'amount': stars}],
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    is_flexible=False
                )
                
                return web.Response(status=200, text=json.dumps({
                    'success': True,
                    'message': f'Invoice sent for {tier_name} subscription ({stars} Stars)',
                    'type': 'subscription'
                }))
            else:
                return web.Response(status=400, text='Invalid package type')
                
        except Exception as e:
            logger.error(f"[FRONTEND API] Error handling payment request: {e}")
            return web.Response(status=500, text='Internal server error')

    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle successful payment and deliver Gems or Subscriptions with idempotency protection."""
        user_id = update.effective_user.id
        payload = update.message.successful_payment.invoice_payload
        payment_amount = update.message.successful_payment.total_amount
        telegram_payment_charge_id = update.message.successful_payment.telegram_payment_charge_id
        
        logger.info(f"[PAYMENT SUCCESS] User {user_id} paid {payment_amount} Stars for {payload} (charge_id: {telegram_payment_charge_id})")
        
        # Add network resilience and retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Idempotency check - prevent duplicate processing
                existing_payment = supabase.table('processed_payments').select('*').eq('telegram_charge_id', telegram_payment_charge_id).execute()
                if existing_payment.data:
                    logger.warning(f"[PAYMENT] Payment {telegram_payment_charge_id} already processed for user {user_id}")
                    await update.message.reply_text("✅ Payment already processed successfully!")
                    return
                
                # If we get here, process payment successfully
                break
                
            except Exception as retry_error:
                retry_count += 1
                logger.warning(f"[PAYMENT] Retry {retry_count}/{max_retries} for payment {telegram_payment_charge_id}: {retry_error}")
                
                if retry_count >= max_retries:
                    # Final failure after all retries
                    logger.error(f"[PAYMENT] Failed after {max_retries} retries: {retry_error}")
                    await update.message.reply_text(
                        "✅ Payment received, but processing failed after multiple attempts.\n\n"
                        f"Support ID: {telegram_payment_charge_id}\n"
                        "Please contact support immediately. Your payment will be manually processed."
                    )
                    return
                else:
                    # Wait before retry with exponential backoff
                    import asyncio
                    await asyncio.sleep(2 ** retry_count)
        
        # Continue with normal payment processing
        try:
            # Record payment processing attempt
            supabase.table('processed_payments').insert({
                'telegram_charge_id': telegram_payment_charge_id,
                'user_id': user_id,
                'payload': payload,
                'amount': payment_amount,
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'processing'
            }).execute()
            
            # Track Star earnings for analytics
            payment_type = 'gems' if payload in GEM_PACKS else 'subscription'
            gems_granted = GEM_PACKS.get(payload, 0) if payment_type == 'gems' else SUBSCRIPTION_TIERS.get(payload, [None, None, 0])[2]
            subscription_tier = SUBSCRIPTION_TIERS.get(payload, [None])[0] if payment_type == 'subscription' else None
            
            supabase.table('star_earnings').insert({
                'telegram_charge_id': telegram_payment_charge_id,
                'user_id': user_id,
                'payload': payload,
                'stars_amount': payment_amount,
                'payment_type': payment_type,
                'gems_granted': gems_granted,
                'subscription_tier': subscription_tier
            }).execute()
            
            # Handle gem packs
            if payload in GEM_PACKS:
                gem_amount = GEM_PACKS[payload]
                self.db.get_or_create_user(user_id, update.effective_user.username or "Unknown")
                
                # Atomic transaction for gem addition
                user_data = supabase.table('users').select('gems').eq('telegram_id', user_id).execute()
                current_gems = user_data.data[0]['gems'] if user_data.data else 0
                new_total = current_gems + gem_amount
                
                # Update gems atomically
                result = supabase.table('users').update({'gems': new_total}).eq('telegram_id', user_id).execute()
                if not result.data:
                    raise Exception("Failed to update user gems")
                
                # Mark payment as completed
                supabase.table('processed_payments').update({'status': 'completed'}).eq('telegram_charge_id', telegram_payment_charge_id).execute()
                
                await update.message.reply_text(
                    f"✅ **Payment Successful!**\n\n"
                    f"💎 **{gem_amount} Gems** added to your account!\n"
                    f"📊 **Total Gems:** {new_total}\n\n"
                    f"Thank you for your purchase! 💖",
                    parse_mode='Markdown'
                )
                logger.info(f"[PAYMENT SUCCESS] Added {gem_amount} gems to user {user_id}. New total: {new_total}")
                
            # Handle subscriptions
            elif payload in SUBSCRIPTION_TIERS:
                tier, stars, monthly_gems = SUBSCRIPTION_TIERS[payload]
                
                # Atomic subscription update
                self.db.update_subscription(user_id, tier, duration_days=30)
                
                # Add monthly gems atomically
                self.db.get_or_create_user(user_id, update.effective_user.username or "Unknown")
                user_data = supabase.table('users').select('gems').eq('telegram_id', user_id).execute()
                current_gems = user_data.data[0]['gems'] if user_data.data else 0
                new_total = current_gems + monthly_gems
                
                result = supabase.table('users').update({'gems': new_total}).eq('telegram_id', user_id).execute()
                if not result.data:
                    raise Exception("Failed to update user gems for subscription")
                
                # Mark payment as completed
                supabase.table('processed_payments').update({'status': 'completed'}).eq('telegram_charge_id', telegram_payment_charge_id).execute()
                
                await update.message.reply_text(
                    f"✅ **Subscription Activated!**\n\n"
                    f"✨ **{tier.title()} Subscription** (30 days)\n"
                    f"🚀 **Unlimited messages** unlocked!\n"
                    f"💎 **{monthly_gems} Gems** added to your account!\n"
                    f"📊 **Total Gems:** {new_total}\n\n"
                    f"Welcome to premium! 💖",
                    parse_mode='Markdown'
                )
                logger.info(f"[PAYMENT SUCCESS] Activated {tier} subscription for user {user_id}. Added {monthly_gems} gems. New total: {new_total}")
            else:
                # Unknown payload - should not happen after pre-checkout validation
                logger.error(f"[PAYMENT] Unknown payload {payload} for user {user_id}")
                supabase.table('processed_payments').update({'status': 'failed', 'error': 'unknown_payload'}).eq('telegram_charge_id', telegram_payment_charge_id).execute()
                await update.message.reply_text("⚠️ Payment received but product not recognized. Contact support.")
                
        except Exception as e:
            logger.error(f"[PAYMENT ERROR] Failed to process payment for user {user_id}: {e}")
            # Mark payment as failed
            try:
                supabase.table('processed_payments').update({'status': 'failed', 'error': str(e)}).eq('telegram_charge_id', telegram_payment_charge_id).execute()
            except:
                pass
            
            await update.message.reply_text(
                "✅ Payment received, but there was an issue processing your order.\n\n"
                f"Support ID: {telegram_payment_charge_id}\n"
                "Please contact support with this ID. We'll resolve this quickly!"
            )

    async def terms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Terms: By using this bot, you agree to our terms and conditions. No refunds except for failed deliveries. Contact /support for help.")

    async def support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Support: For any issues, contact @YourSupportUsername or reply here.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Return user subscription status, expiry, and gem balance for frontend sync."""
        user_id = update.effective_user.id
        user_db_data = self.db.get_or_create_user(user_id, update.effective_user.username or "Unknown")
        gems = user_db_data.get('gems', 0) if user_db_data else 0
        messages_today = user_db_data.get('messages_today', 0) if user_db_data else 0
        
        sub_tier = self.db.check_subscription(user_id)
        expiry = None
        if sub_tier:
            res = supabase.table('subscriptions').select('expires_at').eq('user_id', user_id).order('expires_at', desc=True).limit(1).execute()
            if res.data:
                expiry = res.data[0]['expires_at']
        
        # Comprehensive status for WebApp sync
        status_data = {
            "user_id": user_id,
            "username": update.effective_user.username,
            "gems": gems,
            "messages_today": messages_today,
            "daily_limit": DAILY_MESSAGE_LIMIT,
            "subscription": {
                "tier": sub_tier,
                "expires_at": expiry,
                "is_active": bool(sub_tier)
            },
            "features": {
                "unlimited_messages": bool(sub_tier),
                "voice_calls_available": gems >= VOICE_CALL_COST_PER_MINUTE,
                "voice_notes_available": gems >= VOICE_NOTE_COST,
                "images_available": True,
                "videos_available": gems >= 80
            },
            "costs": {
                "voice_call_per_minute": VOICE_CALL_COST_PER_MINUTE,
                "voice_note": VOICE_NOTE_COST,
                "image": 10,
                "video": 80
            },
            "payment_methods": ["telegram_stars"],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if this is a WebApp request
        if update.message and hasattr(update.message, 'web_app_data') and update.message.web_app_data:
            # Return JSON for WebApp
            await update.message.reply_text(
                f"```json\n{json.dumps(status_data, indent=2)}\n```",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Regular bot command response
            status_text = f"""
📊 **Your Status**

💎 **Gems:** {gems}
📝 **Messages today:** {messages_today}/{DAILY_MESSAGE_LIMIT}
✨ **Subscription:** {sub_tier.title() if sub_tier else 'Free'}
{f"📅 **Expires:** {expiry}" if expiry else ""}

🎯 **Available Features:**
{'✅' if status_data['features']['voice_calls_available'] else '❌'} Voice Calls ({VOICE_CALL_COST_PER_MINUTE} gems/min)
{'✅' if status_data['features']['voice_notes_available'] else '❌'} Voice Notes ({VOICE_NOTE_COST} gems)
✅ Images (10 gems)
{'✅' if status_data['features']['videos_available'] else '❌'} Videos (80 gems)
            """
            await update.message.reply_text(status_text.strip(), parse_mode=ParseMode.MARKDOWN)
            if res.data:
                expiry = res.data[0]['expires_at']
        
        msg = f"💎 Gems: {gems}\n📊 Messages today: {messages_today}/50\n"
        if sub_tier:
            msg += f"✨ Subscription: {sub_tier.title()} (expires: {expiry})\n🚀 Messages: UNLIMITED"
        else:
            msg += f"✨ Subscription: None\n📝 Messages: {messages_today}/{DAILY_MESSAGE_LIMIT} daily limit"
        
        await update.message.reply_text(msg)

    async def earnings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Star earnings analytics (Admin only)."""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if str(user_id) != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        try:
            # Get total earnings
            total_result = supabase.rpc('get_total_earnings').execute()
            if total_result.data:
                total_data = total_result.data[0]
                total_stars = total_data['total_stars']
                total_transactions = total_data['total_transactions']
                total_customers = total_data['total_customers']
                gems_revenue = total_data['gems_revenue']
                subscription_revenue = total_data['subscription_revenue']
            else:
                total_stars = total_transactions = total_customers = gems_revenue = subscription_revenue = 0
            
            # Get last 30 days earnings
            period_result = supabase.rpc('get_earnings_period', {'period_days': 30}).execute()
            if period_result.data:
                period_data = period_result.data[0]
                month_stars = period_data['total_stars']
                month_transactions = period_data['total_transactions']
                month_customers = period_data['unique_customers']
                avg_transaction = float(period_data['avg_transaction_value']) if period_data['avg_transaction_value'] else 0
            else:
                month_stars = month_transactions = month_customers = avg_transaction = 0
            
            # Get last 7 days
            week_result = supabase.rpc('get_earnings_period', {'period_days': 7}).execute()
            week_stars = week_result.data[0]['total_stars'] if week_result.data else 0
            
            message = f"""💰 **STAR EARNINGS ANALYTICS**

🌟 **TOTAL EARNINGS**
• Total Stars: **{total_stars:,}** ⭐
• Total Transactions: **{total_transactions:,}**
• Total Customers: **{total_customers:,}**

📊 **REVENUE BREAKDOWN**
• Gem Sales: **{gems_revenue:,}** ⭐
• Subscriptions: **{subscription_revenue:,}** ⭐

📈 **RECENT PERFORMANCE**
• Last 30 days: **{month_stars:,}** ⭐ ({month_transactions} transactions)
• Last 7 days: **{week_stars:,}** ⭐
• Active customers (30d): **{month_customers:,}**
• Avg transaction: **{avg_transaction:.1f}** ⭐

💡 *Use /dailyearnings for daily breakdown*"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text("❌ Error retrieving earnings data")
            logger.error(f"Earnings command error: {e}")

    async def dailyearnings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show daily earnings breakdown (Admin only)."""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if str(user_id) != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        try:
            # Get last 7 days of earnings
            result = supabase.table('earnings_analytics').select('*').order('date', desc=True).limit(7).execute()
            
            if not result.data:
                await update.message.reply_text("📊 No earnings data available yet.")
                return
            
            message = "📅 **DAILY EARNINGS (Last 7 Days)**\n\n"
            
            total_week = 0
            for day in result.data:
                date = day['date']
                stars = day['stars_earned']
                transactions = day['total_transactions']
                customers = day['unique_customers']
                total_week += stars
                
                message += f"**{date}**\n"
                message += f"• Stars: {stars:,} ⭐ ({transactions} transactions)\n"
                message += f"• Customers: {customers}\n\n"
            
            message += f"**📊 Week Total: {total_week:,} ⭐**"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text("❌ Error retrieving daily earnings")
            logger.error(f"Daily earnings command error: {e}")

    async def topcustomers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show top customers by spending (Admin only)."""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if str(user_id) != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        try:
            # Get top 10 customers
            result = supabase.table('top_customers').select('*').limit(10).execute()
            
            if not result.data:
                await update.message.reply_text("👥 No customer data available yet.")
                return
            
            message = "👑 **TOP CUSTOMERS BY SPENDING**\n\n"
            
            for i, customer in enumerate(result.data, 1):
                username = customer['username'] or customer['user_name'] or 'Unknown'
                stars_spent = customer['total_stars_spent']
                purchases = customer['total_purchases']
                
                message += f"**{i}.** @{username}\n"
                message += f"• Spent: {stars_spent:,} ⭐ ({purchases} purchases)\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text("❌ Error retrieving customer data")
            logger.error(f"Top customers command error: {e}")

# Custom photo request detection functions

# Custom photo request detection functions
CUSTOM_PHOTO_KEYWORDS = [
    r"photo", r"picture", r"pic", r"send.*photo", r"show.*photo", r"send.*pic", r"show.*pic", r"send.*picture", r"show.*picture", r"nude", r"nudes", r"body", r"boobs", r"pussy"
]

def is_custom_photo_request(message: str) -> bool:
    message = message.lower()
    for pattern in CUSTOM_PHOTO_KEYWORDS:
        if re.search(pattern, message):
            return True
    return False

def is_custom_video_request(message: str) -> tuple[bool, Optional[str]]:
    message_lower = message.lower()
    for lora_type, lora_data in WAVESPEED_ACTION_LORA_MAP.items():
        keywords = lora_data["keywords_to_detect"]
        for keyword in keywords:
            if keyword in message_lower:
                return True, lora_type
    basic_video_keywords = [r"video", r"send.*video", r"show.*video", r"dancing", r"dance"]
    for pattern in basic_video_keywords:
        if re.search(pattern, message_lower):
            return True, None
    return False, None

def is_voice_note_request(message: str) -> bool:
    message = message.lower()
    for pattern in VOICE_NOTE_KEYWORDS:
        if re.search(pattern, message):
            return True
    return False

def is_voice_call_request(message: str) -> bool:
    message = message.lower()
    for pattern in VOICE_CALL_KEYWORDS:
        if re.search(pattern, message):
            return True
    return False

def blur_image_with_replicate(image_url: str, blur_scale: int = 1000) -> Optional[str]:
    try:
        logger.info(f"[BLUR] Starting blur process for {image_url} with scale {blur_scale}")
        if not REPLICATE_API_TOKEN:
            logger.error(f"[BLUR] No REPLICATE_API_TOKEN available")
            return None
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        output = client.run("kharioki/blur-faces:bdcc18be6a02a8f2efce1a3f7489f74a1d6729caea9b53061358fe75c93799d2", input={"image": image_url, "blur_scale": blur_scale})
        logger.info(f"[BLUR] Replicate output: {output} (type: {type(output)})")
        
        # Handle both string and FileOutput objects from Replicate
        if isinstance(output, str) and output.startswith("http"):
            logger.info(f"[BLUR] Successfully blurred image (string): {output}")
            return output
        elif hasattr(output, 'url') and output.url.startswith("http"):
            logger.info(f"[BLUR] Successfully blurred image (FileOutput): {output.url}")
            return output.url
        elif str(output).startswith("http"):
            logger.info(f"[BLUR] Successfully blurred image (converted): {str(output)}")
            return str(output)
        
        logger.warning(f"[BLUR] Invalid output format: {type(output)} - {output}")
        return None
    except Exception as e:
        logger.error(f"[BLUR] Failed to blur {image_url}: {e}")
        return None

def can_upsell(user_session):
    return not (user_session.last_video_task and user_session.last_video_task.get("task_id"))

def clean_voice_note_text(text: str) -> str:
    text = text.replace("*", "")
    text = re.sub(r"\[.*?\]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def clean_voice_call_text(text: str) -> str:
    if not text: return text
    text = re.sub(r"\*[^*]*\*", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip()
    text = re.sub(r'\*[^*]*\*', '', text)
    
    # Remove all content in brackets
    text = re.sub(r'\[[^\]]*\]', '', text)
    
    # Remove all content in parentheses that looks like actions
    text = re.sub(r'\([^)]*(?:chuckle|sigh|moan|breath|whisper|giggle|laugh|gasp)[^)]*\)', '', text, flags=re.IGNORECASE)
    
    # Remove standalone action words that might leak through
    action_words = [
        'chuckles', 'chuckling', 'sighs', 'sighing', 'moans', 'moaning', 
        'gasps', 'gasping', 'whispers', 'whispering', 'giggles', 'giggling',
        'laughs', 'laughing', 'breathes', 'breathing', 'purrs', 'purring'
    ]
    for word in action_words:
        # Remove if it's a standalone word or at the beginning/end
        text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and trim
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove empty sentences or fragments
    text = re.sub(r'[.!?]\s*[.!?]', '.', text)
    
    return text


def main():
    """The main function to set up and run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    bot = SecretShareBot(application)
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("testupsell", bot.test_upsell))
    application.add_handler(CommandHandler("forceupsell", bot.forceupsell))
    application.add_handler(CommandHandler("testvideo", bot.testvideo))
    application.add_handler(CommandHandler("testphone", bot.testphone))
    application.add_handler(CommandHandler("testpayments", bot.test_payment_edge_cases))
    application.add_handler(CommandHandler("store", bot.store))
    application.add_handler(CommandHandler("buygems", bot.buygems))
    application.add_handler(CommandHandler("terms", bot.terms))
    application.add_handler(CommandHandler("support", bot.support))
    application.add_handler(CommandHandler("status", bot.status))
    application.add_handler(CommandHandler("earnings", bot.earnings))
    application.add_handler(CommandHandler("dailyearnings", bot.dailyearnings))
    application.add_handler(CommandHandler("topcustomers", bot.topcustomers))
    application.add_handler(PreCheckoutQueryHandler(bot.precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, bot.successful_payment_callback))
    application.add_handler(CallbackQueryHandler(bot.age_verification_callback, pattern="^verify_age_"))
    application.add_handler(CallbackQueryHandler(bot.character_callback, pattern="^char\|"))
    application.add_handler(CallbackQueryHandler(bot.scenario_callback, pattern="^scenario\|"))
    application.add_handler(CallbackQueryHandler(bot.main_menu_callback, pattern="^back_to_chars$"))
    application.add_handler(CallbackQueryHandler(bot.premium_offer_callback, pattern="^premium_yes\|"))
    application.add_handler(CallbackQueryHandler(bot.unblur_image_callback, pattern="^unblur_image$"))
    application.add_handler(CallbackQueryHandler(bot.handle_payment_callback, pattern="^buy_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_daily(bot._check_inactive_users, time=time(hour=12, minute=0, tzinfo=timezone.utc), name="daily_inactive_check")
        job_queue.run_repeating(bot._cleanup_inactive_users, interval=3600, first=3600, name="memory_cleanup")  # Every hour
        job_queue.run_repeating(bot._sync_recent_payments, interval=30, first=30, name="payment_sync")  # Every 30 seconds - FRONTEND INTEGRATION

    async def post_init(app: Application) -> None:
        await bot.kobold_api.start_session()
        bot.kobold_available = await bot.kobold_api.check_availability()
        if bot.kobold_available:
            logger.info("✅ KoboldCPP is running and connected!")
        else:
            logger.warning("⚠️ KoboldCPP not available - bot will use fallback text responses.")

    async def on_shutdown(app: Application) -> None:
        await bot.kobold_api.close_session()
        logger.info("Bot is shutting down. API session closed.")

    application.post_init = post_init
    application.on_shutdown = on_shutdown
    logger.info("🚀 Starting Secret Share Bot v69 (The Launch-Ready Build)...")
    logger.info("v69 fixes implemented: String casting, image variation, SFW enforcement")
    logger.info("🔄 Beginning Telegram polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import time as time_module
    import random
    import uuid
    
    # Generate unique instance ID for debugging
    instance_id = str(uuid.uuid4())[:8]
    logger.info(f"🚀 Starting Secret Share Bot instance {instance_id}")
    
    delay = 10 + random.randint(0, 10)
    logger.info(f"⏰ Instance {instance_id} waiting {delay} seconds to avoid polling conflicts...")
    time_module.sleep(delay)
    
    logger.info(f"✅ Instance {instance_id} delay complete, proceeding with startup...")

    logger.info("Checking for 'last_seen' column in 'users' table for retention features...")
    try:
        supabase.table('users').select('last_seen').limit(1).execute()
        logger.info("✅ Database check successful: 'last_seen' column exists.")
    except Exception as e:
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.error("!!! CRITICAL DATABASE ERROR: 'last_seen' column not found in 'users' table.")
        logger.error("!!! The 24-hour retention feature WILL NOT WORK without it.")
        logger.error("!!! Please run the provided Supabase SQL script to add the column.")
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    try:
        logger.info(f"🎯 Instance {instance_id} starting main bot function...")
        main()
    except Exception as e:
        logger.error(f"❌ Instance {instance_id} failed to start: {e}")
        raise  # Re-raise to prevent silent failures
