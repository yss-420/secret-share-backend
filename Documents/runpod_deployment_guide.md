# 🚀 Secret Share Bot - RunPod Deployment Guide

## Overview
This guide covers deploying your Secret Share Bot on RunPod with full webhook support for real-time voice call and video tracking.

## ✅ What's Now Supported

### **Real-Time Webhooks:**
1. **Wavespeed Video Webhooks** - Instant video delivery when ready
2. **Twilio Call Webhooks** - Real-time call duration tracking
3. **ElevenLabs Call Webhooks** - Call completion events
4. **User Notifications** - Automatic messages when calls/videos complete

### **Database Tracking:**
- Voice call logs with duration
- Call analytics view
- Real-time updates via webhooks

## 🔧 RunPod Setup

### **1. Container Configuration**
```bash
# Base image
python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    python-telegram-bot==20.7 \
    supabase \
    replicate \
    elevenlabs \
    pydub \
    python-dotenv \
    aiohttp \
    requests
```

### **2. Environment Variables**
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_key

# APIs
REPLICATE_API_TOKEN=your_replicate_token
WAVESPEED_API_TOKEN=your_wavespeed_token
ELEVENLABS_API_KEY=your_elevenlabs_key

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Admin
ADMIN_CHAT_ID=your_admin_id
```

### **3. Webhook Configuration**

#### **For Twilio:**
1. Go to Twilio Console → Phone Numbers → Manage → Active numbers
2. Set Status Callback URL: `https://your-runpod-domain.com/api/twilio-webhook`
3. Set HTTP Method: POST

#### **For ElevenLabs:**
1. Go to ElevenLabs Dashboard → Settings → Webhooks
2. Add webhook URL: `https://your-runpod-domain.com/api/elevenlabs-webhook`
3. Select events: `call_ended`, `call_failed`

#### **For Wavespeed:**
- Already configured in your bot code
- Webhook URL: `https://your-runpod-domain.com/api/wavespeed-webhook`

## 📊 Webhook Endpoints

### **Available Endpoints:**
- `POST /api/wavespeed-webhook` - Video completion
- `POST /api/twilio-webhook` - Call status updates
- `POST /api/elevenlabs-webhook` - Call completion events

### **Port Configuration:**
- Bot runs on port 8081 for webhooks
- Ensure RunPod exposes this port

## 🎯 Benefits of 24/7 Deployment

### **1. Real-Time Features:**
- ✅ Instant video delivery via webhooks
- ✅ Real-time call duration tracking
- ✅ User notifications when calls end
- ✅ No polling needed - everything is event-driven

### **2. Better User Experience:**
- Users get immediate notifications
- Accurate call billing with real duration
- No delays in video delivery

### **3. Scalability:**
- Handle multiple concurrent calls
- Process webhooks efficiently
- Maintain call state across restarts

## 🔄 Migration from Polling to Webhooks

### **What Changes:**
1. **Videos**: No more polling - instant delivery via webhooks
2. **Calls**: Real-time duration tracking instead of estimates
3. **Notifications**: Users get immediate feedback

### **What Stays the Same:**
- All existing bot functionality
- Database structure
- User experience flow

## 📈 Monitoring & Analytics

### **Database Views Available:**
```sql
-- Call analytics
SELECT * FROM voice_call_analytics;

-- User call history
SELECT * FROM voice_calls WHERE user_id = ?;

-- Revenue tracking
SELECT SUM(gem_cost) FROM voice_calls WHERE created_at >= ?;
```

### **Log Monitoring:**
- Webhook events logged with `[TWILIO WEBHOOK]`, `[ELEVENLABS WEBHOOK]`
- Call duration updates logged
- User notifications tracked

## 🚀 Deployment Checklist

### **Pre-Deployment:**
- [ ] Update Supabase schema (run the SQL script)
- [ ] Configure Twilio webhooks
- [ ] Configure ElevenLabs webhooks
- [ ] Test webhook endpoints locally

### **Deployment:**
- [ ] Set up RunPod container
- [ ] Configure environment variables
- [ ] Expose port 8081
- [ ] Set up domain/SSL for webhooks
- [ ] Test all webhook endpoints

### **Post-Deployment:**
- [ ] Test voice call with duration tracking
- [ ] Test video delivery via webhooks
- [ ] Monitor logs for webhook events
- [ ] Verify database updates

## 💡 Pro Tips

1. **SSL Required**: Webhooks require HTTPS, so set up SSL on your RunPod domain
2. **Retry Logic**: Webhooks should be idempotent (safe to retry)
3. **Monitoring**: Set up alerts for webhook failures
4. **Backup**: Consider database backups for call logs

## 🎉 Result

With this setup, you'll have:
- **Real-time call tracking** with accurate duration
- **Instant video delivery** when ready
- **User notifications** for call completion
- **Complete audit trail** in database
- **Scalable architecture** for growth

Your bot will be production-ready with enterprise-level webhook handling! 🚀 