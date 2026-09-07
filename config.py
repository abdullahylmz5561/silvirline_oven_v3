"""
SILVERLINE Akıllı Fırın Arayüzü - Genel Ayarlar
=================================================
Jetson TX2 üzerinde 800x480 dokunmatik panel için hazırlanmıştır.
Geliştirme sırasında (Jetson takılı değilken) DEBUG_MODE = True yaparak
uygulamayı normal bir masaüstü penceresinde, seri haberleşme simülasyonuyla
çalıştırabilirsiniz.
"""

# --- Ekran ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# True: pencereli (masaüstünde geliştirme), fare imleci görünür, seri port
#       bulunamazsa otomatik simülasyon moduna geçer.
# False: gerçek donanım (Jetson TX2) - tam ekran, imleç gizli, kiosk modu.
DEBUG_MODE = True

# --- Seri Haberleşme (fırın kontrol kartı ile) ---
SERIAL_PORT = "/dev/ttyTHS1"   # Jetson TX2 donanımsal UART. Gerekirse /dev/ttyUSB0 yapın.
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 1.0           # saniye
# Port açılamazsa (kart bağlı değilse) otomatik olarak simülasyon moduna düş.
SERIAL_AUTO_SIMULATE = True

# --- Sıcaklık sınırları ---
MIN_TEMP = 50
MAX_TEMP = 250
DEFAULT_TEMP = 180
TEMP_STEP = 10

# --- Açılış animasyonu ---
SPLASH_DURATION_MS = 2600
SPLASH_TEXT = "SILVERLINE"

# --- Sesli asistan ---
# Google Cloud Speech-to-Text + Text-to-Speech kullanılıyor (internet gerekir).
# Uyandırma kelimesi (wake word) tespiti YERELDE çalışır - sürekli ses akışı
# buluta gönderilmez; sadece wake word tetiklendikten veya mikrofon butonuna
# basıldıktan sonraki komut cümlesi buluta gider.
ASSISTANT_ENABLED = True

# Google Cloud kimlik bilgileri (Service Account JSON dosyası).
# export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json şeklinde ortam
# değişkeni ile de verilebilir; burası boşsa o ortam değişkeni kullanılır.
GOOGLE_CREDENTIALS_PATH = ""   # örn. "/home/nvidia/silverline_oven/gcloud_key.json"

STT_LANGUAGE_CODE = "tr-TR"
TTS_LANGUAGE_CODE = "tr-TR"
TTS_VOICE_NAME = "tr-TR-Wavenet-A"     # Google'ın Türkçe WaveNet seslerinden biri
AUDIO_SAMPLE_RATE = 16000               # STT ve wake word için gereken oran
AUDIO_CHANNELS = 1
MIC_DEVICE_INDEX = None                 # None = sistem varsayılan mikrofonu

# Hoparlörden çalmadan önce eklenen sessizlik - donanımın "uyanma" süresi
# yüzünden yanıtın ilk hecesi kesiliyorsa bu değeri artırın (ör. 400).
TTS_PLAYBACK_PADDING_MS = 250

# --- Uyandırma kelimesi (openWakeWord) ---
WAKE_WORD_ENABLED = True
WAKE_WORD_MODEL_PATH = "assets/hey_silverline.onnx"   # eğitilmiş özel model
WAKE_WORD_THRESHOLD = 0.5

# --- Ses kaydı / VAD (voice activity detection) ---
VAD_AGGRESSIVENESS = 2          # 0-3, yüksek = daha agresif sessizlik tespiti
VAD_SILENCE_MS = 900            # bu kadar sessizlikten sonra kayıt durur
VAD_MAX_RECORD_MS = 8000        # komut cümlesi için üst sınır (güvenlik)

# --- Konuşma motoru (Claude API) ---
# Eski kural tabanlı çözümleyici (core/intent_parser.py) yalnızca sabit
# kalıplara cevap veriyordu. Bunun yerine Claude API ile serbest sohbet +
# function calling kullanılıyor: model hem doğal sohbet edip tarif önerebilir
# hem de gerektiğinde gerçekten fırını kontrol eden araçları (tool) çağırır.
#
# Kurulum: pip install anthropic
#          export ANTHROPIC_API_KEY=sk-ant-...
# (Anahtarı asla config.py içine yazmayın - ortam değişkeni olarak tutun.)
LLM_ENABLED = True
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"   # hızlı ve ucuz, sesli asistan için yeterli
CONVERSATION_MAX_TURNS = 6   # hafızada tutulacak kullanıcı+asistan çift sayısı

