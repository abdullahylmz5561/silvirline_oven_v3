"""
core/intent_parser.py
========================
STT'den gelen Türkçe cümleyi, assistant_bridge.handle_intent()'in beklediği
(intent_adı, parametreler) çiftlerine çevirir.

Fırının komut seti sınırlı ve netliğin (yanlış moda geçmemek) kritik olduğu
bir cihaz olduğu için kural/anahtar-kelime tabanlı bir çözümleyici tercih
edildi: LLM tabanlı bir çözümleyiciye göre çok daha hızlı, ücretsiz ve
öngörülebilir. Yeni bir sesli komut eklemek için sadece PATTERNS'e veya
ilgili fonksiyona birkaç satır eklemek yeterli.

Örnekler:
  "fırını iki yüz derece pizza moduna ayarla, başlat"
      -> [("set_mode", {"mode": "PIZZA"}), ("set_temperature", {"value": 200}), ("start_cooking", {})]
  "ekmek tarifini uygula"
      -> [("apply_recipe", {"mode": "ALT_UST", "temp": 180, "minutes": 45})]
  "on dakika zamanlayıcı kur"
      -> [("set_timer", {"minutes": 10})]
"""

import re

from core.recipes_data import RECIPES

# Mod anahtar kelimeleri - ÖZEL DURUMLAR (maksi ızgara, alt üst fan) genel
# olanlardan (ızgara, alt üst) ÖNCE kontrol edilmeli, yoksa "ızgara" kelimesi
# "maksi ızgara" cümlesinde de eşleşip yanlış moda düşer.
MODE_PATTERNS = [
    (r"maksi\s*(ız|iz)gara|maksi\s*grill", "MAXI_GRILL"),
    (r"alt\s*üst\s*fan|üst\s*alt\s*fan|fanlı", "ALT_UST_FAN"),
    (r"alt\s*üst|üstten\s*alttan|üst\s*alt", "ALT_UST"),
    (r"\bpizza\b", "PIZZA"),
    (r"(ız|iz)gara|grill", "GRILL"),
    (r"\balt\b(?!\s*üst)", "ALT"),
]

TEMP_PATTERN = re.compile(r"(\d{2,3})\s*derece")
TIMER_PATTERN = re.compile(r"(\d{1,3})\s*dakika")

START_WORDS = ["başlat", "çalıştır", "pişirmeye başla", "pişir"]
STOP_WORDS = ["durdur", "dur şimdi", "iptal et", "kapat"]

# Rakamları yazıyla söyleyen kullanıcılar için basit bir sözlük
# (STT genelde rakamlara çevirir ama emniyet için burada da tutuyoruz).
NUMBER_WORDS = {
    "yüz": 100, "yüzelli": 150, "iki yüz": 200, "iki yüz elli": 250,
    "on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50,
    "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90,
}


def parse_intent(text: str):
    """
    Türkçe cümleyi ayrıştırır, [(intent_adı, params), ...] listesi döndürür.
    Hiçbir şey eşleşmezse boş liste döner (assistant_bridge bunu "anlaşılamadı"
    olarak yorumlayıp kullanıcıya sesli geri bildirim verir).
    """
    text = text.lower().strip()
    intents = []

    # --- Tarif eşleşmesi (varsa en yüksek öncelik - hem mod hem sıcaklık hem
    #     süreyi tek seferde ayarlar) ---
    for recipe in RECIPES:
        if recipe["name"].lower() in text:
            intents.append((
                "apply_recipe",
                {"mode": recipe["mode"], "temp": recipe["temp"], "minutes": recipe["min"]},
            ))
            break  # bir tarif eşleşince mod/sıcaklık ayrıca aranmaz

    if not intents:
        # --- Mod ---
        for pattern, mode_key in MODE_PATTERNS:
            if re.search(pattern, text):
                intents.append(("set_mode", {"mode": mode_key}))
                break

        # --- Sıcaklık ---
        temp_match = TEMP_PATTERN.search(text)
        if temp_match:
            intents.append(("set_temperature", {"value": int(temp_match.group(1))}))
        else:
            for word, value in NUMBER_WORDS.items():
                if word in text and "derece" in text:
                    intents.append(("set_temperature", {"value": value}))
                    break

    # --- Zamanlayıcı ---
    timer_match = TIMER_PATTERN.search(text)
    if timer_match:
        intents.append(("set_timer", {"minutes": int(timer_match.group(1))}))

    # --- Başlat / Durdur ---
    if any(w in text for w in START_WORDS):
        intents.append(("start_cooking", {}))
    elif any(w in text for w in STOP_WORDS):
        intents.append(("stop_cooking", {}))

    return intents


def describe_intents(intents) -> str:
    """Kullanıcıya sesli/görsel geri bildirim için kısa bir Türkçe özet üretir."""
    if not intents:
        return "Üzgünüm, anlayamadım. Tekrar deneyebilir misiniz?"

    mode_labels = {
        "ALT": "Alt", "ALT_UST": "Alt-Üst", "ALT_UST_FAN": "Alt-Üst Fan",
        "PIZZA": "Pizza", "GRILL": "Izgara", "MAXI_GRILL": "Maksi Izgara",
    }
    parts = []
    for name, params in intents:
        if name == "apply_recipe":
            parts.append(f'{mode_labels.get(params["mode"], params["mode"])} modu, {params["temp"]} derece, {params["minutes"]} dakika ayarlandı')
        elif name == "set_mode":
            parts.append(f'{mode_labels.get(params["mode"], params["mode"])} modu seçildi')
        elif name == "set_temperature":
            parts.append(f'{params["value"]} dereceye ayarlandı')
        elif name == "set_timer":
            parts.append(f'{params["minutes"]} dakika zamanlayıcı kuruldu')
        elif name == "start_cooking":
            parts.append("pişirme başlatıldı")
        elif name == "stop_cooking":
            parts.append("pişirme durduruldu")
    return ", ".join(parts).capitalize() + "."
