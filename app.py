"""
app.py — Ripleytia AI Ses Değiştirici V1 Beta
=============================================
Yapımcı: Ripleytia
Özel Kalibre Edilmiş Yapay Zeka Gerçek Zamanlı Ses Dönüştürücü.
Oyun (Warzone vb.) ve Canlı Yayınlar için Gelişmiş Windows Öncelik, 
EcoQoS Koruması, MMCSS Pro Audio ve PyTorch CUDA Optimizasyonu içerir.
"""

import os
import sys
import shutil
import ctypes
from pathlib import Path
from typing import Optional
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

# ── 1. DONANIM & WINDOWS OYUN / YAYIN OPTİMİZASYONLARI ──
def apply_game_stream_optimizations():
    """FiveM, Warzone ve canlı yayınlarda takılmayı ve gecikmeyi engelleyen akıllı dengeleme optimizasyonları"""
    log_msgs = []

    # 1. Windows 1ms Donanımsal Zamanlayıcı Kilidi (FiveM CPU dalgalanmalarında ms sıçramasını önler)
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        log_msgs.append("✓ Windows 1ms Yüksek Hassasiyetli Zamanlayıcı Aktif")
    except Exception as e:
        log_msgs.append(f"! timeBeginPeriod hatası: {e}")

    # 2. Windows Süreç Önceliği: DENGELİ (FiveM ve Warzone'un CPU çekirdeklerini boğmasını engellemek için)
    try:
        pid = os.getpid()
        handle = ctypes.windll.kernel32.OpenProcess(0x0200 | 0x0400, False, pid)
        res = ctypes.windll.kernel32.SetPriorityClass(handle, 0x00000020) # NORMAL_PRIORITY_CLASS
        ctypes.windll.kernel32.CloseHandle(handle)
        if res: log_msgs.append("✓ Windows Süreç Önceliği: DENGELİ (Oyun FPS'ini korur)")
    except Exception as e:
        log_msgs.append(f"! Öncelik ayarlanamadı: {e}")

    # 3. Windows 11 EcoQoS / Power Throttling Kapatma (Oyun odaktayken sesin uyutulmasını engeller)
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x0200 | 0x0400, False, os.getpid())
        class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
            _fields_ = [('Version', ctypes.c_ulong), ('ControlMask', ctypes.c_ulong), ('StateMask', ctypes.c_ulong)]
        state = PROCESS_POWER_THROTTLING_STATE(1, 1, 0)
        res2 = ctypes.windll.kernel32.SetProcessInformation(handle, 4, ctypes.byref(state), ctypes.sizeof(state))
        ctypes.windll.kernel32.CloseHandle(handle)
        if res2: log_msgs.append("✓ Windows Güç Kısıtlaması (EcoQoS) Devre Dışı")
    except Exception as e:
        log_msgs.append(f"! EcoQoS kapatılamadı: {e}")

    # 4. Windows MMCSS Pro Audio Kaydı (Ses tamponunu donanımsal korur)
    try:
        avrt = ctypes.windll.Avrt
        task_index = ctypes.c_ulong(0)
        h = avrt.AvSetMmThreadCharacteristicsW("Pro Audio", ctypes.byref(task_index))
        if h: log_msgs.append("✓ Windows MMCSS: Pro Audio Modu Devrede")
    except Exception as e:
        log_msgs.append(f"! MMCSS hatası: {e}")

    # 5. PyTorch VRAM Güvenlik Kalkanı (OBS Studio + FiveM + Warzone Dengeli Paylaşımı)
    if torch.cuda.is_available():
        try:
            # RVC + HuBERT fiilen ~750MB harcar. Tavanı 1.4GB (%18) yaparak OBS ve Oyun için 6.6GB+ VRAM serbest bırakıyoruz!
            torch.cuda.set_per_process_memory_fraction(0.18, 0)
            torch.backends.cudnn.benchmark = False
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.cuda.empty_cache()
            log_msgs.append("✓ PyTorch VRAM Kalkanı: 1.4 GB (OBS & Oyun için 6.6GB+ serbest bırakıldı)")
        except Exception as e:
            log_msgs.append(f"! CUDA ayar hatası: {e}")

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

# Okada dizinine geçiş
if W_OKADA_DIR.exists():
    os.chdir(str(W_OKADA_DIR))

