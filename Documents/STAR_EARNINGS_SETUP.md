# 💰 STAR EARNINGS TRACKING SYSTEM - SETUP GUIDE

## 📊 What's Added

Your bot now has a comprehensive Star earnings tracking and analytics system with admin dashboard commands!

## 🔧 Setup Steps

### Step 1: Add Database Schema
Run this SQL in your Supabase SQL Editor:

```sql
-- Copy and paste the entire contents of star_earnings_schema.sql
-- This creates the earnings table, indexes, views, and analytics functions
```

### Step 2: Test the System
After deploying, test with:

1. **Make a test purchase** (buy gems with Stars)
2. **Check tracking** with `/earnings` command (admin only)
3. **Verify data** in Supabase dashboard

## 📱 Admin Commands

### `/earnings` - Main Dashboard
Shows comprehensive earnings overview:
- Total Stars earned all-time
- Revenue breakdown (gems vs subscriptions)
- Recent performance (7-day, 30-day)
- Customer metrics

### `/dailyearnings` - Daily Breakdown
Shows last 7 days with:
- Daily Star earnings
- Transaction counts
- Unique customers per day

### `/topcustomers` - Customer Analytics
Shows top 10 customers by:
- Total Stars spent
- Number of purchases
- Last purchase date

## 🎯 Features

### Automatic Tracking
- Every successful payment is automatically logged
- Tracks payment type (gems/subscription)
- Records Stars amount and gems granted
- Includes user ID and timestamp

### Analytics Views
- **earnings_analytics**: Daily earnings breakdown
- **monthly_earnings**: Monthly summaries
- **top_customers**: Customer spending rankings

### Security
- All analytics commands are admin-only
- Checks ADMIN_CHAT_ID environment variable
- Non-admins get "access denied" message

## 📈 Sample Admin Dashboard Output

```
💰 STAR EARNINGS ANALYTICS

🌟 TOTAL EARNINGS
• Total Stars: 12,450 ⭐
• Total Transactions: 147
• Total Customers: 89

📊 REVENUE BREAKDOWN
• Gem Sales: 8,200 ⭐
• Subscriptions: 4,250 ⭐

📈 RECENT PERFORMANCE
• Last 30 days: 3,420 ⭐ (42 transactions)
• Last 7 days: 890 ⭐
• Active customers (30d): 28
• Avg transaction: 84.7 ⭐
```

## 🔍 Database Queries

You can also run custom queries in Supabase:

```sql
-- Total earnings this month
SELECT SUM(stars_amount) FROM star_earnings 
WHERE created_at >= date_trunc('month', now());

-- Top earning days
SELECT DATE(created_at), SUM(stars_amount) as daily_stars
FROM star_earnings 
GROUP BY DATE(created_at) 
ORDER BY daily_stars DESC 
LIMIT 10;

-- Revenue by payment type
SELECT payment_type, SUM(stars_amount), COUNT(*)
FROM star_earnings 
GROUP BY payment_type;
```

## ✅ Benefits

1. **Real-time tracking** - Every payment automatically logged
2. **Business intelligence** - Daily/monthly revenue analytics
3. **Customer insights** - Top spenders and purchase patterns
4. **Admin dashboard** - Easy access via Telegram commands
5. **Data export** - Full access via Supabase for external tools

## 🚀 Ready to Use!

Your Star earnings tracking system is now:
- ✅ Fully implemented in code
- ✅ Database schema ready to deploy
- ✅ Admin commands working
- ✅ Automatic payment logging
- ✅ Comprehensive analytics

Just run the SQL schema and you'll have full revenue tracking! 💰 