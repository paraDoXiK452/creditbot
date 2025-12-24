package com.creditbot.smsgateway

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Telephony
import android.telephony.SmsManager
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.creditbot.smsgateway.databinding.ActivityMainBinding
import com.google.zxing.integration.android.IntentIntegrator
import kotlinx.coroutines.*
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.*

/**
 * 📱 SMS Gateway для CreditBot
 * 
 * Основные функции:
 * - QR код авторизация через Telegram Bot
 * - Приём команд на отправку SMS через Telegram
 * - Фоновая работа и автозапуск
 * - Логирование всех операций
 */
class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private val scope = CoroutineScope(Dispatchers.Main + Job())
    
    // Настройки из QR кода
    private var botToken: String? = null
    private var chatId: String? = null
    private var deviceName: String = "Android Device"
    
    // Выбор SIM-карты
    private var selectedSimSlot: Int = -1  // -1 = по умолчанию, 0 = SIM1, 1 = SIM2
    
    // Статистика
    private var sentCount = 0
    private var errorCount = 0
    
    // Запрос разрешений
    private val requestPermissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            addLog("✅ Разрешения получены")
            checkConfiguration()
            checkSimCards()
            checkDefaultSmsApp()
        } else {
            addLog("❌ Необходимы разрешения для работы")
            Toast.makeText(this, "Необходимы разрешения SMS, CAMERA и READ_PHONE_STATE", Toast.LENGTH_LONG).show()
        }
    }
    
    // Запрос роли SMS-приложения по умолчанию
    private val requestSmsRoleLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (Telephony.Sms.getDefaultSmsPackage(this) == packageName) {
            addLog("✅ Установлено как SMS-приложение по умолчанию!")
            Toast.makeText(this, "Теперь SMS будут отправляться без проблем!", Toast.LENGTH_LONG).show()
        } else {
            addLog("⚠️ Не установлено как приложение по умолчанию")
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        instance = this
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupUI()
        loadConfiguration()
        requestPermissions()
    }
    
    private fun setupUI() {
        binding.btnScanQr.setOnClickListener {
            scanQRCode()
        }
        
        // Выбор SIM-карты
        binding.radioGroupSim.setOnCheckedChangeListener { _, checkedId ->
            selectedSimSlot = when (checkedId) {
                binding.radioSim1.id -> 0  // SIM 1
                binding.radioSim2.id -> 1  // SIM 2
                else -> -1  // По умолчанию
            }
            saveSimSelection()
            addLog("📱 Выбрана SIM: ${if (selectedSimSlot == -1) "по умолчанию" else "SIM ${selectedSimSlot + 1}"}")
        }
        
        binding.btnStartService.setOnClickListener {
            if (botToken != null && chatId != null) {
                startSMSService()
            } else {
                Toast.makeText(this, "Сначала отсканируйте QR код", Toast.LENGTH_SHORT).show()
            }
        }
        
        binding.btnStopService.setOnClickListener {
            stopSMSService()
        }
        
        binding.btnClearLogs.setOnClickListener {
            binding.tvLogs.text = ""
        }
        
        binding.btnTestSms.setOnClickListener {
            testSMS()
        }
        
        binding.btnSetDefaultSms.setOnClickListener {
            requestDefaultSmsApp()
        }
    }
    
    private fun requestPermissions() {
        val permissions = arrayOf(
            Manifest.permission.SEND_SMS,
            Manifest.permission.READ_SMS,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.CAMERA,
            Manifest.permission.INTERNET,
            Manifest.permission.FOREGROUND_SERVICE
        )
        
        val needRequest = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (needRequest.isNotEmpty()) {
            requestPermissionsLauncher.launch(needRequest.toTypedArray())
        } else {
            addLog("✅ Все разрешения получены")
            checkConfiguration()
            checkSimCards()
            checkDefaultSmsApp()
        }
    }
    
    private fun checkDefaultSmsApp() {
        val defaultSmsPackage = Telephony.Sms.getDefaultSmsPackage(this)
        if (defaultSmsPackage != packageName) {
            addLog("⚠️ Не установлено как SMS-приложение по умолчанию")
            addLog("💡 Для Infinix/Xiaomi/Oppo ОБЯЗАТЕЛЬНО установить!")
            addLog("   Нажмите кнопку '🔧 Установить по умолчанию'")
        } else {
            addLog("✅ Установлено как SMS-приложение по умолчанию")
        }
    }
    
    private fun requestDefaultSmsApp() {
        if (Telephony.Sms.getDefaultSmsPackage(this) == packageName) {
            Toast.makeText(this, "Уже установлено как приложение по умолчанию", Toast.LENGTH_SHORT).show()
            return
        }
        
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // Android 10+: используем RoleManager
                val roleManager = getSystemService(Context.ROLE_SERVICE) as RoleManager
                if (roleManager.isRoleAvailable(RoleManager.ROLE_SMS)) {
                    if (!roleManager.isRoleHeld(RoleManager.ROLE_SMS)) {
                        val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS)
                        requestSmsRoleLauncher.launch(intent)
                        addLog("📱 Запрос роли SMS-приложения...")
                    }
                }
            } else {
                // Android 4.4 - 9: стандартный способ
                val intent = Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT)
                intent.putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, packageName)
                requestSmsRoleLauncher.launch(intent)
                addLog("📱 Запрос установки как SMS-приложения по умолчанию...")
            }
        } catch (e: Exception) {
            addLog("❌ Ошибка запроса роли SMS: ${e.message}")
            Toast.makeText(this, "Попробуйте вручную в Настройках", Toast.LENGTH_LONG).show()
        }
    }
    
    private fun checkSimCards() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP_MR1) {
            try {
                val subscriptionManager = getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as android.telephony.SubscriptionManager
                val subscriptionInfoList = subscriptionManager.activeSubscriptionInfoList
                
                if (subscriptionInfoList != null && subscriptionInfoList.isNotEmpty()) {
                    addLog("📞 Обнаружено SIM-карт: ${subscriptionInfoList.size}")
                    for (i in subscriptionInfoList.indices) {
                        val info = subscriptionInfoList[i]
                        addLog("  SIM ${i + 1}: ${info.displayName}")
                    }
                    
                    // Если только одна SIM - скрываем выбор
                    if (subscriptionInfoList.size == 1) {
                        binding.radioGroupSim.visibility = android.view.View.GONE
                        addLog("💡 Одна SIM - выбор не требуется")
                    }
                } else {
                    addLog("⚠️ Активных SIM-карт не найдено")
                }
            } catch (e: Exception) {
                addLog("⚠️ Ошибка проверки SIM: ${e.message}")
            }
        }
    }
    
    private fun scanQRCode() {
        val integrator = IntentIntegrator(this)
        integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE)
        integrator.setPrompt("Отсканируйте QR код из CreditBot")
        integrator.setCameraId(0)
        integrator.setBeepEnabled(true)
        integrator.setBarcodeImageEnabled(false)
        integrator.initiateScan()
    }
    
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        val result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data)
        if (result != null) {
            if (result.contents != null) {
                parseQRCode(result.contents)
            } else {
                Toast.makeText(this, "Отменено", Toast.LENGTH_SHORT).show()
            }
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }
    
    private fun parseQRCode(qrData: String) {
        try {
            // Формат QR: {"bot_token":"xxx","chat_id":"yyy","device_name":"zzz"}
            val json = JSONObject(qrData)
            botToken = json.getString("bot_token")
            chatId = json.getString("chat_id")
            deviceName = json.optString("device_name", "Android Device")
            
            // Сохраняем
            saveConfiguration()
            
            addLog("✅ QR код отсканирован")
            addLog("📱 Устройство: $deviceName")
            addLog("💬 Chat ID: $chatId")
            
            // Отправляем подтверждение в Telegram
            sendTelegramMessage("✅ Устройство подключено!\n📱 $deviceName")
            
            binding.tvStatus.text = "Статус: Настроено"
            binding.btnStartService.isEnabled = true
            
        } catch (e: Exception) {
            addLog("❌ Ошибка QR кода: ${e.message}")
            Toast.makeText(this, "Неверный QR код", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun saveConfiguration() {
        val prefs = getSharedPreferences("sms_gateway", MODE_PRIVATE)
        prefs.edit().apply {
            putString("bot_token", botToken)
            putString("chat_id", chatId)
            putString("device_name", deviceName)
            putInt("sim_slot", selectedSimSlot)
            apply()
        }
    }
    
    private fun saveSimSelection() {
        val prefs = getSharedPreferences("sms_gateway", MODE_PRIVATE)
        prefs.edit().putInt("sim_slot", selectedSimSlot).apply()
    }
    
    private fun loadConfiguration() {
        val prefs = getSharedPreferences("sms_gateway", MODE_PRIVATE)
        botToken = prefs.getString("bot_token", null)
        chatId = prefs.getString("chat_id", null)
        deviceName = prefs.getString("device_name", "Android Device") ?: "Android Device"
        selectedSimSlot = prefs.getInt("sim_slot", -1)
        
        // Устанавливаем выбранную SIM в UI
        when (selectedSimSlot) {
            0 -> binding.radioSim1.isChecked = true
            1 -> binding.radioSim2.isChecked = true
            else -> binding.radioSimDefault.isChecked = true
        }
        
        if (botToken != null && chatId != null) {
            binding.tvStatus.text = "Статус: Настроено"
            binding.btnStartService.isEnabled = true
            addLog("✅ Конфигурация загружена")
        } else {
            binding.tvStatus.text = "Статус: Требуется настройка"
            binding.btnStartService.isEnabled = false
        }
    }
    
    private fun checkConfiguration() {
        if (botToken != null && chatId != null) {
            addLog("✅ Готово к работе")
        } else {
            addLog("⚠️ Отсканируйте QR код для начала работы")
        }
    }
    
    private fun startSMSService() {
        val intent = Intent(this, SMSService::class.java)
        intent.putExtra("bot_token", botToken)
        intent.putExtra("chat_id", chatId)
        intent.putExtra("device_name", deviceName)
        intent.putExtra("sim_slot", selectedSimSlot)
        
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        
        binding.tvStatus.text = "Статус: Работает 🟢"
        val simInfo = when (selectedSimSlot) {
            0 -> " (SIM 1)"
            1 -> " (SIM 2)"
            else -> " (SIM по умолчанию)"
        }
        addLog("🚀 Служба запущена$simInfo")
        
        Toast.makeText(this, "Служба запущена", Toast.LENGTH_SHORT).show()
    }
    
    private fun stopSMSService() {
        val intent = Intent(this, SMSService::class.java)
        stopService(intent)
        
        binding.tvStatus.text = "Статус: Остановлено 🔴"
        addLog("⏹️ Служба остановлена")
        
        Toast.makeText(this, "Служба остановлена", Toast.LENGTH_SHORT).show()
    }
    
    private fun testSMS() {
        if (botToken == null || chatId == null) {
            Toast.makeText(this, "Сначала настройте подключение", Toast.LENGTH_SHORT).show()
            return
        }
        
        addLog("🧪 Тестовая отправка...")
        sendTelegramMessage("🧪 Тест связи с CreditBot\n\nВсё работает отлично!")
    }
    
    fun sendSMS(phone: String, message: String): Boolean {
        return try {
            // Для Android 5.1+ (API 22+) используем SubscriptionManager для выбора SIM
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP_MR1) {
                val subscriptionManager = getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as android.telephony.SubscriptionManager
                val subscriptionInfoList = subscriptionManager.activeSubscriptionInfoList
                
                if (subscriptionInfoList != null && subscriptionInfoList.isNotEmpty()) {
                    // Если выбрана конкретная SIM
                    val subscriptionId = if (selectedSimSlot >= 0 && selectedSimSlot < subscriptionInfoList.size) {
                        subscriptionInfoList[selectedSimSlot].subscriptionId
                    } else {
                        // По умолчанию используем первую SIM
                        subscriptionInfoList[0].subscriptionId
                    }
                    
                    val smsManager = SmsManager.getSmsManagerForSubscriptionId(subscriptionId)
                    val parts = smsManager.divideMessage(message)
                    
                    if (parts.size > 1) {
                        smsManager.sendMultipartTextMessage(phone, null, parts, null, null)
                    } else {
                        smsManager.sendTextMessage(phone, null, message, null, null)
                    }
                    
                    sentCount++
                    updateStats()
                    val simName = if (selectedSimSlot >= 0) "SIM ${selectedSimSlot + 1}" else "SIM по умолчанию"
                    addLog("✅ SMS отправлено ($simName): $phone")
                    true
                } else {
                    // Нет активных SIM
                    addLog("❌ Нет активных SIM-карт")
                    false
                }
            } else {
                // Для старых версий Android используем стандартный метод
                val smsManager = SmsManager.getDefault()
                val parts = smsManager.divideMessage(message)
                
                if (parts.size > 1) {
                    smsManager.sendMultipartTextMessage(phone, null, parts, null, null)
                } else {
                    smsManager.sendTextMessage(phone, null, message, null, null)
                }
                
                sentCount++
                updateStats()
                addLog("✅ SMS отправлено: $phone")
                true
            }
            
        } catch (e: Exception) {
            errorCount++
            updateStats()
            addLog("❌ Ошибка отправки: ${e.message}")
            false
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
                
                val responseCode = connection.responseCode
                if (responseCode == 200) {
                    withContext(Dispatchers.Main) {
                        addLog("📤 Отчёт отправлен в Telegram")
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    addLog("❌ Ошибка Telegram: ${e.message}")
                }
            }
        }
    }
    
    private fun updateStats() {
        binding.tvStats.text = "📊 Отправлено: $sentCount | Ошибок: $errorCount"
    }
    
    fun addLog(message: String) {
        runOnUiThread {
            val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
            val logEntry = "[$timestamp] $message\n"
            binding.tvLogs.append(logEntry)
            
            // Автоскролл вниз
            binding.scrollView.post {
                binding.scrollView.fullScroll(android.view.View.FOCUS_DOWN)
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        instance = null
        scope.cancel()
    }
    
    companion object {
        private const val TAG = "MainActivity"
        var instance: MainActivity? = null
    }
}
