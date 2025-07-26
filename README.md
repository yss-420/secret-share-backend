# 🤖 Secret Share Bot - Backend

A sophisticated Telegram bot for AI-powered adult conversations with premium features including:
- 🎭 Multiple AI characters with scenarios
- 🖼️ AI-generated images with LoRA models
- 🎬 Video generation with Wavespeed
- 🗣️ Voice notes and phone calls via ElevenLabs
- 💎 Telegram Stars payment integration
- 🌐 WebApp frontend integration

## 🚀 **Production Ready Features**

✅ **Security Hardened**
- Row Level Security (RLS) policies
- SQL injection protection
- Environment variable security
- Database authentication isolation

✅ **Payment Integration** 
- Telegram Stars payment processing
- Atomic payment transactions
- Frontend-backend payment sync
- Subscription management

✅ **AI Integrations**
- KoboldCPP for text generation
- Replicate for image generation
- Wavespeed for video generation
- ElevenLabs for voice features

✅ **Robust Architecture**
- Supabase database backend
- Real-time payment synchronization
- Session persistence
- Error handling and logging

## 📋 **Quick Deploy**

### **Requirements**
- Python 3.11+
- Supabase account (database)
- RunPod account (hosting)
- Various API keys (see Environment Variables)

### **Deploy to RunPod**
1. **Fork/Clone** this repository
2. **Follow** the detailed [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
3. **Configure** environment variables in RunPod
4. **Deploy** and get webhook URL
5. **Update** Telegram bot webhook

## 🔧 **Environment Variables**

Required environment variables for RunPod deployment:

```bash
# Core Bot
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_telegram_id

# Database
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# AI Services
REPLICATE_API_TOKEN=your_replicate_token
WAVESPEED_API_TOKEN=your_wavespeed_token
ELEVENLABS_API_KEY=your_elevenlabs_key

# Voice Services
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

## 📁 **Project Structure**

```
secret_share_bot/
├── secret_share_bot.py          # Main bot application
├── requirements.txt             # Python dependencies
├── runpod.toml                 # RunPod configuration
├── DEPLOYMENT_GUIDE.md         # Complete deployment guide
├── FRONTEND_INTEGRATION.md     # Frontend integration guide
├── Database/                   # SQL schema files
│   ├── complete_supabase_schema_v7.sql
│   ├── security_fixes_critical.sql
│   └── ...other SQL files
└── Documents/                  # Documentation
    ├── RUNPOD_DEPLOYMENT_CHECKLIST.md
    ├── STAR_EARNINGS_SETUP.md
    └── ...other docs
```

## 🎯 **Key Features**

### **Character System**
- 8 unique AI characters with distinct personalities
- Dynamic scenario selection
- Conversation history persistence
- Character-specific image generation

### **Premium Features**
- AI-generated images (30 gems)
- Video generation (80 gems)  
- Voice notes (30 gems)
- Voice phone calls (50 gems/minute)

### **Payment System**
- Telegram Stars integration
- Real-time payment processing
- Frontend-backend synchronization
- Subscription tiers

### **Admin Dashboard**
- `/earnings` - Revenue analytics
- `/dailyearnings` - Daily breakdown
- `/topcustomers` - Customer insights
- `/status` - System health monitoring

## 🧪 **Testing**

### **Local Testing**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN=your_token
# ... other env vars

# Run bot
python secret_share_bot.py
```

### **Production Testing**
- Test all bot commands (`/start`, character selection, etc.)
- Test payment flows
- Test webhook integrations
- Monitor RunPod logs

## 🛡️ **Security**

This bot implements enterprise-grade security:
- **Database:** RLS policies prevent data leakage
- **Authentication:** Telegram-based user validation
- **Payments:** Atomic transaction processing
- **API Keys:** Secure environment variable management

## 📊 **Monitoring**

### **Logs**
- RunPod function logs for execution monitoring
- Supabase logs for database activity
- Payment transaction logs

### **Metrics**
- User engagement analytics
- Revenue tracking
- Error rate monitoring
- Response time metrics

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 **License**

This project is proprietary. All rights reserved.

## 🆘 **Support**

For deployment issues:
1. Check [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
2. Review RunPod function logs
3. Verify environment variables
4. Test database connectivity

---

**Built with ❤️ for premium Telegram bot experiences** 