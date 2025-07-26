# 🔗 Frontend Integration Guide - Secret Share Bot

## ✅ Backend Changes: **COMPLETE**
Your backend now has:
- **Payment sync polling** (every 30 seconds)
- **User data refresh** (when users return from WebApp)
- **Real-time gem updates** (for active users)

---

## 📱 Frontend Changes Needed

### **1. After Payment Success - Add This Code:**

```javascript
// After payment is successfully processed in your frontend
async function onPaymentSuccess(paymentData) {
  try {
    // Insert payment record into Supabase
    const { data, error } = await supabase
      .from('processed_payments')
      .insert({
        telegram_charge_id: paymentData.paymentId || `webapp_${Date.now()}`,
        user_id: window.Telegram.WebApp.initDataUnsafe.user.id,
        payload: paymentData.package, // e.g., 'gems_100'
        amount: paymentData.stars, // Amount in Telegram Stars
        gems_to_add: paymentData.gems, // Gems to add to user account
        status: 'completed',
        processed_at: new Date().toISOString()
      })

    if (error) {
      console.error('Payment record error:', error)
      return
    }

    console.log('✅ Payment recorded successfully')
    
    // Show success message
    window.Telegram.WebApp.showAlert('💎 Payment successful! Your gems will be available shortly.', () => {
      // Close WebApp to return user to bot
      window.Telegram.WebApp.close()
    })

  } catch (error) {
    console.error('Payment processing error:', error)
    window.Telegram.WebApp.showAlert('❌ Payment processing failed. Please contact support.')
  }
}
```

### **2. Update Your Payment Flow:**

```javascript
// In your payment component/function, replace your success handler with:

// OLD: Just update frontend display
// NEW: Record payment + sync with backend
await onPaymentSuccess({
  paymentId: 'unique_payment_id',
  package: 'gems_100', // Package identifier  
  stars: 100, // Amount paid in stars
  gems: 95 // Gems to add to user account
})
```

### **3. Optional - Real-time Gem Display:**

```javascript
// Optional: Listen for real-time gem updates
const subscription = supabase
  .channel('user_gems')
  .on('postgres_changes', 
    { 
      event: 'UPDATE', 
      schema: 'public', 
      table: 'users',
      filter: `telegram_id=eq.${window.Telegram.WebApp.initDataUnsafe.user.id}`
    },
    (payload) => {
      console.log('💎 Gems updated:', payload.new.gems)
      // Update your UI with new gem count
      updateGemDisplay(payload.new.gems)
    }
  )
  .subscribe()
```

---

## 🔄 How It Works Now:

```
1. User clicks "💎 Store" in Telegram Bot
         ↓
2. Opens your Frontend WebApp
         ↓
3. User makes payment in Frontend
         ↓
4. Frontend calls onPaymentSuccess() 
         ↓
5. Payment inserted into Supabase ✅
         ↓
6. Backend polls every 30 seconds ✅
         ↓
7. Backend updates active user gems ✅
         ↓
8. User returns to bot with updated gems! 🎉
```

---

## 🧪 Testing:

1. **Start your backend** with the new polling code
2. **Add the payment success code** to your frontend
3. **Test payment flow**: 
   - Make payment in WebApp
   - Return to bot
   - Check if gems are updated
4. **Check logs** for `[PAYMENT_SYNC]` messages

---

## 📋 Required Frontend Files:

You only need to modify **1 file** in your frontend:
- **Payment success handler** (wherever you process payments)

**That's it!** The backend handles all the sync magic automatically. 🚀 