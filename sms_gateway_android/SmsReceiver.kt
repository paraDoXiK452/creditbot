package com.creditbot.smsgateway

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log

/**
 * SMS Receiver для регистрации приложения как SMS-приложения по умолчанию
 * Это необходимо для Infinix, Xiaomi и других производителей с ограничениями
 */
class SmsReceiver : BroadcastReceiver() {
    
    override fun onReceive(context: Context?, intent: Intent?) {
        if (intent == null || context == null) return
        
        when (intent.action) {
            Telephony.Sms.Intents.SMS_DELIVER_ACTION -> {
                // Получение SMS (для регистрации как SMS-приложение)
                Log.d(TAG, "SMS получено")
            }
            
            Telephony.Sms.Intents.SMS_RECEIVED_ACTION -> {
                // Получение SMS (старый API)
                Log.d(TAG, "SMS получено (legacy)")
            }
        }
    }
    
    companion object {
        private const val TAG = "SmsReceiver"
    }
}
