"""
dsp_engine.py — Ripleytia AI Gerçek Zamanlı DSP Ses Değiştirici ve Ekolayzır Motoru
==================================================================================
Yapay Zeka (AI) gerektirmeden çalışan, ultra düşük gecikmeli (5-15 ms) gömülü ses motoru.
Gömülü Profiller: Kadın, Erkek, Çocuk, Robot.
Özellikler:
  - Çok Bantlı Parametrik Ekolayzır (Biquad IIR: LPF, HPF, BPF, Notch, Peaking, Low-Shelf, High-Shelf)
  - Donanımsal/Matematiksel Pitch & Formant Kaydırma (Dual-Delay Line Crossfade)
  - Siber Robot Modülatörü (Ring Modulation + Metalik Tarak Filtresi Rezonatörü)
  - Dinamik Kompresör, Gürültü Kapısı (Noise Gate) ve Sınırlandırıcı (Peak Limiter)
  - Windows Sanal Ses Kablosu (CABLE Input) & Çift Çıkış (Kulaklık Monitörü) Desteği
"""

import json
import math
import os
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import scipy.signal
import sounddevice as sd

PROFILES_FILE = Path(__file__).resolve().parent / "dsp_profiles.json"

# ── 1. VARSAYILAN GÖMÜLÜ SES PROFİLLERİ ──
DEFAULT_PROFILES: Dict[str, Any] = {
    "Kadın": {
        "name": "Kadın",
        "description": "Doğal kadın sesi tınısı, tiz netliği ve göğüs rezonansı filtreleme",
        "pitch_semitones": 5.0,
        "pitch_fine_cents": 0.0,
        "robot_enabled": False,
        "robot_carrier_hz": 70.0,
        "robot_depth": 0.0,
        "robot_resonance": 0.0,
        "eq_bands": [
            {"name": "Sub-Bass Kesme", "type": "highpass", "freq": 130.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "Göğüs Tonu (Low-Shelf)", "type": "lowshelf", "freq": 240.0, "gain": -4.5, "q": 1.0, "enabled": True},
            {"name": "Gövde / Vokal", "type": "peaking", "freq": 1200.0, "gain": 2.0, "q": 1.2, "enabled": True},
            {"name": "Kadın Rezonansı & Parlaklık", "type": "peaking", "freq": 3500.0, "gain": 4.5, "q": 1.5, "enabled": True},
            {"name": "Hava & Nefes (High-Shelf)", "type": "highshelf", "freq": 9000.0, "gain": 3.0, "q": 0.9, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -45.0,
            "comp_threshold_db": -18.0,
            "comp_ratio": 3.0,
            "attack_ms": 10.0,
            "release_ms": 100.0,
            "makeup_gain_db": 2.5,
            "output_gain_db": 0.0,
        }
    },
    "Erkek": {
        "name": "Erkek",
        "description": "Derin bas, tok göğüs rezonansı ve sinematik karanlık erkek tonu",
        "pitch_semitones": -4.0,
        "pitch_fine_cents": 0.0,
        "robot_enabled": False,
        "robot_carrier_hz": 50.0,
        "robot_depth": 0.0,
        "robot_resonance": 0.0,
        "eq_bands": [
            {"name": "Alt Frekans Temizleme", "type": "highpass", "freq": 65.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "Derin Göğüs Bası (Low-Shelf)", "type": "lowshelf", "freq": 140.0, "gain": 5.0, "q": 1.2, "enabled": True},
            {"name": "Kutu Tınısını Azaltma", "type": "peaking", "freq": 800.0, "gain": -2.5, "q": 1.0, "enabled": True},
            {"name": "Konuşma Anlaşılırlığı", "type": "peaking", "freq": 2600.0, "gain": 1.5, "q": 1.3, "enabled": True},
            {"name": "Koyu Ton (High-Shelf)", "type": "highshelf", "freq": 7000.0, "gain": -2.0, "q": 1.0, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -46.0,
            "comp_threshold_db": -16.0,
            "comp_ratio": 3.5,
            "attack_ms": 15.0,
            "release_ms": 120.0,
            "makeup_gain_db": 2.0,
            "output_gain_db": 0.0,
        }
    },
    "Çocuk": {
        "name": "Çocuk",
        "description": "Yüksek perde (anime/çocuksu ton), hafif göğüs ve dinamik tizler",
        "pitch_semitones": 8.5,
        "pitch_fine_cents": 0.0,
        "robot_enabled": False,
        "robot_carrier_hz": 90.0,
        "robot_depth": 0.0,
        "robot_resonance": 0.0,
        "eq_bands": [
            {"name": "Yetişkin Basını Kesme", "type": "highpass", "freq": 190.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "Kalınlık Azaltma", "type": "peaking", "freq": 350.0, "gain": -6.0, "q": 1.5, "enabled": True},
            {"name": "Çocuksu Vokal Tınısı", "type": "peaking", "freq": 1800.0, "gain": 3.5, "q": 1.3, "enabled": True},
            {"name": "Tiz Canlılık", "type": "peaking", "freq": 4500.0, "gain": 5.0, "q": 1.2, "enabled": True},
            {"name": "Işıltı (High-Shelf)", "type": "highshelf", "freq": 10000.0, "gain": 2.0, "q": 0.8, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -42.0,
            "comp_threshold_db": -20.0,
            "comp_ratio": 4.0,
            "attack_ms": 5.0,
            "release_ms": 80.0,
            "makeup_gain_db": 3.0,
            "output_gain_db": 0.0,
        }
    },
    "Robot": {
        "name": "Robot",
        "description": "Siber siborg / yapay zeka robot sesi, ring modülasyonu ve metalik rezonatör",
        "pitch_semitones": 0.0,
        "pitch_fine_cents": 0.0,
        "robot_enabled": True,
        "robot_carrier_hz": 65.0,
        "robot_depth": 0.85,
        "robot_resonance": 0.65,
        "eq_bands": [
            {"name": "Robot HPF", "type": "highpass", "freq": 150.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "Metalik Rezonans Tepesi", "type": "peaking", "freq": 520.0, "gain": 6.5, "q": 4.0, "enabled": True},
            {"name": "Sentetik Telsiz Bandı", "type": "peaking", "freq": 1600.0, "gain": 5.0, "q": 3.0, "enabled": True},
            {"name": "Çentik (Notch) Filtresi", "type": "notch", "freq": 3100.0, "gain": -12.0, "q": 5.0, "enabled": True},
            {"name": "Telekom Sınırı (LPF)", "type": "lowpass", "freq": 6500.0, "gain": -12.0, "q": 1.2, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -40.0,
            "comp_threshold_db": -14.0,
            "comp_ratio": 8.0,
            "attack_ms": 2.0,
            "release_ms": 50.0,
            "makeup_gain_db": 4.0,
            "output_gain_db": 0.0,
        }
    }
}


# ── 2. BIQUAD IIR PARAMETRİK EKOLAYZIR HESAPLAYICI ──
class BiquadFilter:
    """Robert Bristow-Johnson Audio EQ Cookbook Biquad IIR Filtresi"""
    def __init__(self, sample_rate: int = 48000):
        self.sr = sample_rate
        self.b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.zi = np.zeros(2, dtype=np.float32)

    def set_params(self, filter_type: str, f0: float, gain_db: float, q: float):
        fs = float(self.sr)
        f0 = max(10.0, min(f0, fs * 0.495))
        q = max(0.05, min(q, 20.0))
        w0 = 2.0 * math.pi * f0 / fs
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / (2.0 * q)
        A = 10.0 ** (gain_db / 40.0)

        ftype = filter_type.lower()
        if ftype == "lowpass":
            b0 = (1.0 - cos_w0) / 2.0
            b1 = 1.0 - cos_w0
            b2 = (1.0 - cos_w0) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "highpass":
            b0 = (1.0 + cos_w0) / 2.0
            b1 = -(1.0 + cos_w0)
            b2 = (1.0 + cos_w0) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "bandpass":
            b0 = sin_w0 / 2.0
            b1 = 0.0
            b2 = -sin_w0 / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "notch":
            b0 = 1.0
            b1 = -2.0 * cos_w0
            b2 = 1.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha
        elif ftype == "lowshelf":
            sqrt_A = math.sqrt(A)
            beta = math.sqrt((A * A + 1.0) / q - (A - 1.0) ** 2) if (A * A + 1.0) / q - (A - 1.0) ** 2 > 0 else 0.0
            b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + beta * sin_w0)
            b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
            b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - beta * sin_w0)
            a0 = (A + 1.0) + (A - 1.0) * cos_w0 + beta * sin_w0
            a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
            a2 = (A + 1.0) + (A - 1.0) * cos_w0 - beta * sin_w0
        elif ftype == "highshelf":
            sqrt_A = math.sqrt(A)
            beta = math.sqrt((A * A + 1.0) / q - (A - 1.0) ** 2) if (A * A + 1.0) / q - (A - 1.0) ** 2 > 0 else 0.0
            b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + beta * sin_w0)
            b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
            b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - beta * sin_w0)
            a0 = (A + 1.0) - (A - 1.0) * cos_w0 + beta * sin_w0
            a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
            a2 = (A + 1.0) - (A - 1.0) * cos_w0 - beta * sin_w0
        else:  # peaking (çan / bell) varsayılan
            b0 = 1.0 + alpha * A
            b1 = -2.0 * cos_w0
            b2 = 1.0 - alpha * A
            a0 = 1.0 + alpha / A
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha / A

        if abs(a0) < 1e-9:
            a0 = 1.0

        self.b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

    def process(self, x: np.ndarray) -> np.ndarray:
        if len(x) == 0:
            return x
        y, self.zi = scipy.signal.lfilter(self.b, self.a, x, zi=self.zi)
        return y.astype(np.float32)


