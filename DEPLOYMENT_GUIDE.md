# 🚀 Secret Share Bot - Production Deployment Guide

## ✅ **Pre-Deployment Checklist**
- [x] Security fixes applied
- [x] Frontend integration code added
- [x] Database properly configured
- [x] All environment variables ready

---

## 📁 **Phase 1: GitHub Repository Setup**

### **Step 1: Create GitHub Repository**
1. **Go to GitHub.com** and create new repository
2. **Name:** `secret-share-bot-backend` 
3. **Visibility:** Private (recommended for production bot)
4. **Don't** initialize with README (we'll push existing code)

### **Step 2: Prepare Local Repository**
```bash
# Navigate to your project directory
cd /Users/manav/Desktop/secret_share_bot

# Initialize git (if not already done)
git init

# Add all files to git
git add .

# Create initial commit
git commit -m "Initial commit: Production-ready Secret Share Bot with security fixes and frontend integration"

# Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/yss-420/secret-share-bot-backend.git

# Push to GitHub
git push -u origin main
```

### **Step 3: Verify Upload**
- Check that `secret_share_bot.py` is uploaded ✅
- Check that `requirements.txt` is uploaded ✅  
- Check that `.env` is **NOT** uploaded (should be in .gitignore) ✅
- Check that Database/ folder with SQL files is uploaded ✅

---

## ☁️ **Phase 2: RunPod Deployment**

### **Step 1: RunPod Account Setup**
1. **Go to:** https://runpod.io
2. **Sign up** or login
3. **Add billing** (you'll need $5-10 to start)
4. **Navigate to:** Serverless → Functions

### **Step 2: Create New Function**
1. **Click:** "New Function"
2. **Name:** `secret-share-bot`
3. **Select Runtime:** `Python 3.11`
4. **Select GPU:** None (CPU is enough for a bot)
5. **Set Memory:** 2GB (sufficient for bot operations)

### **Step 3: Configure GitHub Integration**
1. **Source:** GitHub Repository
2. **Repository:** `YOUR_USERNAME/secret-share-bot-backend`
3. **Branch:** `main`
4. **Python Version:** `3.11`
5. **Handler:** `secret_share_bot.main`

### **Step 4: Add Environment Variables**
In RunPod Environment Variables section, add:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
REPLICATE_API_TOKEN=your_replicate_token
WAVESPEED_API_TOKEN=your_wavespeed_token
ELEVENLABS_API_KEY=your_elevenlabs_key
ADMIN_CHAT_ID=your_telegram_admin_chat_id
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

### **Step 5: Deploy Function**
1. **Click:** "Deploy"
2. **Wait:** for deployment to complete (5-10 minutes)
3. **Copy:** the webhook URL (looks like: `https://api.runpod.ai/v2/YOUR_FUNCTION_ID/run`)

---

## 🔗 **Phase 3: Webhook URL Configuration**

### **Step 1: Update Telegram Bot Webhook**
```bash
# Replace YOUR_BOT_TOKEN and YOUR_RUNPOD_URL
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "YOUR_RUNPOD_URL/webhook"}'
```

### **Step 2: Update Frontend WebApp URL** 
In your frontend code, update:
```javascript
// Update API endpoint to point to RunPod
const API_BASE_URL = 'YOUR_RUNPOD_URL'
```

### **Step 3: Update External Webhooks**
Update webhook URLs in:
- **Wavespeed Dashboard:** Video generation callbacks
- **ElevenLabs Dashboard:** Voice call webhooks
- **Twilio Dashboard:** Phone number webhooks

---

## 🧪 **Phase 4: Testing & Verification**

### **Step 1: Test Bot Functionality**
- [ ] Send `/start` command
- [ ] Test character selection
- [ ] Test image generation
- [ ] Test payment flow (if applicable)
- [ ] Test voice features

### **Step 2: Test Webhook Integration**
- [ ] Test video generation webhooks
- [ ] Test voice call callbacks
- [ ] Test payment processing

### **Step 3: Monitor Logs**
- **RunPod Console:** Check function logs for errors
- **Telegram:** Test all bot commands
- **Supabase:** Monitor database activity

---

## 📊 **Phase 5: Production Monitoring**

### **Step 1: Set Up Monitoring**
- **RunPod:** Monitor function execution time
- **Supabase:** Monitor database performance
- **Telegram:** Test bot responsiveness

### **Step 2: Scale if Needed**
- **If slow:** Increase RunPod memory
- **If errors:** Check environment variables
- **If downtime:** Consider RunPod autoscaling

---

## 🛡️ **Security Checklist**

- [ ] Environment variables properly set in RunPod
- [ ] No API keys in GitHub repository
- [ ] HTTPS webhooks configured
- [ ] Database RLS policies active
- [ ] Bot token secured

---

## 🔧 **Troubleshooting**

### **Common Issues:**
1. **Bot not responding:** Check RunPod logs for errors
2. **Database errors:** Verify Supabase credentials
3. **Webhook failures:** Ensure URLs are publicly accessible
4. **Payment issues:** Check Telegram Stars configuration

### **Debug Commands:**
```bash
# Test webhook manually
curl -X POST "YOUR_RUNPOD_URL/webhook" \
     -H "Content-Type: application/json" \
     -d '{"test": "message"}'

# Check Telegram webhook status
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

---

## ✅ **Deployment Complete!**

Once all steps are complete, your bot will be:
- **Running** on RunPod serverless infrastructure
- **Secured** with proper environment variables
- **Integrated** with frontend WebApp
- **Monitoring** ready for production traffic

🎉 **Your Secret Share Bot is now live in production!** 