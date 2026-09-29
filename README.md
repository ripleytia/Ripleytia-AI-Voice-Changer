# 🎙️ Ripleytia AI Ses Değiştirici V1 Beta
> **Gelişmiş Yayıncı & Oyuncu Yapay Zeka Gerçek Zamanlı Ses Dönüştürücü**  
> **Yapımcı:** Ripleytia

![Ripleytia AI Voice Changer Ekran Görüntüsü](assets/preview.png)

---

### ⚠️ ÖNEMLİ BİLGİLENDİRME (BETA SÜRÜMÜ)
> [!WARNING]
> **Bu uygulama henüz V1 BETA aşamasındadır.**
> Geliştirilme süreci devam etmekte olup; farklı donanım konfigürasyonlarında, sanal ses kablosu sürücülerinde veya yoğun oyun senaryolarında beklenmedik hatalar, ses kesilmeleri ya da sürücü uyumsuzlukları ile karşılaşabilirsiniz. Hata bildirimlerinizi GitHub Issues sekmesinden iletebilirsiniz.

---

### ✨ Öne Çıkan Özellikler

* **⚡ Gömülü Hızlı DSP / 4 Ses Profili (Yapay Zekasız & %0 GPU Yükü)**:
  * **Kadın, Erkek, Çocuk ve Robot** olmak üzere 4 hazır dahili ses profili.
  * Hiçbir yapay zeka (AI) modeli gerektirmeden, **ultra düşük gecikme (~5 ms)** ile anlık çalışır.
  * Ekran kartınız (GPU) %0 kullanımda kalır; tüm GPU gücü FiveM, Warzone ve OBS yayınına ayrılır.
* **🎛️ Detaylı 5-Bant Parametrik Ekolayzır (Parametric EQ)**:
  * Her profil için özelleştirilebilir frekans bantları (Düşük, Orta, Yüksek).
  * Filtre tipleri: **Peaking (Çan), Low-Shelf (Düşük Raf), High-Shelf (Yüksek Raf), Low-Pass, High-Pass, Band-Pass, Notch (Çentik)**.
  * Hassas Kazanç (Gain dB) ve Q Faktörü (Bant Genişliği) ayarları.
* **🎵 Donanımsal Pitch & Siber Robot Modülatörü**:
  * Çift gecikme hatlı pürüzsüz perde kaydırma (Semitone & Fine-tune cents).
  * Halka modülasyonu (Ring Modulation) ve metalik tarak filtresi (Comb Resonator) ile siborg robot sesi.
* **🗜️ Vokal Dinamik Kompresörü & Noise Gate**:
  * Eşik (Threshold), Sıkıştırma Oranı (Ratio), Attack, Release ve Makyaj Kazancı (Makeup Gain).
  * Arka plan klavye, fan ve oda gürültüsünü konuşulmadığı anlarda tamamen kesen akıllı gürültü kapısı.
* **🔊 Windows Sanal Ses Kablosu (CABLE Input) & Kulaklık Monitörü**:
  * Sesi doğrudan **VB-Audio Virtual Cable (CABLE Input)** cihazına aktararak Discord, FiveM, TeamSpeak, OBS ve Warzone'a tek tıkla iletme.
  * **"Kendi Sesimi Duy"** kulaklık monitörü ile sesinizin nasıl gittiğini anlık olarak dinleme.
* **🤖 Ripleytia AI (RVC Model Klonlama) Modu**:
  * İstendiğinde tek tıkla gelişmiş RVC yapay zeka model dönüştürme moduna geçiş.
  * FiveM RP, Warzone ve Yayıncı profilleri ile 1ms Windows zamanlayıcı ve VRAM kalkanı.
* **🟣 Ripleytia Gothic Mor Tasarımı**: Özel karanlık mor siberpunk arayüz ve canlı MS performans monitörü.

---

### 🚀 Hızlı Başlangıç & Kurulum

#### 1. Gereksinimler
- **İşletim Sistemi**: Windows 10 / 11 (64-bit)
- **Ekran Kartı**: NVIDIA RTX / GTX (CUDA Desteği Önerilir)
- **Python**: Python 3.10.x önerilir
- **Sanal Ses Kablosu**: VB-Audio Virtual Cable (Discord, OBS ve oyunlara sesi aktarmak için)

#### 2. Kurulum ve Çalıştırma (Tek Tıkla Otomatik)
1. Bu depoyu indirin (ZIP veya Git klonu):
   ```bash
   git clone https://github.com/ripleytia/Ripleytia-AI-Voice-Changer.git
   cd Ripleytia-AI-Voice-Changer
   ```
2. **`run.bat`** dosyasına çift tıklayın!
   * **Akıllı Otomatik Kurulum:** Sistem ilk açılışta Python ortamını, GPU (CUDA) PyTorch desteğini ve tüm kütüphaneleri otomatik olarak algılayıp kurar.
   * Dilerseniz manuel olarak önce `install.bat` dosyasını çalıştırabilir, ardından `run.bat` ile açabilirsiniz.

---

### 🎮 Hazır Oyun & Yayın Profilleri

| Profil | Chunk | Hedef Gecikme (ms) | En Uygun Senaryo |
| :--- | :---: | :---: | :--- |
| **🎭 FiveM RP** | 112 | ~75 ms | FiveM, GTA RP, Discord sohbeti (En hızlı yanıt) |
| **🎯 Warzone & FPS** | 192 | ~110 ms | Warzone, Apex Legends, Valorant vb. rekabetçi oyunlar |
| **🛡️ Yayıncı Güvenli** | 256 | ~150 ms | OBS üzerinden yüksek bitrate yayınlar |

---

### 📜 Lisans & Teşekkür
* Bu proje **MIT Lisansı** altında lisanslanmıştır.
* **Yapımcı:** Ripleytia
* Taban motor mimarisinde W-Okada açık kaynak RVC araştırmalarından esinlenilmiş, oyuncular ve yayıncılar için optimize edilmiştir.
