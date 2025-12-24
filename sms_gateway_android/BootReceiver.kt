package com.creditbot.smsgateway

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

/**
 * 🔄 Автозапуск службы SMS при загрузке устройства
 * 
 * Запускает SMSService автоматически после перезагрузки телефона,
 * если ранее служба была активна
 */
class BootReceiver : BroadcastReceiver() {
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || 
            intent.action == "android.intent.action.QUICKBOOT_POWERON") {
            
            Log.d(TAG, "Boot completed, checking SMS service configuration")
            
            // Проверяем есть ли сохранённая конфигурация
            val prefs = context.getSharedPreferences("sms_gateway", Context.MODE_PRIVATE)
            val botToken = prefs.getString("bot_token", null)
            val chatId = prefs.getString("chat_id", null)
            val deviceName = prefs.getString("device_name", "Android Device")
            val autoStart = prefs.getBoolean("auto_start_on_boot", true)
            
            if (botToken != null && chatId != null && autoStart) {
                // Запускаем службу
                val serviceIntent = Intent(context, SMSService::class.java)
                serviceIntent.putExtra("bot_token", botToken)
                serviceIntent.putExtra("chat_id", chatId)
                serviceIntent.putExtra("device_name", deviceName)
                
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        context.startForegroundService(serviceIntent)
                    } else {
                        context.startService(serviceIntent)
                    }
                    
                    Log.d(TAG, "SMS service started after boot")
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to start SMS service after boot: ${e.message}")
                }
            } else {
                Log.d(TAG, "SMS service not configured or auto-start disabled")
            }
        }
    }
    
    companion object {
        private const val TAG = "BootReceiver"
    }
}
