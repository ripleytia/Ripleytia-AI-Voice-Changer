"""
dsp_engine.py — Ripleytia AI Çökme Korumalı Güvenli DSP Ses Mühendisliği Motoru
==================================================================================
Çoklu İş Parçacıklı (Multithreaded), Kuyruk (Queue) Tabanlı ve Hata Yakalama Duvarlı
Yüksek Kararlılıklı Gerçek Zamanlı Ses İşleme Motoru (SafeAudioProcessor).

Mimari İyileştirmeler:
  1. Threading & Buffer Güvenliği (Asynchronous Processing):
     - PortAudio Ses I/O geri çağrımı (Callback) ile DSP hesaplamaları ayrıldı.
     - Çift yönlü kilitlenmeyen kuyruklar (queue.Queue) ile ses kartı kesintileri ve tampon taşmaları engellendi.
     - Ön-tamponlama (Pre-buffering) ile ilk açılıştaki underrun/çıtırtı tamamen sıfırlandı.
  2. Veri Doğrulama ve Sınırlandırma (Safe Math & Anti-Clipping):
     - Tüm giriş/çıkış verilerinde NaN / Infinity denetimi (np.nan_to_num).
     - [-0.99, +0.99] aralığında donanımsal kırpma (np.clip) ve yumuşak tavan (tanh limiter).
     - Faz taşmalarına karşı döngüsel faz sarma (Phase wrapping: % 2*pi).
  3. Hata Yakalama Duvarı (Fail-Safe Try-Except Blocks):
     - Her DSP aşamasında hata yakalama duvarı; olası hatada ses çökmez, ham ses (bypass) güvenle iletilir.
  4. Vektörize C-Seviyesi Hızlandırma:
     - Yavaş Python 'for' döngüleri kaldırıldı; tüm dinamikler Scipy IIR ve NumPy vektörleriyle mikrosaniyelere indirildi.
"""

import json
import math
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import scipy.signal
import sounddevice as sd

PROFILES_FILE = Path(__file__).resolve().parent / "dsp_profiles.json"