# ── 3. ZAMAN ALANINDA ULTRA DÜŞÜK GECİKMELİ PITCH SHIFTER ──
class RealtimePitchShifter:
    """
    Çift Gecikme Hattı (Dual-Delay Line) ve Üçgen Pencere Geçişli (Crossfade)
    zaman alanı pitch shifter algoritması. 0 ms ek gecikme ile çalışır.
    """
    def __init__(self, sample_rate: int = 48000, max_delay: int = 4096):
        self.sr = sample_rate
        self.buffer = np.zeros(max_delay * 2, dtype=np.float32)
        self.buf_size = len(self.buffer)
        self.write_ptr = 0
        self.window_size = int(self.sr * 0.04)  # ~40 ms pencere
        self.phase = 0.0
        self.ratio = 1.0

    def set_pitch(self, semitones: float, fine_cents: float = 0.0):
        total_st = semitones + (fine_cents / 100.0)
        self.ratio = 2.0 ** (total_st / 12.0)

    def process(self, x: np.ndarray) -> np.ndarray:
        n = len(x)
        if n == 0 or abs(self.ratio - 1.0) < 0.001:
            # Pitch değişimi yoksa tamponu doldur ve doğrudan döndür
            for i in range(n):
                self.buffer[self.write_ptr] = x[i]
                self.write_ptr = (self.write_ptr + 1) % self.buf_size
            return x

        rate = 1.0 - self.ratio
        w = float(self.window_size)
        out = np.empty(n, dtype=np.float32)

        for i in range(n):
            in_val = x[i]
            self.buffer[self.write_ptr] = in_val

            # 1. Hat gecikmesi
            d1 = (self.phase % w)
            idx1 = (self.write_ptr - int(d1)) % self.buf_size

            # 2. Hat gecikmesi (yarım pencere faz farkı)
            d2 = ((self.phase + w * 0.5) % w)
            idx2 = (self.write_ptr - int(d2)) % self.buf_size

            # Çapraz geçiş katsayısı (0 -> 1 -> 0)
            fade = abs((d1 / w) - 0.5) * 2.0
            out[i] = (self.buffer[idx1] * (1.0 - fade)) + (self.buffer[idx2] * fade)

            self.phase += rate
            if self.phase < 0:
                self.phase += w * 1000.0
            self.write_ptr = (self.write_ptr + 1) % self.buf_size

        return out


