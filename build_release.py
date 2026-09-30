import os
import sys
import subprocess
import shutil

def build_executable():
    print("=========================================================")
    print("  Ripleytia AI Ses Değiştirici - PyInstaller Build Script")
    print("=========================================================")

    # Dizinleri belirle
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")
    APP_SCRIPT = os.path.join(BASE_DIR, "app.py")

    if not os.path.exists(ASSETS_DIR):
        print(f"[UYARI] '{ASSETS_DIR}' klasörü bulunamadı! İkonlar eksik olabilir.")
    
    # Derleme öncesi eski derleme artıklarını temizle
    for folder in ["build", "dist"]:
        path = os.path.join(BASE_DIR, folder)
        if os.path.exists(path):
            print(f"[*] Eski '{folder}' klasörü temizleniyor...")
            shutil.rmtree(path)

    # PyInstaller komut argümanlarını hazırla
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "Ripleytia_AI_Ses_Degistirici",
        "--windowed",                 # Konsol penceresini gizle (--noconsole)
        "--onefile",                  # Tek bir çalıştırılabilir dosya
        "--clean",                    # Geçici build dosyalarını temizle
        f"--add-data={ASSETS_DIR};assets",  # Assets klasörünü EXE'ye göm
        f"--add-data={os.path.join(BASE_DIR, 'dsp_profiles.json')};.", # Profilleri göm
    ]

    # Eğer ikon varsa, komuta ekle
    if os.path.exists(ICON_PATH):
        pyinstaller_args.append(f"--icon={ICON_PATH}")

    # Ana betiği komuta ekle
    pyinstaller_args.append(APP_SCRIPT)

    print("\n[*] PyInstaller çalıştırılıyor... Lütfen bekleyin, bu işlem birkaç dakika sürebilir.\n")
    
    try:
        # PyInstaller'ı çalıştır
        subprocess.check_call(pyinstaller_args, cwd=BASE_DIR)
        print("\n[BAŞARILI] Derleme tamamlandı! EXE dosyanız 'dist' klasöründedir.")
        
        # Kullanıcıyı Inno Setup'a yönlendir
        print("\nSonraki Adım: 'dist' klasöründeki EXE dosyasını installer.iss kullanarak Inno Setup ile paketleyebilirsiniz.")
    except subprocess.CalledProcessError as e:
        print(f"\n[HATA] Derleme sırasında hata oluştu: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