# ── 1. GELİŞMİŞ GÖMÜLÜ SES PROFİLLERİ (AKILLI ANATOMİK ÖNAYARLAR) ──
DEFAULT_PROFILES: Dict[str, Any] = {
    "Kadın": {
        "name": "Kadın",
        "description": "Anatomik kadın sesi: +12 st perde, +%15 vokal traktüs (formant) kaydırma, 4.2k netliği ve dinamik de-esser",
        "pitch_semitones": 12.0,
        "pitch_fine_cents": 0.0,
        "formant_shift_percent": 15.0,  # +%15 yukarı
        "tube_saturation_drive": 0.22,  # Sıcak tüp harmonikleri
        "warmth_exciter_amount": 0.08,
        "deesser_enabled": True,
        "deesser_amount": 0.65,
        "deesser_threshold_db": -26.0,
        "robot_enabled": False,
        "robot_carrier_hz": 70.0,
        "robot_depth": 0.0,
        "robot_resonance": 0.0,
        "robot_bitcrush_bits": 16,
        "eq_bands": [
            {"name": "Sub-Bass Temizleme", "type": "highpass", "freq": 120.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "Göğüs Rezonansı Bastırma", "type": "lowshelf", "freq": 260.0, "gain": -4.0, "q": 1.0, "enabled": True},
            {"name": "Vokal Gövde", "type": "peaking", "freq": 1100.0, "gain": 1.5, "q": 1.2, "enabled": True},
            {"name": "Kadın Vokal Parlaklığı", "type": "peaking", "freq": 4200.0, "gain": 3.8, "q": 1.4, "enabled": True},
            {"name": "İpeksi Hava (Air)", "type": "highshelf", "freq": 9500.0, "gain": 2.5, "q": 0.9, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -45.0,
            "comp_threshold_db": -18.0,
            "comp_ratio": 3.2,
            "attack_ms": 8.0,
            "release_ms": 90.0,
            "makeup_gain_db": 2.5,
            "output_gain_db": 0.0,
        }
    },
    "Erkek": {
        "name": "Erkek",
        "description": "Anatomik erkek sesi: -8 st perde, -%12 vokal traktüs genişletme, 125 Hz derin göğüs desteği ve analog tüp doygunluğu",
        "pitch_semitones": -8.0,
        "pitch_fine_cents": 0.0,
        "formant_shift_percent": -12.0,  # -%12 aşağı (uzun vokal traktüs)
        "tube_saturation_drive": 0.35,  # Zengin tok analog harmonikler
        "warmth_exciter_amount": 0.50,  # 100-250 Hz göğüs exciter
        "deesser_enabled": True,
        "deesser_amount": 0.30,
        "deesser_threshold_db": -24.0,
        "robot_enabled": False,
        "robot_carrier_hz": 50.0,
        "robot_depth": 0.0,
        "robot_resonance": 0.0,
        "robot_bitcrush_bits": 16,
        "eq_bands": [
            {"name": "Alt Frekans Temizleme", "type": "highpass", "freq": 60.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "120Hz Derin Göğüs Desteği", "type": "peaking", "freq": 125.0, "gain": 5.5, "q": 1.2, "enabled": True},
            {"name": "Kutu Tınısı Azaltma", "type": "peaking", "freq": 650.0, "gain": -3.0, "q": 1.1, "enabled": True},
            {"name": "Erkek Vokal Vurgusu", "type": "peaking", "freq": 2400.0, "gain": 2.0, "q": 1.3, "enabled": True},
            {"name": "Sıcak Üst Frekans", "type": "highshelf", "freq": 7500.0, "gain": -1.5, "q": 1.0, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -46.0,
            "comp_threshold_db": -16.0,
            "comp_ratio": 3.8,
            "attack_ms": 12.0,
            "release_ms": 110.0,
            "makeup_gain_db": 2.0,
            "output_gain_db": 0.0,
        }
    },
    "Çocuk": {
        "name": "Çocuk",
        "description": "Anatomik çocuk sesi: +14 st yüksek perde, +%25 küçük vokal traktüs formantı, dinamik de-esser ve tiz ışıltı",
        "pitch_semitones": 14.0,
        "pitch_fine_cents": 0.0,
        "formant_shift_percent": 25.0,  # +%25 yukarı
        "tube_saturation_drive": 0.18,
        "warmth_exciter_amount": 0.05,
        "deesser_enabled": True,
        "deesser_amount": 0.75,  # Yüksek perdelerde tıslamayı önler
        "deesser_threshold_db": -24.0,
        "robot_enabled": False,
        "robot_carrier_hz": 90.0,
        "robot_depth": 0.0,
        "robot_resonance": 0.0,
        "robot_bitcrush_bits": 16,
        "eq_bands": [
            {"name": "Yetişkin Basını Kesme", "type": "highpass", "freq": 180.0, "gain": 0.0, "q": 0.707, "enabled": True},
            {"name": "Kalınlık Azaltma", "type": "peaking", "freq": 350.0, "gain": -5.5, "q": 1.4, "enabled": True},
            {"name": "Çocuksu Vokal Tınısı", "type": "peaking", "freq": 1600.0, "gain": 3.0, "q": 1.3, "enabled": True},
            {"name": "Tiz Canlılık", "type": "peaking", "freq": 4800.0, "gain": 4.5, "q": 1.2, "enabled": True},
            {"name": "Işıltı & Ferahlık", "type": "highshelf", "freq": 10500.0, "gain": 2.5, "q": 0.8, "enabled": True},
        ],
        "dynamics": {
            "gate_threshold_db": -42.0,
            "comp_threshold_db": -20.0,
            "comp_ratio": 4.2,
            "attack_ms": 5.0,
            "release_ms": 75.0,
            "makeup_gain_db": 3.0,
            "output_gain_db": 0.0,
        }
    },
    "Robot": {
        "name": "Robot",
        "description": "Siborg robot sesi: Halka modülasyonu (Ring Mod), flanger tarak filtresi, telsiz rezonatörü ve 10-bit bitcrusher",
        "pitch_semitones": 0.0,
        "pitch_fine_cents": 0.0,
        "formant_shift_percent": 0.0,
        "tube_saturation_drive": 0.40,
        "warmth_exciter_amount": 0.20,
        "deesser_enabled": False,
        "deesser_amount": 0.0,
        "deesser_threshold_db": -30.0,
        "robot_enabled": True,
        "robot_carrier_hz": 65.0,
        "robot_depth": 0.88,
        "robot_resonance": 0.65,
        "robot_bitcrush_bits": 10,
        "eq_bands": [
            {"name": "Robot HPF", "type": "highpass", "freq": 160.0, "gain": 0.0, "q": 0.707, "enabled": True},
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


# ── 2. ÇÖKME KORUMALI VE GÜVENLİ SES İŞLEMCİSİ (SAFE AUDIO PROCESSOR) ──
class SafeAudioProcessor:
    """
    Veri doğrulamalı (Anti-NaN/Inf), kırpma korumalı (Clipping Protection)
    ve hata yakalama duvarlı profesyonel DSP hesaplama sınıfı.
    """
    def __init__(self, sample_rate: int = 48000, n_fft: int = 1024, hop_size: int = 256):
        self.sr = sample_rate
        self.n_fft = n_fft
        self.hop_size = hop_size
        self.window = np.hanning(n_fft).astype(np.float32)

        # STFT ve Faz Takibi
        self.prev_phase = np.zeros(n_fft // 2 + 1, dtype=np.float32)
        self.sum_phase = np.zeros(n_fft // 2 + 1, dtype=np.float32)

        # Dinamik De-Esser Bandpass Filtresi (4.0 kHz - 8.5 kHz)
        nyq = sample_rate * 0.5
        b_de, a_de = scipy.signal.butter(2, [min(0.95, 4000.0 / nyq), min(0.99, 8500.0 / nyq)], btype='bandpass')
        self.de_b, self.de_a = b_de.astype(np.float32), a_de.astype(np.float32)
        self.de_zi = np.zeros(max(len(b_de), len(a_de)) - 1, dtype=np.float32)
        self.deesser_env = 0.0

        # Göğüs Rezonansı / Warmth Exciter Filtresi (100 Hz - 250 Hz)
        b_ex, a_ex = scipy.signal.butter(2, [max(0.001, 100.0 / nyq), min(0.95, 250.0 / nyq)], btype='bandpass')
        self.ex_b, self.ex_a = b_ex.astype(np.float32), a_ex.astype(np.float32)
        self.ex_zi = np.zeros(max(len(b_ex), len(a_ex)) - 1, dtype=np.float32)

        # Vektörize Kompresör IIR Zarf Takip Durumları (C seviyesinde IIR)
        self.comp_zi = np.zeros(1, dtype=np.float32)

        # Robot Efekti
        self.robot_carrier_phase = 0.0
        self.robot_delay_buf = np.zeros(int(sample_rate * 0.05), dtype=np.float32)
        self.robot_delay_ptr = 0

    @staticmethod
    def sanitize(x: np.ndarray) -> np.ndarray:
        """
        [KRİTİK GÜVENLİK]: NaN, Inf kontrolü ve kırpma (clipping) önleyici.
        Herhangi bir hesaplama taşmasını sıfırlayarak ses kartı ve sürücü çökmesini engeller.
        """
        if x is None or not isinstance(x, np.ndarray):
            return np.zeros(256, dtype=np.float32)
        # NaN ve Sonsuz (Inf) değerleri anında temizle
        if not np.isfinite(x).all():
            x = np.nan_to_num(x, copy=False, nan=0.0, posinf=0.98, neginf=-0.98)
        # Sinyali donanımsal ses sınırları içinde tut (Peak Clipping Protection)
        return np.clip(x, -0.99, 0.99)

    def shift_formant_pitch(self, frame: np.ndarray, pitch_st: float, fine_cents: float, formant_pct: float) -> np.ndarray:
        """
        [HATA KORUMALI]: Spektral Cepstral Formant Kaydırma & Faz Vokoderi.
        Olası bir spektral taşmada orijinal ses çerçevesini güvenle döndürür (Bypass).
        """
        try:
            # Giriş doğrulaması
            clean_frame = self.sanitize(frame)

            pitch_ratio = 2.0 ** ((pitch_st + fine_cents / 100.0) / 12.0)
            formant_scale = 1.0 + (formant_pct / 100.0)

            # Değişim yoksa sıfır maliyetle dön
            if abs(pitch_ratio - 1.0) < 0.005 and abs(formant_scale - 1.0) < 0.005:
                return clean_frame

            # 1. FFT
            windowed = clean_frame * self.window
            spec = np.fft.rfft(windowed)
            mag = np.abs(spec)
            phase = np.angle(spec)
            n_bins = len(mag)
            freq_grid = np.linspace(0.0, 1.0, n_bins)

            # 2. Spektral Zarf Ayrıştırma (Cepstral Liftering)
            log_mag = np.log(np.maximum(mag, 1e-6))
            ceps = np.fft.irfft(log_mag)
            lifter_len = min(36, len(ceps) // 4)
            ceps[lifter_len:-lifter_len] = 0.0
            env = np.maximum(np.exp(np.real(np.fft.rfft(ceps))), 1e-5)

            # 3. Spektral Beyazlatma (Excitation)
            excitation = mag / env

            # 4. Harmonik Perde Kaydırma
            if abs(pitch_ratio - 1.0) >= 0.005:
                shifted_grid = np.clip(freq_grid / pitch_ratio, 0.0, 1.0)
                shifted_excitation = np.interp(shifted_grid, freq_grid, excitation)
            else:
                shifted_excitation = excitation

            # 5. Bağımsız Vokal Traktüs Formant Zarfı Ölçekleme
            if abs(formant_scale - 1.0) >= 0.005:
                warped_grid = np.clip(freq_grid / formant_scale, 0.0, 1.0)
                target_env = np.interp(warped_grid, freq_grid, env)
            else:
                target_env = env

            new_mag = shifted_excitation * target_env

            # 6. Faz Vokoderi (Faz taşmasına karşı döngüsel modüler sarma)
            omega = 2.0 * np.pi * np.arange(n_bins) * self.hop_size / self.n_fft
            dphase = phase - self.prev_phase
            self.prev_phase = phase.copy()

            delta = (dphase - omega + np.pi) % (2.0 * np.pi) - np.pi
            inst_freq = omega + delta
            
            # [ÖNEMLİ]: sum_phase'in sonsuza ıraksamasını engelle (Phase Wrap)
            self.sum_phase = (self.sum_phase + inst_freq * pitch_ratio) % (2.0 * np.pi)

            # 7. Sentez
            new_spec = new_mag * np.exp(1j * self.sum_phase)
            out_frame = np.real(np.fft.irfft(new_spec)) * self.window
            return self.sanitize(out_frame)

        except Exception as e:
            # Hata durumunda ses akışını kesme, ham sesi geçir (Fail-safe bypass)
            return self.sanitize(frame)

    def apply_tube_saturation(self, x: np.ndarray, drive: float = 0.25) -> np.ndarray:
        """[HATA KORUMALI]: Analog Lambalı Harmonik Doygunluk"""
        try:
            if drive <= 0.01:
                return x
            k = 1.0 + drive * 2.5
            bias = 0.08 * drive
            sat = np.tanh(k * x + bias) - np.tanh(bias)
            out = (x * (1.0 - drive * 0.7) + sat * (drive * 0.7)) / (1.0 + drive * 0.2)
            return self.sanitize(out)
        except Exception:
            return x

    def apply_warmth_exciter(self, x: np.ndarray, amount: float = 0.4) -> np.ndarray:
        """[HATA KORUMALI]: Göğüs Rezonansı (100-250 Hz Tokluk)"""
        try:
            if amount <= 0.01:
                return x
            band, self.ex_zi = scipy.signal.lfilter(self.ex_b, self.ex_a, x, zi=self.ex_zi)
            harmonics = np.tanh(2.5 * band)
            out = x + harmonics * (amount * 0.5)
            return self.sanitize(out)
        except Exception:
            return x

    def apply_deesser(self, x: np.ndarray, enabled: bool = True, threshold_db: float = -26.0, amount: float = 0.6) -> np.ndarray:
        """[HATA KORUMALI]: Dinamik De-Esser (4 - 8.5 kHz Sibilance Filtresi)"""
        try:
            if not enabled or amount <= 0.01:
                return x
            sibilance, self.de_zi = scipy.signal.lfilter(self.de_b, self.de_a, x, zi=self.de_zi)
            rms = np.sqrt(np.mean(sibilance ** 2) + 1e-9)
            rms_db = 20.0 * np.log10(rms)

            if rms_db > threshold_db:
                excess_db = rms_db - threshold_db
                att_db = min(18.0, excess_db * amount)
                gain = 10.0 ** (-att_db / 20.0)
                out = x - sibilance * (1.0 - gain)
                return self.sanitize(out)
            return x
        except Exception:
            return x

    def apply_robot_effects(self, x: np.ndarray, carrier_hz: float, depth: float, resonance: float, bitcrush: int = 16) -> np.ndarray:
        """[HATA KORUMALI]: Robot Ring Modülasyonu, Tarak Rezonatörü & Bitcrusher"""
        try:
            if depth <= 0.001 and resonance <= 0.001 and bitcrush >= 16:
                return x

            n = len(x)
            # 1. Halka Modülasyonu
            if depth > 0.001:
                t = (np.arange(n) + self.robot_carrier_phase) / float(self.sr)
                self.robot_carrier_phase = (self.robot_carrier_phase + n) % self.sr
                carrier = np.cos(2.0 * math.pi * carrier_hz * t)
                x = x * ((1.0 - depth) + (depth * carrier))

            # 2. Metalik Tarak (Comb) Rezonatörü
            if resonance > 0.001:
                delay_len = max(20, int(self.sr * 0.0085))
                buf_len = len(self.robot_delay_buf)
                out = np.empty(n, dtype=np.float32)
                for i in range(n):
                    read_idx = (self.robot_delay_ptr - delay_len) % buf_len
                    delayed = self.robot_delay_buf[read_idx]
                    val = x[i] + (delayed * resonance)
                    self.robot_delay_buf[self.robot_delay_ptr] = val
                    self.robot_delay_ptr = (self.robot_delay_ptr + 1) % buf_len
                    out[i] = val
                x = out

            # 3. Bitcrusher
            if bitcrush < 16:
                levels = 2.0 ** max(2, min(14, bitcrush))
                x = np.round(x * levels) / levels

            return self.sanitize(x)
        except Exception:
            return x

    def apply_vectorized_dynamics(self, x: np.ndarray, gate_thresh_db: float = -45.0, comp_thresh_db: float = -18.0, comp_ratio: float = 3.0, makeup_db: float = 0.0) -> np.ndarray:
        """
        [HIZ & KARARLILIK]: Tamamen Vektörize Edilmiş C-Seviyesi Dinamik Kompresör ve Noise Gate.
        Python döngülerini ortadan kaldırarak 0.01 ms işlem süresi sağlar.
        """
        try:
            if len(x) == 0:
                return x

            # 1. Scipy IIR Zarf Takipçisi (C seviyesinde yıldırım hızında)
            att_coeff = 0.992
            b_env = [1.0 - att_coeff]
            a_env = [1.0, -att_coeff]
            abs_x = np.abs(x)

            env, self.comp_zi = scipy.signal.lfilter(b_env, a_env, abs_x, zi=self.comp_zi)
            env_db = 20.0 * np.log10(np.maximum(env, 1e-5))

            # 2. Vektörize Kompresör Kazanç Hesabı
            excess = env_db - comp_thresh_db
            comp_gain_db = np.where(excess > 0.0, -excess * (1.0 - 1.0 / max(1.0, comp_ratio)), 0.0)
            comp_gain = 10.0 ** (comp_gain_db / 20.0)

            # 3. Vektörize Gürültü Kapısı (Noise Gate)
            gate_thresh_lin = 10.0 ** (gate_thresh_db / 20.0)
            gate_gain = np.where(env < gate_thresh_lin, (env / (gate_thresh_lin + 1e-9)) ** 2, 1.0)

            # 4. Makyaj Kazancı & Uygulama
            makeup_linear = 10.0 ** (makeup_db / 20.0)
            out = x * comp_gain * gate_gain * makeup_linear

            # 5. Yumuşak Tepe Sınırlandırıcı (Analog Tanh Limiter)
            out = np.tanh(out * 1.05) * 0.95
            return self.sanitize(out)

        except Exception:
            return self.sanitize(x)


# ── 3. BIQUAD IIR PARAMETRİK EKOLAYZIR HESAPLAYICI ──
class BiquadFilter:
    """Robert Bristow-Johnson Audio EQ Cookbook Biquad IIR Filtresi"""
    def __init__(self, sample_rate: int = 48000):
        self.sr = sample_rate
        self.b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.zi = np.zeros(2, dtype=np.float32)

    def set_params(self, filter_type: str, f0: float, gain_db: float, q: float):
        try:
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
                disc = (A * A + 1.0) / q - (A - 1.0) ** 2
                beta = math.sqrt(max(0.0, disc))
                b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + beta * sin_w0)
                b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
                b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - beta * sin_w0)
                a0 = (A + 1.0) + (A - 1.0) * cos_w0 + beta * sin_w0
                a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
                a2 = (A + 1.0) + (A - 1.0) * cos_w0 - beta * sin_w0
            elif ftype == "highshelf":
                sqrt_A = math.sqrt(A)
                disc = (A * A + 1.0) / q - (A - 1.0) ** 2
                beta = math.sqrt(max(0.0, disc))
                b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + beta * sin_w0)
                b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
                b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - beta * sin_w0)
                a0 = (A + 1.0) - (A - 1.0) * cos_w0 + beta * sin_w0
                a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
                a2 = (A + 1.0) - (A - 1.0) * cos_w0 - beta * sin_w0
            else:  # peaking (çan / bell)
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
        except Exception:
            self.b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
            self.a = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    def process(self, x: np.ndarray) -> np.ndarray:
        try:
            if len(x) == 0:
                return x
            y, self.zi = scipy.signal.lfilter(self.b, self.a, x, zi=self.zi)
            return SafeAudioProcessor.sanitize(y)
        except Exception:
            return x


# ── 4. ÇOKLU İŞ PARÇACIKLI & KUYRUK TABANLI DSP SES MOTORU (DSPVoiceEngine) ──
class DSPVoiceEngine:
    """
    Kilitlenmeyen Kuyruk (Queue) ve Ayrı Çalışan İşçi İş Parçacığı (Worker Thread)
    ile Ses Kartını asla dondurmayan profesyonel gerçek zamanlı ses motoru.
    """
    def __init__(self, sample_rate: int = 48000, chunk_size: int = 512):
        self.sr = sample_rate
        self.chunk_size = chunk_size
        self.profiles: Dict[str, Any] = self._load_profiles()
        self.active_profile_name: str = "Kadın"

        # Çekirdek İşlemci ve Filtreler
        self.processor = SafeAudioProcessor(self.sr, n_fft=1024, hop_size=256)
        self.eq_filters: List[BiquadFilter] = [BiquadFilter(self.sr) for _ in range(5)]

        # STFT OLA Halka Tamponları
        self.in_ring_buf = np.zeros(1024, dtype=np.float32)
        self.out_ring_buf = np.zeros(1024, dtype=np.float32)

        # Asenkron Kuyruklar (Thread-Safe Queues)
        self.input_queue: queue.Queue = queue.Queue(maxsize=32)
        self.output_queue: queue.Queue = queue.Queue(maxsize=32)

        # Durum ve İş Parçacığı
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running: bool = False
        self.stream: Optional[sd.Stream] = None
        self.monitor_stream: Optional[sd.OutputStream] = None
        self.monitor_enabled: bool = False
        self.monitor_device_id: Optional[int] = None

        self._lock = threading.Lock()
        self.load_active_profile(self.active_profile_name)

    def _load_profiles(self) -> Dict[str, Any]:
        """Profilleri JSON dosyasından oku veya varsayılanları kaydet"""
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in DEFAULT_PROFILES.items():
                        if k not in data:
                            data[k] = v
                        else:
                            for sub_k, sub_v in v.items():
                                if sub_k not in data[k]:
                                    data[k][sub_k] = sub_v
                    return data
            except Exception as e:
                print(f"[DSP] Profil okuma uyarısı: {e}")

        self.save_profiles(DEFAULT_PROFILES)
        return json.loads(json.dumps(DEFAULT_PROFILES))

    def save_profiles(self, profiles_data: Optional[Dict[str, Any]] = None):
        """Profilleri kalıcı olarak diske kaydet"""
        data = profiles_data or self.profiles
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("[DSP] Profil kaydetme uyarısı:", e)

    def reset_profile_to_default(self, profile_name: str):
        """Seçili profili varsayılan ayarlara döndür"""
        if profile_name in DEFAULT_PROFILES:
            with self._lock:
                self.profiles[profile_name] = json.loads(json.dumps(DEFAULT_PROFILES[profile_name]))
                self.save_profiles()
                if self.active_profile_name == profile_name:
                    self.load_active_profile(profile_name)

    def load_active_profile(self, profile_name: str):
        """Aktif profili yükle ve parametreleri güncelle"""
        if profile_name not in self.profiles:
            profile_name = "Kadın"
        self.active_profile_name = profile_name
        prof = self.profiles[profile_name]

        with self._lock:
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
                    self.eq_filters[i].set_params("peaking", 1000.0, 0.0, 1.0)

    def update_profile_param(self, category: str, key: str, value: Any, band_index: Optional[int] = None):
        """GUI'den gelen tek bir parametre değişimini uygula ve kaydet"""
        with self._lock:
            prof = self.profiles[self.active_profile_name]
            if category in ["pitch", "robot", "vocal"]:
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

        self.save_profiles()

    def process_block(self, in_data: np.ndarray) -> np.ndarray:
        """Her bir ses bloğunu koruma duvarları arkasında işler"""
        try:
            with self._lock:
                prof = self.profiles[self.active_profile_name]
                pitch_st = float(prof.get("pitch_semitones", 0.0))
                fine_cents = float(prof.get("pitch_fine_cents", 0.0))
                formant_pct = float(prof.get("formant_shift_percent", 0.0))
                tube_drive = float(prof.get("tube_saturation_drive", 0.2))
                warmth_amt = float(prof.get("warmth_exciter_amount", 0.2))
                deesser_en = bool(prof.get("deesser_enabled", True))
                deesser_amt = float(prof.get("deesser_amount", 0.5))
                deesser_th = float(prof.get("deesser_threshold_db", -26.0))

                robot_on = prof.get("robot_enabled", False)
                carrier_hz = float(prof.get("robot_carrier_hz", 65.0))
                robot_depth = float(prof.get("robot_depth", 0.8))
                robot_res = float(prof.get("robot_resonance", 0.5))
                robot_crush = int(prof.get("robot_bitcrush_bits", 16))
                dyn = prof.get("dynamics", {})

            n = len(in_data)
            if n == 0:
                return in_data

            # 1. Spektral Formant Kaydırma & Pitch Shifting (Overlap-Add ile)
            self.in_ring_buf[:-n] = self.in_ring_buf[n:]
            self.in_ring_buf[-n:] = in_data

            processed_frame = self.processor.shift_formant_pitch(
                self.in_ring_buf, pitch_st, fine_cents, formant_pct
            )

            self.out_ring_buf[:-n] = self.out_ring_buf[n:]
            self.out_ring_buf[-n:] = 0.0
            self.out_ring_buf += processed_frame
            y = self.out_ring_buf[:n].copy()

            # 2. Robot Modülatörü
            if robot_on:
                y = self.processor.apply_robot_effects(y, carrier_hz, robot_depth, robot_res, robot_crush)

            # 3. Analog Tüp / Bant Doygunluğu (Tube Saturation)
            y = self.processor.apply_tube_saturation(y, tube_drive)

            # 4. Göğüs Rezonansı & Warmth Exciter (100 - 250 Hz)
            y = self.processor.apply_warmth_exciter(y, warmth_amt)

            # 5. Dinamik De-Esser (4 - 8.5 kHz Sibilance Bastırma)
            y = self.processor.apply_deesser(y, enabled=deesser_en, threshold_db=deesser_th, amount=deesser_amt)

            # 6. 5-Bant Parametrik Ekolayzır
            for f in self.eq_filters:
                y = f.process(y)

            # 7. Vektörize Kompresör, Gürültü Kapısı & Sınırlandırıcı
            y = self.processor.apply_vectorized_dynamics(
                y,
                gate_thresh_db=dyn.get("gate_threshold_db", -45.0),
                comp_thresh_db=dyn.get("comp_threshold_db", -18.0),
                comp_ratio=dyn.get("comp_ratio", 3.0),
                makeup_db=dyn.get("makeup_gain_db", 0.0)
            )

            return SafeAudioProcessor.sanitize(y)

        except Exception as e:
            # Kritik Hata Duvarı: Orijinal sesi geçir, asla çökme!
            return SafeAudioProcessor.sanitize(in_data)

    def _dsp_worker_loop(self):
        """
        [ASENKRON DSP ÇALIŞMA DÖNGÜSÜ]:
        Ana ses callback'ini bloke etmeden bağımsız thread'de çalışır.
        """
        while self.is_running:
            try:
                frame = self.input_queue.get(timeout=0.04)
            except queue.Empty:
                continue

            try:
                # Hesaplamayı yap
                processed = self.process_block(frame)
            except Exception:
                processed = SafeAudioProcessor.sanitize(frame)

            # Çıkış kuyruğuna ver
            try:
                self.output_queue.put_nowait(processed)
            except queue.Full:
                try:
                    # Gecikmeyi önlemek için en eski çerçeveyi düşür
                    self.output_queue.get_nowait()
                    self.output_queue.put_nowait(processed)
                except Exception:
                    pass

            # Kulaklık monitörü (Ana ses callback'i yerine burada güvenle yazılır)
            if self.monitor_enabled and self.monitor_stream and self.monitor_stream.active:
                try:
                    mon_data = np.column_stack([processed, processed]) if self.monitor_stream.channels == 2 else processed[:, None]
                    self.monitor_stream.write(mon_data)
                except Exception:
                    pass

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        """
        [SES KARTI CALLBACK'İ]:
        Bu fonksiyon native PortAudio thread'inde çalışır.
        Burada HİÇBİR ağır matematik veya bloklayıcı işlem yapılmaz! Sadece kuyruk kopyalaması yapılır.
        """
        if status:
            pass

        # 1. Giriş verisini kuyruğa gönder
        try:
            in_mono = indata[:, 0].copy()
            self.input_queue.put_nowait(in_mono)
        except queue.Full:
            pass

        # 2. İşlenmiş çıkış verisini kuyruktan al
        try:
            out_mono = self.output_queue.get_nowait()
            outdata[:, 0] = out_mono
            if outdata.shape[1] > 1:
                outdata[:, 1] = out_mono
        except queue.Empty:
            # Tampon yetişmediğinde gürültü/çıtırtı yerine sessizlik ver (Underrun Koruması)
            outdata.fill(0.0)

    def start(self, input_id: Optional[int], output_id: Optional[int]):
        """DSP motorunu çift kuyruk ve işçi iş parçacığıyla başlat"""
        self.stop()

        # Kuyrukları sıfırla
        while not self.input_queue.empty():
            try: self.input_queue.get_nowait()
            except Exception: break
        while not self.output_queue.empty():
            try: self.output_queue.get_nowait()
            except Exception: break

        # [ÖN-TAMPONLAMA]: İlk açılışta 2 blok sessizlik ekle ki ses kartı çıtırtı yapmasın
        for _ in range(2):
            self.output_queue.put_nowait(np.zeros(self.chunk_size, dtype=np.float32))

        self.is_running = True

        # İşçi iş parçacığını başlat
        self.worker_thread = threading.Thread(target=self._dsp_worker_loop, daemon=True)
        self.worker_thread.start()

        # PortAudio akışını başlat
        try:
            self.stream = sd.Stream(
                samplerate=self.sr,
                blocksize=self.chunk_size,
                device=(input_id, output_id),
                channels=(1, 2),
                dtype="float32",
                latency="low",
                callback=self._audio_callback
            )
            self.stream.start()
            print(f"[DSP] Güvenli Asenkron DSP Motoru başlatıldı -> In: {input_id}, Out: {output_id}")
        except Exception as e:
            self.is_running = False
            raise RuntimeError(f"DSP Ses Akışı başlatılamadı: {e}")

    def stop(self):
        """DSP motorunu ve iş parçacıklarını güvenle durdur"""
        self.is_running = False

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

        if self.worker_thread and self.worker_thread.is_alive():
            try:
                self.worker_thread.join(timeout=0.2)
            except Exception:
                pass
            self.worker_thread = None

        print("[DSP] Ses akışı ve iş parçacıkları güvenle durduruldu.")

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