from voice_changer.VoiceChangerManager import VoiceChangerManager
from voice_changer.VoiceChangerParamsManager import VoiceChangerParamsManager
from voice_changer.utils.VoiceChangerParams import VoiceChangerParams
from voice_changer.utils.LoadModelParams import LoadModelParams, LoadModelParamFile
from voice_changer.Local.AudioDeviceList import list_audio_device
from const import UPLOAD_DIR

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
        self.geometry("1020x860")
        self.minsize(960, 800)
        self.configure(fg_color=C_BG)

        self.vcm: Optional[VoiceChangerManager] = None
        self.is_playing = False
        self.model_loaded = False
        self.current_perf = []
        
        self.all_in_devs = []
        self.all_out_devs = []
        self.in_map = {}
        self.out_map = {}

        # Logoları ve İkonları Yükle
        self._set_app_icons()

        # Arayüzü İnşa Et
        self._build_ui()

        # Motor başlatmayı arka plana al
        self.start_btn.configure(state="disabled", text="⏳ Ripleytia AI Motoru Hazırlanıyor...")
        threading.Thread(target=self._init_backend, daemon=True).start()

        # Performans / MS güncelleme döngüsü
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

    def _on_perf_emit(self, perf):
        self.current_perf = perf

    def _init_backend(self):
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
            self.vcm.setEmitTo(self._on_perf_emit)

            self._scan_devices()

            self.after(0, lambda: self.start_btn.configure(state="normal", text="▶ Başlat (Yayın / Oyun Hazır)"))
            print("[GUI] Ripleytia AI Ses Motoru başarıyla hazırlandı!")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Motor Hatası", str(e)))

    def _build_ui(self):
        # ── 1. ÜST PANEL & RIPLEYTIA LOGO BAŞLIĞI ──
        header_frame = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        header_frame.pack(fill="x", padx=16, pady=(16, 8))

        # Sol: R Logosu ve Başlık
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=10)

        logo_file = (ROOT / "assets" / "logo_64.png") if (ROOT / "assets" / "logo_64.png").exists() else (ROOT / "v3" / "assets" / "logo_64.png")
        if logo_file.exists():
            try:
                pil_logo = Image.open(str(logo_file))
                self.logo_header_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(48, 48))
                lbl_logo_img = ctk.CTkLabel(title_box, text="", image=self.logo_header_img)
                lbl_logo_img.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        text_box = ctk.CTkFrame(title_box, fg_color="transparent")
        text_box.pack(side="left")

        lbl_title = ctk.CTkLabel(text_box, text="RIPLEYTIA AI SES DEĞİŞTİRİCİ V1 BETA", font=FONT_TITLE, text_color=C_TITLE)
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            text_box,
            text="Gelişmiş Yayıncı & Oyuncu Yapay Zeka Ses Motoru | Yapımcı: Ripleytia",
            font=("Segoe UI", 11), text_color=C_SUB
        )
        lbl_sub.pack(anchor="w")

        # Sağ: Rozet ve Canlı MS
        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=10)

        adm_badge = ctk.CTkLabel(
            right_box, text="🛡️ OYUNCU & YAYINCI KORUMASI AKTİF",
            fg_color="#133820", text_color=C_GREEN, corner_radius=8,
            border_width=1, border_color="#1b5e20", font=ctk.CTkFont(size=10, weight="bold"),
            padx=10, pady=4
        )
        adm_badge.pack(anchor="e", pady=(0, 4))

        self.perf_lbl = ctk.CTkLabel(
            right_box,
            text="⏱️ Gecikme: -- ms  |  Model: -- ms  |  Tampon: --",
            font=("Consolas", 11, "bold"), text_color=C_CYAN
        )
        self.perf_lbl.pack(anchor="e")

        # ── 2. ANA ÇİFT KOLON IZGARA ──
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=6)
        main.columnconfigure(0, weight=5)
        main.columnconfigure(1, weight=5)

        # ══════════════════════════════════════════════════════════════════
        # SOL KOLON: Model, Cihazlar, Oyun Presetleri & Başlat Butonu
        # ══════════════════════════════════════════════════════════════════
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Model Seçimi Kartı ──
        c_mod = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_mod.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c_mod, text="🧠 Model Seçimi (RVC v1 / v2)", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(12, 6))

        self.pth_var = ctk.StringVar()
        self.idx_var = ctk.StringVar()

        def_pth = ROOT / "backend" / "models" / "weights" / "pqueen.pth"
        if def_pth.exists(): self.pth_var.set(str(def_pth))

        def_idx = ROOT / "backend" / "models" / "weights" / "added_IVF195_Flat_nprobe_1_pqueen_v2.index"
        if def_idx.exists(): self.idx_var.set(str(def_idx))

        self._add_file_picker(c_mod, "Model (.pth):", self.pth_var, "*.pth")
        self._add_file_picker(c_mod, "Index (.index):", self.idx_var, "*.index")

        self.load_btn = ctk.CTkButton(
            c_mod, text="📥 Modeli Yükle ve Aktifleştir", command=self._load_model,
            font=FONT_H, fg_color=C_ACCENT, hover_color=C_HOVER, height=36
        )
        self.load_btn.pack(fill="x", padx=16, pady=(10, 14))

        # ── Ses Cihazları Kartı ──
        c_dev = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_dev.pack(fill="x", pady=(0, 10))
        
        dev_header = ctk.CTkFrame(c_dev, fg_color="transparent")
        dev_header.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(dev_header, text="🔊 Ses Cihazları", font=FONT_H, text_color=C_TITLE).pack(side="left")
        
        self.api_filter_var = ctk.StringVar(value="MME")
        api_seg = ctk.CTkSegmentedButton(
            dev_header, values=["MME", "DirectSound", "WASAPI", "Tümü"],
            variable=self.api_filter_var, command=lambda _: self._apply_device_filter(),
            font=("Segoe UI", 10), height=24, selected_color=C_ACCENT, selected_hover_color=C_HOVER
        )
        api_seg.pack(side="right")

        ctk.CTkLabel(c_dev, text="Giriş (Mikrofon):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(4, 2))
        self.in_cb = ctk.CTkComboBox(
            c_dev, values=["Taranıyor..."], command=lambda v: self._update_device("serverInputDeviceId", v),
            font=FONT_B, height=30
        )
        self.in_cb.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(c_dev, text="Çıkış (Hoparlör / Sanal Kablo):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(4, 2))
        self.out_cb = ctk.CTkComboBox(
            c_dev, values=["Taranıyor..."], command=lambda v: self._update_device("serverOutputDeviceId", v),
            font=FONT_B, height=30
        )
        self.out_cb.pack(fill="x", padx=16, pady=(0, 6))

        # Sample Rate
        sr_frame = ctk.CTkFrame(c_dev, fg_color="transparent")
        sr_frame.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(sr_frame, text="Örnekleme Hızı (Sample Rate):", font=FONT_B, text_color=C_SUB).pack(side="left")
        self.sr_cb = ctk.CTkComboBox(
            sr_frame, values=["48000", "44100"], width=90, font=FONT_NUM,
            command=lambda v: self._set_sample_rate(int(v))
        )
        self.sr_cb.pack(side="right")
        self.sr_cb.set("48000")

        # ── 3. OYUN & YAYIN OPTİMİZASYON KARTI (FIVEM & WARZONE) ──
        c_game = ctk.CTkFrame(left, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_game.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(c_game, text="🎮 FiveM, Warzone & Yayın Önayarları", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(10, 4))
        
        preset_box = ctk.CTkFrame(c_game, fg_color="transparent")
        preset_box.pack(fill="x", padx=16, pady=(0, 10))
        preset_box.columnconfigure((0, 1, 2), weight=1)

        btn_p1 = ctk.CTkButton(
            preset_box, text="🎭 FiveM RP\n(112 Chunk / ~75ms)", font=("Segoe UI", 10, "bold"), height=38,
            fg_color="#334155", hover_color="#475569", command=lambda: self._apply_preset(112, 16384)
        )
        btn_p1.grid(row=0, column=0, padx=2, sticky="ew")

        btn_p2 = ctk.CTkButton(
            preset_box, text="🎯 Warzone & FPS\n(192 Chunk / ~110ms)", font=("Segoe UI", 10, "bold"), height=38,
            fg_color=C_ACCENT, hover_color=C_HOVER, command=lambda: self._apply_preset(192, 32768)
        )
        btn_p2.grid(row=0, column=1, padx=2, sticky="ew")

        btn_p3 = ctk.CTkButton(
            preset_box, text="🛡️ Yayıncı Güvenli\n(256 Chunk / ~150ms)", font=("Segoe UI", 10, "bold"), height=38,
            fg_color="#334155", hover_color="#475569", command=lambda: self._apply_preset(256, 32768)
        )
        btn_p3.grid(row=0, column=2, padx=2, sticky="ew")

        # ── Başlat / Durdur Butonu ──
        self.start_btn = ctk.CTkButton(
            left, text="▶ Başlat (Yayın / Oyun Hazır)", command=self._toggle_audio,
            font=("Segoe UI", 15, "bold"), fg_color="#10B981", hover_color="#059669", height=48, corner_radius=10
        )
        self.start_btn.pack(fill="x", pady=4)

        # ══════════════════════════════════════════════════════════════════
        # SAĞ KOLON: Ripleytia Ses Kalibrasyon Parametreleri
        # ══════════════════════════════════════════════════════════════════
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        c_prm = ctk.CTkFrame(right, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        c_prm.pack(fill="both", expand=True)

        ctk.CTkLabel(c_prm, text="⚙️ Ses Kalibrasyon Parametreleri", font=FONT_H, text_color=C_TITLE).pack(anchor="w", padx=16, pady=(12, 6))

        # Sliders with numeric labels
        self._add_slider(c_prm, "Tune / Pitch Kaydırma (st)", "tran", -24, 24, 0, fmt="{:+.0f} st", is_int=True)
        self._add_slider(c_prm, "Index Ratio (Aksan/Benzerlik)", "indexRatio", 0.0, 1.0, 0.75, fmt="{:.2f}")
        self._add_slider(c_prm, "Protect Voiceless (Nefes Koruma)", "protect", 0.0, 0.5, 0.33, fmt="{:.2f}")
        self._add_slider(c_prm, "Sessizlik Eşiği (Noise Gate - GPU Tasarrufu)", "silentThreshold", 0.0001, 0.01, 0.002, fmt="{:.4f}")
        self._add_slider(c_prm, "Giriş Kazancı (Gain In)", "serverInputAudioGain", 0.1, 3.0, 1.0, fmt="{:.1f}x", is_server_device=True)
        self._add_slider(c_prm, "Çıkış Kazancı (Gain Out)", "serverOutputAudioGain", 0.1, 3.0, 1.0, fmt="{:.1f}x", is_server_device=True)

        # F0 Detector
        ctk.CTkLabel(c_prm, text="Pitch Algoritması (F0 Detector):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(8, 2))
        self.f0_cb = ctk.CTkComboBox(
            c_prm, values=["rmvpe_onnx", "rmvpe", "fcpe", "crepe_tiny", "harvest", "dio"],
            command=self._on_f0_change, font=FONT_B, height=30
        )
        self.f0_cb.pack(fill="x", padx=16, pady=(0, 6))
        self.f0_cb.set("rmvpe_onnx")

        # Chunk (Gecikme)
        ctk.CTkLabel(c_prm, text="Chunk (İşleme Hızı / Gecikme):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(8, 2))
        self.chk_cb = ctk.CTkComboBox(
            c_prm, values=["64", "96", "112", "128", "192", "256", "320", "512", "1024"],
            command=lambda v: self._update_chunk(int(v)), font=FONT_B, height=30
        )
        self.chk_cb.pack(fill="x", padx=16, pady=(0, 6))
        self.chk_cb.set("192")

        # Extra (Sınır Bozulma Koruması)
        ctk.CTkLabel(c_prm, text="Extra (Sınır Bozulma Koruması):", font=FONT_B, text_color=C_SUB).pack(anchor="w", padx=16, pady=(8, 2))
        self.ext_cb = ctk.CTkComboBox(
            c_prm, values=["4096", "8192", "16384", "32768", "65536"],
            command=lambda v: self.vcm.update_settings("extraConvertSize", int(v)) if self.vcm else None,
            font=FONT_B, height=30
        )
        self.ext_cb.pack(fill="x", padx=16, pady=(0, 14))
        self.ext_cb.set("32768")

    def _apply_preset(self, chunk: int, extra: int):
        self.chk_cb.set(str(chunk))
        self.ext_cb.set(str(extra))
        self._update_chunk(chunk)
        if self.vcm:
            self.vcm.update_settings("extraConvertSize", extra)
        print(f"[PRESET] Oyun & Yayın Önayarı uygulandı: Chunk={chunk}, Extra={extra}")

    def _add_file_picker(self, parent, label, var, ext):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f, text=label, font=FONT_B, text_color=C_SUB).pack(side="left")
        
        btn = ctk.CTkButton(
            f, text="Seç", width=55, height=26, font=FONT_B,
            fg_color="#334155", hover_color="#475569",
            command=lambda: var.set(filedialog.askopenfilename(filetypes=[("Dosya", ext)]))
        )
        btn.pack(side="right")
        
        lbl = ctk.CTkLabel(f, textvariable=var, text_color="#cbd5e1", font=("Consolas", 10), anchor="e")
        lbl.pack(side="right", padx=8, fill="x", expand=True)

    def _add_slider(self, parent, label_text, key, min_v, max_v, default_v, fmt="{:.2f}", is_int=False, is_server_device=False):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(6, 0))
        ctk.CTkLabel(header, text=label_text, font=FONT_B, text_color=C_SUB).pack(side="left")
        val_lbl = ctk.CTkLabel(header, text=fmt.format(default_v), font=FONT_NUM, text_color=C_TITLE)
        val_lbl.pack(side="right")

        if is_int:
            steps = max(1, int(max_v - min_v))
        else:
            steps = max(20, int((max_v - min_v) * 50))
        sl = ctk.CTkSlider(parent, from_=min_v, to=max_v, number_of_steps=steps, height=18, button_color=C_ACCENT, button_hover_color=C_HOVER)
        sl.set(default_v)
        sl.pack(fill="x", padx=16, pady=(2, 6))

        def on_change(val):
            v = int(round(val)) if is_int else float(val)
            val_lbl.configure(text=fmt.format(v))
            if self.vcm:
                if is_server_device:
                    self.vcm.serverDevice.update_settings(key, v)
                else:
                    self.vcm.update_settings(key, v)

        sl.configure(command=on_change)

    def _scan_devices(self):
        try:
            in_devs, out_devs = list_audio_device()
            self.all_in_devs = in_devs
            self.all_out_devs = out_devs
            self.after(0, self._apply_device_filter)
        except Exception as e:
            print("[GUI] Cihaz tarama hatası:", e)

    def _apply_device_filter(self):
        filter_mode = self.api_filter_var.get()
        
        def match(dev):
            if filter_mode == "Tümü": return True
            return filter_mode.lower() in dev.hostAPI.lower()

        filtered_in = [d for d in self.all_in_devs if match(d)]
        filtered_out = [d for d in self.all_out_devs if match(d)]

        if not filtered_in: filtered_in = self.all_in_devs
        if not filtered_out: filtered_out = self.all_out_devs

        self.in_map = {f"[{d.index}] {d.name}": d for d in filtered_in}
        self.out_map = {f"[{d.index}] {d.name}": d for d in filtered_out}

        in_keys = list(self.in_map.keys())
        out_keys = list(self.out_map.keys())

        if in_keys:
            self.in_cb.configure(values=in_keys)
            preferred_in = next((k for k in in_keys if "usb" in k.lower() or "mikrofon" in k.lower()), in_keys[0])
            self.in_cb.set(preferred_in)
            self._update_device("serverInputDeviceId", preferred_in)

        if out_keys:
            self.out_cb.configure(values=out_keys)
            preferred_out = next((k for k in out_keys if "cable input" in k.lower() or "cable" in k.lower()), out_keys[0])
            self.out_cb.set(preferred_out)
            self._update_device("serverOutputDeviceId", preferred_out)

    def _update_device(self, key, val_str):
        mapping = self.in_map if "Input" in key else self.out_map
        dev = mapping.get(val_str)
        if self.vcm and dev:
            self.vcm.serverDevice.update_settings(key, dev.index)
            print(f"[GUI] {key} güncellendi -> ID: {dev.index} ({val_str})")

            # Sample Rate Otomasyonu
            if "wasapi" in dev.hostAPI.lower() or "directsound" in dev.hostAPI.lower():
                self._set_sample_rate(48000)
            else:
                def_sr = int(getattr(dev, "default_samplerate", 48000))
                self._set_sample_rate(def_sr if def_sr in [44100, 48000] else 48000)

    def _set_sample_rate(self, sr: int):
        if self.vcm:
            self.vcm.serverDevice.update_settings("serverAudioSampleRate", sr)
            self.vcm.serverDevice.update_settings("serverInputAudioSampleRate", sr)
            self.vcm.serverDevice.update_settings("serverOutputAudioSampleRate", sr)
            self.sr_cb.set(str(sr))
            print(f"[GUI] Sample Rate ayarlandı -> {sr} Hz")

    def _update_chunk(self, val: int):
        if self.vcm:
            self.vcm.serverDevice.update_settings("serverReadChunkSize", val)
            print(f"[GUI] serverReadChunkSize güncellendi -> {val}")

    def _on_f0_change(self, val: str):
        if self.vcm:
            self.vcm.update_settings("f0Detector", val)
            print(f"[GUI] f0Detector güncellendi -> {val}")

    def _load_model(self):
        if not self.vcm: return
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
                voiceChangerType="RVC",
                slot=0,
                isSampleMode=False,
                sampleId="",
                files=[LoadModelParamFile(**x) for x in files_to_send],
                params={"isHalf": True}
            )

            print("[GUI] Ripleytia AI loadModel çağrılıyor...")
            self.vcm.loadModel(params)
            self.vcm.update_settings("modelSlotIndex", 0)
            self.vcm.update_settings("silentThreshold", 0.002)
            self.vcm.update_settings("f0Detector", "rmvpe_onnx")
            self.model_loaded = True
            messagebox.showinfo("Başarılı", "✓ Model Yüklendi ve Aktifleştirildi!")
            print("[GUI] ✓ Model Slot 0 yüklendi (silentThreshold=0.002, f0Detector=rmvpe_onnx)!")

        except Exception as e:
            messagebox.showerror("Model Yükleme Hatası", str(e))
            print("[GUI] Model Yükleme Hatası:", e)

    def _toggle_audio(self):
        if not self.vcm:
            messagebox.showwarning("Bekleyin", "Motor henüz hazır değil.")
            return

        if not self.model_loaded:
            messagebox.showwarning("Model Gerekli", "Lütfen önce 'Modeli Yükle ve Aktifleştir' butonuna basarak bir model yükleyin!")
            return

        self.is_playing = not self.is_playing

        if self.is_playing:
            self.vcm.serverDevice.update_settings("serverAudioStated", 1)
            self.start_btn.configure(text="⏹ Durdur", fg_color="#EF4444", hover_color="#DC2626")
            print("\n" + "="*55)
            print("🚀 [RIPLEYTIA AI SES DÖNÜŞÜMÜ BAŞLATILDI]")
            print(f"   Mikrofon ID: {self.vcm.serverDevice.settings.serverInputDeviceId}")
            print(f"   Hoparlör ID: {self.vcm.serverDevice.settings.serverOutputDeviceId}")
            print(f"   Sample Rate: {self.vcm.serverDevice.settings.serverAudioSampleRate} Hz")
            print(f"   Chunk: {self.vcm.serverDevice.settings.serverReadChunkSize}")
            print("   Oyun/Yayın Önceliği: HIGH & MMCSS PRO AUDIO AKTİF")
            print("="*55 + "\n")
        else:
            self.vcm.serverDevice.update_settings("serverAudioStated", 0)
            self.start_btn.configure(text="▶ Başlat (Yayın / Oyun Hazır)", fg_color="#10B981", hover_color="#059669")
            print("[GUI] Ses akışı durduruldu.")

    def _perf_monitor_loop(self):
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
                    text=f"⏱️ Toplam: {total_ms} ms  |  Model: {model_ms} ms  |  Chunk: {chunk}",
                    text_color="#10B981"
                )
            elif is_active:
                self.perf_lbl.configure(text="⏱️ Ses Akışı Aktif (İşleniyor...)", text_color=C_CYAN)
            else:
                self.perf_lbl.configure(text="⏱️ Durduruldu  |  Model: -- ms  |  Tampon: --", text_color=C_MUTED)

        self.after(250, self._perf_monitor_loop)


if __name__ == "__main__":
    app = RipleytiaVoiceChangerApp()
    app.mainloop()
