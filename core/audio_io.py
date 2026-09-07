"""
core/audio_io.py
==================
Mikrofon kaydı, sessizlik algılama (VAD) ve hoparlörden ses çalma.

Bu modül wake-word motorundan ve bulut STT/TTS'ten bağımsızdır - sadece
"ham ses" ile ilgilenir. Böylece ileride mikrofon/hoparlör donanımı
değişirse (Jetson üzerindeki kart farklıysa) sadece bu dosya güncellenir.

Tüm fonksiyonlar 16 kHz, mono, 16-bit PCM (int16) varsayar - hem
openWakeWord hem Google STT bu formatı bekliyor.
"""

import queue
import numpy as np
import sounddevice as sd
import webrtcvad

import config


def record_until_silence(max_ms: int = None) -> bytes:
    """
    Mikrofonu açar, kullanıcı konuşmayı bitirip config.VAD_SILENCE_MS kadar
    sessiz kalana (ya da max_ms süresi dolana) kadar kaydeder.
    Geriye ham 16-bit PCM byte dizisi döner (Google STT'ye doğrudan verilebilir).
    """
    max_ms = max_ms or config.VAD_MAX_RECORD_MS
    frame_ms = 30  # webrtcvad sadece 10/20/30 ms çerçeve kabul eder
    frame_samples = int(config.AUDIO_SAMPLE_RATE * frame_ms / 1000)

    vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)
    audio_q = queue.Queue()

    def callback(indata, frames, time_info, status):
        audio_q.put(bytes(indata))

    frames = []
    silence_ms = 0
    elapsed_ms = 0
    speech_started = False

    with sd.RawInputStream(
        samplerate=config.AUDIO_SAMPLE_RATE,
        blocksize=frame_samples,
        device=config.MIC_DEVICE_INDEX,
        dtype="int16",
        channels=config.AUDIO_CHANNELS,
        callback=callback,
    ):
        while elapsed_ms < max_ms:
            chunk = audio_q.get()
            frames.append(chunk)
            elapsed_ms += frame_ms

            is_speech = vad.is_speech(chunk, config.AUDIO_SAMPLE_RATE)
            if is_speech:
                speech_started = True
                silence_ms = 0
            elif speech_started:
                silence_ms += frame_ms
                if silence_ms >= config.VAD_SILENCE_MS:
                    break

    return b"".join(frames)


def play_pcm(audio_bytes: bytes, sample_rate: int):
    """
    16-bit PCM ses verisini hoparlörden çalar (Google TTS çıktısı için).

    ALSA/PortAudio çıkışı sd.play() çağrıldığı anda değil, donanım gerçekten
    veri akıtmaya başladığında "uyanıyor" - bu uyanma birkaç yüz milisaniye
    sürebiliyor ve o sürede gönderilen ilk örnekler kayboluyor. Sonuç: yanıtın
    ilk hecesi kesiliyor ("Tamam fırını açıyorum" -> "mam fırını açıyorum").

    Çözüm: sesin başına config.TTS_PLAYBACK_PADDING_MS kadar sessizlik
    ekliyoruz. Bu sessizlik çalınırken donanım gerçek sesi kaçırmadan
    akışa geçmiş oluyor. Jetson'da gerçek donanımla test ederken hâlâ
    kesilme oluyorsa bu değeri config.py'de artırın (ör. 400).
    """
    data = np.frombuffer(audio_bytes, dtype=np.int16)

    padding_ms = getattr(config, "TTS_PLAYBACK_PADDING_MS", 250)
    padding_samples = int(sample_rate * padding_ms / 1000)
    silence = np.zeros(padding_samples, dtype=np.int16)
    padded = np.concatenate([silence, data])

    # latency='high': PortAudio'ya daha büyük bir tampon ayırmasını söyler,
    # bu da donanımın devreye girme süresini padding ile birlikte tolere eder.
    sd.play(padded, samplerate=sample_rate, latency="high")
    sd.wait()
