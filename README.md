# SILVERLINE Akıllı Fırın Arayüzü

Jetson TX2 üzerinde çalışan, 800×480 dokunmatik panel için PyQt5 ile
yazılmış tam ekran fırın kontrol arayüzü.

## Kurulum

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Jetson TX2 (JetPack) üzerinde PyQt5'i pip yerine apt ile kurmak genelde
daha sorunsuzdur:

```bash
sudo apt install python3-pyqt5 python3-serial
```

## Çalıştırma

```bash
python3 main.py
```

- **Geliştirme (PC'de, donanım yokken):** `config.py` içinde
  `DEBUG_MODE = True` olarak kalsın. Uygulama 800×480 boyutunda normal bir
  pencere olarak açılır, fare ile kullanılabilir ve seri port bulunamazsa
  otomatik olarak **simülasyon moduna** geçip gerçekçi sahte sıcaklık
  telemetrisi üretir.
- **Gerçek donanım (Jetson TX2 + dokunmatik panel):** `DEBUG_MODE = False`
  yapın. Uygulama tam ekran, çerçevesiz ve imleç gizli şekilde açılır.
- **Çıkış:** Her iki modda da **ESC** tuşu uygulamayı kapatır
  (açılış animasyonu dahil).

## Klasör yapısı

```
main.py                    Giriş noktası, splash -> ana pencere geçişi
config.py                  Tüm ayarlar (ekran, seri port, sıcaklık sınırları)

core/
  oven_controller.py       Fırının tek durum kaynağı. UI ve sesli asistan
                            fırını HER ZAMAN bu sınıf üzerinden yönetir.
  serial_comm.py           Kontrol kartıyla UART haberleşmesi + simülasyon
  recipes_data.py          Tarif verisi (UI ve intent parser'ın ortak kaynağı)
  assistant_bridge.py      Sesli asistan orkestrasyonu (wake word + push-to-talk)
  wake_word.py              Yerel (offline) "Hey Silverline" tespiti (openWakeWord)
  voice_session.py         Tek bir sesli komut oturumu: kayıt→STT→niyet→TTS
  audio_io.py               Mikrofon kaydı (VAD ile) ve hoparlörden çalma
  cloud_speech.py          Google Cloud STT/TTS istemcileri
  intent_parser.py         Türkçe metinden fırın komutu çıkarma (kural tabanlı)

ui/
  main_window.py           Ana pencere, nav rail + ekran yığını, ESC/tam ekran
  nav_rail.py               Sol menü (Ana Ekran / Tarifler / Zamanlayıcı / Ayarlar / Mikrofon)
  splash_screen.py         "SILVERLINE" açılış animasyonu
  icons.py                 QPainter ile çizilen fırın piktogramları ve menü ikonları
  widgets/temp_dial.py     Dairesel sıcaklık kadranı
  views/
    home_view.py           Ana ekran: kadran + fırın fonksiyonları ızgarası
    recipes_view.py        Tarif kütüphanesi (kategori filtreli)
    timer_view.py          Bağımsız zamanlayıcı
    settings_view.py       Cihaz ayarları + seri bağlantı durumu

styles/theme.qss           Koyu grafit + kor/amber tema
```

## Sesli asistan kurulumu

Google Cloud Speech-to-Text + Text-to-Speech kullanılıyor (internet gerekir).
Uyandırma kelimesi tespiti ise **yerelde (offline)** çalışıyor — sürekli ses
akışı buluta gönderilmiyor, sadece tetiklendikten sonraki komut cümlesi
buluta gidiyor.

**1. Google Cloud tarafı**
```bash
pip install -r requirements.txt
```
- Google Cloud Console'da bir proje açın, **Speech-to-Text API** ve
  **Text-to-Speech API**'yi etkinleştirin, faturalandırmayı açın.
- Bir Service Account oluşturup JSON anahtarını indirin.
- `config.py` içinde `GOOGLE_CREDENTIALS_PATH`'i o dosyanın yoluna ayarlayın
  (ya da `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`).

**2. Uyandırma kelimesi modeli**
- [openWakeWord](https://github.com/dscripka/openWakeWord) ile özel
  "Hey Silverline" modelini eğitin (birkaç dakikalık sentetik veri,
  GPU gerekmiyor) ve `.onnx` dosyasını `config.WAKE_WORD_MODEL_PATH`
  konumuna (`assets/hey_silverline.onnx`) koyun.
- Model hazır değilse `config.WAKE_WORD_ENABLED = False` yaparak sadece
  push-to-talk (mikrofon butonu) ile devam edebilirsiniz.

**3. Ses donanımı**
- Jetson TX2'ye bağlı mikrofon/hoparlörün `arecord -l` / `aplay -l` ile
  görünür olduğundan emin olun. Belirli bir cihaz seçmek gerekirse
  `config.MIC_DEVICE_INDEX`'i ayarlayın.

**4. Etkinleştirme**
- `config.ASSISTANT_ENABLED = True` (varsayılan olarak açık).
- Nav rail'deki mikrofon butonu: gri = boşta, turuncu dolu = dinliyor,
  çelik mavisi = buluta gönderilip işleniyor, koyu kor = yanıt seslendiriliyor.
- Ekranın altında beliren kısa şerit, asistanın anladığı/söylediği metni
  gösterir.

**5. Bilinen donanım sorunu: kesik yanıt**
- **Yanıtın ilk hecesi kesiliyorsa** ("Tamam fırını açıyorum" yerine "mam
  fırını açıyorum" gibi duyuluyorsa): bu, ALSA/PortAudio çıkışının ses
  çalmaya başlamadan önceki "uyanma" gecikmesinden kaynaklanır.
  `core/audio_io.py` bunu sesin başına otomatik sessizlik ekleyerek
  (`config.TTS_PLAYBACK_PADDING_MS`, varsayılan 250ms) çözüyor. Jetson'ın
  gerçek ses kartında hâlâ kesilme oluyorsa bu değeri 400-500 gibi
  artırın. Aynı sınıf gecikme teorik olarak kayıt başlangıcında da
  (kullanıcının ilk kelimesi) yaşanabilir - öyle bir şikayet gelirse
  `record_until_silence()`'a benzer bir "priming" eklenebilir.
`MODE_PATTERNS`/`parse_intent()`'e birkaç satır eklemeniz, gerekirse
`core/assistant_bridge.py`'deki `_intent_handlers` sözlüğüne yeni bir
`intent_adı -> OvenController metodu` eşlemesi koymanız yeterli.

## Kiosk kurulumu (Ubuntu dock / tam ekran sorunu)

Standart bir Ubuntu masaüstü oturumunda (GNOME/Unity), soldaki dock/launcher
panel WM'e (pencere yöneticisine) "ekranın şu kadarını bana ayır" diye bir
alan (strut) bildirir. `showFullScreen()` çoğu zaman bunu görmezden gelemez,
bu yüzden dock açık kalıyormuş gibi görünür.

**Uygulama bunu artık kendi içinde çözüyor:** `MainWindow.show_kiosk()` ve
`SplashScreen.show_kiosk()`, pencereyi `X11BypassWindowManagerHint` ile WM'in
karar mekanizmasının tamamen dışına çıkarıp ekranın gerçek piksel boyutuna
(`QApplication.primaryScreen().geometry()`) manuel olarak oturtuyor. Ayrıca
splash artık ana pencerenin **önünde** açılıyor (ana pencere baştan itibaren
arkada tam ekran hazır bekliyor), böylece splash kapanınca araya masaüstünün
göründüğü bir boşluk girmiyor.

**Üretim cihazı için asıl önerilen kalıcı çözüm** yine de işletim sistemi
seviyesinde: Jetson'ı GNOME/Unity yerine dock içermeyen hafif bir ortamla
(ör. `openbox` veya `matchbox-window-manager`) ya da doğrudan bu uygulamayı
autostart eden minimal bir X oturumuyla açmak. Bu, gerçek bir fırın ürününde
standart pratiktir ve dock/panel sorununu kökten ortadan kaldırır:

```bash
sudo apt install openbox
# ~/.xinitrc veya autostart betiğine ekleyin:
python3 /path/to/silverline_oven/main.py &
openbox-session
```

Bu şekilde masaüstü ortamı hiç yüklenmez, ekranda sadece uygulama olur.

## Seri haberleşme protokolü

Basit, satır bazlı (`\n` ile biten) metin protokolü. Kontrol kartı
firmware'inde aynı komutları uygulamanız yeterli:

**Jetson → Kart**
| Komut | Açıklama |
|---|---|
| `MODE:<AD>` | örn. `MODE:ALT_UST_FAN` |
| `SETTEMP:<int>` | Hedef sıcaklık (°C) |
| `SETTIMER:<saniye>` | Zamanlayıcı süresi |
| `START` | Pişirmeyi başlat |
| `STOP` | Pişirmeyi durdur |

**Kart → Jetson**
| Mesaj | Açıklama |
|---|---|
| `TEMP:<int>` | Anlık iç sıcaklık |
| `DOOR:<0/1>` | Kapı durumu (1 = açık) |
| `STATUS:<IDLE\|HEATING\|READY\|ERROR>` | Fırın durumu |

Port `config.py` içinde `SERIAL_PORT` ile ayarlanır (Jetson TX2'nin
donanımsal UART'ı için varsayılan `/dev/ttyTHS1`; USB-seri çevirici
kullanıyorsanız `/dev/ttyUSB0` yapın). Kart bağlı değilse ve
`SERIAL_AUTO_SIMULATE = True` ise arayüz otomatik olarak simülasyon
moduna düşer — donanım gelmeden geliştirmeye devam edebilirsiniz.

## Sesli asistan mimarisi

**Bu artık sadece komut yürüten bir sistem değil — Claude API ile serbest
sohbet edebilen bir asistan.** Kullanıcı doğrudan "pizza modunu aç" gibi
bir komut vermek zorunda değil; "bu akşam misafirim var, hafif bir şeyler
yapmak istiyorum" gibi açık uçlu bir şey de söyleyebilir, Claude tarif
önerir, sohbet eder. Kullanıcı fırını GERÇEKTEN bir duruma getirmesini
istediğinde (ör. "tamam bunu uygula, başlat") Claude ilgili aracı (tool)
çağırır ve bu çağrı `assistant_bridge.handle_intent()` üzerinden **dokunmatik
ekranın kullandığı aynı** `OvenController`'a gider:

```python
# core/llm_assistant.py, Claude'a tanımlanan araçlardan biri çağrıldığında:
bridge.handle_intent("set_mode", {"mode": "PIZZA"})
bridge.handle_intent("apply_recipe", {"mode": "ALT_UST", "temp": 180, "minutes": 45})
```

`core/voice_session.py` tüm akışı (kayıt → STT → Claude → TTS) ayrı bir
thread'de yürütüp UI'ı bloklamaz. Sohbet geçmişi (`AssistantBridge._conversation_history`)
oturumlar arasında korunur, böylece "peki onu 10 dakika daha pişirsem?"
gibi önceki cümleye bağlı bir şey söylendiğinde Claude bağlamı hatırlar.

**Kurulum:**
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```
Anahtarı console.anthropic.com üzerinden alabilirsiniz. `config.py` içinde
`ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"` olarak ayarlı - hızlı ve
ucuz, sesli asistan için yeterli; daha nüanslı sohbet/tarif isterseniz
`"claude-sonnet-5"` ile değiştirebilirsiniz.

**Not:** `core/intent_parser.py` (eski kural tabanlı çözümleyici) artık
kullanılmıyor ama projede duruyor - internet/API anahtarı olmadan da
çalışan çok basit bir yedek mod isterseniz oraya geri dönülebilir.

## Notlar / sonraki adımlar

- Fırın fonksiyon ikonları (`ui/icons.py`) dosya kullanmadan, koddan
  QPainter ile çizilir — Jetson'a dağıtımda eksik asset dosyası riski
  yoktur ve gerçek fırın piktogramlarıyla (alt çizgi, üst-alt çizgi,
  fan, zigzag ızgara) birebir aynı mantığı kullanır.
- `ui/main_window.py`'deki ESC davranışı hem splash ekranında hem ana
  pencerede aktiftir.
- Gerçek kartla test ederken `STATUS:ERROR` gibi hata durumlarını
  arayüzde göstermek isterseniz `OvenController.status_changed`
  sinyaline bir dinleyici eklemeniz yeterli (şu an sadece loglanıyor).
