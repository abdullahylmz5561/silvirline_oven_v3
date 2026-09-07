"""
core/cloud_speech.py
======================
Google Cloud Speech-to-Text ve Text-to-Speech sarmalayıcıları.

Kurulum:
  pip install google-cloud-speech google-cloud-texttospeech
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  (ya da config.GOOGLE_CREDENTIALS_PATH'i doldurun)

Google Cloud Console'da "Speech-to-Text API" ve "Text-to-Speech API"
etkinleştirilmiş, faturalandırması açık bir proje ve o projeye ait bir
Service Account JSON anahtarı gerekir.
"""

import os

import config

if config.GOOGLE_CREDENTIALS_PATH:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.GOOGLE_CREDENTIALS_PATH)

from google.cloud import speech
from google.cloud import texttospeech

_speech_client = None
_tts_client = None


def _get_speech_client():
    global _speech_client
    if _speech_client is None:
        _speech_client = speech.SpeechClient()
    return _speech_client


def _get_tts_client():
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


def speech_to_text(pcm_audio: bytes) -> str:
    """16-bit/16kHz PCM ses verisini Türkçe metne çevirir. Sonuç yoksa boş string döner."""
    client = _get_speech_client()
    recognition_config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=config.AUDIO_SAMPLE_RATE,
        language_code=config.STT_LANGUAGE_CODE,
        # Fırın komutlarında geçen kelimelere ağırlık vererek tanıma
        # doğruluğunu artırır (ör. "alt üst fan", "maksi ızgara").
        speech_contexts=[
            speech.SpeechContext(
                phrases=[
                    "alt üst fan", "alt üst", "maksi ızgara", "ızgara",
                    "pizza", "derece", "dakika", "başlat", "durdur",
                    "ekmek", "kek", "börek", "tavuk", "sütlaç",
                ],
                boost=15.0,
            )
        ],
    )
    audio = speech.RecognitionAudio(content=pcm_audio)

    response = client.recognize(config=recognition_config, audio=audio)
    if not response.results:
        return ""
    return response.results[0].alternatives[0].transcript.strip()


def text_to_speech(text: str) -> tuple[bytes, int]:
    """Metni Türkçe konuşma sesine çevirir. (pcm_bytes, sample_rate) döner."""
    client = _get_tts_client()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=config.TTS_LANGUAGE_CODE,
        name=config.TTS_VOICE_NAME,
    )
    sample_rate = 24000
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content, sample_rate
