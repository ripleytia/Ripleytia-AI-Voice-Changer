"""
app.py — Ripleytia AI Ses Değiştirici V1 Beta
=============================================
Yapımcı: Ripleytia
Gelişmiş Yayıncı & Oyuncu Gerçek Zamanlı Ses Dönüştürücü.

Özellikler:
  1. ⚡ Gömülü Hızlı DSP / 4 Profil Modu (Yapay Zeka Gerektirmez / %0 GPU / Ultra Düşük Gecikme):
     - Kadın, Erkek, Çocuk, Robot ses profilleri
     - Detaylı 5-Bant Parametrik Ekolayzır (LPF, HPF, BPF, Notch, Peaking, Low/High Shelf)
     - Pitch / Formant Kaydırma, Siber Robot Modülatörü (Ring Mod + Tarak Rezonatörü)
     - Dinamik Kompresör, Gürültü Kapısı (Noise Gate) ve Sınırlandırıcı (Limiter)
     - Windows Sanal Ses Kablosu (CABLE Input) & Çift Çıkış (Kulaklık Monitörü)
  2. 🤖 Ripleytia AI Modu (RVC Yapay Zeka Model Klonlama):
     - RVC v1/v2 .pth ve .index desteği
     - FiveM, Warzone & Canlı Yayın optimizasyonları (112, 192, 256 chunk)
     - Windows 1ms Zamanlayıcı, MMCSS Pro Audio ve VRAM Kalkanı
"""

import os
import sys
import shutil
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any, List
from tkinter import filedialog, messagebox
import threading

# Windows konsolunda UTF-8 karakterlerin çökmesini engelle
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Bağımlılık kontrolü ve otomatik onarım
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
    import torch
    import sounddevice as sd
except ModuleNotFoundError as e:
    missing_mod = e.name
    print(f"\n" + "=" * 60)
    print(f" [UYARI] Gerekli Python modülü eksik: '{missing_mod}'")
    print(f" Ripleytia AI otomatik olarak yüklüyor, lütfen bekleyin...")
    print("=" * 60 + "\n")
    try:
        import subprocess
        pkg = "Pillow" if missing_mod == "PIL" else missing_mod
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        import customtkinter as ctk
        from PIL import Image, ImageTk
        import torch
        import sounddevice as sd
        print(f"✓ '{missing_mod}' başarıyla yüklendi!\n")
    except Exception as install_err:
        print(f"\n[HATA] Otomatik kurulum tamamlanamadı: {install_err}")
        print("Lütfen 'install.bat' dosyasını çalıştırarak tüm bağımlılıkları kurun.")
        print("veya komut satırından: pip install -r requirements.txt\n")
        try:
            input("Çıkmak için Enter tuşuna basın...")
        except Exception:
            pass
        sys.exit(1)

from dsp_engine import DSPVoiceEngine, list_dsp_devices, DEFAULT_PROFILES

# ── 1. DONANIM & WINDOWS OYUN / YAYIN OPTİMİZASYONLARI ──
def apply_game_stream_optimizations():
    """FiveM, Warzone ve canlı yayınlarda takılmayı ve gecikmeyi engelleyen akıllı dengeleme optimizasyonları"""
    log_msgs = []

    # 1. Windows 1ms Donanımsal Zamanlayıcı Kilidi (FiveM CPU dalgalanmalarında ms sıçramasını önler)
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        log_msgs.append("✓ Windows 1ms Yüksek Hassasiyetli Zamanlayıcı Aktif")
    except Exception as e:
        log_msgs.append(f"Zamanlayıcı uyarısı: {e}")

    # 2. Windows Süreç Önceliği (Dengeli Mod - Oyun FPS'ini korur)
    try:
        NORMAL_PRIORITY_CLASS = 0x00000020
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), NORMAL_PRIORITY_CLASS)
        log_msgs.append("✓ Windows Süreç Önceliği: DENGELİ (Oyun FPS'ini korur)")
    except Exception as e:
        log_msgs.append(f"Öncelik uyarısı: {e}")

    # 3. Windows EcoQoS (Power Throttling) Koruması Kapatıldı
    try:
        PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
        PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION = 0x4
        class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
            _fields_ = [
                ("Version", ctypes.c_ulong),
                ("ControlMask", ctypes.c_ulong),
                ("StateMask", ctypes.c_ulong),
            ]
        state = PROCESS_POWER_THROTTLING_STATE()
        state.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
        state.ControlMask = PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION
        state.StateMask = 0
        ctypes.windll.kernel32.SetProcessInformation(
            ctypes.windll.kernel32.GetCurrentProcess(), 4, ctypes.byref(state), ctypes.sizeof(state)
        )
        log_msgs.append("✓ Windows Güç Kısıtlaması (EcoQoS) Devre Dışı")
    except Exception as e:
        log_msgs.append(f"EcoQoS uyarısı: {e}")

    # 4. Windows MMCSS (Multimedia Class Scheduler Service) Pro Audio
    try:
        avrt = ctypes.windll.avrt
        task_index = ctypes.c_ulong(0)
        h_task = avrt.AvSetMmThreadCharacteristicsW("Pro Audio", ctypes.byref(task_index))
        if h_task:
            log_msgs.append("✓ Windows MMCSS: Pro Audio Modu Devrede")
    except Exception as e:
        log_msgs.append(f"MMCSS uyarısı: {e}")

    # 5. PyTorch VRAM Güvenlik Kalkanı (FiveM & Warzone için VRAM rezerve et)
    try:
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.backends.cudnn.benchmark = False
            torch.cuda.set_per_process_memory_fraction(0.18, 0)
            log_msgs.append("✓ PyTorch VRAM Kalkanı: ~1.4 GB (FiveM, Warzone & OBS için 6.6GB+ serbest)")
    except Exception as e:
        log_msgs.append(f"CUDA VRAM uyarısı: {e}")

    return log_msgs

# Optimizasyonları süreç başlar başlamaz uygula
opt_logs = apply_game_stream_optimizations()
for msg in opt_logs:
    print("[OPTIMIZER]", msg)

# ── 2. W-OKADA BACKEND IMPORT VE YOLLARI ──
ROOT = Path(__file__).resolve().parent
candidates = [
    ROOT / "server",
    ROOT / "w-okada" / "server",
    ROOT.parent / "w-okada" / "server",
    ROOT.parent.parent / "w-okada" / "server"
]
W_OKADA_DIR = next((p for p in candidates if p.exists()), candidates[0])
if str(W_OKADA_DIR) not in sys.path:
    sys.path.insert(0, str(W_OKADA_DIR))

if W_OKADA_DIR.exists():
    try:
        os.chdir(str(W_OKADA_DIR))
    except Exception:
        pass

VoiceChangerManager = None
VoiceChangerParamsManager = None
VoiceChangerParams = None
LoadModelParams = None
LoadModelParamFile = None
list_audio_device = None
UPLOAD_DIR = "upload_dir"

try:
    from voice_changer.VoiceChangerManager import VoiceChangerManager
    from voice_changer.VoiceChangerParamsManager import VoiceChangerParamsManager
    from voice_changer.utils.VoiceChangerParams import VoiceChangerParams
    from voice_changer.utils.LoadModelParams import LoadModelParams, LoadModelParamFile
    from voice_changer.Local.AudioDeviceList import list_audio_device
    from const import UPLOAD_DIR
except Exception as okada_err:
    print("[BACKEND] W-Okada AI motoru isteğe bağlı hazırlandı (DSP modu bağımsız çalışır):", okada_err)

# ── 3. RIPLEYTIA GOTHIC PURPLE TEMA RENKLERİ ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C_BG = "#0b0612"         # Derin Gotik Siyah/Mor
C_CARD = "#150d22"       # Kart Arka Planı
C_BORDER = "#451e6b"     # Kart Kenarlık Moru
C_TITLE = "#e0aaff"      # Başlık Açık Eflatun
C_SUB = "#b39ddb"        # Alt Metin Yumuşak Mor
C_ACCENT = "#7b2cbf"     # Canlı Mor Buton
C_HOVER = "#9d4edd"      # Hover Mor
C_CYAN = "#66FCF1"       # Vurgu Neon
C_GREEN = "#00e676"      # Başarı / Rozet Yeşili
C_MUTED = "#8b7e9b"

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_H = ("Segoe UI", 13, "bold")
FONT_B = ("Segoe UI", 11)
FONT_NUM = ("Consolas", 11, "bold")


class RipleytiaVoiceChangerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ripleytia AI Ses Değiştirici V1 Beta")
        self.geometry("1100x890")
        self.minsize(980, 820)
        self.configure(fg_color=C_BG)

        # ── DSP Ses Motoru (Yapay Zekasız Mod) ──
        self.dsp_engine = DSPVoiceEngine(sample_rate=48000, chunk_size=512)
        self.dsp_is_playing = False
        self.dsp_in_map: Dict[str, Any] = {}
        self.dsp_out_map: Dict[str, Any] = {}
        self.dsp_mon_map: Dict[str, Any] = {}
        self.dsp_profile_buttons: Dict[str, ctk.CTkButton] = {}
        self.eq_widgets: List[Dict[str, Any]] = []
        self.dyn_widgets: Dict[str, Any] = {}
        self.pitch_widgets: Dict[str, Any] = {}

        # ── AI Motoru Durumu ──
        self.vcm: Optional[Any] = None
        self.ai_is_playing = False
        self.ai_model_loaded = False
        self.current_perf = []
        self.ai_in_map = {}
        self.ai_out_map = {}

        # Aktif Çalışma Modu: 'dsp' veya 'ai'
        self.current_mode = "dsp"

        # Logoları ve İkonları Yükle
        self._set_app_icons()

        # Arayüzü İnşa Et
        self._build_ui()

        # Cihazları ve DSP Profillerini Yükle
        self._refresh_dsp_devices()
        self._refresh_dsp_ui_values()

        # AI Motorunu Arka Planda Başlat (Kullanıcı AI'a geçmek isterse hazır olsun)
        if VoiceChangerManager is not None:
            threading.Thread(target=self._init_ai_backend, daemon=True).start()

        # Performans Döngüsü
        self.after(300, self._perf_monitor_loop)

    def _set_app_icons(self):
        assets_dir = ROOT / "assets" if (ROOT / "assets").exists() else (ROOT / "v3" / "assets" if (ROOT / "v3" / "assets").exists() else ROOT.parent / "v3" / "assets")
        ico_file = assets_dir / "icon.ico"
        logo_file = assets_dir / "logo_64.png"

        try:
            if ico_file.exists():
                self.iconbitmap(str(ico_file))
        except Exception:
            pass

        try:
            if logo_file.exists():
                self.icon_photo = ImageTk.PhotoImage(Image.open(str(logo_file)))
                self.wm_iconphoto(True, self.icon_photo)
        except Exception:
            pass

    def _build_ui(self):
        # ── 1. ÜST PANEL & RIPLEYTIA LOGO BAŞLIĞI ──
        header_frame = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        header_frame.pack(fill="x", padx=16, pady=(14, 6))

        # Sol: Logo & Başlık
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        logo_file = (ROOT / "assets" / "logo_64.png") if (ROOT / "assets" / "logo_64.png").exists() else (ROOT / "v3" / "assets" / "logo_64.png")
        if logo_file.exists():
            try:
                pil_logo = Image.open(str(logo_file))
                self.logo_header_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(44, 44))
                lbl_logo_img = ctk.CTkLabel(title_box, text="", image=self.logo_header_img)
                lbl_logo_img.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        text_box = ctk.CTkFrame(title_box, fg_color="transparent")
        text_box.pack(side="left")

        lbl_title = ctk.CTkLabel(text_box, text="RIPLEYTIA AI SES DEĞİŞTİRİCİ V1 BETA", font=FONT_TITLE, text_color=C_TITLE)
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            text_box,
            text="Gelişmiş Yayıncı & Oyuncu Ses Motoru | Yapımcı: Ripleytia",
            font=("Segoe UI", 11), text_color=C_SUB
        )
        lbl_sub.pack(anchor="w")

        # Sağ: Durum Rozeti ve Canlı Monitör
        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=8)

        self.adm_badge = ctk.CTkLabel(
            right_box, text="⚡ DSP MODU: SIFIR GPU & ANLIK TEPKİ",
            fg_color="#2c1a4d", text_color=C_TITLE, corner_radius=8,
            border_width=1, border_color=C_BORDER, font=ctk.CTkFont(size=10, weight="bold"),
            padx=10, pady=4
        )
        self.adm_badge.pack(anchor="e", pady=(0, 2))

        self.perf_lbl = ctk.CTkLabel(
            right_box,
            text="⏱️ Gecikme: ~5 ms  |  Tampon: 512  |  GPU: %0",
            font=("Consolas", 11, "bold"), text_color=C_CYAN
        )
        self.perf_lbl.pack(anchor="e")

        # ── 2. MOD DEĞİŞTİRİCİ SEGMENTLİ SEÇİCİ ──
        mode_bar = ctk.CTkFrame(self, fg_color="transparent")
        mode_bar.pack(fill="x", padx=16, pady=(4, 6))

        self.mode_seg = ctk.CTkSegmentedButton(
            mode_bar,
            values=[
                "⚡ Klasik DSP & 4 Profil Modu (Yapay Zekasız / Anlık / %0 GPU)",
                "🤖 Ripleytia AI Modu (RVC Yapay Zeka Model Klonlama)"
            ],
            command=self._on_mode_change,
            font=("Segoe UI", 12, "bold"),
            height=34,
            selected_color=C_ACCENT,
            selected_hover_color=C_HOVER
        )
        self.mode_seg.pack(fill="x")
        self.mode_seg.set("⚡ Klasik DSP & 4 Profil Modu (Yapay Zekasız / Anlık / %0 GPU)")

        # ── 3. ANA İÇERİK KONTEYNERLARI ──
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # A) DSP Modu Arayüzü
        self.dsp_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self._build_dsp_ui(self.dsp_frame)
        self.dsp_frame.pack(fill="both", expand=True)

        # B) AI Modu Arayüzü (Başlangıçta gizli)
        self.ai_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self._build_ai_ui(self.ai_frame)

    # ══════════════════════════════════════════════════════════════════
    # DSP MODU: KADIN, ERKEK, ÇOCUK, ROBOT & DETAYLI EKOLAYZIR ARAYÜZÜ
    # ══════════════════════════════════════════════════════════════════
    def _build_dsp_ui(self, parent):
        parent.columnconfigure(0, weight=4)  # Sol: Profiller & Cihazlar
        parent.columnconfigure(1, weight=6)  # Sağ: Detaylı Ekolayzır & Parametreler

        # ────────── SOL KOLON ──────────
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # 1. Gömülü 4 Ses Profili Kartı
        c_prof = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_prof.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(c_prof, text="🎭 Gömülü Ses Profilleri (Yapay Zekasız)", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(10, 4))

        # 4 Profil Butonları (2x2 Izgara)
        grid_prof = ctk.CTkFrame(c_prof, fg_color="transparent")
        grid_prof.pack(fill="x", padx=12, pady=(0, 8))
        grid_prof.columnconfigure((0, 1), weight=1)

        profiles_info = [
            ("Kadın", "👩 Kadın Sesi", "#d946ef"),
            ("Erkek", "👨 Erkek Sesi", "#3b82f6"),
            ("Çocuk", "🧒 Çocuk Sesi", "#f59e0b"),
            ("Robot", "🤖 Robot Sesi", "#06b6d4"),
        ]

        for idx, (p_id, p_label, p_color) in enumerate(profiles_info):
            r = idx // 2
            c = idx % 2
            btn = ctk.CTkButton(
                grid_prof, text=p_label, font=("Segoe UI", 12, "bold"), height=42,
                fg_color="#221338", hover_color="#3b1d61", border_width=1, border_color=C_BORDER,
                command=lambda pid=p_id: self._select_dsp_profile(pid)
            )
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            self.dsp_profile_buttons[p_id] = btn

        self.lbl_prof_desc = ctk.CTkLabel(
            c_prof, text="Doğal kadın sesi tınısı, tiz netliği ve göğüs rezonansı filtreleme",
            font=("Segoe UI", 10), text_color=C_SUB, wraplength=340, justify="left"
        )
        self.lbl_prof_desc.pack(anchor="w", padx=16, pady=(2, 10))

        # 2. Ses Giriş & Sanal Kablo Çıkış Yönlendirmesi
        c_dev = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_dev.pack(fill="x", pady=(0, 10))

        dev_header = ctk.CTkFrame(c_dev, fg_color="transparent")
        dev_header.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(dev_header, text="🔊 Sanal Ses Cihazı & Yönlendirme", font=FONT_H, text_color=C_TITLE).pack(side="left")

        self.dsp_api_filter = ctk.StringVar(value="MME")
        api_seg = ctk.CTkSegmentedButton(
            dev_header, values=["MME", "DirectSound", "WASAPI", "Tümü"],
            variable=self.dsp_api_filter, command=lambda _: self._refresh_dsp_devices(),
            font=("Segoe UI", 9), height=22, selected_color=C_ACCENT, selected_hover_color=C_HOVER
        )
        api_seg.pack(side="right")

        # Giriş
        ctk.CTkLabel(c_dev, text="Giriş (Mikrofon):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(4, 2))
        self.dsp_in_cb = ctk.CTkComboBox(c_dev, values=["Taranıyor..."], font=FONT_B, height=28, command=self._on_dsp_device_changed)
        self.dsp_in_cb.pack(fill="x", padx=16, pady=(0, 6))

        # Çıkış (Sanal Kablo)
        ctk.CTkLabel(c_dev, text="Çıkış (Sanal Ses Kablosu / CABLE Input / Hoparlör):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(4, 2))
        self.dsp_out_cb = ctk.CTkComboBox(c_dev, values=["Taranıyor..."], font=FONT_B, height=28, command=self._on_dsp_device_changed)
        self.dsp_out_cb.pack(fill="x", padx=16, pady=(0, 6))

        # Kendi Sesimi Duy (Monitör)
        mon_frame = ctk.CTkFrame(c_dev, fg_color="#180e29", corner_radius=8)
        mon_frame.pack(fill="x", padx=16, pady=(4, 10))

        mon_top = ctk.CTkFrame(mon_frame, fg_color="transparent")
        mon_top.pack(fill="x", padx=8, pady=(6, 2))
        self.mon_switch_var = ctk.BooleanVar(value=False)
        self.mon_switch = ctk.CTkSwitch(
            mon_top, text="🎧 Kendi Sesimi Duy (Kulaklık Monitörü)", variable=self.mon_switch_var,
            command=self._on_toggle_monitor, font=("Segoe UI", 11, "bold"), text_color=C_CYAN,
            progress_color=C_ACCENT
        )
        self.mon_switch.pack(side="left")

        self.dsp_mon_cb = ctk.CTkComboBox(mon_frame, values=["Taranıyor..."], font=("Segoe UI", 10), height=26, command=self._on_dsp_device_changed)
        self.dsp_mon_cb.pack(fill="x", padx=8, pady=(2, 6))

        # 3. DSP Başlat / Durdur Butonu
        self.dsp_start_btn = ctk.CTkButton(
            left, text="▶ DSP Ses Değiştiriciyi Başlat", command=self._toggle_dsp_audio,
            font=("Segoe UI", 14, "bold"), fg_color="#10B981", hover_color="#059669", height=44, corner_radius=10
        )
        self.dsp_start_btn.pack(fill="x", pady=(0, 8))

        # 4. Profil Kaydetme & Sıfırlama Butonları
        tools_row = ctk.CTkFrame(left, fg_color="transparent")
        tools_row.pack(fill="x")
        tools_row.columnconfigure((0, 1), weight=1)

        btn_save = ctk.CTkButton(
            tools_row, text="💾 Profili Kaydet", font=("Segoe UI", 11), height=32,
            fg_color="#334155", hover_color="#475569", command=self._save_current_dsp_profile
        )
        btn_save.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        btn_reset = ctk.CTkButton(
            tools_row, text="🔄 Varsayılana Sıfırla", font=("Segoe UI", 11), height=32,
            fg_color="#4b1220", hover_color="#6b1d30", command=self._reset_current_dsp_profile
        )
        btn_reset.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # ────────── SAĞ KOLON: DETAYLI EKOLAYZIR VE SES PARAMETRELERİ ──────────
        right = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Sağ Üst Başlık
        eq_header = ctk.CTkFrame(right, fg_color="transparent")
        eq_header.pack(fill="x", padx=16, pady=(12, 6))
        self.lbl_eq_title = ctk.CTkLabel(eq_header, text="🎛️ Profil Ekolayzır & Ses Kalibrasyonu (Kadın)", font=FONT_H, text_color=C_TITLE)
        self.lbl_eq_title.pack(side="left")

        # CTkTabview: Ekolayzır, Pitch/Robot, Kompresör
        self.dsp_tabs = ctk.CTkTabview(right, fg_color="#120a1d", segmented_button_selected_color=C_ACCENT, segmented_button_selected_hover_color=C_HOVER)
        self.dsp_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        tab_eq = self.dsp_tabs.add("🎚️ 5-Bant Parametrik EQ")
        tab_pitch = self.dsp_tabs.add("🎵 Pitch & Robot Modülatörü")
        tab_dyn = self.dsp_tabs.add("🗜️ Kompresör & Noise Gate")

        # ── SEKME 1: 5-BANT PARAMETRİK EKOLAYZIR ──
        self._build_eq_tab(tab_eq)

        # ── SEKME 2: PITCH VE ROBOT MODÜLATÖRÜ ──
        self._build_pitch_tab(tab_pitch)

        # ── SEKME 3: DİNAMİK KOMPRESÖR VE NOISE GATE ──
        self._build_dynamics_tab(tab_dyn)

    def _build_eq_tab(self, parent):
        scroll_eq = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_eq.pack(fill="both", expand=True, padx=4, pady=4)

        self.eq_widgets = []
        band_names = [
            "Bant 1: Alt Frekanslar (Sub-Bass / High-Pass)",
            "Bant 2: Düşük Orta (Low-Mid / Göğüs Tonu)",
            "Bant 3: Orta Frekans (Mid / Vokal Gövdesi)",
            "Bant 4: Yüksek Orta (High-Mid / Parlaklık & Netlik)",
            "Bant 5: Tiz & Hava (High-Shelf / Low-Pass)",
        ]

        for i in range(5):
            band_box = ctk.CTkFrame(scroll_eq, fg_color="#190e29", corner_radius=10, border_width=1, border_color="#361752")
            band_box.pack(fill="x", pady=5, padx=2)

            # Başlık ve Aç/Kapa
            b_top = ctk.CTkFrame(band_box, fg_color="transparent")
            b_top.pack(fill="x", padx=10, pady=(6, 2))
            
            lbl_bname = ctk.CTkLabel(b_top, text=band_names[i], font=("Segoe UI", 11, "bold"), text_color=C_TITLE)
            lbl_bname.pack(side="left")

            sw_en_var = ctk.BooleanVar(value=True)
            sw_en = ctk.CTkSwitch(
                b_top, text="Aktif", variable=sw_en_var, font=("Segoe UI", 10),
                progress_color=C_ACCENT, command=lambda idx=i, v=sw_en_var: self._on_eq_enable_toggle(idx, v.get())
            )
            sw_en.pack(side="right")

            # Kontroller (Tip, Freq, Gain, Q)
            ctrl_grid = ctk.CTkFrame(band_box, fg_color="transparent")
            ctrl_grid.pack(fill="x", padx=10, pady=(2, 8))
            ctrl_grid.columnconfigure((0, 1, 2, 3), weight=1)

            # 1. Filtre Tipi
            ctk.CTkLabel(ctrl_grid, text="Filtre Tipi:", font=("Segoe UI", 9), text_color=C_SUB).grid(row=0, column=0, sticky="w", padx=2)
            cb_type = ctk.CTkComboBox(
                ctrl_grid, values=["peaking", "lowshelf", "highshelf", "highpass", "lowpass", "bandpass", "notch"],
                font=("Segoe UI", 10), height=24, width=95,
                command=lambda val, idx=i: self.dsp_engine.update_profile_param("eq", "type", val, band_index=idx)
            )
            cb_type.grid(row=1, column=0, sticky="ew", padx=2)

            # 2. Frekans
            lbl_f_val = ctk.CTkLabel(ctrl_grid, text="1000 Hz", font=FONT_NUM, text_color=C_CYAN)
            ctk.CTkLabel(ctrl_grid, text="Frekans (Hz):", font=("Segoe UI", 9), text_color=C_SUB).grid(row=0, column=1, sticky="w", padx=2)
            lbl_f_val.grid(row=0, column=1, sticky="e", padx=2)
            sl_f = ctk.CTkSlider(
                ctrl_grid, from_=20, to=20000, number_of_steps=200, height=16,
                button_color=C_ACCENT, button_hover_color=C_HOVER,
                command=lambda val, idx=i, lbl=lbl_f_val: self._on_eq_freq_slider(idx, val, lbl)
            )
            sl_f.grid(row=1, column=1, sticky="ew", padx=2)

            # 3. Kazanç (Gain dB)
            lbl_g_val = ctk.CTkLabel(ctrl_grid, text="0.0 dB", font=FONT_NUM, text_color=C_TITLE)
            ctk.CTkLabel(ctrl_grid, text="Kazanç (dB):", font=("Segoe UI", 9), text_color=C_SUB).grid(row=0, column=2, sticky="w", padx=2)
            lbl_g_val.grid(row=0, column=2, sticky="e", padx=2)
            sl_g = ctk.CTkSlider(
                ctrl_grid, from_=-24.0, to=24.0, number_of_steps=96, height=16,
                button_color=C_ACCENT, button_hover_color=C_HOVER,
                command=lambda val, idx=i, lbl=lbl_g_val: self._on_eq_gain_slider(idx, val, lbl)
            )
            sl_g.grid(row=1, column=2, sticky="ew", padx=2)

            # 4. Q Faktörü (Bant Genişliği)
            lbl_q_val = ctk.CTkLabel(ctrl_grid, text="1.00 Q", font=FONT_NUM, text_color=C_TITLE)
            ctk.CTkLabel(ctrl_grid, text="Q Faktörü:", font=("Segoe UI", 9), text_color=C_SUB).grid(row=0, column=3, sticky="w", padx=2)
            lbl_q_val.grid(row=0, column=3, sticky="e", padx=2)
            sl_q = ctk.CTkSlider(
                ctrl_grid, from_=0.1, to=10.0, number_of_steps=99, height=16,
                button_color=C_ACCENT, button_hover_color=C_HOVER,
                command=lambda val, idx=i, lbl=lbl_q_val: self._on_eq_q_slider(idx, val, lbl)
            )
            sl_q.grid(row=1, column=3, sticky="ew", padx=2)

            self.eq_widgets.append({
                "type_cb": cb_type,
                "freq_sl": sl_f,
                "freq_lbl": lbl_f_val,
                "gain_sl": sl_g,
                "gain_lbl": lbl_g_val,
                "q_sl": sl_q,
                "q_lbl": lbl_q_val,
                "en_sw": sw_en,
                "en_var": sw_en_var
            })

    def _build_pitch_tab(self, parent):
        scroll_p = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_p.pack(fill="both", expand=True, padx=4, pady=4)

        # 1. Pitch Kaydırma Kartı
        p_card = ctk.CTkFrame(scroll_p, fg_color="#190e29", corner_radius=10, border_width=1, border_color="#361752")
        p_card.pack(fill="x", pady=6)
        ctk.CTkLabel(p_card, text="🎤 Pitch Kaydırma (Yarım Ton & İnce Ayar)", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=14, pady=(8, 4))

        # Semitones
        f_st = ctk.CTkFrame(p_card, fg_color="transparent")
        f_st.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_st, text="Perde Kaydırma (Yarım Ton / Semitone):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_pitch_st = ctk.CTkLabel(f_st, text="+0.0 st", font=FONT_NUM, text_color=C_CYAN)
        self.lbl_pitch_st.pack(side="right")

        self.sl_pitch_st = ctk.CTkSlider(
            p_card, from_=-12.0, to=12.0, number_of_steps=48, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=self._on_pitch_st_slider
        )
        self.sl_pitch_st.pack(fill="x", padx=14, pady=(2, 8))

        # Fine Cents
        f_fine = ctk.CTkFrame(p_card, fg_color="transparent")
        f_fine.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_fine, text="İnce Ayar (Cent):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_pitch_fine = ctk.CTkLabel(f_fine, text="0 cent", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_pitch_fine.pack(side="right")

        self.sl_pitch_fine = ctk.CTkSlider(
            p_card, from_=-100.0, to=100.0, number_of_steps=100, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=self._on_pitch_fine_slider
        )
        self.sl_pitch_fine.pack(fill="x", padx=14, pady=(2, 12))

        # 2. Siber Robot Modülatörü Kartı
        r_card = ctk.CTkFrame(scroll_p, fg_color="#190e29", corner_radius=10, border_width=1, border_color="#361752")
        r_card.pack(fill="x", pady=6)

        r_top = ctk.CTkFrame(r_card, fg_color="transparent")
        r_top.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(r_top, text="🤖 Siber Robot & Ring Modülatörü", font=FONT_H, text_color=C_TITLE).pack(side="left")

        self.sw_robot_var = ctk.BooleanVar(value=False)
        self.sw_robot = ctk.CTkSwitch(
            r_top, text="Robot Efekti Aktif", variable=self.sw_robot_var, font=("Segoe UI", 11, "bold"),
            progress_color=C_ACCENT, command=self._on_robot_switch_toggle
        )
        self.sw_robot.pack(side="right")

        # Robot Taşıyıcı Frekansı
        f_hz = ctk.CTkFrame(r_card, fg_color="transparent")
        f_hz.pack(fill="x", padx=14, pady=(6, 0))
        ctk.CTkLabel(f_hz, text="Taşıyıcı Frekans (Carrier Hz - Siborg Tınısı):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_robot_hz = ctk.CTkLabel(f_hz, text="65 Hz", font=FONT_NUM, text_color=C_CYAN)
        self.lbl_robot_hz.pack(side="right")

        self.sl_robot_hz = ctk.CTkSlider(
            r_card, from_=20.0, to=400.0, number_of_steps=190, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=self._on_robot_hz_slider
        )
        self.sl_robot_hz.pack(fill="x", padx=14, pady=(2, 8))

        # Modülasyon Derinliği
        f_dep = ctk.CTkFrame(r_card, fg_color="transparent")
        f_dep.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_dep, text="Modülasyon Derinliği (Ring Mod Depth):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_robot_dep = ctk.CTkLabel(f_dep, text="%80", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_robot_dep.pack(side="right")

        self.sl_robot_dep = ctk.CTkSlider(
            r_card, from_=0.0, to=1.0, number_of_steps=50, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=self._on_robot_dep_slider
        )
        self.sl_robot_dep.pack(fill="x", padx=14, pady=(2, 8))

        # Metalik Rezonans (Comb Filter)
        f_res = ctk.CTkFrame(r_card, fg_color="transparent")
        f_res.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_res, text="Metalik Tarak Rezonansı (Metallic Feedback):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_robot_res = ctk.CTkLabel(f_res, text="%60", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_robot_res.pack(side="right")

        self.sl_robot_res = ctk.CTkSlider(
            r_card, from_=0.0, to=0.9, number_of_steps=45, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=self._on_robot_res_slider
        )
        self.sl_robot_res.pack(fill="x", padx=14, pady=(2, 12))

    def _build_dynamics_tab(self, parent):
        scroll_d = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_d.pack(fill="both", expand=True, padx=4, pady=4)

        # 1. Gürültü Kapısı (Noise Gate)
        g_card = ctk.CTkFrame(scroll_d, fg_color="#190e29", corner_radius=10, border_width=1, border_color="#361752")
        g_card.pack(fill="x", pady=6)
        ctk.CTkLabel(g_card, text="🔇 Akıllı Gürültü Kapısı (Noise Gate)", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=14, pady=(8, 2))
        ctk.CTkLabel(g_card, text="Konuşmadığınızda arka plan fan, klavye ve oda gürültüsünü anında sıfırlar", font=("Segoe UI", 10), text_color=C_SUB).pack(anchor="w", padx=14, pady=(0, 6))

        f_gate = ctk.CTkFrame(g_card, fg_color="transparent")
        f_gate.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_gate, text="Kapı Eşiği (Gate Threshold):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_dyn_gate = ctk.CTkLabel(f_gate, text="-45.0 dB", font=FONT_NUM, text_color=C_CYAN)
        self.lbl_dyn_gate.pack(side="right")

        self.sl_dyn_gate = ctk.CTkSlider(
            g_card, from_=-80.0, to=-20.0, number_of_steps=120, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=lambda v: self._on_dyn_slider("gate_threshold_db", v, self.lbl_dyn_gate, "{:.1f} dB")
        )
        self.sl_dyn_gate.pack(fill="x", padx=14, pady=(2, 12))

        # 2. Dinamik Kompresör Kartı
        c_card = ctk.CTkFrame(scroll_d, fg_color="#190e29", corner_radius=10, border_width=1, border_color="#361752")
        c_card.pack(fill="x", pady=6)
        ctk.CTkLabel(c_card, text="🗜️ Dinamik Vokal Kompresörü", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=14, pady=(8, 2))
        ctk.CTkLabel(c_card, text="Ses dalgalanmalarını dengeler, bağırma anında patlamayı engeller ve tok ses üretir", font=("Segoe UI", 10), text_color=C_SUB).pack(anchor="w", padx=14, pady=(0, 6))

        # Threshold
        f_th = ctk.CTkFrame(c_card, fg_color="transparent")
        f_th.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_th, text="Sıkıştırma Eşiği (Threshold):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_dyn_th = ctk.CTkLabel(f_th, text="-18.0 dB", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_dyn_th.pack(side="right")
        self.sl_dyn_th = ctk.CTkSlider(
            c_card, from_=-60.0, to=0.0, number_of_steps=120, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=lambda v: self._on_dyn_slider("comp_threshold_db", v, self.lbl_dyn_th, "{:.1f} dB")
        )
        self.sl_dyn_th.pack(fill="x", padx=14, pady=(2, 6))

        # Ratio
        f_rt = ctk.CTkFrame(c_card, fg_color="transparent")
        f_rt.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_rt, text="Sıkıştırma Oranı (Ratio):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_dyn_rt = ctk.CTkLabel(f_rt, text="3.0:1", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_dyn_rt.pack(side="right")
        self.sl_dyn_rt = ctk.CTkSlider(
            c_card, from_=1.0, to=20.0, number_of_steps=76, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=lambda v: self._on_dyn_slider("comp_ratio", v, self.lbl_dyn_rt, "{:.1f}:1")
        )
        self.sl_dyn_rt.pack(fill="x", padx=14, pady=(2, 6))

        # Attack
        f_att = ctk.CTkFrame(c_card, fg_color="transparent")
        f_att.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_att, text="Saldırı Süresi (Attack):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_dyn_att = ctk.CTkLabel(f_att, text="10.0 ms", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_dyn_att.pack(side="right")
        self.sl_dyn_att = ctk.CTkSlider(
            c_card, from_=0.5, to=100.0, number_of_steps=99, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=lambda v: self._on_dyn_slider("attack_ms", v, self.lbl_dyn_att, "{:.1f} ms")
        )
        self.sl_dyn_att.pack(fill="x", padx=14, pady=(2, 6))

        # Release
        f_rel = ctk.CTkFrame(c_card, fg_color="transparent")
        f_rel.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_rel, text="Bırakma Süresi (Release):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_dyn_rel = ctk.CTkLabel(f_rel, text="100.0 ms", font=FONT_NUM, text_color=C_TITLE)
        self.lbl_dyn_rel.pack(side="right")
        self.sl_dyn_rel = ctk.CTkSlider(
            c_card, from_=5.0, to=500.0, number_of_steps=99, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=lambda v: self._on_dyn_slider("release_ms", v, self.lbl_dyn_rel, "{:.1f} ms")
        )
        self.sl_dyn_rel.pack(fill="x", padx=14, pady=(2, 6))

        # Makeup Gain
        f_mk = ctk.CTkFrame(c_card, fg_color="transparent")
        f_mk.pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(f_mk, text="Makyaj Kazancı (Makeup Gain):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.lbl_dyn_mk = ctk.CTkLabel(f_mk, text="+2.5 dB", font=FONT_NUM, text_color=C_CYAN)
        self.lbl_dyn_mk.pack(side="right")
        self.sl_dyn_mk = ctk.CTkSlider(
            c_card, from_=-12.0, to=18.0, number_of_steps=60, height=18,
            button_color=C_ACCENT, button_hover_color=C_HOVER,
            command=lambda v: self._on_dyn_slider("makeup_gain_db", v, self.lbl_dyn_mk, "{:+.1f} dB")
        )
        self.sl_dyn_mk.pack(fill="x", padx=14, pady=(2, 12))

    # ══════════════════════════════════════════════════════════════════
    # DSP OLAY VE DEĞER GÜNCELLEME İŞLEYİCİLERİ
    # ══════════════════════════════════════════════════════════════════
    def _select_dsp_profile(self, profile_name: str):
        self.dsp_engine.load_active_profile(profile_name)
        self._refresh_dsp_ui_values()
        print(f"[DSP] Aktif profil değiştirildi -> {profile_name}")

    def _refresh_dsp_ui_values(self):
        pname = self.dsp_engine.active_profile_name
        prof = self.dsp_engine.profiles.get(pname, {})

        # Profil Başlık & Açıklama
        self.lbl_eq_title.configure(text=f"🎛️ Profil Ekolayzır & Ses Kalibrasyonu ({pname})")
        self.lbl_prof_desc.configure(text=prof.get("description", ""))

        # Profil Butonları Vurgu Rengi
        for pid, btn in self.dsp_profile_buttons.items():
            if pid == pname:
                btn.configure(fg_color=C_ACCENT, border_color=C_GREEN, border_width=2)
            else:
                btn.configure(fg_color="#221338", border_color=C_BORDER, border_width=1)

        # 1. EQ Bantları
        eq_bands = prof.get("eq_bands", [])
        for i, w in enumerate(self.eq_widgets):
            if i < len(eq_bands):
                b = eq_bands[i]
                w["type_cb"].set(b.get("type", "peaking"))
                w["freq_sl"].set(b.get("freq", 1000.0))
                w["freq_lbl"].configure(text=f"{int(b.get('freq', 1000.0))} Hz")
                w["gain_sl"].set(b.get("gain", 0.0))
                w["gain_lbl"].configure(text=f"{b.get('gain', 0.0):+.1f} dB")
                w["q_sl"].set(b.get("q", 1.0))
                w["q_lbl"].configure(text=f"{b.get('q', 1.0):.2f} Q")
                w["en_var"].set(b.get("enabled", True))

        # 2. Pitch
        st = prof.get("pitch_semitones", 0.0)
        fine = prof.get("pitch_fine_cents", 0.0)
        self.sl_pitch_st.set(st)
        self.lbl_pitch_st.configure(text=f"{st:+.1f} st")
        self.sl_pitch_fine.set(fine)
        self.lbl_pitch_fine.configure(text=f"{fine:+.0f} cent")

        # 3. Robot
        r_en = prof.get("robot_enabled", False)
        r_hz = prof.get("robot_carrier_hz", 65.0)
        r_dep = prof.get("robot_depth", 0.8)
        r_res = prof.get("robot_resonance", 0.5)

        self.sw_robot_var.set(r_en)
        self.sl_robot_hz.set(r_hz)
        self.lbl_robot_hz.configure(text=f"{int(r_hz)} Hz")
        self.sl_robot_dep.set(r_dep)
        self.lbl_robot_dep.configure(text=f"%{int(r_dep * 100)}")
        self.sl_robot_res.set(r_res)
        self.lbl_robot_res.configure(text=f"%{int(r_res * 100)}")

        # 4. Dynamics
        dyn = prof.get("dynamics", {})
        self.sl_dyn_gate.set(dyn.get("gate_threshold_db", -45.0))
        self.lbl_dyn_gate.configure(text=f"{dyn.get('gate_threshold_db', -45.0):.1f} dB")

        self.sl_dyn_th.set(dyn.get("comp_threshold_db", -18.0))
        self.lbl_dyn_th.configure(text=f"{dyn.get('comp_threshold_db', -18.0):.1f} dB")

        self.sl_dyn_rt.set(dyn.get("comp_ratio", 3.0))
        self.lbl_dyn_rt.configure(text=f"{dyn.get('comp_ratio', 3.0):.1f}:1")

        self.sl_dyn_att.set(dyn.get("attack_ms", 10.0))
        self.lbl_dyn_att.configure(text=f"{dyn.get('attack_ms', 10.0):.1f} ms")

        self.sl_dyn_rel.set(dyn.get("release_ms", 100.0))
        self.lbl_dyn_rel.configure(text=f"{dyn.get('release_ms', 100.0):.1f} ms")

        self.sl_dyn_mk.set(dyn.get("makeup_gain_db", 0.0))
        self.lbl_dyn_mk.configure(text=f"{dyn.get('makeup_gain_db', 0.0):+.1f} dB")

    def _on_eq_enable_toggle(self, band_idx: int, enabled: bool):
        self.dsp_engine.update_profile_param("eq", "enabled", enabled, band_index=band_idx)

    def _on_eq_freq_slider(self, band_idx: int, val: float, lbl: ctk.CTkLabel):
        lbl.configure(text=f"{int(round(val))} Hz")
        self.dsp_engine.update_profile_param("eq", "freq", float(round(val)), band_index=band_idx)

    def _on_eq_gain_slider(self, band_idx: int, val: float, lbl: ctk.CTkLabel):
        lbl.configure(text=f"{val:+.1f} dB")
        self.dsp_engine.update_profile_param("eq", "gain", float(round(val, 1)), band_index=band_idx)

    def _on_eq_q_slider(self, band_idx: int, val: float, lbl: ctk.CTkLabel):
        lbl.configure(text=f"{val:.2f} Q")
        self.dsp_engine.update_profile_param("eq", "q", float(round(val, 2)), band_index=band_idx)

    def _on_pitch_st_slider(self, val: float):
        v = round(val, 1)
        self.lbl_pitch_st.configure(text=f"{v:+.1f} st")
        self.dsp_engine.update_profile_param("pitch", "pitch_semitones", float(v))

    def _on_pitch_fine_slider(self, val: float):
        v = int(round(val))
        self.lbl_pitch_fine.configure(text=f"{v:+.0f} cent")
        self.dsp_engine.update_profile_param("pitch", "pitch_fine_cents", float(v))

    def _on_robot_switch_toggle(self):
        en = self.sw_robot_var.get()
        self.dsp_engine.update_profile_param("robot", "robot_enabled", en)

    def _on_robot_hz_slider(self, val: float):
        v = int(round(val))
        self.lbl_robot_hz.configure(text=f"{v} Hz")
        self.dsp_engine.update_profile_param("robot", "robot_carrier_hz", float(v))

    def _on_robot_dep_slider(self, val: float):
        v = round(val, 2)
        self.lbl_robot_dep.configure(text=f"%{int(v * 100)}")
        self.dsp_engine.update_profile_param("robot", "robot_depth", float(v))

    def _on_robot_res_slider(self, val: float):
        v = round(val, 2)
        self.lbl_robot_res.configure(text=f"%{int(v * 100)}")
        self.dsp_engine.update_profile_param("robot", "robot_resonance", float(v))

    def _on_dyn_slider(self, key: str, val: float, lbl: ctk.CTkLabel, fmt: str):
        v = round(val, 1)
        lbl.configure(text=fmt.format(v))
        self.dsp_engine.update_profile_param("dynamics", key, float(v))

    def _save_current_dsp_profile(self):
        self.dsp_engine.save_profiles()
        pname = self.dsp_engine.active_profile_name
        messagebox.showinfo("Kayıt Başarılı", f"✓ '{pname}' profilinin tüm ekolayzır ve ses ayarları kalıcı olarak kaydedildi!")

    def _reset_current_dsp_profile(self):
        pname = self.dsp_engine.active_profile_name
        if messagebox.askyesno("Sıfırlama Onayı", f"'{pname}' profilini varsayılan fabrika ayarlarına sıfırlamak istiyor musunuz?"):
            self.dsp_engine.reset_profile_to_default(pname)
            self._refresh_dsp_ui_values()
            messagebox.showinfo("Sıfırlandı", f"✓ '{pname}' profili fabrika ayarlarına döndürüldü.")

    # ══════════════════════════════════════════════════════════════════
    # DSP SES CİHAZLARI & SES AKIŞ YÖNETİMİ
    # ══════════════════════════════════════════════════════════════════
    def _refresh_dsp_devices(self):
        api_filter = self.dsp_api_filter.get()
        in_devs, out_devs = list_dsp_devices(api_filter)

        self.dsp_in_map = {d["label"]: d for d in in_devs}
        self.dsp_out_map = {d["label"]: d for d in out_devs}
        self.dsp_mon_map = {d["label"]: d for d in out_devs}

        in_keys = list(self.dsp_in_map.keys())
        out_keys = list(self.dsp_out_map.keys())

        if in_keys:
            self.dsp_in_cb.configure(values=in_keys)
            pref_in = next((k for k in in_keys if "usb" in k.lower() or "mikrofon" in k.lower()), in_keys[0])
            self.dsp_in_cb.set(pref_in)

        if out_keys:
            self.dsp_out_cb.configure(values=out_keys)
            # VB-Audio CABLE Input varsa otomatik seç
            pref_out = next((k for k in out_keys if "cable input" in k.lower() or "cable" in k.lower()), out_keys[0])
            self.dsp_out_cb.set(pref_out)

            # Monitör için kulaklık veya hoparlör seç
            self.dsp_mon_cb.configure(values=out_keys)
            pref_mon = next((k for k in out_keys if "kulakl" in k.lower() or "head" in k.lower() or "hoparl" in k.lower()), out_keys[-1])
            self.dsp_mon_cb.set(pref_mon)

    def _on_dsp_device_changed(self, _=None):
        if self.dsp_is_playing:
            # Akış aktifken cihaz değişirse kesintisiz yeniden başlat
            self._start_dsp_stream()

    def _on_toggle_monitor(self):
        enabled = self.mon_switch_var.get()
        mon_str = self.dsp_mon_cb.get()
        mon_dev = self.dsp_mon_map.get(mon_str)
        mon_id = mon_dev["index"] if mon_dev else None
        self.dsp_engine.set_monitor(enabled, mon_id)

    def _start_dsp_stream(self):
        in_str = self.dsp_in_cb.get()
        out_str = self.dsp_out_cb.get()
        in_dev = self.dsp_in_map.get(in_str)
        out_dev = self.dsp_out_map.get(out_str)

        if not in_dev or not out_dev:
            messagebox.showwarning("Cihaz Seçimi", "Lütfen geçerli bir Mikrofon ve Çıkış Cihazı (CABLE Input / Hoparlör) seçin.")
            return

        try:
            self.dsp_engine.start(in_dev["index"], out_dev["index"])
            # Monitör
            self._on_toggle_monitor()
            self.dsp_is_playing = True
            self.dsp_start_btn.configure(text="⏹ DSP Sesini Durdur", fg_color="#EF4444", hover_color="#DC2626")
            print(f"\n🚀 [DSP SES DÖNÜŞÜMÜ BAŞLATILDI - {self.dsp_engine.active_profile_name} PROFİLİ]")
            print(f"   Giriş: {in_str}")
            print(f"   Çıkış: {out_str}")
            print("=" * 60)
        except Exception as e:
            self.dsp_is_playing = False
            self.dsp_start_btn.configure(text="▶ DSP Ses Değiştiriciyi Başlat", fg_color="#10B981", hover_color="#059669")
            messagebox.showerror("Ses Akışı Hatası", f"DSP Ses Motoru başlatılamadı:\n{e}")

    def _stop_dsp_stream(self):
        self.dsp_engine.stop()
        self.dsp_is_playing = False
        self.dsp_start_btn.configure(text="▶ DSP Ses Değiştiriciyi Başlat", fg_color="#10B981", hover_color="#059669")

    def _toggle_dsp_audio(self):
        if self.dsp_is_playing:
            self._stop_dsp_stream()
        else:
            self._start_dsp_stream()

    # ══════════════════════════════════════════════════════════════════
    # MOD DEĞİŞİMİ: DSP MODU <-> AI MODU
    # ══════════════════════════════════════════════════════════════════
    def _on_mode_change(self, mode_str: str):
        if "DSP" in mode_str:
            self.current_mode = "dsp"
            self.ai_frame.pack_forget()
            self.dsp_frame.pack(fill="both", expand=True)
            self.adm_badge.configure(
                text="⚡ DSP MODU: SIFIR GPU & ANLIK TEPKİ",
                fg_color="#2c1a4d", text_color=C_TITLE
            )
            self.perf_lbl.configure(text="⏱️ Gecikme: ~5 ms  |  Tampon: 512  |  GPU: %0", text_color=C_CYAN)
        else:
            self.current_mode = "ai"
            self.dsp_frame.pack_forget()
            self.ai_frame.pack(fill="both", expand=True)
            self.adm_badge.configure(
                text="🛡️ RVC AI OYUNCU & YAYINCI KORUMASI AKTİF",
                fg_color="#133820", text_color=C_GREEN
            )
            self.perf_lbl.configure(text="⏱️ AI Modeli Bekleniyor...", text_color=C_MUTED)

    # ══════════════════════════════════════════════════════════════════
    # AI (RVC) MODU ARAYÜZÜ VE İŞLEVLERİ
    # ══════════════════════════════════════════════════════════════════
    def _build_ai_ui(self, parent):
        parent.columnconfigure(0, weight=5)
        parent.columnconfigure(1, weight=5)

        # ── SOL KOLON: Model, Cihazlar, Oyun Presetleri ──
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Model Seçimi
        c_mod = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_mod.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c_mod, text="🧠 Model Seçimi (RVC v1 / v2)", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(10, 4))

        self.pth_var = ctk.StringVar()
        self.idx_var = ctk.StringVar()

        def_pth = ROOT / "backend" / "models" / "weights" / "pqueen.pth"
        if def_pth.exists(): self.pth_var.set(str(def_pth))

        def_idx = ROOT / "backend" / "models" / "weights" / "added_IVF195_Flat_nprobe_1_pqueen_v2.index"
        if def_idx.exists(): self.idx_var.set(str(def_idx))

        self._add_file_picker(c_mod, "Model (.pth):", self.pth_var, "*.pth")
        self._add_file_picker(c_mod, "Index (.index):", self.idx_var, "*.index")

        self.load_btn = ctk.CTkButton(
            c_mod, text="📥 Modeli Yükle ve Aktifleştir", command=self._load_ai_model,
            font=FONT_H, fg_color=C_ACCENT, hover_color=C_HOVER, height=34
        )
        self.load_btn.pack(fill="x", padx=16, pady=(8, 12))

        # AI Ses Cihazları
        c_dev = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_dev.pack(fill="x", pady=(0, 10))
        
        dev_h = ctk.CTkFrame(c_dev, fg_color="transparent")
        dev_h.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(dev_h, text="🔊 AI Ses Cihazları", font=FONT_H, text_color=C_TITLE).pack(side="left")

        self.ai_api_filter_var = ctk.StringVar(value="MME")
        api_seg = ctk.CTkSegmentedButton(
            dev_h, values=["MME", "DirectSound", "WASAPI", "Tümü"],
            variable=self.ai_api_filter_var, command=lambda _: self._apply_ai_device_filter(),
            font=("Segoe UI", 9), height=22, selected_color=C_ACCENT, selected_hover_color=C_HOVER
        )
        api_seg.pack(side="right")

        ctk.CTkLabel(c_dev, text="Giriş (Mikrofon):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(4, 2))
        self.ai_in_cb = ctk.CTkComboBox(c_dev, values=["Taranıyor..."], command=lambda v: self._update_ai_device("serverInputDeviceId", v), font=FONT_B, height=28)
        self.ai_in_cb.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(c_dev, text="Çıkış (Hoparlör / Sanal Kablo):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(4, 2))
        self.ai_out_cb = ctk.CTkComboBox(c_dev, values=["Taranıyor..."], command=lambda v: self._update_ai_device("serverOutputDeviceId", v), font=FONT_B, height=28)
        self.ai_out_cb.pack(fill="x", padx=16, pady=(0, 6))

        # Sample Rate
        sr_frame = ctk.CTkFrame(c_dev, fg_color="transparent")
        sr_frame.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(sr_frame, text="Örnekleme Hızı (Sample Rate):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.ai_sr_cb = ctk.CTkComboBox(sr_frame, values=["48000", "44100"], width=90, font=FONT_NUM, command=lambda v: self._set_ai_sample_rate(int(v)))
        self.ai_sr_cb.pack(side="right")
        self.ai_sr_cb.set("48000")

        # Oyun & Yayın Önayarları
        c_game = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_game.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c_game, text="🎮 FiveM, Warzone & Yayın Önayarları", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(8, 4))

        preset_box = ctk.CTkFrame(c_game, fg_color="transparent")
        preset_box.pack(fill="x", padx=16, pady=(0, 10))
        preset_box.columnconfigure((0, 1, 2), weight=1)

        btn_p1 = ctk.CTkButton(
            preset_box, text="🎭 FiveM RP\n(112 Chunk / ~75ms)", font=("Segoe UI", 9, "bold"), height=36,
            fg_color="#334155", hover_color="#475569", command=lambda: self._apply_ai_preset(112, 16384)
        )
        btn_p1.grid(row=0, column=0, padx=2, sticky="ew")

        btn_p2 = ctk.CTkButton(
            preset_box, text="🎯 Warzone & FPS\n(192 Chunk / ~110ms)", font=("Segoe UI", 9, "bold"), height=36,
            fg_color=C_ACCENT, hover_color=C_HOVER, command=lambda: self._apply_ai_preset(192, 32768)
        )
        btn_p2.grid(row=0, column=1, padx=2, sticky="ew")

        btn_p3 = ctk.CTkButton(
            preset_box, text="🛡️ Yayıncı Güvenli\n(256 Chunk / ~150ms)", font=("Segoe UI", 9, "bold"), height=36,
            fg_color="#334155", hover_color="#475569", command=lambda: self._apply_ai_preset(256, 32768)
        )
        btn_p3.grid(row=0, column=2, padx=2, sticky="ew")

        # AI Başlat Butonu
        self.ai_start_btn = ctk.CTkButton(
            left, text="▶ AI Sesini Başlat (Yayın / Oyun Hazır)", command=self._toggle_ai_audio,
            font=("Segoe UI", 14, "bold"), fg_color="#10B981", hover_color="#059669", height=44, corner_radius=10
        )
        self.ai_start_btn.pack(fill="x", pady=4)

        # ── SAĞ KOLON: RVC Parametreleri ──
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        c_prm = ctk.CTkFrame(right, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_prm.pack(fill="both", expand=True)

        ctk.CTkLabel(c_prm, text="⚙️ RVC AI Ses Kalibrasyon Parametreleri", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(12, 4))

        self._add_ai_slider(c_prm, "Tune / Pitch Kaydırma (st)", "tran", -24, 24, 0, fmt="{:+.0f} st", is_int=True)
        self._add_ai_slider(c_prm, "Index Ratio (Aksan/Benzerlik)", "indexRatio", 0.0, 1.0, 0.75, fmt="{:.2f}")
        self._add_ai_slider(c_prm, "Protect Voiceless (Nefes Koruma)", "protect", 0.0, 0.5, 0.33, fmt="{:.2f}")
        self._add_ai_slider(c_prm, "Sessizlik Eşiği (Noise Gate - GPU Tasarrufu)", "silentThreshold", 0.0001, 0.01, 0.002, fmt="{:.4f}")
        self._add_ai_slider(c_prm, "Giriş Kazancı (Gain In)", "serverInputAudioGain", 0.1, 3.0, 1.0, fmt="{:.1f}x", is_server_device=True)
        self._add_ai_slider(c_prm, "Çıkış Kazancı (Gain Out)", "serverOutputAudioGain", 0.1, 3.0, 1.0, fmt="{:.1f}x", is_server_device=True)

        # F0 Algoritması
        ctk.CTkLabel(c_prm, text="Pitch Algoritması (F0 Detector):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(6, 2))
        self.f0_cb = ctk.CTkComboBox(
            c_prm, values=["rmvpe_onnx", "rmvpe", "fcpe", "crepe_tiny", "harvest", "dio"],
            command=self._on_ai_f0_change, font=FONT_B, height=28
        )
        self.f0_cb.pack(fill="x", padx=16, pady=(0, 6))
        self.f0_cb.set("rmvpe_onnx")

        # Chunk (Gecikme)
        ctk.CTkLabel(c_prm, text="Chunk (İşleme Hızı / Gecikme):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(6, 2))
        self.chk_cb = ctk.CTkComboBox(
            c_prm, values=["64", "96", "112", "128", "192", "256", "320", "512", "1024"],
            command=lambda v: self._update_ai_chunk(int(v)), font=FONT_B, height=28
        )
        self.chk_cb.pack(fill="x", padx=16, pady=(0, 6))
        self.chk_cb.set("192")

        # Extra
        ctk.CTkLabel(c_prm, text="Extra (Sınır Bozulma Koruması):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(6, 2))
        self.ext_cb = ctk.CTkComboBox(
            c_prm, values=["4096", "8192", "16384", "32768", "65536"],
            command=lambda v: self.vcm.update_settings("extraConvertSize", int(v)) if self.vcm else None,
            font=FONT_B, height=28
        )
        self.ext_cb.pack(fill="x", padx=16, pady=(0, 10))
        self.ext_cb.set("32768")

    def _init_ai_backend(self):
        try:
            Path("model_dir").mkdir(exist_ok=True)
            Path(UPLOAD_DIR).mkdir(exist_ok=True)

            params = VoiceChangerParams(
                model_dir="model_dir",
                content_vec_500="content_vec_500.pt",
                content_vec_500_onnx="content_vec_500.onnx",
                content_vec_500_onnx_on=False,
                hubert_base="hubert_base.pt",
                hubert_base_jp="hubert_base_jp.pt",
                hubert_soft="hubert_soft.pt",
                nsf_hifigan="nsf_hifigan.pt",
                crepe_onnx_full="crepe_onnx_full.onnx",
                crepe_onnx_tiny="crepe_onnx_tiny.onnx",
                rmvpe="rmvpe.pt",
                rmvpe_onnx="rmvpe.onnx",
                sample_mode="",
                whisper_tiny="whisper_tiny.pt",
            )
            VoiceChangerParamsManager.get_instance().setParams(params)
            self.vcm = VoiceChangerManager.get_instance(params)
            self.vcm.setEmitTo(self._on_ai_perf_emit)

            self._scan_ai_devices()
            print("[GUI] Ripleytia AI Ses Motoru başarıyla hazırlandı!")
        except Exception as e:
            print("[GUI] AI Motoru Arka Plan Hatası:", e)

    def _on_ai_perf_emit(self, perf):
        self.current_perf = perf

    def _scan_ai_devices(self):
        if not list_audio_device: return
        try:
            in_devs, out_devs = list_audio_device()
            self.ai_all_in_devs = in_devs
            self.ai_all_out_devs = out_devs
            self.after(0, self._apply_ai_device_filter)
        except Exception as e:
            print("[GUI] AI Cihaz tarama hatası:", e)

    def _apply_ai_device_filter(self):
        if not hasattr(self, "ai_all_in_devs"): return
        filter_mode = self.ai_api_filter_var.get()
        def match(dev):
            if filter_mode == "Tümü": return True
            return filter_mode.lower() in dev.hostAPI.lower()

        filtered_in = [d for d in self.ai_all_in_devs if match(d)]
        filtered_out = [d for d in self.ai_all_out_devs if match(d)]
        if not filtered_in: filtered_in = self.ai_all_in_devs
        if not filtered_out: filtered_out = self.ai_all_out_devs

        self.ai_in_map = {f"[{d.index}] {d.name}": d for d in filtered_in}
        self.ai_out_map = {f"[{d.index}] {d.name}": d for d in filtered_out}

        in_keys = list(self.ai_in_map.keys())
        out_keys = list(self.ai_out_map.keys())

        if in_keys:
            self.ai_in_cb.configure(values=in_keys)
            pref_in = next((k for k in in_keys if "usb" in k.lower() or "mikrofon" in k.lower()), in_keys[0])
            self.ai_in_cb.set(pref_in)
            self._update_ai_device("serverInputDeviceId", pref_in)

        if out_keys:
            self.ai_out_cb.configure(values=out_keys)
            pref_out = next((k for k in out_keys if "cable input" in k.lower() or "cable" in k.lower()), out_keys[0])
            self.ai_out_cb.set(pref_out)
            self._update_ai_device("serverOutputDeviceId", pref_out)

    def _update_ai_device(self, key, val_str):
        mapping = self.ai_in_map if "Input" in key else self.ai_out_map
        dev = mapping.get(val_str)
        if self.vcm and dev:
            self.vcm.serverDevice.update_settings(key, dev.index)
            if "wasapi" in dev.hostAPI.lower() or "directsound" in dev.hostAPI.lower():
                self._set_ai_sample_rate(48000)

    def _set_ai_sample_rate(self, sr: int):
        if self.vcm:
            self.vcm.serverDevice.update_settings("serverAudioSampleRate", sr)
            self.vcm.serverDevice.update_settings("serverInputAudioSampleRate", sr)
            self.vcm.serverDevice.update_settings("serverOutputAudioSampleRate", sr)
            self.ai_sr_cb.set(str(sr))

    def _update_ai_chunk(self, val: int):
        if self.vcm:
            self.vcm.serverDevice.update_settings("serverReadChunkSize", val)

    def _on_ai_f0_change(self, val: str):
        if self.vcm:
            self.vcm.update_settings("f0Detector", val)

    def _apply_ai_preset(self, chunk: int, extra: int):
        self.chk_cb.set(str(chunk))
        self.ext_cb.set(str(extra))
        self._update_ai_chunk(chunk)
        if self.vcm:
            self.vcm.update_settings("extraConvertSize", extra)

    def _add_file_picker(self, parent, label, var, ext):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=3)
        ctk.CTkLabel(f, text=label, font=FONT_B, text_color=C_SUB).pack(side="left")
        btn = ctk.CTkButton(
            f, text="Seç", width=50, height=24, font=FONT_B,
            fg_color="#334155", hover_color="#475569",
            command=lambda: var.set(filedialog.askopenfilename(filetypes=[("Dosya", ext)]))
        )
        btn.pack(side="right")
        lbl = ctk.CTkLabel(f, textvariable=var, text_color="#cbd5e1", font=("Consolas", 10), anchor="e")
        lbl.pack(side="right", padx=6, fill="x", expand=True)

    def _add_ai_slider(self, parent, label_text, key, min_v, max_v, default_v, fmt="{:.2f}", is_int=False, is_server_device=False):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(4, 0))
        ctk.CTkLabel(header, text=label_text, font=FONT_B, text_color=C_SUB).pack(side="left")
        val_lbl = ctk.CTkLabel(header, text=fmt.format(default_v), font=FONT_NUM, text_color=C_TITLE)
        val_lbl.pack(side="right")

        steps = max(1, int(max_v - min_v)) if is_int else max(20, int((max_v - min_v) * 50))
        sl = ctk.CTkSlider(parent, from_=min_v, to=max_v, number_of_steps=steps, height=16, button_color=C_ACCENT, button_hover_color=C_HOVER)
        sl.set(default_v)
        sl.pack(fill="x", padx=16, pady=(2, 4))

        def on_change(val):
            v = int(round(val)) if is_int else float(val)
            val_lbl.configure(text=fmt.format(v))
            if self.vcm:
                if is_server_device:
                    self.vcm.serverDevice.update_settings(key, v)
                else:
                    self.vcm.update_settings(key, v)
        sl.configure(command=on_change)

    def _load_ai_model(self):
        if not self.vcm:
            messagebox.showwarning("Bekleyin", "AI motoru hazırlanıyor, lütfen birkaç saniye bekleyin.")
            return
        pth = self.pth_var.get().strip()
        idx = self.idx_var.get().strip()
        if not pth or not os.path.exists(pth):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir .pth modeli seçin.")
            return

        up_dir = Path(UPLOAD_DIR)
        up_dir.mkdir(exist_ok=True)
        files_to_send = []
        try:
            pth_name = Path(pth).name
            shutil.copy(pth, up_dir / pth_name)
            files_to_send.append({"name": pth_name, "kind": "rvcModel", "dir": ""})
            if idx and os.path.exists(idx):
                idx_name = Path(idx).name
                shutil.copy(idx, up_dir / idx_name)
                files_to_send.append({"name": idx_name, "kind": "rvcIndex", "dir": ""})

            params = LoadModelParams(
                voiceChangerType="RVC", slot=0, isSampleMode=False, sampleId="",
                files=[LoadModelParamFile(**x) for x in files_to_send], params={"isHalf": True}
            )
            self.vcm.loadModel(params)
            self.vcm.update_settings("modelSlotIndex", 0)
            self.vcm.update_settings("silentThreshold", 0.002)
            self.vcm.update_settings("f0Detector", "rmvpe_onnx")
            self.ai_model_loaded = True
            messagebox.showinfo("Başarılı", "✓ Model Yüklendi ve Aktifleştirildi!")
        except Exception as e:
            messagebox.showerror("Model Hatası", str(e))

    def _toggle_ai_audio(self):
        if not self.vcm:
            messagebox.showwarning("Bekleyin", "AI motoru henüz hazır değil.")
            return
        if not self.ai_model_loaded:
            messagebox.showwarning("Model Gerekli", "Lütfen önce 'Modeli Yükle ve Aktifleştir' butonuna basarak bir model yükleyin!")
            return

        self.ai_is_playing = not self.ai_is_playing
        if self.ai_is_playing:
            self.vcm.serverDevice.update_settings("serverAudioStated", 1)
            self.ai_start_btn.configure(text="⏹ Durdur", fg_color="#EF4444", hover_color="#DC2626")
        else:
            self.vcm.serverDevice.update_settings("serverAudioStated", 0)
            self.ai_start_btn.configure(text="▶ AI Sesini Başlat (Yayın / Oyun Hazır)", fg_color="#10B981", hover_color="#059669")

    # ══════════════════════════════════════════════════════════════════
    # PERFORMANS VE CANLI BİLGİ DÖNGÜSÜ
    # ══════════════════════════════════════════════════════════════════
    def _perf_monitor_loop(self):
        if self.current_mode == "dsp":
            if self.dsp_is_playing:
                pname = self.dsp_engine.active_profile_name
                self.perf_lbl.configure(text=f"⏱️ DSP Aktif ({pname}) | Gecikme: ~5 ms | GPU: %0 | CPU: %0.2", text_color="#10B981")
            else:
                self.perf_lbl.configure(text="⏱️ DSP Durduruldu | Gecikme: ~5 ms | Tampon: 512 | GPU: %0", text_color=C_CYAN)
        else:
            if self.vcm and hasattr(self.vcm, "serverDevice"):
                is_active = getattr(self.vcm.serverDevice.settings, "serverAudioStated", 0) == 1
                perf = self.current_perf
                if not perf and hasattr(self.vcm.serverDevice, "performance"):
                    perf = self.vcm.serverDevice.performance

                if is_active and perf and len(perf) > 0 and (perf[0] > 0 or len(perf) > 1 and perf[1] > 0):
                    total_ms = round(perf[0] * 1000) if perf[0] < 5 else round(perf[0])
                    model_ms = round(perf[1] * 1000) if len(perf) > 1 and perf[1] < 5 else (round(perf[1]) if len(perf) > 1 else total_ms)
                    chunk = getattr(self.vcm.serverDevice.settings, "serverReadChunkSize", 192)
                    self.perf_lbl.configure(
                        text=f"⏱️ Toplam: {total_ms} ms | Model: {model_ms} ms | Chunk: {chunk}",
                        text_color="#10B981"
                    )
                elif is_active:
                    self.perf_lbl.configure(text="⏱️ AI Ses Akışı Aktif (İşleniyor...)", text_color=C_CYAN)
                else:
                    self.perf_lbl.configure(text="⏱️ Durduruldu | Model: -- ms | Tampon: --", text_color=C_MUTED)

        self.after(250, self._perf_monitor_loop)


if __name__ == "__main__":
    app = RipleytiaVoiceChangerApp()
    app.mainloop()