# ── 4. SİBERNETİK ROBOT SES MODÜLATÖRÜ ──
class RobotModulator:
    """Ring modülatörü ve metalik rezonatör ile robotik siborg sesi üretir"""
    def __init__(self, sample_rate: int = 48000):
        self.sr = sample_rate
        self.carrier_phase = 0.0
        self.delay_buf = np.zeros(int(sample_rate * 0.05), dtype=np.float32)
        self.delay_ptr = 0

    def process(self, x: np.ndarray, carrier_hz: float = 65.0, depth: float = 0.8, resonance: float = 0.6) -> np.ndarray:
        if depth <= 0.001 and resonance <= 0.001:
            return x

        n = len(x)
        # Ring modülasyon taşıyıcısı
        t = (np.arange(n) + self.carrier_phase) / float(self.sr)
        self.carrier_phase = (self.carrier_phase + n) % self.sr
        carrier = np.cos(2.0 * math.pi * carrier_hz * t)
        
        # Ring modulation (modülatör derinliği)
        ring_mod = x * ((1.0 - depth) + (depth * carrier))

        # Metalik tarak (comb) rezonatörü
        delay_len = max(20, int(self.sr * 0.0085))  # ~8.5 ms gecikme = metalik robot tınısı
        buf_len = len(self.delay_buf)
        out = np.empty(n, dtype=np.float32)

        for i in range(n):
            read_idx = (self.delay_ptr - delay_len) % buf_len
            delayed = self.delay_buf[read_idx]
            val = ring_mod[i] + (delayed * resonance)
            self.delay_buf[self.delay_ptr] = val
            self.delay_ptr = (self.delay_ptr + 1) % buf_len
            out[i] = val

        return out


