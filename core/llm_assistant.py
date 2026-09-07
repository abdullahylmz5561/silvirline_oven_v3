"""
core/llm_assistant.py
========================
Claude API ile serbest sohbet eden ve gerektiğinde fırını gerçekten
kontrol eden (tool use / function calling) konuşma motoru.

Neden kural tabanlı çözümleyici (core/intent_parser.py) yerine bu:
Sabit kalıp eşleştirme yalnızca önceden tanımlı cümlelere cevap
verebiliyordu ("pizza tarifini uygula" gibi). Bu modül yerine Claude'a
serbest bir cümle veriyoruz ("bu akşam misafirim var, hafif bir şeyler
yapmak istiyorum, ne önerirsin?" gibi) - model hem sohbet edip tarif
önerebiliyor hem "hadi bunu 190 derecede alt-üst fanlı pişir" dendiğinde
gerçekten fırını o moda alan aracı (tool) çağırıyor.

Fırın kontrolü YİNE assistant_bridge.handle_intent() üzerinden yapılıyor -
bu modül modele hangi araçların var olduğunu anlatıyor, model bir araç
çağırmaya karar verdiğinde bu dosya onu handle_intent()'e yönlendiriyor.
Model asla fırına doğrudan erişmiyor; sadece izin verilen fonksiyonları
çağırabiliyor.
"""

import anthropic

import config
from core.oven_controller import OVEN_FUNCTIONS

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()   # ANTHROPIC_API_KEY ortam değişkenini otomatik okur
    return _client


_MODE_LEGEND = "\n".join(f'- {f["key"]}: {f["label"]}' for f in OVEN_FUNCTIONS)

SYSTEM_PROMPT = f"""Sen SILVERLINE akıllı fırının sesli asistanısın. Türkçe, sıcak ve
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
{_MODE_LEGEND}

Sıcaklık aralığı 50-250°C arası. Bir tarif önerip kullanıcı "tamam bunu
yap" derse, önerdiğin sıcaklık/süre/modu uygun araçlarla gerçekten
uygula - tahmin ettiğin makul değerleri kullan (yerel tarif kütüphanesiyle
sınırlı değilsin, herhangi bir yemek için mantıklı sıcaklık/süre önerebilirsin).
"""

TOOLS = [
    {
        "name": "set_mode",
        "description": "Fırının pişirme modunu değiştirir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": [f["key"] for f in OVEN_FUNCTIONS]}
            },
            "required": ["mode"],
        },
    },
    {
        "name": "set_temperature",
        "description": "Fırının hedef sıcaklığını derece (°C) cinsinden ayarlar.",
        "input_schema": {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 50, "maximum": 250}},
            "required": ["value"],
        },
    },
    {
        "name": "set_timer",
        "description": "Pişirme zamanlayıcısını dakika cinsinden kurar.",
        "input_schema": {
            "type": "object",
            "properties": {"minutes": {"type": "integer", "minimum": 1, "maximum": 180}},
            "required": ["minutes"],
        },
    },
    {
        "name": "start_cooking",
        "description": "Fırını mevcut mod ve sıcaklık ayarıyla çalıştırmaya başlar.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "stop_cooking",
        "description": "Fırını durdurur.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def generate_reply(user_text: str, history: list, on_tool_call):
    """
    Kullanıcının söylediği cümleyi Claude'a gönderir, gerekirse fırın
    araçlarını çağırır (on_tool_call(name, params) ile - genelde
    assistant_bridge.handle_intent).

    Döner: (yanıt_metni, güncellenmiş_geçmiş)
    """
    client = _get_client()
    messages = history + [{"role": "user", "content": user_text}]
    final_text_parts = []

    for _ in range(3):  # ardışık araç çağrısı zinciri için güvenlik sınırı
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b.text for b in response.content if b.type == "text"]
        final_text_parts.extend(text_blocks)

        if not tool_uses:
            break

        tool_results = []
        for tu in tool_uses:
            try:
                on_tool_call(tu.name, tu.input)
                result_text = "Tamamlandı."
            except Exception as exc:
                result_text = f"Hata oluştu: {exc}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result_text,
            })
        messages.append({"role": "user", "content": tool_results})

    reply = " ".join(p.strip() for p in final_text_parts if p.strip()) or "Tamam."
    trimmed_history = messages[-(config.CONVERSATION_MAX_TURNS * 2):]
    return reply, trimmed_history
