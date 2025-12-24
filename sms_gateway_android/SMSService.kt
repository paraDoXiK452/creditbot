package com.creditbot.smsgateway

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * 🔄 Фоновый сервис для приёма команд из Telegram
 * 
 * Функции:
 * - Long polling Telegram API
 * - Обработка команд на отправку SMS
 * - Отправка отчётов в Telegram
 * - Работа в фоне с уведомлением
 */
class SMSService : Service() {
    
    private var botToken: String? = null
    private var chatId: String? = null
    private var deviceName: String = "Android Device"
    
    private val scope = CoroutineScope(Dispatchers.IO + Job())
    private var isRunning = false
    private var lastUpdateId = 0L
    
    private val CHANNEL_ID = "sms_gateway_channel"
    private val NOTIFICATION_ID = 1
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        botToken = intent?.getStringExtra("bot_token")
        chatId = intent?.getStringExtra("chat_id")
        deviceName = intent?.getStringExtra("device_name") ?: "Android Device"
        
        if (botToken != null && chatId != null) {
            startForeground(NOTIFICATION_ID, createNotification("Запуск службы..."))
            startPolling()
        } else {
            stopSelf()
        }
        
        return START_STICKY
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "SMS Gateway Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Служба отправки SMS"
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(status: String): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("SMS Gateway")
            .setContentText(status)
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }
    
    private fun updateNotification(status: String) {
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(NOTIFICATION_ID, createNotification(status))
    }
    
    private fun startPolling() {
        isRunning = true
        logToActivity("🚀 Служба запущена")
        sendTelegramMessage("🟢 <b>Служба SMS запущена</b>\n📱 $deviceName")
        
        scope.launch {
            while (isRunning) {
                try {
                    pollUpdates()
                    delay(2000) // Опрос каждые 2 секунды
                } catch (e: Exception) {
                    logToActivity("❌ Ошибка polling: ${e.message}")
                    delay(5000) // Пауза при ошибке
                }
            }
        }
    }
    
    private suspend fun pollUpdates() {
        try {
            val urlString = "https://api.telegram.org/bot$botToken/getUpdates"
            val url = URL("$urlString?offset=$lastUpdateId&timeout=30")
            val connection = url.openConnection() as HttpURLConnection
            
            connection.requestMethod = "GET"
            connection.connectTimeout = 35000
            connection.readTimeout = 35000
            
            val response = BufferedReader(InputStreamReader(connection.inputStream)).use {
                it.readText()
            }
            
            val json = JSONObject(response)
            if (json.getBoolean("ok")) {
                val updates = json.getJSONArray("result")
                
                for (i in 0 until updates.length()) {
                    val update = updates.getJSONObject(i)
                    val updateId = update.getLong("update_id")
                    
                    if (updateId >= lastUpdateId) {
                        lastUpdateId = updateId + 1
                        
                        if (update.has("message")) {
                            val message = update.getJSONObject("message")
                            val fromChatId = message.getJSONObject("chat").getString("id")
                            
                            // Проверяем что сообщение от нашего чата
                            if (fromChatId == chatId) {
                                val text = message.optString("text", "")
                                processCommand(text)
                            }
                        }
                    }
                }
            }
            
            updateNotification("Работает 🟢 | SMS: ${getSentCount()}")
            
        } catch (e: Exception) {
            logToActivity("❌ Polling error: ${e.message}")
        }
    }
    
    private fun processCommand(command: String) {
        logToActivity("📨 Команда: ${command.take(50)}...")
        
        try {
            // Формат: SMS:PHONE:MESSAGE
            if (command.startsWith("SMS:")) {
                val parts = command.split(":", limit = 3)
                if (parts.size == 3) {
                    val phone = parts[1]
                    val message = parts[2]
                    
                    sendSMS(phone, message)
                } else {
                    logToActivity("⚠️ Неверный формат команды")
                    sendTelegramMessage("❌ Неверный формат команды")
                }
            }
            // Тестовая команда
            else if (command == "/ping") {
                sendTelegramMessage("🏓 Pong! Устройство работает.")
            }
            // Статистика
            else if (command == "/stats") {
                sendTelegramMessage(
                    "📊 <b>Статистика</b>\n\n" +
                    "📱 Устройство: $deviceName\n" +
                    "✅ Отправлено SMS: ${getSentCount()}\n" +
                    "❌ Ошибок: ${getErrorCount()}\n" +
                    "🟢 Статус: Работает"
                )
            }
            
        } catch (e: Exception) {
            logToActivity("❌ Ошибка обработки: ${e.message}")
            sendTelegramMessage("❌ Ошибка: ${e.message}")
        }
    }
    
    private fun sendSMS(phone: String, message: String) {
        scope.launch(Dispatchers.Main) {
            // Получаем MainActivity для отправки SMS
            val activity = getMainActivity()
            
            if (activity != null) {
                val success = activity.sendSMS(phone, message)
                
                withContext(Dispatchers.IO) {
                    if (success) {
                        incrementSentCount()
                        sendTelegramMessage(
                            "✅ <b>SMS отправлено</b>\n\n" +
                            "📱 Номер: $phone\n" +
                            "📝 Сообщение: ${message.take(50)}${if (message.length > 50) "..." else ""}"
                        )
                    } else {
                        incrementErrorCount()
                        sendTelegramMessage(
                            "❌ <b>Ошибка отправки SMS</b>\n\n" +
                            "📱 Номер: $phone"
                        )
                    }
                }
            } else {
                logToActivity("❌ MainActivity недоступна")
            }
        }
    }
    
    private fun sendTelegramMessage(text: String) {
        scope.launch(Dispatchers.IO) {
            try {
                val urlString = "https://api.telegram.org/bot$botToken/sendMessage"
                val url = URL(urlString)
                val connection = url.openConnection() as HttpURLConnection
                
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                
                val jsonBody = JSONObject().apply {
                    put("chat_id", chatId)
                    put("text", text)
                    put("parse_mode", "HTML")
                }
                
                connection.outputStream.write(jsonBody.toString().toByteArray())
                connection.responseCode // Выполняем запрос
                
            } catch (e: Exception) {
                logToActivity("❌ Telegram error: ${e.message}")
            }
        }
    }
    
    private fun logToActivity(message: String) {
        val activity = getMainActivity()
        activity?.addLog(message)
    }
    
    private fun getMainActivity(): MainActivity? {
        return MainActivity.instance
    }
    
    private fun getSentCount(): Int {
        val prefs = getSharedPreferences("sms_gateway_stats", Context.MODE_PRIVATE)
        return prefs.getInt("sent_count", 0)
    }
    
    private fun getErrorCount(): Int {
        val prefs = getSharedPreferences("sms_gateway_stats", Context.MODE_PRIVATE)
        return prefs.getInt("error_count", 0)
    }
    
    private fun incrementSentCount() {
        val prefs = getSharedPreferences("sms_gateway_stats", Context.MODE_PRIVATE)
        val count = prefs.getInt("sent_count", 0)
        prefs.edit().putInt("sent_count", count + 1).apply()
    }
    
    private fun incrementErrorCount() {
        val prefs = getSharedPreferences("sms_gateway_stats", Context.MODE_PRIVATE)
        val count = prefs.getInt("error_count", 0)
        prefs.edit().putInt("error_count", count + 1).apply()
    }
    
    override fun onDestroy() {
        super.onDestroy()
        isRunning = false
        scope.cancel()
        
        sendTelegramMessage("🔴 <b>Служба SMS остановлена</b>\n📱 $deviceName")
        logToActivity("⏹️ Служба остановлена")
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
}

// Добавляем companion object в MainActivity
// Нужно добавить в MainActivity.kt:
/*
companion object {
    var instance: MainActivity? = null
}

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    instance = this
    // ... остальной код
}

override fun onDestroy() {
    super.onDestroy()
    instance = null
    // ... остальной код
}
*/