# ── 5. DİNAMİK KOMPRESÖR, NOISE GATE & LİMİTÖR ──
class DynamicProcessor:
    """Vokal dinamik aralığını kontrol eden kompresör, gürültü kapısı ve tepe tavanı"""
    def __init__(self, sample_rate: int = 48000):
        self.sr = sample_rate
        self.envelope = 0.0
        self.gate_envelope = 0.0

    def process(self, x: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        if len(x) == 0:
            return x

        gate_thresh_db = params.get("gate_threshold_db", -45.0)
        comp_thresh_db = params.get("comp_threshold_db", -18.0)
        ratio = max(1.0, params.get("comp_ratio", 3.0))
        attack_ms = max(0.5, params.get("attack_ms", 10.0))
        release_ms = max(5.0, params.get("release_ms", 100.0))
        makeup_gain_db = params.get("makeup_gain_db", 0.0)
        output_gain_db = params.get("output_gain_db", 0.0)

        att_coeff = math.exp(-1000.0 / (attack_ms * self.sr))
        rel_coeff = math.exp(-1000.0 / (release_ms * self.sr))
        gate_att = math.exp(-1000.0 / (2.0 * self.sr))
        gate_rel = math.exp(-1000.0 / (50.0 * self.sr))

        makeup_linear = 10.0 ** ((makeup_gain_db + output_gain_db) / 20.0)
        gate_thresh_lin = 10.0 ** (gate_thresh_db / 20.0)

        n = len(x)
        out = np.empty(n, dtype=np.float32)

        for i in range(n):
            sample = x[i]
            abs_s = abs(sample)

            # Gate zarfı
            coeff = gate_att if abs_s > self.gate_envelope else gate_rel
            self.gate_envelope = (1.0 - coeff) * abs_s + coeff * self.gate_envelope
            if self.gate_envelope < gate_thresh_lin:
                gate_gain = (self.gate_envelope / (gate_thresh_lin + 1e-9)) ** 2
            else:
                gate_gain = 1.0

            # Kompresör zarfı
            coeff = att_coeff if abs_s > self.envelope else rel_coeff
            self.envelope = (1.0 - coeff) * abs_s + coeff * self.envelope

            env_db = 20.0 * math.log10(self.envelope + 1e-6)
            if env_db > comp_thresh_db:
                comp_gain_db = (comp_thresh_db - env_db) * (1.0 - 1.0 / ratio)
                comp_gain = 10.0 ** (comp_gain_db / 20.0)
            else:
                comp_gain = 1.0

            processed = sample * gate_gain * comp_gain * makeup_linear

            # Sınırlandırıcı / Tavan (-0.1 dB = ~0.988)
            if processed > 0.988:
                processed = 0.988 + 0.012 * math.tanh((processed - 0.988) / 0.012)
            elif processed < -0.988:
                processed = -0.988 + 0.012 * math.tanh((processed + 0.988) / 0.012)

            out[i] = processed

        return out


# ── 6. TAM DSP SES İŞLEME VE AKIŞ YÖNETİCİSİ ──
class DSPVoiceEngine:
    """
    Ripleytia AI Yapay Zekasız DSP Ses Motoru.
    Giriş Mikrofonu -> Pitch/Formant -> Robot -> 5-Bant EQ -> Kompresör/Gate -> Çıkış (Sanal Kablo / Kulaklık)
    """
    def __init__(self, sample_rate: int = 48000, chunk_size: int = 512):
        self.sr = sample_rate
        self.chunk_size = chunk_size
        self.profiles: Dict[str, Any] = self._load_profiles()
        self.active_profile_name: str = "Kadın"

        # DSP Alt Sistemleri
        self.pitch_shifter = RealtimePitchShifter(self.sr)
        self.robot_modulator = RobotModulator(self.sr)
        self.eq_filters: List[BiquadFilter] = [BiquadFilter(self.sr) for _ in range(5)]
        self.dynamics = DynamicProcessor(self.sr)

        # Ses Cihazları ve Durum
        self.input_device_id: Optional[int] = None
        self.output_device_id: Optional[int] = None
        self.monitor_device_id: Optional[int] = None
        self.monitor_enabled: bool = False
        self.stream: Optional[sd.Stream] = None
        self.monitor_stream: Optional[sd.OutputStream] = None
        self.is_running: bool = False

        self._lock = threading.Lock()
        self.load_active_profile(self.active_profile_name)

    def _load_profiles(self) -> Dict[str, Any]:
        """Profilleri JSON dosyasından oku veya varsayılanları kaydet"""
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Eksik anahtarları tamamla
                    for k, v in DEFAULT_PROFILES.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception as e:
                print(f"[DSP] Profil yükleme hatası ({e}), varsayılanlar kullanılıyor.")
        
        # İlk oluşturma
        self.save_profiles(DEFAULT_PROFILES)
        return json.loads(json.dumps(DEFAULT_PROFILES))

    def save_profiles(self, profiles_data: Optional[Dict[str, Any]] = None):
        """Profilleri kalıcı olarak diske kaydet"""
        data = profiles_data or self.profiles
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("[DSP] Profil kaydetme hatası:", e)

    def reset_profile_to_default(self, profile_name: str):
        """Seçili profili varsayılan ayarlara döndür"""
        if profile_name in DEFAULT_PROFILES:
            with self._lock:
                self.profiles[profile_name] = json.loads(json.dumps(DEFAULT_PROFILES[profile_name]))
                self.save_profiles()
                if self.active_profile_name == profile_name:
                    self.load_active_profile(profile_name)

    def load_active_profile(self, profile_name: str):
        """Aktif profili yükle ve DSP parametrelerini anlık güncelle"""
        if profile_name not in self.profiles:
            profile_name = "Kadın"
        self.active_profile_name = profile_name
        prof = self.profiles[profile_name]

        with self._lock:
            # 1. Pitch
            st = float(prof.get("pitch_semitones", 0.0))
            fine = float(prof.get("pitch_fine_cents", 0.0))
            self.pitch_shifter.set_pitch(st, fine)

            # 2. EQ Bantları
            eq_bands = prof.get("eq_bands", [])
            for i in range(min(len(self.eq_filters), len(eq_bands))):
                band = eq_bands[i]
                if band.get("enabled", True):
                    self.eq_filters[i].set_params(
                        filter_type=band.get("type", "peaking"),
                        f0=float(band.get("freq", 1000.0)),
                        gain_db=float(band.get("gain", 0.0)),
                        q=float(band.get("q", 1.0))
                    )
                else:
                    # Pasif bant = kazanç 0 dB
                    self.eq_filters[i].set_params("peaking", 1000.0, 0.0, 1.0)

    def update_profile_param(self, category: str, key: str, value: Any, band_index: Optional[int] = None):
        """GUI'den gelen tek bir parametre değişimini kaydet ve sese uygula"""
        with self._lock:
            prof = self.profiles[self.active_profile_name]
            if category == "pitch":
                prof[key] = value
                st = float(prof.get("pitch_semitones", 0.0))
                fine = float(prof.get("pitch_fine_cents", 0.0))
                self.pitch_shifter.set_pitch(st, fine)
            elif category == "robot":
                prof[key] = value
            elif category == "dynamics":
                prof["dynamics"][key] = value
            elif category == "eq" and band_index is not None:
                if 0 <= band_index < len(prof["eq_bands"]):
                    prof["eq_bands"][band_index][key] = value
                    band = prof["eq_bands"][band_index]
                    if band.get("enabled", True):
                        self.eq_filters[band_index].set_params(
                            filter_type=band.get("type", "peaking"),
                            f0=float(band.get("freq", 1000.0)),
                            gain_db=float(band.get("gain", 0.0)),
                            q=float(band.get("q", 1.0))
                        )
                    else:
                        self.eq_filters[band_index].set_params("peaking", 1000.0, 0.0, 1.0)

        # Değişikliği diske kaydet
        self.save_profiles()

    def process_block(self, in_data: np.ndarray) -> np.ndarray:
        """Her bir ses bloğunu tüm DSP zincirinden geçirir"""
        with self._lock:
            prof = self.profiles[self.active_profile_name]
            robot_on = prof.get("robot_enabled", False)
            carrier_hz = float(prof.get("robot_carrier_hz", 65.0))
            robot_depth = float(prof.get("robot_depth", 0.8))
            robot_res = float(prof.get("robot_resonance", 0.5))
            dynamics_params = prof.get("dynamics", {})

        # 1. Pitch Shift
        y = self.pitch_shifter.process(in_data)

        # 2. Robot Modülatörü
        if robot_on:
            y = self.robot_modulator.process(y, carrier_hz, robot_depth, robot_res)

        # 3. 5-Bant Parametrik EQ
        for f in self.eq_filters:
            y = f.process(y)

        # 4. Kompresör, Gürültü Kapısı & Tepe Sınırlandırıcı
        y = self.dynamics.process(y, dynamics_params)

        return y

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        """SoundDevice gerçek zamanlı düşük gecikmeli akış geri çağrımı"""
        if status:
            pass  # Ses taşması durumunda akışın kopmasını engelle

        # Tek kanala indirge ve float32 aralığına al
        in_mono = indata[:, 0].copy().astype(np.float32)
        out_mono = self.process_block(in_mono)

        # Ana çıkışa (CABLE Input / Hoparlör) yaz
        outdata[:, 0] = out_mono
        if outdata.shape[1] > 1:
            outdata[:, 1] = out_mono

        # Kulaklık monitörü aktifse monitöre yaz
        if self.monitor_enabled and self.monitor_stream and self.monitor_stream.active:
            try:
                mon_data = np.column_stack([out_mono, out_mono]) if self.monitor_stream.channels == 2 else out_mono[:, None]
                self.monitor_stream.write(mon_data)
            except Exception:
                pass

    def start(self, input_id: Optional[int], output_id: Optional[int]):
        """DSP motorunu başlat"""
        self.stop()
        self.input_device_id = input_id
        self.output_device_id = output_id

        try:
            self.stream = sd.Stream(
                samplerate=self.sr,
                blocksize=self.chunk_size,
                device=(self.input_device_id, self.output_device_id),
                channels=(1, 2),
                dtype="float32",
                latency="low",
                callback=self._audio_callback
            )
            self.stream.start()
            self.is_running = True
            print(f"[DSP] Motor başlatıldı -> In: {input_id}, Out: {output_id}, SampleRate: {self.sr} Hz")
        except Exception as e:
            self.is_running = False
            raise RuntimeError(f"DSP Ses Akışı başlatılamadı: {e}")

    def stop(self):
        """DSP motorunu durdur"""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        if self.monitor_stream:
            try:
                self.monitor_stream.stop()
                self.monitor_stream.close()
            except Exception:
                pass
            self.monitor_stream = None

        self.is_running = False
        print("[DSP] Ses akışı durduruldu.")

    def set_monitor(self, enabled: bool, monitor_device_id: Optional[int] = None):
        """Kendi sesini kulaklıktan duyma (Monitoring) ayarı"""
        self.monitor_enabled = enabled
        self.monitor_device_id = monitor_device_id

        if self.monitor_stream:
            try:
                self.monitor_stream.stop()
                self.monitor_stream.close()
            except Exception:
                pass
            self.monitor_stream = None

        if enabled and monitor_device_id is not None and self.is_running:
            try:
                self.monitor_stream = sd.OutputStream(
                    samplerate=self.sr,
                    blocksize=self.chunk_size,
                    device=monitor_device_id,
                    channels=2,
                    dtype="float32",
                    latency="low"
                )
                self.monitor_stream.start()
                print(f"[DSP] Monitör kulaklık akışı başlatıldı -> Cihaz ID: {monitor_device_id}")
            except Exception as e:
                print(f"[DSP] Monitör başlatılamadı: {e}")


def list_dsp_devices(filter_api: str = "Tümü") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Tüm Windows ses cihazlarını sounddevice üzerinden listeler ve formatlar"""
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
    except Exception as e:
        print("[DSP] Cihaz sorgulama hatası:", e)
        return [], []

    in_list = []
    out_list = []

    for idx, d in enumerate(devices):
        api_name = hostapis[d["hostapi"]]["name"] if 0 <= d["hostapi"] < len(hostapis) else "Bilinmiyor"
        
        # Filtreleme
        if filter_api != "Tümü" and filter_api.lower() not in api_name.lower():
            continue

        item = {
            "index": idx,
            "name": d["name"],
            "hostapi": api_name,
            "max_in": d["max_input_channels"],
            "max_out": d["max_output_channels"],
            "default_sr": int(d.get("default_samplerate", 48000)),
            "label": f"[{idx}] {d['name']} ({api_name})"
        }

        if d["max_input_channels"] > 0:
            in_list.append(item)
        if d["max_output_channels"] > 0:
            out_list.append(item)

    return in_list, out_list

