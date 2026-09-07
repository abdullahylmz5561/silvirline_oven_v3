"""
core/recipes_data.py
=======================
Tarif kütüphanesinin TEK veri kaynağı. Hem ui/views/recipes_view.py (görsel
kart listesi) hem core/intent_parser.py (sesli komutta tarif adı eşleştirme)
buradan okur - iki yerde aynı listeyi tutup birbirinden sapmasını önler.
"""

RECIPES = [
    {"name": "Ekmek",           "cat": "Ekmek & Hamur", "mode": "ALT_UST",     "temp": 180, "min": 45},
    {"name": "Kruvasan",        "cat": "Ekmek & Hamur", "mode": "ALT_UST_FAN", "temp": 190, "min": 20},
    {"name": "Pizza",           "cat": "Ekmek & Hamur", "mode": "PIZZA",       "temp": 220, "min": 25},
    {"name": "Börek",           "cat": "Ekmek & Hamur", "mode": "ALT_UST",     "temp": 170, "min": 50},
    {"name": "Izgara Tavuk",    "cat": "Et & Tavuk",    "mode": "GRILL",       "temp": 190, "min": 35},
    {"name": "Fırın Köfte",     "cat": "Et & Tavuk",    "mode": "ALT_UST_FAN", "temp": 200, "min": 30},
    {"name": "Kuzu Pirzola",    "cat": "Et & Tavuk",    "mode": "MAXI_GRILL",  "temp": 220, "min": 22},
    {"name": "Kek",             "cat": "Tatlı",         "mode": "ALT_UST",     "temp": 200, "min": 18},
    {"name": "Kurabiye",        "cat": "Tatlı",         "mode": "ALT_UST_FAN", "temp": 175, "min": 14},
    {"name": "Sütlaç",          "cat": "Tatlı",         "mode": "GRILL",       "temp": 210, "min": 20},
    {"name": "Fırın Patates",   "cat": "Sebze",         "mode": "ALT_UST",     "temp": 210, "min": 40},
    {"name": "Fırın Sebze",     "cat": "Sebze",         "mode": "ALT_UST_FAN", "temp": 200, "min": 28},
]
CATEGORIES = ["Tümü", "Ekmek & Hamur", "Et & Tavuk", "Tatlı", "Sebze"]
