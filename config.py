"""
core/llm_assistant.py
========================
Gemini (Vertex AI REST API üzerinden) ile serbest sohbet eden ve
gerektiğinde fırını gerçekten kontrol eden (function calling) motor.

NEDEN google-genai SDK'sı DEĞİL: O paket Python 3.10+ gerektiriyor, Jetson
TX2'nin standart JetPack kurulumu Python 3.6.9 ile geliyor. SDK'yı atlayıp
Vertex AI'ın REST API'sine google-auth + requests ile doğrudan istek
atıyoruz - ikisi de zaten Google Cloud Speech/Text-to-Speech için kurulu
ve Python 3.6 ile tam uyumlu. Sonuç işlevsel olarak SDK ile birebir aynı.

Kimlik bilgisi: STT/TTS için zaten tanımladığınız AYNI Service Account
JSON dosyası (config.GOOGLE_CREDENTIALS_PATH) kullanılıyor.
"""

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

import config
from core.oven_controller import OVEN_FUNCTIONS

_credentials = None


def _get_token() -> str:
    global _credentials
    if _credentials is None:
        _credentials = service_account.Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    if not _credentials.valid:
        _credentials.refresh(GoogleAuthRequest())
    return _credentials.token


_MODE_LEGEND = "\n".join(f'- {f["key"]}: {f["label"]}' for f in OVEN_FUNCTIONS)
_MODE_KEYS = [f["key"] for f in OVEN_FUNCTIONS]

SYSTEM_PROMPT = """Sen SILVERLINE akıllı fırının sesli asistanısın. Türkçe, sıcak ve
samimi konuşuyorsun - bir arkadaş gibi, resmi değil. Yanıtların SESLİ
OKUNACAK: madde işareti, markdown, uzun listeler kullanma; doğal, akıcı
cümleler kur. Tarif önerirken 2-4 cümlelik pratik bir özet ver, gerekirse
kullanıcı detay isterse devam edersin.

Kullanıcı fırınla ilgili genel sohbet edebilir, tarif sorabilir, pişirme
tavsiyesi isteyebilir - bunlara doğrudan kendi bilgin ile cevap ver, araç
çağırmana gerek yok. SADECE kullanıcı fırını gerçekten bir duruma
GETİRMENİ istediğinde (ör. "fırını başlat", "200 dereceye ayarla",
"pizza moduna al", "bunu uygula") ilgili aracı çağır.

Fırın modları:
""" + _MODE_LEGEND + """

Sıcaklık aralığı 50-250°C arası. Bir tarif önerip kullanıcı "tamam bunu
yap" derse, önerdiğin sıcaklık/süre/modu uygun araçlarla gerçekten
uygula - tahmin ettiğin makul değerleri kullan (yerel tarif kütüphanesiyle
sınırlı değilsin, herhangi bir yemek için mantıklı sıcaklık/süre önerebilirsin).
"""

_TOOLS = [{
    "functionDeclarations": [
        {
            "name": "set_mode",
            "description": "Fırının pişirme modunu değiştirir.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"mode": {"type": "STRING", "enum": _MODE_KEYS}},
                "required": ["mode"],
            },
        },
        {
            "name": "set_temperature",
            "description": "Fırının hedef sıcaklığını derece (°C) cinsinden ayarlar.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"value": {"type": "INTEGER"}},
                "required": ["value"],
            },
        },
        {
            "name": "set_timer",
            "description": "Pişirme zamanlayıcısını dakika cinsinden kurar.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"minutes": {"type": "INTEGER"}},
                "required": ["minutes"],
            },
        },
        {
            "name": "start_cooking",
            "description": "Fırını mevcut mod ve sıcaklık ayarıyla çalıştırmaya başlar.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "stop_cooking",
            "description": "Fırını durdurur.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
    ]
}]


def _endpoint_url() -> str:
    loc = config.GEMINI_LOCATION
    return (
        f"https://{loc}-aiplatform.googleapis.com/v1/projects/"
        f"{config.GOOGLE_CLOUD_PROJECT_ID}/locations/{loc}/publishers/google/"
        f"models/{config.GEMINI_MODEL}:generateContent"
    )


def generate_reply(user_text, history, on_tool_call):
    """
    Kullanıcının söylediği cümleyi Gemini'ye gönderir, gerekirse fırın
    araçlarını çağırır (on_tool_call(name, params) ile - genelde
    assistant_bridge.handle_intent).

    history ve dönen geçmiş: düz JSON uyumlu sözlük listesi
    (ör. [{"role": "user", "parts": [{"text": "..."}]}, ...]) - kolayca
    saklanıp bir sonraki çağrıya aynen geri verilebilir.

    Döner: (yanıt_metni, güncellenmiş_geçmiş)
    """
    contents = list(history) + [{"role": "user", "parts": [{"text": user_text}]}]
    final_text_parts = []

    for _ in range(3):  # ardışık araç çağrısı zinciri için güvenlik sınırı
        body = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "tools": _TOOLS,
            "generationConfig": {"maxOutputTokens": 400},
        }
        headers = {
            "Authorization": "Bearer " + _get_token(),
            "Content-Type": "application/json; charset=utf-8",
        }
        resp = requests.post(_endpoint_url(), headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        candidate_content = data["candidates"][0]["content"]
        contents.append(candidate_content)

        parts = candidate_content.get("parts", [])
        function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
        text_parts = [p["text"] for p in parts if "text" in p]
        final_text_parts.extend(text_parts)

        if not function_calls:
            break

        response_parts = []
        for fc in function_calls:
            name = fc["name"]
            args = fc.get("args", {})
            try:
                on_tool_call(name, args)
                result = {"result": "Tamamlandı."}
            except Exception as exc:
                result = {"result": "Hata oluştu: " + str(exc)}
            response_parts.append({"functionResponse": {"name": name, "response": result}})
        contents.append({"role": "user", "parts": response_parts})

    reply = " ".join(t.strip() for t in final_text_parts if t.strip()) or "Tamam."
    trimmed_history = contents[-(config.CONVERSATION_MAX_TURNS * 2):]
    return reply, trimmed_history
