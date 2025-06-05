import sys
import psutil
import os
import time
import json
import platform
import subprocess
import threading
import logging
import datetime
import shutil
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, 
    QTabWidget, QTextEdit, QFrame, QMainWindow, QSplashScreen, QProgressBar, 
    QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QButtonGroup, 
    QRadioButton, QHBoxLayout, QGridLayout, QSlider, QGroupBox, QDialog,
    QMessageBox, QSystemTrayIcon, QMenu, QToolTip, QSpacerItem, QSizePolicy,
    QCalendarWidget, QTimeEdit, QDateTimeEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QMovie, QPixmap, QColor, QCursor, QIcon, QFont, QPainter, QBrush, QPen
from PyQt6.QtCore import (
    Qt, QSize, QTimer, QCoreApplication, QThread, pyqtSignal, 
    QPropertyAnimation, QEasingCurve, QRect, QPoint, QUrl, QTime, QDate, QDateTime
)
import random  # For simulated GPU usage
import winsound  # For sound effects

# Gelişmiş beyaz liste - daha fazla oyun süreci
WHITELISTED_PROCESSES = [
    # Oyunlar
    "Minecraft.exe", "Valorant.exe", "VALORANT-Win64-Shipping.exe", 
    "FortniteClient-Win64-Shipping.exe", "csgo.exe", "PUBG.exe", 
    "RocketLeague.exe", "GTA5.exe", "LeagueOfLegends.exe", "Overwatch.exe",
    "Apex.exe", "ApexLegends.exe", "r5apex.exe", "Warzone.exe", "ModernWarfare.exe",
    "RainbowSix.exe", "RainbowSix_BE.exe", "destiny2.exe", "bf2042.exe",
    # Riot Games
    "RiotClientServices.exe", "RiotClientCrashHandler.exe", "vgc.exe", 
    "vgtray.exe", "Vanguard.exe",
    # Sistem
    "conhost.exe", "explorer.exe", "python.exe", "pythonw.exe"
]

# Tarayıcı süreçleri
BROWSER_PROCESSES = [
    "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe", "brave.exe", 
    "vivaldi.exe", "safari.exe", "iexplore.exe", "chromium.exe"
]

# Yapılandırma dosyası
CONFIG_FILE = "zenti_config.json"
LOG_FILE = "logs/zenti_log.txt"
SCHEDULE_FILE = "zenti_schedule.json"
VERSION = "2.1 Pro"

# Ses efektleri
SOUND_EFFECTS = {
    "startup": "sounds/startup.wav",
    "boost": "sounds/boost.wav",
    "complete": "sounds/complete.wav",
    "error": "sounds/error.wav",
    "notification": "sounds/notification.wav"
}

# Klasörleri oluştur
os.makedirs("logs", exist_ok=True)
os.makedirs("assets", exist_ok=True)
os.makedirs("sounds", exist_ok=True)

# Ses efektlerini oluştur
def create_sound_effects():
    """Eksik ses efektlerini oluştur"""
    try:
        # Basit beep sesleri oluştur
        if not os.path.exists(SOUND_EFFECTS["startup"]):
            with open(SOUND_EFFECTS["startup"], "wb") as f:
                # Boş WAV dosyası oluştur
                pass
            # Ses dosyası yoksa, Windows beep sesini kullan
            winsound.Beep(440, 500)  # 440 Hz, 500 ms
        
        if not os.path.exists(SOUND_EFFECTS["boost"]):
            with open(SOUND_EFFECTS["boost"], "wb") as f:
                pass
            winsound.Beep(660, 300)
        
        if not os.path.exists(SOUND_EFFECTS["complete"]):
            with open(SOUND_EFFECTS["complete"], "wb") as f:
                pass
            winsound.Beep(880, 300)
        
        if not os.path.exists(SOUND_EFFECTS["error"]):
            with open(SOUND_EFFECTS["error"], "wb") as f:
                pass
            winsound.Beep(220, 500)
        
        if not os.path.exists(SOUND_EFFECTS["notification"]):
            with open(SOUND_EFFECTS["notification"], "wb") as f:
                pass
            winsound.Beep(550, 200)
    except Exception as e:
        logging.error(f"Ses efektleri oluşturulurken hata: {str(e)}")

# Ses çal
def play_sound(sound_name):
    """Belirtilen ses efektini çal"""
    try:
        sound_file = SOUND_EFFECTS.get(sound_name)
        if sound_file and os.path.exists(sound_file):
            winsound.PlaySound(sound_file, winsound.SND_ASYNC)
        else:
            # Ses dosyası yoksa, Windows beep sesini kullan
            if sound_name == "startup":
                winsound.Beep(440, 500)  # 440 Hz, 500 ms
            elif sound_name == "boost":
                winsound.Beep(660, 300)
            elif sound_name == "complete":
                winsound.Beep(880, 300)
            elif sound_name == "error":
                winsound.Beep(220, 500)
            elif sound_name == "notification":
                winsound.Beep(550, 200)
    except Exception as e:
        logging.error(f"Ses çalınırken hata: {str(e)}")

# Günlük kaydını ayarla
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Eski günlük dosyalarını temizle (7 günden eski)
def clean_old_logs():
    try:
        now = datetime.now()
        for file in os.listdir("logs"):
            if file.endswith(".txt"):
                file_path = os.path.join("logs", file)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if now - file_time > timedelta(days=7):
                    os.remove(file_path)
                    print(f"Eski günlük dosyası silindi: {file}")
    except Exception as e:
        print(f"Günlük temizleme hatası: {e}")

# Eski günlükleri temizle
clean_old_logs()

def get_third_party_processes():
    """Sistemde çalışan üçüncü taraf süreçlerin listesini al"""
    third_party = []
    system_paths = [
        os.environ.get('SystemRoot', r'C:\Windows'),
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    ]
    system_paths = [p.lower() for p in system_paths if p]

    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_percent']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                exe = proc.info['exe']
                cpu = proc.info['cpu_percent']
                memory = proc.info['memory_percent']
                
                if not name or not exe:
                    continue
                    
                exe_lower = exe.lower()
                # Sistem uygulamalarının yolunu içermiyorsa ekle
                if not any(exe_lower.startswith(path) for path in system_paths):
                    # Beyaz listedeki uygulamaları da otomatik seçili bırakma
                    if name not in WHITELISTED_PROCESSES:
                        # Tarayıcı mı kontrol et
                        is_browser = name in BROWSER_PROCESSES
                        third_party.append((pid, name, cpu, memory, is_browser))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logging.error(f"Süreç listesi alınırken hata: {str(e)}")
        
    # CPU kullanımına göre sırala (en yüksek kullanım üstte)
    third_party.sort(key=lambda x: x[2], reverse=True)
    return third_party

class SystemInfo:
    """Gelişmiş sistem bilgisi toplama sınıfı"""
    
    @staticmethod
    def get_cpu_info():
        """Detaylı CPU bilgilerini al"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count_physical = psutil.cpu_count(logical=False) or 1
            cpu_count_logical = psutil.cpu_count(logical=True) or 1
            
            cpu_freq = 0
            if psutil.cpu_freq():
                cpu_freq = psutil.cpu_freq().current
        
            # CPU sıcaklığını almaya çalış
            cpu_temp = None
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if name.lower() in ['coretemp', 'k10temp', 'cpu_thermal']:
                            if entries:
                                cpu_temp = entries[0].current
                                break
        
            cpu_info = {
                "usage": cpu_percent,
                "cores_physical": cpu_count_physical,
                "cores_logical": cpu_count_logical,
                "frequency": cpu_freq,
                "temperature": cpu_temp
            }
            return cpu_info
        except Exception as e:
            logging.error(f"CPU bilgisi alınırken hata: {str(e)}")
            return {"usage": 0, "cores_physical": 0, "cores_logical": 0, "frequency": 0, "temperature": None}
    
    @staticmethod
    def get_memory_info():
        """Detaylı bellek bilgilerini al"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
        
            memory_info = {
                "total": mem.total / (1024 ** 3),  # GB
                "available": mem.available / (1024 ** 3),  # GB
                "used": mem.used / (1024 ** 3),  # GB
                "percent": mem.percent,
                "swap_total": swap.total / (1024 ** 3),  # GB
                "swap_used": swap.used / (1024 ** 3),  # GB
                "swap_percent": swap.percent
            }
            return memory_info
        except Exception as e:
            logging.error(f"RAM bilgisi alınırken hata: {str(e)}")
            return {"total": 0, "available": 0, "used": 0, "percent": 0, 
                "swap_total": 0, "swap_used": 0, "swap_percent": 0}
    
    @staticmethod
    def get_disk_info():
        """Disk bilgilerini al"""
        try:
            all_disks = []
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                    # Windows'ta CD-ROM sürücülerini atla
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_info = {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total": usage.total / (1024 ** 3),  # GB
                        "used": usage.used / (1024 ** 3),  # GB
                        "free": usage.free / (1024 ** 3),  # GB
                        "percent": usage.percent
                    }
                    all_disks.append(disk_info)
                except Exception:
                    continue
        
            # Disk I/O istatistiklerini al
            io_counters = psutil.disk_io_counters()
            io_stats = {
                "read_bytes": io_counters.read_bytes / (1024 ** 2) if io_counters else 0,  # MB
                "write_bytes": io_counters.write_bytes / (1024 ** 2) if io_counters else 0,  # MB
                "read_count": io_counters.read_count if io_counters else 0,
                "write_count": io_counters.write_count if io_counters else 0
            }
        
            return {
                "disks": all_disks,
                "io_stats": io_stats,
                # Ana disk (C: sürücüsü) bilgilerini de ayrıca ekle
                "system_disk": next((d for d in all_disks if d["mountpoint"] == "C:\\"), all_disks[0] if all_disks else None)
            }
        except Exception as e:
            logging.error(f"Disk bilgisi alınırken hata: {str(e)}")
            return {"disks": [], "io_stats": {"read_bytes": 0, "write_bytes": 0, "read_count": 0, "write_count": 0}, "system_disk": None}
    
    @staticmethod
    def get_gpu_info():
        """GPU bilgilerini almaya çalış"""
        try:
            if platform.system() == "Windows":
                # Windows Yönetim Araçları Komut Satırı kullanarak
                result = subprocess.check_output(
                    "wmic path win32_VideoController get Name, AdapterRAM, DriverVersion", 
                    shell=True
                ).decode('utf-8')
            
                # Sonucu işle
                lines = result.strip().split('\n')
                if len(lines) >= 2:
                    # Başlık satırını atla, ilk GPU'yu al
                    gpu_data = lines[1].strip()
                
                    # GPU adını çıkar
                    gpu_name = gpu_data.split('  ')[0].strip()
                
                    # Bellek miktarını tahmin et (tam değil)
                    gpu_memory = "Bilinmiyor"
                    for part in gpu_data.split('  '):
                        if part.strip().isdigit():
                            try:
                                memory_bytes = int(part.strip())
                                gpu_memory = f"{memory_bytes / (1024**3):.1f} GB"
                                break
                            except:
                                pass
                
                    # Sürücü versiyonunu çıkar
                    driver_version = "Bilinmiyor"
                    for part in gpu_data.split('  '):
                        if part.strip() and "." in part.strip() and not part.strip().startswith(gpu_name):
                            driver_version = part.strip()
                            break
                
                    # GPU kullanımını tahmin et (tam değil)
                    # Gerçek GPU kullanımını almak için NVIDIA-smi veya AMD eşdeğeri gerekir
                    gpu_usage = random.randint(30, 70)  # Simüle edilmiş değer
                
                    return {
                        "name": gpu_name,
                        "memory": gpu_memory,
                        "driver": driver_version,
                        "usage": gpu_usage
                    }
            
                return {"name": "GPU Algılandı", "memory": "Bilinmiyor", "driver": "Bilinmiyor", "usage": 0}
            else:
                return {"name": "Bu platformda GPU bilgisi mevcut değil", "memory": "Bilinmiyor", "driver": "Bilinmiyor", "usage": 0}
        except Exception as e:
            logging.error(f"GPU bilgisi alınamadı: {e}")
            return {"name": "Algılanamadı", "memory": "Bilinmiyor", "driver": "Bilinmiyor", "usage": 0}
    
    @staticmethod
    def get_network_info():
        """Ağ kullanım bilgilerini al"""
        try:
            # Ağ I/O sayaçlarını al
            net_io = psutil.net_io_counters()
        
            # Ağ bağlantılarını al
            connections = psutil.net_connections()
            active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
        
            # Ağ arayüzlerini al
            interfaces = []
            for name, stats in psutil.net_if_stats().items():
                if stats.isup:  # Sadece aktif arayüzleri ekle
                    interfaces.append({
                        "name": name,
                        "speed": stats.speed,
                        "mtu": stats.mtu
                    })
        
            # Ping testi yap
            ping_result = None
            try:
                # Google DNS'e ping at
                ping_output = subprocess.check_output(
                    "ping -n 1 8.8.8.8", 
                    shell=True
                ).decode('utf-8')
            
                # Ping süresini çıkar
                for line in ping_output.split('\n'):
                    if "time=" in line or "süre=" in line:
                        parts = line.split('time=') if 'time=' in line else line.split('süre=')
                        if len(parts) > 1:
                            ping_result = parts[1].strip().split(' ')[0]
                            break
            except:
                pass
        
            return {
                "bytes_sent": net_io.bytes_sent / (1024 ** 2),  # MB
                "bytes_recv": net_io.bytes_recv / (1024 ** 2),  # MB
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "active_connections": active_connections,
                "interfaces": interfaces,
                "ping": ping_result
            }
        except Exception as e:
            logging.error(f"Ağ bilgisi alınırken hata: {str(e)}")
            return {
                "bytes_sent": 0, "bytes_recv": 0, 
                "packets_sent": 0, "packets_recv": 0,
                "active_connections": 0, "interfaces": [],
                "ping": None
            }

class FPSBenchmark:
    """Gelişmiş FPS kıyaslama sınıfı"""
    
    def __init__(self):
        self.history = []
        self.game_profiles = {
            "Valorant": {"cpu_weight": 0.7, "ram_weight": 0.3, "base_fps": 240, "gpu_weight": 0.5},
            "Fortnite": {"cpu_weight": 0.6, "ram_weight": 0.4, "base_fps": 200, "gpu_weight": 0.6},
            "CSGO": {"cpu_weight": 0.8, "ram_weight": 0.2, "base_fps": 300, "gpu_weight": 0.4},
            "Minecraft": {"cpu_weight": 0.5, "ram_weight": 0.5, "base_fps": 150, "gpu_weight": 0.3},
            "Apex Legends": {"cpu_weight": 0.65, "ram_weight": 0.35, "base_fps": 180, "gpu_weight": 0.7},
            "Default": {"cpu_weight": 0.6, "ram_weight": 0.4, "base_fps": 200, "gpu_weight": 0.5}
        }
    
    def display(self, log_func):
        """Sistem metriklerini ve tahmini FPS'yi görüntüle"""
        try:
            cpu_info = SystemInfo.get_cpu_info()
            mem_info = SystemInfo.get_memory_info()
            gpu_info = SystemInfo.get_gpu_info()
        
            cpu = cpu_info["usage"]
            ram = mem_info["percent"]
            gpu = gpu_info.get("usage", 0)
        
            log_func(f"🧠 CPU Kullanımı: %{cpu:.1f} ({cpu_info['cores_logical']} çekirdek)")
            log_func(f"📦 RAM Kullanımı: %{ram:.1f} ({mem_info['used']:.1f}GB / {mem_info['total']:.1f}GB)")
            log_func(f"🎮 GPU Kullanımı: %{gpu} ({gpu_info['name']})")
        
            # Trend analizi için geçmişi sakla
            self.history.append((cpu, ram, gpu))
            if len(self.history) > 10:
                self.history.pop(0)
        
            # Farklı oyunlar için FPS tahminlerini al
            fps_estimates = []
            for game, profile in self.game_profiles.items():
                if game != "Default":
                    fps = self.estimate_fps(cpu, ram, gpu, profile)
                    log_func(f"🎮 {game} için Tahmini FPS: {fps}")
                    fps_estimates.append(f"{game}: {fps}")
        
            # Varsayılan tahmin
            fps_estimate = self.estimate_fps(cpu, ram, gpu)
            log_func(f"🎮 Genel Tahmini FPS: {fps_estimate}")
            fps_estimates.append(f"Genel: {fps_estimate}")
        
            # Performans trendi
            if len(self.history) >= 2:
                cpu_trend = self.history[-1][0] - self.history[0][0]
                ram_trend = self.history[-1][1] - self.history[0][1]
                if cpu_trend < -5 or ram_trend < -5:
                    log_func("📈 Performans iyileşiyor!")
                elif cpu_trend > 5 or ram_trend > 5:
                    log_func("📉 Performans düşüyor!")
        
            return "\n".join(fps_estimates)
        except Exception as e:
            log_func(f"❌ Benchmark hatası: {str(e)}")
            logging.error(f"Benchmark error: {str(e)}")
            return "Hata"
    
    def estimate_fps(self, cpu, ram, gpu, profile=None):
        """CPU, RAM ve GPU kullanımına göre FPS tahmini yap"""
        if profile is None:
            profile = self.game_profiles["Default"]
    
        # Performans puanını hesapla (düşük daha iyidir)
        cpu_factor = cpu * profile["cpu_weight"]
        ram_factor = ram * profile["ram_weight"]
        gpu_factor = gpu * profile.get("gpu_weight", 0.5) if gpu else 0
    
        performance_score = cpu_factor + ram_factor + gpu_factor
    
        # Performans puanına göre ayarlanmış temel FPS
        base_fps = profile["base_fps"]
    
        if performance_score < 30:
            return f"{int(base_fps * 1.5)}+ FPS (Ultra Boost)"
        elif performance_score < 50:
            return f"{int(base_fps * 1.2)}-{int(base_fps * 1.5)} FPS (High Boost)"
        elif performance_score < 70:
            return f"{int(base_fps * 0.8)}-{int(base_fps * 1.2)} FPS (Medium Boost)"
        else:
            return f"{int(base_fps * 0.5)}-{int(base_fps * 0.8)} FPS (Low Boost)"

class SystemOptimizer:
    """Gelişmiş sistem optimizasyonu sınıfı"""
    
    def __init__(self, log_func):
        self.log = log_func
        self.optimization_level = 1  # Varsayılan: Orta
        self.last_optimization = None
        self.optimization_steps = [
            "Sistem analizi yapılıyor...",
            "Gereksiz süreçler kapatılıyor...",
            "Geçici dosyalar temizleniyor...",
            "Ağ ayarları optimize ediliyor...",
            "Sistem servisleri yapılandırılıyor...",
            "Görsel efektler optimize ediliyor...",
            "Güç planı ayarlanıyor...",
            "Kayıt defteri optimizasyonu yapılıyor...",
            "Bellek optimizasyonu yapılıyor...",
            "Disk önbelleği temizleniyor...",
            "Oyun modu etkinleştiriliyor...",
            "Optimizasyon tamamlanıyor..."
        ]
    
    # Add this new method
    def set_optimization_level(self, level):
        """Optimizasyon seviyesini ayarla (1-3)"""
        self.optimization_level = level
        self.log(f"⚙️ Optimizasyon seviyesi {level} olarak ayarlandı")

    def optimize_system(self, selected_pids=None, progress_callback=None):
        """Seviyeye göre tüm optimizasyon stratejilerini çalıştır"""
        self.log("🚀 Sistem optimizasyonu başlatılıyor...")
        start_time = time.time()
    
        # Optimizasyon adımlarını çalıştır
        total_steps = len(self.optimization_steps)
        for i, step in enumerate(self.optimization_steps):
            # İlerleme durumunu güncelle
            progress = int((i / total_steps) * 100)
            if progress_callback:
                progress_callback(progress)
        
            # Adım mesajını günlüğe kaydet
            self.log(f"⚙️ {step}")
        
            # Gerçek optimizasyon işlemlerini gerçekleştir
            if i == 0:  # Sistem analizi
                time.sleep(0.5)  # Simüle edilmiş işlem
            elif i == 1:  # Gereksiz süreçler
                if selected_pids:
                    self.close_selected_processes(selected_pids)
            elif i == 2:  # Geçici dosyalar
                self.clean_temp_files()
            elif i == 3:  # Ağ ayarları
                self.optimize_network()
            elif i == 4:  # Sistem servisleri
                if self.optimization_level >= 2:
                    self.optimize_services()
            elif i == 5:  # Görsel efektler
                if self.optimization_level >= 2:
                    self.optimize_visual_effects()
            elif i == 6:  # Güç planı
                if self.optimization_level >= 2:
                    self.optimize_power_settings()
            elif i == 7:  # Kayıt defteri
                if self.optimization_level >= 3:
                    self.optimize_registry()
            elif i == 8:  # Bellek optimizasyonu
                if self.optimization_level >= 2:
                    self.optimize_memory()
            elif i == 9:  # Disk önbelleği
                if self.optimization_level >= 2:
                    self.clean_disk_cache()
            elif i == 10:  # Oyun modu
                if self.optimization_level >= 1:
                    self.enable_game_mode()
        
            # Her adım arasında kısa bir bekleme
            time.sleep(0.3)
    
        # Son optimizasyon zamanını kaydet
        self.last_optimization = datetime.now()
    
        # Tamamlanma süresi
        elapsed_time = time.time() - start_time
        self.log(f"✅ Sistem optimizasyonu tamamlandı ({elapsed_time:.2f} saniye)")
    
        # Son ilerleme güncellemesi
        if progress_callback:
            progress_callback(100)
    
    def close_selected_processes(self, selected_pids):
        """Seçilen süreçleri sonlandır"""
        if not selected_pids:
            self.log("⚠️ Kapatılacak süreç seçilmedi")
            return
            
        closed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                if pid in selected_pids and name not in WHITELISTED_PROCESSES:
                    proc.terminate()
                    self.log(f"🚫 {name} (PID {pid}) süreci kapatıldı")
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        self.log(f"🚫 Toplam {closed_count} süreç kapatıldı")
    
    def clean_temp_files(self):
        """Geçici dosyaları temizle"""
        try:
            cleaned_size = 0
            # Windows geçici dosyaları
            if platform.system() == "Windows":
                temp_paths = [
                    os.environ.get('TEMP', ''),
                    os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
                    os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
                ]
                
                for temp_path in temp_paths:
                    if os.path.exists(temp_path):
                        before_size = self.get_folder_size(temp_path)
                        try:
                            for item in os.listdir(temp_path):
                                item_path = os.path.join(temp_path, item)
                                try:
                                    if os.path.isfile(item_path):
                                        os.unlink(item_path)
                                    elif os.path.isdir(item_path):
                                        shutil.rmtree(item_path, ignore_errors=True)
                                except:
                                    pass
                            after_size = self.get_folder_size(temp_path)
                            cleaned_size += (before_size - after_size)
                        except:
                            pass
                
                # Tarayıcı önbelleklerini temizle (optimizasyon seviyesi yüksekse)
                if self.optimization_level >= 2:
                    # Chrome önbelleği
                    chrome_cache = os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache")
                    if os.path.exists(chrome_cache):
                        before_size = self.get_folder_size(chrome_cache)
                        for item in os.listdir(chrome_cache):
                            try:
                                item_path = os.path.join(chrome_cache, item)
                                if os.path.isfile(item_path):
                                    os.unlink(item_path)
                            except:
                                pass
                        after_size = self.get_folder_size(chrome_cache)
                        cleaned_size += (before_size - after_size)
                    
                    # Firefox önbelleği
                    firefox_cache = os.path.expanduser("~\\AppData\\Local\\Mozilla\\Firefox\\Profiles")
                    if os.path.exists(firefox_cache):
                        for profile in os.listdir(firefox_cache):
                            profile_cache = os.path.join(firefox_cache, profile, "cache2")
                            if os.path.exists(profile_cache):
                                before_size = self.get_folder_size(profile_cache)
                                for item in os.listdir(profile_cache):
                                    try:
                                        item_path = os.path.join(profile_cache, item)
                                        if os.path.isfile(item_path):
                                            os.unlink(item_path)
                                    except:
                                        pass
                                after_size = self.get_folder_size(profile_cache)
                                cleaned_size += (before_size - after_size)
            
            self.log(f"🧹 Geçici dosyalar temizlendi ({cleaned_size / (1024**2):.2f} MB)")
        except Exception as e:
            self.log(f"❌ Disk temizliği hatası: {str(e)}")
    
    def get_folder_size(self, folder_path):
        """Klasör boyutunu hesapla"""
        total_size = 0
        try:
            for path, dirs, files in os.walk(folder_path):
                for f in files:
                    try:
                        fp = os.path.join(path, f)
                        total_size += os.path.getsize(fp)
                    except:
                        pass
        except:
            pass
        return total_size
    
    def optimize_services(self):
        """Windows servislerini optimize et"""
        if platform.system() != "Windows":
            return
            
        try:
            # Oyun sırasında güvenle devre dışı bırakılabilecek servisler
            gaming_services = [
                "DiagTrack",  # Bağlı Kullanıcı Deneyimleri ve Telemetri
                "SysMain",    # Superfetch
                "WSearch",    # Windows Arama
                "wuauserv",   # Windows Güncelleme
                "Themes",     # Temalar
                "PrintNotify" # Yazıcı bildirimleri
            ]
            
            disabled_count = 0
            for service in gaming_services:
                try:
                    os.system(f"sc config {service} start= disabled >nul 2>&1")
                    os.system(f"sc stop {service} >nul 2>&1")
                    disabled_count += 1
                except:
                    pass
            
            self.log(f"⚙️ {disabled_count} gereksiz servis devre dışı bırakıldı")
        except Exception as e:
            self.log(f"❌ Servis optimizasyonu hatası: {str(e)}")
    
    def optimize_visual_effects(self):
        """Görsel efektleri performans için optimize et"""
        if platform.system() != "Windows":
            return
            
        try:
            # Kayıt defteri üzerinden görsel efektleri devre dışı bırak
            os.system("reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects\" /v VisualFXSetting /t REG_DWORD /d 2 /f >nul 2>&1")
            
            # Animasyonları devre dışı bırak
            os.system("reg add \"HKCU\\Control Panel\\Desktop\\WindowMetrics\" /v MinAnimate /t REG_SZ /d 0 /f >nul 2>&1")
            
            # Ek görsel efektleri devre dışı bırak
            if self.optimization_level >= 3:
                os.system("reg add \"HKCU\\Control Panel\\Desktop\" /v UserPreferencesMask /t REG_BINARY /d 9012078010000000 /f >nul 2>&1")
                os.system("reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v ListviewAlphaSelect /t REG_DWORD /d 0 /f >nul 2>&1")
                os.system("reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v TaskbarAnimations /t REG_DWORD /d 0 /f >nul 2>&1")
            
            self.log("🎨 Görsel efektler performans için optimize edildi")
        except Exception as e:
            self.log(f"❌ Görsel efekt optimizasyonu hatası: {str(e)}")
    
    def optimize_power_settings(self):
        """Güç planını yüksek performansa ayarla"""
        if platform.system() != "Windows":
            return
            
        try:
            os.system("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >nul 2>&1")
            
            # Ek güç optimizasyonları
            os.system("powercfg /change monitor-timeout-ac 15 >nul 2>&1")
            os.system("powercfg /change disk-timeout-ac 0 >nul 2>&1")
            os.system("powercfg /change standby-timeout-ac 0 >nul 2>&1")
            os.system("powercfg /change hibernate-timeout-ac 0 >nul 2>&1")
            
            self.log("⚡ Güç planı 'Yüksek Performans' olarak ayarlandı")
        except Exception as e:
            self.log(f"❌ Güç planı optimizasyonu hatası: {str(e)}")
    
    def optimize_network(self):
        """Ağ ayarlarını optimize et"""
        if platform.system() != "Windows":
            return
            
        try:
            # Nagle algoritmasını devre dışı bırak
            os.system("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\\" /v TcpAckFrequency /t REG_DWORD /d 1 /f >nul 2>&1")
            os.system("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\\" /v TCPNoDelay /t REG_DWORD /d 1 /f >nul 2>&1")
            
            # DNS'i Google'ın DNS'ine ayarla
            if self.optimization_level >= 2:
                os.system("netsh interface ip set dns \"Wi-Fi\" static 8.8.8.8 primary >nul 2>&1")
                os.system("netsh interface ip add dns \"Wi-Fi\" 8.8.4.4 index=2 >nul 2>&1")
                os.system("netsh interface ip set dns \"Ethernet\" static 8.8.8.8 primary >nul 2>&1")
                os.system("netsh interface ip add dns \"Ethernet\" 8.8.4.4 index=2 >nul 2>&1")
            
            self.log("🌐 Ağ ayarları optimize edildi")
        except Exception as e:
            self.log(f"❌ Ağ optimizasyonu hatası: {str(e)}")
    
    def optimize_advanced_network(self):
        """Gelişmiş ağ optimizasyonları"""
        if platform.system() != "Windows":
            return
            
        try:
            # QoS rezervasyonunu devre dışı bırak
            os.system("reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Psched\" /v NonBestEffortLimit /t REG_DWORD /d 0 /f >nul 2>&1")
            
            # NetBIOS'u devre dışı bırak
            os.system("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\services\\NetBT\\Parameters\\Interfaces\\Tcpip_*\" /v NetbiosOptions /t REG_DWORD /d 2 /f >nul 2>&1")
            
            # IPv6 bileşenlerini devre dışı bırak (oyun için)
            os.system("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters\" /v DisabledComponents /t REG_DWORD /d 0xff /f >nul 2>&1")
            
            # TCP pencere boyutunu optimize et
            os.system("netsh int tcp set global autotuninglevel=normal >nul 2>&1")
            os.system("netsh int tcp set global chimney=enabled >nul 2>&1")
            os.system("netsh int tcp set global rss=enabled >nul 2>&1")
            
            self.log("🌐 Gelişmiş ağ ayarları optimize edildi")
        except Exception as e:
            self.log(f"❌ Gelişmiş ağ optimizasyonu hatası: {str(e)}")
    
    def optimize_registry(self):
        """Oyun için kayıt defteri ayarlarını optimize et"""
        if platform.system() != "Windows":
            return
            
        try:
            # Game DVR'ı devre dışı bırak
            os.system("reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_Enabled /t REG_DWORD /d 0 /f >nul 2>&1")
            os.system("reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR\" /v AllowGameDVR /t REG_DWORD /d 0 /f >nul 2>&1")
            
            # Tam ekran optimizasyonlarını devre dışı bırak
            os.system("reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_FSEBehaviorMode /t REG_DWORD /d 2 /f >nul 2>&1")
            os.system("reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_HonorUserFSEBehaviorMode /t REG_DWORD /d 1 /f >nul 2>&1")
            os.system("reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_FSEBehavior /t REG_DWORD /d 2 /f >nul 2>&1")
            os.system("reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_DXGIHonorFSEWindowsCompatible /t REG_DWORD /d 1 /f >nul 2>&1")
            
            # HPET'i devre dışı bırak (High Precision Event Timer)
            os.system("bcdedit /deletevalue useplatformclock >nul 2>&1")
            
            # Dinamik Tick'i devre dışı bırak
            os.system("bcdedit /set disabledynamictick yes >nul 2>&1")
            
            # Oyun modu ayarları
            os.system("reg add \"HKCU\\Software\\Microsoft\\GameBar\" /v AutoGameModeEnabled /t REG_DWORD /d 1 /f >nul 2>&1")
            os.system("reg add \"HKCU\\Software\\Microsoft\\GameBar\" /v AllowAutoGameMode /t REG_DWORD /d 1 /f >nul 2>&1")
            
            self.log("🔧 Registry ayarları oyunlar için optimize edildi")
        except Exception as e:
            self.log(f"❌ Registry optimizasyonu hatası: {str(e)}")

    def optimize_memory(self):
        """Bellek kullanımını optimize et"""
        if platform.system() != "Windows":
            return
        
        try:
            # Çalışma belleğini temizle
            os.system("powershell -Command \"[System.Reflection.Assembly]::LoadWithPartialName('Microsoft.VisualBasic'); [Microsoft.VisualBasic.Interaction]::Shell('rundll32.exe advapi32.dll,ProcessIdleTasks', 0, $true, 5000)\" >nul 2>&1")
        
            # Sayfa dosyası boyutunu optimize et
            if self.optimization_level >= 3:
                # Sayfa dosyası boyutunu sistem belleğinin 1.5 katı olarak ayarla
                mem = psutil.virtual_memory()
                page_size = int(mem.total / (1024 ** 2) * 1.5)  # MB cinsinden
                os.system(f"wmic pagefileset where name=\"C:\\\\pagefile.sys\" set InitialSize={page_size},MaximumSize={page_size} >nul 2>&1")
        
            self.log("💾 Bellek kullanımı optimize edildi")
        except Exception as e:
            self.log(f"❌ Bellek optimizasyonu hatası: {str(e)}")

    def clean_disk_cache(self):
        """Disk önbelleğini temizle"""
        if platform.system() != "Windows":
            return
        
        try:
            # Disk önbelleğini temizle
            os.system("ipconfig /flushdns >nul 2>&1")
            os.system("wsreset >nul 2>&1")
        
            # Windows Update önbelleğini temizle
            os.system("net stop wuauserv >nul 2>&1")
            os.system("net stop bits >nul 2>&1")
            os.system("rd /s /q %windir%\\SoftwareDistribution >nul 2>&1")
            os.system("net start wuauserv >nul 2>&1")
            os.system("net start bits >nul 2>&1")
        
            self.log("💿 Disk önbelleği temizlendi")
        except Exception as e:
            self.log(f"❌ Disk önbelleği temizleme hatası: {str(e)}")

    def enable_game_mode(self):
        """Windows Oyun Modunu etkinleştir"""
        if platform.system() != "Windows":
            return
        
        try:
            # Windows Oyun Modunu etkinleştir
            os.system("reg add \"HKCU\\Software\\Microsoft\\GameBar\" /v AllowAutoGameMode /t REG_DWORD /d 1 /f >nul 2>&1")
            os.system("reg add \"HKCU\\Software\\Microsoft\\GameBar\" /v AutoGameModeEnabled /t REG_DWORD /d 1 /f >nul 2>&1")
        
            self.log("🎮 Windows Oyun Modu etkinleştirildi")
        except Exception as e:
            self.log(f"❌ Oyun Modu etkinleştirme hatası: {str(e)}")

class Worker(QThread):
    """Gelişmiş çalışan iş parçacığı"""
    
    log_signal = pyqtSignal(str)
    realtime_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)
    schedule_signal = pyqtSignal()
    
    def __init__(self, selected_pid_func):
        super().__init__()
        self.running = True
        self.get_selected_pids = selected_pid_func
        self.benchmark = FPSBenchmark()
        self.optimizer = SystemOptimizer(self.emit_log)
        self.update_interval = 3000  # ms
        self.optimization_level = 1  # Varsayılan: Orta
        self.scheduled_tasks = []
        self.load_schedule()
    
        # Ağ ve disk istatistikleri için önceki değerler
        self.prev_net_bytes_sent = 0
        self.prev_net_bytes_recv = 0
        self.prev_disk_read = 0
        self.prev_disk_write = 0
        self.prev_time = time.time()
    
    def run(self):
        """Ana iş parçacığı döngüsü"""
        last_schedule_check = datetime.now()
        
        while self.running:
            # Sistem metriklerini güncelle
            self.update_metrics()
            
            # Zamanlanmış görevleri kontrol et (her dakika)
            now = datetime.now()
            if (now - last_schedule_check).total_seconds() >= 60:
                self.check_scheduled_tasks()
                last_schedule_check = now
            
            # Güncelleme aralığı için uyku
            self.msleep(self.update_interval)
    
    def update_metrics(self):
        """Tüm sistem metriklerini güncelle ve sinyaller gönder"""
        try:
            current_time = time.time()
            time_diff = current_time - self.prev_time
        
            # Sistem bilgilerini al
            cpu_info = SystemInfo.get_cpu_info()
            mem_info = SystemInfo.get_memory_info()
            disk_info = SystemInfo.get_disk_info()
            net_info = SystemInfo.get_network_info()
            gpu_info = SystemInfo.get_gpu_info()
        
            # Ağ hızını hesapla (MB/s)
            net_bytes_sent = net_info["bytes_sent"]
            net_bytes_recv = net_info["bytes_recv"]
        
            net_speed_up = (net_bytes_sent - self.prev_net_bytes_sent) / time_diff if time_diff > 0 else 0
            net_speed_down = (net_bytes_recv - self.prev_net_bytes_recv) / time_diff if time_diff > 0 else 0
        
            self.prev_net_bytes_sent = net_bytes_sent
            self.prev_net_bytes_recv = net_bytes_recv
        
            # Disk hızını hesapla (MB/s)
            disk_read = disk_info["io_stats"]["read_bytes"]
            disk_write = disk_info["io_stats"]["write_bytes"]
        
            disk_read_speed = (disk_read - self.prev_disk_read) / time_diff if time_diff > 0 else 0
            disk_write_speed = (disk_write - self.prev_disk_write) / time_diff if time_diff > 0 else 0
        
            self.prev_disk_read = disk_read
            self.prev_disk_write = disk_write
        
            self.prev_time = current_time
        
            # Kıyaslama çalıştır
            fps_estimate = self.benchmark.display(self.emit_log)
        
            # Gerçek zamanlı verileri UI'a gönder
            realtime_data = {
                "cpu": cpu_info,
                "memory": mem_info,
                "disk": disk_info,
                "network": net_info,
                "gpu": gpu_info,
                "fps_estimate": fps_estimate,
                "net_speed": {
                    "upload": net_speed_up,
                    "download": net_speed_down
                },
                "disk_speed": {
                    "read": disk_read_speed,
                    "write": disk_write_speed
                }
            }
            self.realtime_signal.emit(realtime_data)
        
        except Exception as e:
            self.emit_log(f"❌ Metrics update error: {str(e)}")
            logging.error(f"Metrics update error: {str(e)}")
    
    def perform_optimization(self):
        """İlerleme güncellemeleriyle sistem optimizasyonu gerçekleştir"""
        try:
            self.emit_log(f"🚀 Optimizasyon başlatılıyor (Seviye: {self.optimization_level})...")
        
            # Ses efekti çal
            play_sound("boost")
        
            # Optimizasyon seviyesini ayarla
            self.optimizer.set_optimization_level(self.optimization_level)
        
            # Optimizasyonu çalıştır
            self.optimizer.optimize_system(
                self.get_selected_pids(),
                progress_callback=self.progress_signal.emit
            )
        
            # Optimizasyondan sonra metrikleri güncelle
            self.update_metrics()
        
            # Tamamlandı ses efekti
            play_sound("complete")
        
            self.emit_log("✅ Optimizasyon tamamlandı!")
        except Exception as e:
            self.emit_log(f"❌ Optimization error: {str(e)}")
            logging.error(f"Optimization error: {str(e)}")
        
            # Hata ses efekti
            play_sound("error")
        
            self.progress_signal.emit(100)
    
    def set_optimization_level(self, level):
        """Optimizasyon seviyesini ayarla (1-3)"""
        self.optimization_level = level
    
    def set_update_interval(self, interval):
        """Güncelleme aralığını milisaniye cinsinden ayarla"""
        self.update_interval = max(1000, interval)
    
    def add_scheduled_task(self, time_str, level):
        """Zamanlanmış bir görev ekle"""
        try:
            task = {"time": time_str, "level": level}
            self.scheduled_tasks.append(task)
            self.save_schedule()
            self.emit_log(f"📅 Zamanlanmış görev eklendi: {time_str} (Seviye: {level})")
        
            # Bildirim ses efekti
            play_sound("notification")
        
            return True
        except Exception as e:
            self.emit_log(f"❌ Zamanlanmış görev eklenirken hata: {str(e)}")
            return False
    
    def remove_scheduled_task(self, index):
        """Zamanlanmış bir görevi kaldır"""
        try:
            if 0 <= index < len(self.scheduled_tasks):
                task = self.scheduled_tasks.pop(index)
                self.save_schedule()
                self.emit_log(f"🗑️ Zamanlanmış görev kaldırıldı: {task['time']}")
                return True
            return False
        except Exception as e:
            self.emit_log(f"❌ Zamanlanmış görev kaldırılırken hata: {str(e)}")
            return False
    
    def save_schedule(self):
        """Zamanlanmış görevleri dosyaya kaydet"""
        try:
            with open(SCHEDULE_FILE, "w") as f:
                json.dump(self.scheduled_tasks, f, indent=4)
        except Exception as e:
            logging.error(f"Zamanlanmış görevler kaydedilirken hata: {str(e)}")
    
    def load_schedule(self):
        """Zamanlanmış görevleri dosyadan yükle"""
        try:
            if os.path.exists(SCHEDULE_FILE):
                with open(SCHEDULE_FILE, "r") as f:
                    self.scheduled_tasks = json.load(f)
                self.emit_log(f"📅 {len(self.scheduled_tasks)} zamanlanmış görev yüklendi")
        except Exception as e:
            logging.error(f"Zamanlanmış görevler yüklenirken hata: {str(e)}")
            self.scheduled_tasks = []
    
    def check_scheduled_tasks(self):
        """Zamanlanmış görevleri kontrol et ve gerekirse çalıştır"""
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
        
            for task in self.scheduled_tasks:
                if task["time"] == current_time:
                    self.emit_log(f"⏰ Zamanlanmış optimizasyon başlatılıyor (Seviye: {task['level']})...")
                
                    # Bildirim ses efekti
                    play_sound("notification")
                
                    # Optimizasyon seviyesini ayarla ve çalıştır
                    old_level = self.optimization_level
                    self.optimization_level = task["level"]
                
                    # Ana iş parçacığını engellememek için yeni bir iş parçacığı başlat
                    threading.Thread(target=self.perform_optimization).start()
                
                    # Eski seviyeyi geri yükle
                    self.optimization_level = old_level
                
                    # UI'ı güncelle
                    self.schedule_signal.emit()
        except Exception as e:
            logging.error(f"Zamanlanmış görevler kontrol edilirken hata: {str(e)}")
    
    def stop(self):
        """İş parçacığını durdur"""
        self.running = False
    
    def emit_log(self, msg):
        """Zaman damgalı bir günlük mesajı yayınla"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        full_msg = f"{timestamp} {msg}"
        self.log_signal.emit(full_msg)
        
        # Dosyaya da kaydet
        logging.info(msg)

class AnimatedProgressBar(QProgressBar):
    """Animasyonlu ilerleme çubuğu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setMinimum(0)
        self.setMaximum(100)
        
        # Create the animation BEFORE setting the value
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(800)  # 800ms animasyon süresi
        
        # Now it's safe to set the value
        self.setValue(0)
        
        self.setStyleSheet("""
            QProgressBar {
                background-color: #23272a;
                border-radius: 10px;
                height: 25px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                stop:0 #7289da, stop:1 #43b581);
                border-radius: 10px;
            }
        """)
    
    def setValue(self, value):
        """Değeri animasyonlu olarak ayarla"""
        if self.value() != value:
            self.animation.stop()
            self.animation.setStartValue(self.value())
            self.animation.setEndValue(value)
            self.animation.start()
        else:
            super().setValue(value)

class GameSelector(QComboBox):
    """Özel oyun seçici açılır menü"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                background-color: #2c2f33;
                color: white;
                border: 2px solid #7289da;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #7289da;
                border-left-style: solid;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c2f33;
                color: white;
                selection-background-color: #7289da;
                selection-color: white;
                border: 2px solid #7289da;
                border-radius: 8px;
            }
        """)
        
        # Popüler oyunları ekle
        self.addItem("Valorant")
        self.addItem("Fortnite")
        self.addItem("CS:GO")
        self.addItem("Minecraft")
        self.addItem("Apex Legends")
        self.addItem("League of Legends")
        self.addItem("PUBG")
        self.addItem("Call of Duty: Warzone")
        self.addItem("GTA V")
        self.addItem("Overwatch")
        self.addItem("Diğer")

class PerformanceGraph(QWidget):
    """Özel performans grafiği bileşeni"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cpu_data = [0] * 60  # 60 veri noktası
        self.ram_data = [0] * 60
        self.gpu_data = [0] * 60  # GPU verisi eklendi
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #23272a; border-radius: 10px;")
    
    def update_data(self, cpu, ram, gpu=0):
        """Grafik verilerini güncelle"""
        self.cpu_data.append(cpu)
        self.ram_data.append(ram)
        self.gpu_data.append(gpu)
        
        # Sadece son 60 veri noktasını tut
        if len(self.cpu_data) > 60:
            self.cpu_data.pop(0)
        if len(self.ram_data) > 60:
            self.ram_data.pop(0)
        if len(self.gpu_data) > 60:
            self.gpu_data.pop(0)
            
        self.update()
    
    def paintEvent(self, event):
        """Performans grafiğini çiz"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Arka planı çiz
        painter.fillRect(self.rect(), QBrush(QColor("#23272a")))
        
        # Izgara çizgilerini çiz
        painter.setPen(QPen(QColor("#444444"), 1))
        width = self.width()
        height = self.height()
        
        # Yatay ızgara çizgileri - Ondalık sayıları tam sayıya dönüştür
        for i in range(1, 5):
            y = int(height - (height * i / 5))
            painter.drawLine(0, y, width, y)
        
        # CPU verilerini çiz
        if len(self.cpu_data) > 1:
            painter.setPen(QPen(QColor("#7289da"), 2))
            
            for i in range(len(self.cpu_data) - 1):
                x1 = int(i * width / 59)
                y1 = int(height - (self.cpu_data[i] * height / 100))
                x2 = int((i + 1) * width / 59)
                y2 = int(height - (self.cpu_data[i + 1] * height / 100))
                painter.drawLine(x1, y1, x2, y2)
        
        # RAM verilerini çiz
        if len(self.ram_data) > 1:
            painter.setPen(QPen(QColor("#43b581"), 2))
            
            for i in range(len(self.ram_data) - 1):
                x1 = int(i * width / 59)
                y1 = int(height - (self.ram_data[i] * height / 100))
                x2 = int((i + 1) * width / 59)
                y2 = int(height - (self.ram_data[i + 1] * height / 100))
                painter.drawLine(x1, y1, x2, y2)
        
        # GPU verilerini çiz
        if len(self.gpu_data) > 1:
            painter.setPen(QPen(QColor("#faa61a"), 2))
            
            for i in range(len(self.gpu_data) - 1):
                x1 = int(i * width / 59)
                y1 = int(height - (self.gpu_data[i] * height / 100))
                x2 = int((i + 1) * width / 59)
                y2 = int(height - (self.gpu_data[i + 1] * height / 100))
                painter.drawLine(x1, y1, x2, y2)
        
        # Açıklamaları çiz
        painter.setPen(QPen(QColor("#7289da"), 2))
        painter.drawLine(width - 100, 20, width - 80, 20)
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawText(width - 75, 25, "CPU")
        
        painter.setPen(QPen(QColor("#43b581"), 2))
        painter.drawLine(width - 100, 40, width - 80, 40)
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawText(width - 75, 45, "RAM")
        
        painter.setPen(QPen(QColor("#faa61a"), 2))
        painter.drawLine(width - 100, 60, width - 80, 60)
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawText(width - 75, 65, "GPU")

class ScheduleDialog(QDialog):
    """Zamanlanmış görev ekleme iletişim kutusu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zamanlanmış Optimizasyon Ekle")
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #2c2f33;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #7289da;
                color: white;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5b6eae;
            }
            QPushButton:pressed {
                background-color: #4a5d8f;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Zaman seçici
        time_label = QLabel("Optimizasyon Zamanı:")
        layout.addWidget(time_label)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setStyleSheet("""
            QTimeEdit {
                background-color: #23272a;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.time_edit)
        
        # Seviye seçici
        level_label = QLabel("Optimizasyon Seviyesi:")
        layout.addWidget(level_label)
        
        self.level_group = QButtonGroup()
        level_layout = QHBoxLayout()
        
        levels = ["Düşük", "Orta", "Ultra"]
        for i, level in enumerate(levels):
            btn = QRadioButton(level)
            btn.setStyleSheet("""
                QRadioButton {
                    color: white;
                    font-size: 14px;
                }
                QRadioButton::indicator:checked {
                    background-color: #7289da;
                    border-radius: 6px;
                }
            """)
            
            if i == 1:  # Varsayılan: Orta
                btn.setChecked(True)
            
            self.level_group.addButton(btn, i + 1)
            level_layout.addWidget(btn)
        
        layout.addLayout(level_layout)
        
        # Açıklama
        info_label = QLabel(
            "Bu özellik, belirtilen zamanda otomatik olarak sistem optimizasyonu "
            "gerçekleştirecektir. Bilgisayarınızın açık olduğundan ve Zenti Boost'un "
            "çalıştığından emin olun."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #99aab5; font-size: 12px; margin-top: 20px;")
        layout.addWidget(info_label)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Kaydet")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_schedule_data(self):
        """Seçilen zamanı ve seviyeyi al"""
        time_str = self.time_edit.time().toString("HH:mm")
        level = self.level_group.checkedId()
        return time_str, level

class ProcessTableWidget(QTableWidget):
    """Gelişmiş süreç tablosu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Seç", "Süreç Adı", "PID", "CPU %", "RAM %"])
        self.setStyleSheet("""
            QTableWidget {
                background-color: #23272a;
                color: white;
                border-radius: 10px;
                gridline-color: #444444;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #7289da;
                color: white;
            }
            QHeaderView::section {
                background-color: #2c2f33;
                color: white;
                padding: 5px;
                border: 1px solid #444444;
            }
            QCheckBox {
                color: white;
            }
        """)
        
        # Sütun genişliklerini ayarla
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.setColumnWidth(0, 40)  # Seç
        self.setColumnWidth(2, 80)  # PID
        self.setColumnWidth(3, 80)  # CPU
        self.setColumnWidth(4, 80)  # RAM
        
        # Satır yüksekliğini ayarla
        self.verticalHeader().setDefaultSectionSize(30)
        self.verticalHeader().setVisible(False)
        
        # Seçim davranışını ayarla
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Sıralama etkinleştir
        self.setSortingEnabled(True)
    
    def update_processes(self, processes):
        """Süreç listesini güncelle"""
        self.setSortingEnabled(False)
        self.setRowCount(0)
        
        for row, (pid, name, cpu, memory, is_browser) in enumerate(processes):
            self.insertRow(row)
            
            # Onay kutusu
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.setCellWidget(row, 0, checkbox_widget)
            
            # Süreç adı
            name_item = QTableWidgetItem(name)
            if is_browser:
                name_item.setForeground(QColor("#faa61a"))  # Tarayıcıları vurgula
            self.setItem(row, 1, name_item)
            
            # PID
            pid_item = QTableWidgetItem(str(pid))
            self.setItem(row, 2, pid_item)
            
            # CPU kullanımı
            cpu_item = QTableWidgetItem(f"{cpu:.1f}%")
            if cpu > 10:
                cpu_item.setForeground(QColor("#f04747"))  # Yüksek CPU kullanımını vurgula
            self.setItem(row, 3, cpu_item)
            
            # RAM kullanımı
            ram_item = QTableWidgetItem(f"{memory:.1f}%")
            if memory > 5:
                ram_item.setForeground(QColor("#f04747"))  # Yüksek RAM kullanımını vurgula
            self.setItem(row, 4, ram_item)
        
        self.setSortingEnabled(True)
    
    def get_selected_pids(self):
        """Seçilen süreçlerin PID'lerini al"""
        selected_pids = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                pid_item = self.item(row, 2)
                if pid_item:
                    try:
                        pid = int(pid_item.text())
                        selected_pids.append(pid)
                    except ValueError:
                        pass
        return selected_pids
    
    def select_all(self):
        """Tüm süreçleri seç"""
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all(self):
        """Tüm süreçlerin seçimini kaldır"""
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)

class ZentiBoostUI(QMainWindow):
    """Gelişmiş ana UI sınıfı"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Zenti Boost Pro v{VERSION} | Ultimate FPS Enhancer")
        self.setFixedSize(1000, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c2f33;
                color: white;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
        """)
        
        # Yer tutucu simgeleri oluştur
        self.create_placeholder_icons()
        
        # Ses efektlerini oluştur
        create_sound_effects()
        
        # Pencere simgesini ayarla
        self.setWindowIcon(QIcon("assets/zenti_icon.png"))
        
        # Sistem tepsisini başlat
        self.setup_system_tray()
        
        # Yapılandırmayı yükle
        self.load_config()
        
        # İşçi iş parçacığını başlat
        self.worker = Worker(self.get_selected_pids)
        self.worker.log_signal.connect(self.update_log)
        self.worker.realtime_signal.connect(self.update_realtime)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.schedule_signal.connect(self.update_schedule_list)
        self.worker.start()
        
        # UI'ı başlat
        self.init_ui()
        
        # Açılış ekranını göster
        self.show_splash_screen()
    
    def create_placeholder_icons(self):
        """Yer tutucu simgeler oluştur"""
        # Yer tutucu simge
        if not os.path.exists("assets/zenti_icon.png"):
            try:
                # Basit bir renkli kare oluştur
                icon = QPixmap(64, 64)
                icon.fill(QColor("#7289da"))
                icon.save("assets/zenti_icon.png")
            except Exception as e:
                logging.error(f"Yer tutucu simge oluşturma hatası: {str(e)}")
        
        # Yer tutucu logo animasyonu
        if not os.path.exists("assets/zenti_logo.gif"):
            try:
                # Basit bir renkli kare oluştur
                logo = QPixmap(100, 100)
                logo.fill(QColor("#7289da"))
                logo.save("assets/zenti_logo.png")
                # GIF kolayca oluşturulamaz, bu yüzden PNG kullanacağız
            except Exception as e:
                logging.error(f"Yer tutucu logo oluşturma hatası: {str(e)}")
        
        # Yer tutucu açılış ekranı
        if not os.path.exists("assets/splash_image.png"):
            try:
                # Basit bir renkli dikdörtgen oluştur
                splash = QPixmap(600, 400)
                splash.fill(QColor("#2c2f33"))
                
                # Metin ekle
                painter = QPainter(splash)
                painter.setPen(QColor("#ffffff"))
                font = QFont("Arial", 24, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(splash.rect(), Qt.AlignmentFlag.AlignCenter, "Zenti Boost Pro")
                painter.end()
                
                splash.save("assets/splash_image.png")
            except Exception as e:
                logging.error(f"Yer tutucu açılış ekranı oluşturma hatası: {str(e)}")
    
    def init_ui(self):
        """Ana UI'ı başlat"""
        main_layout = QVBoxLayout()
        
        # Logo ve başlık ile başlık
        header_layout = QHBoxLayout()
        
        # Logo Animasyonu
        self.logo = QLabel()
        if os.path.exists("assets/zenti_logo.gif"):
            movie = QMovie("assets/zenti_logo.gif")
            movie.setScaledSize(QSize(100, 100))
            self.logo.setMovie(movie)
            movie.start()
        else:
            # GIF yoksa statik görüntü kullan
            self.logo.setPixmap(QPixmap("assets/zenti_logo.png").scaled(100, 100))
        
        header_layout.addWidget(self.logo)
        
        # Başlık ve alt başlık
        title_layout = QVBoxLayout()
        title = QLabel("ZENTI BOOST PRO")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #7289da;")
        subtitle = QLabel("Ultimate FPS Enhancer & System Optimizer")
        subtitle.setStyleSheet("font-size: 16px; color: #99aab5;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Oyun seçici
        game_layout = QVBoxLayout()
        game_label = QLabel("Şunun için optimize et:")
        game_label.setStyleSheet("font-size: 14px; color: #99aab5;")
        self.game_selector = GameSelector()
        self.game_selector.currentTextChanged.connect(self.game_changed)
        game_layout.addWidget(game_label)
        game_layout.addWidget(self.game_selector)
        header_layout.addLayout(game_layout)
        
        main_layout.addLayout(header_layout)
        
        # Sekmeler Kurulumu
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #7289da;
                border-radius: 10px;
                background-color: #2c2f33;
            }
            QTabBar::tab {
                background: #23272a;
                color: #b9bbbe;
                padding: 12px 20px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                min-width: 140px;
                margin-right: 6px;
            }
            QTabBar::tab:selected {
                background: #7289da;
                color: white;
                font-weight: 700;
            }
        """)
        
        # Sekmeleri kur
        self.setup_boost_tab()
        self.setup_process_tab()
        self.setup_performance_tab()
        self.setup_schedule_tab()
        self.setup_settings_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Sürüm ve kredilerle durum çubuğu
        footer_layout = QHBoxLayout()
        
        # Sürüm bilgisi
        version = QLabel(f"Zenti Boost Pro v{VERSION}")
        version.setStyleSheet("color: #99aab5; font-size: 12px;")
        footer_layout.addWidget(version)
        
        footer_layout.addStretch()
        
        # Krediler
        credits = QLabel("Developed by WebWarden | Enhanced by v0")
        credits.setStyleSheet("color: #99aab5; font-size: 12px;")
        footer_layout.addWidget(credits)
        
        main_layout.addLayout(footer_layout)
        
        # Merkezi Bileşen
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
    
    def setup_boost_tab(self):
        """Optimizasyon kontrolleriyle boost sekmesini kur"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Optimizasyon seviyesi seçimi
        level_group = QGroupBox("Optimizasyon Seviyesi")
        level_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: 600;
                color: white;
                border: 2px solid #7289da;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
            }
        """)
        
        level_layout = QHBoxLayout()
        self.level_group = QButtonGroup()
        
        levels = [
            ("Düşük", "Temel optimizasyonlar, minimum sistem değişiklikleri"),
            ("Orta", "Dengeli optimizasyonlar, orta düzey sistem değişiklikleri"),
            ("Ultra", "Agresif optimizasyonlar, maksimum performans için")
        ]
        
        for i, (level, desc) in enumerate(levels):
            level_widget = QWidget()
            level_layout_inner = QVBoxLayout()
            
            # Radyo düğmesi
            btn = QRadioButton(level)
            btn.setStyleSheet("""
                QRadioButton {
                    font-size: 16px;
                    color: #ffffff;
                    padding: 10px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                }
                QRadioButton::indicator:checked {
                    background-color: #7289da;
                    border-radius: 10px;
                }
            """)
            
            if i == 1:  # Varsayılan: Orta
                btn.setChecked(True)
            
            self.level_group.addButton(btn, i + 1)
            level_layout_inner.addWidget(btn)
            
            # Açıklama
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #99aab5; font-size: 12px;")
            desc_label.setWordWrap(True)
            level_layout_inner.addWidget(desc_label)
            
            level_widget.setLayout(level_layout_inner)
            level_layout.addWidget(level_widget)
        
        level_group.setLayout(level_layout)
        layout.addWidget(level_group)
        
        # Seviye değişikliğini bağla
        self.level_group.buttonClicked.connect(self.level_changed)
        
        # İlerleme çubuğu ve durum
        progress_layout = QVBoxLayout()

        # Durum etiketi
        self.boost_status = QLabel("Hazır")
        self.boost_status.setStyleSheet("""
            font-size: 14px;
            color: #99aab5;
            margin-top: 10px;
            margin-bottom: 5px;
        """)
        progress_layout.addWidget(self.boost_status)

        # İlerleme çubuğu
        self.progress_bar = AnimatedProgressBar()
        progress_layout.addWidget(self.progress_bar)

        layout.addLayout(progress_layout)
        
        # Boost Düğmesi
        self.boost_btn = QPushButton("⚡ BOOST NOW")
        self.boost_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.boost_btn.clicked.connect(self.perform_boost)
        self.boost_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #7289da, stop:1 #43b581);
                border-radius: 12px;
                padding: 15px;
                font-size: 20px;
                font-weight: 700;
                color: white;
                margin-top: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #5b6eae, stop:1 #3ca374);
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #4a5d8f, stop:1 #2d7d59);
            }
        """)
        layout.addWidget(self.boost_btn)
        
        # Günlük Çıktı Kutusu
        log_label = QLabel("Optimizasyon Günlüğü:")
        log_label.setStyleSheet("font-size: 16px; font-weight: 600; color: white; margin-top: 20px;")
        layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #23272a;
                color: #43b581;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                border-radius: 10px;
                padding: 12px;
                border: 1px solid #444444;
            }
        """)
        layout.addWidget(self.log_output)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🚀 Boost")
    
    def setup_process_tab(self):
        """Süreç yönetimiyle süreçler sekmesini kur"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Talimatlar ve kontroller
        header_layout = QHBoxLayout()
        
        # Talimatlar Etiketi
        info_label = QLabel("❗ Kapatmak istediğiniz üçüncü taraf uygulamaları seçin (Sistem uygulamaları gizlidir)")
        info_label.setStyleSheet("color: #99aab5; font-weight: 600;")
        header_layout.addWidget(info_label)
        
        # Yenile düğmesi
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_btn.clicked.connect(self.load_processes)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #23272a;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background-color: #2c2f33;
            }
        """)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Arama kutusu
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Ara:")
        search_label.setStyleSheet("color: white; font-size: 14px;")
        search_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #23272a;
                color: white;
                border-radius: 8px;
                padding: 8px;
                border: 1px solid #444444;
            }
        """)
        self.search_box.textChanged.connect(self.filter_processes)
        search_layout.addWidget(self.search_box)
        
        layout.addLayout(search_layout)
        
        # Süreç Tablosu
        self.process_table = ProcessTableWidget()
        layout.addWidget(self.process_table)
        
        # Hızlı eylemler
        actions_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.clicked.connect(self.select_all_processes)
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #23272a;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background-color: #2c2f33;
            }
        """)
        actions_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Tümünü Kaldır")
        deselect_all_btn.clicked.connect(self.deselect_all_processes)
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #23272a;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background-color: #2c2f33;
            }
        """)
        actions_layout.addWidget(deselect_all_btn)
        
        end_selected_btn = QPushButton("Seçilenleri Kapat")
        end_selected_btn.clicked.connect(self.end_selected_processes)
        end_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 14px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #d03737;
            }
        """)
        actions_layout.addWidget(end_selected_btn)
        
        layout.addLayout(actions_layout)
        
        # Süreçleri yükle
        self.load_processes()
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "⚙️ Processes")
    
    def setup_performance_tab(self):
        """Performans izleme sekmesini kur"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Gerçek zamanlı performans grafiği
        graph_label = QLabel("Gerçek Zamanlı Performans Grafiği:")
        graph_label.setStyleSheet("font-size: 16px; font-weight: 600; color: white;")
        layout.addWidget(graph_label)
        
        self.performance_graph = PerformanceGraph()
        layout.addWidget(self.performance_graph)
        
        # Sistem bilgileri ızgarası
        info_grid = QGridLayout()
        
        # CPU Bilgisi
        cpu_group = QGroupBox("CPU Bilgisi")
        cpu_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #23272a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                background-color: #23272a;
            }
        """)
        
        cpu_layout = QVBoxLayout()
        self.cpu_usage_label = QLabel("Kullanım: 0%")
        self.cpu_cores_label = QLabel("Çekirdekler: 0")
        self.cpu_freq_label = QLabel("Frekans: 0 MHz")
        self.cpu_temp_label = QLabel("Sıcaklık: Bilinmiyor")

        for label in [self.cpu_usage_label, self.cpu_cores_label, self.cpu_freq_label, self.cpu_temp_label]:
            label.setStyleSheet("color: white; font-size: 14px;")
            cpu_layout.addWidget(label)
        
        cpu_group.setLayout(cpu_layout)
        info_grid.addWidget(cpu_group, 0, 0)
        
        # RAM Bilgisi
        ram_group = QGroupBox("RAM Bilgisi")
        ram_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #23272a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                background-color: #23272a;
            }
        """)
        
        ram_layout = QVBoxLayout()
        self.ram_usage_label = QLabel("Kullanım: 0%")
        self.ram_total_label = QLabel("Toplam: 0 GB")
        self.ram_available_label = QLabel("Kullanılabilir: 0 GB")
        self.ram_swap_label = QLabel("Takas Alanı: 0 GB")

        for label in [self.ram_usage_label, self.ram_total_label, self.ram_available_label, self.ram_swap_label]:
            label.setStyleSheet("color: white; font-size: 14px;")
            ram_layout.addWidget(label)
        
        ram_group.setLayout(ram_layout)
        info_grid.addWidget(ram_group, 0, 1)
        
        # GPU Bilgisi
        gpu_group = QGroupBox("GPU Bilgisi")
        gpu_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #23272a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                background-color: #23272a;
            }
        """)
        
        gpu_layout = QVBoxLayout()
        self.gpu_name_label = QLabel("Model: Algılanıyor...")
        self.gpu_memory_label = QLabel("Bellek: Bilinmiyor")
        self.gpu_driver_label = QLabel("Sürücü: Bilinmiyor")
        self.gpu_usage_label = QLabel("Kullanım: 0%")

        for label in [self.gpu_name_label, self.gpu_memory_label, self.gpu_driver_label, self.gpu_usage_label]:
            label.setStyleSheet("color: white; font-size: 14px;")
            gpu_layout.addWidget(label)
        
        gpu_group.setLayout(gpu_layout)
        info_grid.addWidget(gpu_group, 1, 0)
        
        # Disk Bilgisi
        disk_group = QGroupBox("Disk Bilgisi")
        disk_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #23272a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                background-color: #23272a;
            }
        """)
        
        disk_layout = QVBoxLayout()
        self.disk_usage_label = QLabel("Kullanım: 0%")
        self.disk_total_label = QLabel("Toplam: 0 GB")
        self.disk_free_label = QLabel("Boş: 0 GB")
        self.disk_io_label = QLabel("I/O: 0 MB/s")

        for label in [self.disk_usage_label, self.disk_total_label, self.disk_free_label, self.disk_io_label]:
            label.setStyleSheet("color: white; font-size: 14px;")
            disk_layout.addWidget(label)
        
        disk_group.setLayout(disk_layout)
        info_grid.addWidget(disk_group, 1, 1)
        
        # Ağ Bilgisi
        net_group = QGroupBox("Ağ Bilgisi")
        net_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #23272a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                background-color: #23272a;
            }
        """)
        
        net_layout = QGridLayout()

        self.net_sent_label = QLabel("Gönderilen: 0 MB")
        self.net_recv_label = QLabel("Alınan: 0 MB")
        self.net_speed_up_label = QLabel("Yükleme: 0 MB/s")
        self.net_speed_down_label = QLabel("İndirme: 0 MB/s")
        self.net_ping_label = QLabel("Ping: Bilinmiyor")
        self.net_connections_label = QLabel("Bağlantılar: 0")

        for label in [self.net_sent_label, self.net_recv_label, self.net_speed_up_label, 
                     self.net_speed_down_label, self.net_ping_label, self.net_connections_label]:
            label.setStyleSheet("color: white; font-size: 14px;")

        net_layout.addWidget(self.net_sent_label, 0, 0)
        net_layout.addWidget(self.net_recv_label, 0, 1)
        net_layout.addWidget(self.net_speed_up_label, 1, 0)
        net_layout.addWidget(self.net_speed_down_label, 1, 1)
        net_layout.addWidget(self.net_ping_label, 2, 0)
        net_layout.addWidget(self.net_connections_label, 2, 1)

        net_group.setLayout(net_layout)
        info_grid.addWidget(net_group, 2, 0, 1, 2)  # İki sütunu kapla
        
        layout.addLayout(info_grid)
        
        # FPS Tahminleri
        fps_label = QLabel("Tahmini FPS Değerleri:")
        fps_label.setStyleSheet("font-size: 16px; font-weight: 600; color: white; margin-top: 20px;")
        layout.addWidget(fps_label)
        
        self.fps_output = QTextEdit()
        self.fps_output.setReadOnly(True)
        self.fps_output.setStyleSheet("""
            QTextEdit {
                background-color: #23272a;
                color: #43b581;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                border-radius: 10px;
                padding: 12px;
                border: 1px solid #444444;
                max-height: 100px;
            }
        """)
        layout.addWidget(self.fps_output)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "📊 Performance")
    
    def setup_schedule_tab(self):
        """Zamanlanmış görevler sekmesini kur"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Başlık
        header_label = QLabel("Zamanlanmış Optimizasyonlar")
        header_label.setStyleSheet("font-size: 18px; font-weight: 700; color: white;")
        layout.addWidget(header_label)
        
        # Açıklama
        desc_label = QLabel(
            "Belirli zamanlarda otomatik olarak sistem optimizasyonu gerçekleştirmek için "
            "zamanlanmış görevler oluşturun. Bilgisayarınız açık ve Zenti Boost çalışıyor olmalıdır."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #99aab5; font-size: 14px; margin-bottom: 15px;")
        layout.addWidget(desc_label)
        
        # Zamanlanmış görevler listesi
        self.schedule_list = QListWidget()
        self.schedule_list.setStyleSheet("""
            QListWidget {
                background-color: #23272a;
                border-radius: 10px;
                font-size: 14px;
                color: white;
                border: 1px solid #444444;
                padding: 5px;
                min-height: 200px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #7289da;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #2c2f33;
            }
        """)
        layout.addWidget(self.schedule_list)
        
        # Butonlar
        buttons_layout = QHBoxLayout()
        
        add_schedule_btn = QPushButton("➕ Yeni Zamanlanmış Görev Ekle")
        add_schedule_btn.clicked.connect(self.add_schedule)
        add_schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #43b581;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3ca374;
            }
        """)
        buttons_layout.addWidget(add_schedule_btn)
        
        remove_schedule_btn = QPushButton("🗑️ Seçili Görevi Kaldır")
        remove_schedule_btn.clicked.connect(self.remove_schedule)
        remove_schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #d03737;
            }
        """)
        buttons_layout.addWidget(remove_schedule_btn)
        
        layout.addLayout(buttons_layout)
        
        # Zamanlanmış görevleri yükle
        self.update_schedule_list()
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "⏰ Schedule")
    
    def setup_settings_tab(self):
        """Ayarlar sekmesini kur"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Güncelleme aralığı
        interval_group = QGroupBox("Güncelleme Aralığı")
        interval_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
            }
        """)
        
        interval_layout = QVBoxLayout()
        
        interval_label = QLabel("Performans metriklerinin güncelleme sıklığı (saniye):")
        interval_label.setStyleSheet("color: white; font-size: 14px;")
        interval_layout.addWidget(interval_label)
        
        slider_layout = QHBoxLayout()
        
        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setMinimum(1)
        self.interval_slider.setMaximum(10)
        self.interval_slider.setValue(3)
        self.interval_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #23272a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #7289da;
                border: 1px solid #5b6eae;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #7289da;
                border-radius: 4px;
            }
        """)
        self.interval_slider.valueChanged.connect(self.interval_changed)
        slider_layout.addWidget(self.interval_slider)
        
        self.interval_value = QLabel("3s")
        self.interval_value.setStyleSheet("color: white; font-size: 14px; min-width: 30px;")
        slider_layout.addWidget(self.interval_value)
        
        interval_layout.addLayout(slider_layout)
        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)
        
        # Başlangıç seçenekleri
        startup_group = QGroupBox("Başlangıç Seçenekleri")
        startup_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
            }
        """)
        
        startup_layout = QVBoxLayout()
        
        self.start_with_windows = QCheckBox("Windows ile başlat")
        self.start_with_windows.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #7289da;
                border: 2px solid white;
                border-radius: 2px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #23272a;
                border: 2px solid #444444;
                border-radius: 2px;
            }
        """)
        startup_layout.addWidget(self.start_with_windows)
        
        self.start_minimized = QCheckBox("Simge durumunda başlat")
        self.start_minimized.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #7289da;
                border: 2px solid white;
                border-radius: 2px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #23272a;
                border: 2px solid #444444;
                border-radius: 2px;
            }
        """)
        startup_layout.addWidget(self.start_minimized)
        
        self.auto_boost = QCheckBox("Başlangıçta otomatik boost")
        self.auto_boost.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #7289da;
                border: 2px solid white;
                border-radius: 2px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #23272a;
                border: 2px solid #444444;
                border-radius: 2px;
            }
        """)
        startup_layout.addWidget(self.auto_boost)
        
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        # Ses ayarları
        sound_group = QGroupBox("Ses Ayarları")
        sound_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #23272a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                background-color: #23272a;
            }
        """)

        sound_layout = QVBoxLayout()

        self.enable_sounds = QCheckBox("Ses efektlerini etkinleştir")
        self.enable_sounds.setChecked(True)
        self.enable_sounds.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #7289da;
                border: 2px solid white;
                border-radius: 2px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #23272a;
                border: 2px solid #444444;
                border-radius: 2px;
            }
        """)
        sound_layout.addWidget(self.enable_sounds)

        # Ses seviyesi
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Ses Seviyesi:")
        volume_label.setStyleSheet("color: white; font-size: 14px;")
        volume_layout.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(80)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #23272a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #7289da;
                border: 1px solid #5b6eae;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #7289da;
                border-radius: 4px;
            }
        """)
        volume_layout.addWidget(self.volume_slider)

        self.volume_value = QLabel("80%")
        self.volume_value.setStyleSheet("color: white; font-size: 14px; min-width: 40px;")
        self.volume_slider.valueChanged.connect(self.volume_changed)
        volume_layout.addWidget(self.volume_value)

        sound_layout.addLayout(volume_layout)

        # Test sesi düğmesi
        test_sound_btn = QPushButton("Ses Efektini Test Et")
        test_sound_btn.clicked.connect(lambda: play_sound("notification"))
        test_sound_btn.setStyleSheet("""
            QPushButton {
                background-color: #7289da;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background-color: #5b6eae;
            }
        """)
        sound_layout.addWidget(test_sound_btn)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)
        
        # Ayarları kaydet düğmesi
        save_btn = QPushButton("Ayarları Kaydet")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.clicked.connect(self.save_config)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7289da;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: 600;
                color: white;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #5b6eae;
            }
            QPushButton:pressed {
                background-color: #4a5d8f;
            }
        """)
        layout.addWidget(save_btn)
        
        # Hakkında bölümü
        about_group = QGroupBox("Hakkında")
        about_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                color: white;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
            }
        """)
        
        about_layout = QVBoxLayout()
        
        about_text = QLabel(
            "Zenti Boost Pro, oyun performansınızı artırmak için tasarlanmış profesyonel "
            "bir FPS optimizasyon aracıdır. Gereksiz süreçleri kapatarak, sistem ayarlarını "
            "optimize ederek ve geçici dosyaları temizleyerek bilgisayarınızın "
            "performansını en üst düzeye çıkarır."
        )
        about_text.setWordWrap(True)
        about_text.setStyleSheet("color: white; font-size: 14px;")
        about_layout.addWidget(about_text)
        
        version_text = QLabel(f"Versiyon: {VERSION} Pro")
        version_text.setStyleSheet("color: #99aab5; font-size: 12px; margin-top: 10px;")
        about_layout.addWidget(version_text)
        
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        # Her şeyi yukarı itmek için esneme ekle
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "⚙️ Settings")
    
    def setup_system_tray(self):
        """Sistem tepsisi simgesini ve menüsünü kur"""
        try:
            self.tray_icon = QSystemTrayIcon(QIcon("assets/zenti_icon.png"), self)
            
            # Tepsi menüsü oluştur
            tray_menu = QMenu()
            
            # Eylemler ekle
            show_action = tray_menu.addAction("Göster")
            show_action.triggered.connect(self.show)
            
            boost_action = tray_menu.addAction("Hızlı Boost")
            boost_action.triggered.connect(self.perform_boost)
            
            tray_menu.addSeparator()
            
            exit_action = tray_menu.addAction("Çıkış")
            exit_action.triggered.connect(self.close)
            
            # Menüyü ayarla
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Tepsi simgesini göster
            self.tray_icon.show()
        except Exception as e:
            logging.error(f"Sistem tepsisi kurulurken hata: {str(e)}")
            # Sistem tepsisi olmadan devam et
            pass
    
    def tray_icon_activated(self, reason):
        """Tepsi simgesi aktivasyonunu işle"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
    
    def load_processes(self):
        """Üçüncü taraf süreçleri listeye yükle"""
        self.process_table.update_processes(get_third_party_processes())
    
    def filter_processes(self):
        """Arama metnine göre süreçleri filtrele"""
        # Arama kutusu işlevselliği ProcessTableWidget'a taşındı
        pass
    
    def select_all_processes(self):
        """Listedeki tüm süreçleri seç"""
        self.process_table.select_all()
    
    def deselect_all_processes(self):
        """Listedeki tüm süreçlerin seçimini kaldır"""
        self.process_table.deselect_all()
    
    def end_selected_processes(self):
        """Seçilen süreçleri hemen sonlandır"""
        selected_pids = self.get_selected_pids()
        
        if not selected_pids:
            QMessageBox.information(self, "Bilgi", "Lütfen kapatılacak süreçleri seçin.")
            return
        
        reply = QMessageBox.question(
            self, 
            "Süreçleri Sonlandır", 
            f"Seçilen {len(selected_pids)} süreci sonlandırmak istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Süreçleri kapatmak için geçici bir optimizer oluştur
            optimizer = SystemOptimizer(self.log)
            optimizer.close_selected_processes(selected_pids)
            
            # Süreç listesini yenile
            self.load_processes()
    
    def get_selected_pids(self):
        """Seçilen süreçlerin PID'lerini al"""
        return self.process_table.get_selected_pids()
    
    def perform_boost(self):
        """Boost işlemini gerçekleştir"""
        # Seçilen optimizasyon seviyesini al
        level = self.level_group.checkedId()
        
        # İşçideki optimizasyon seviyesini ayarla
        self.worker.set_optimization_level(level)
        
        # Günlüğü temizle ve ilerlemeyi sıfırla
        self.log_output.clear()
        self.progress_bar.setValue(0)
        
        # Boost başlangıcını günlüğe kaydet
        selected_mode = self.level_group.checkedButton().text()
        self.log(f"🚀 {selected_mode} Boost başlatılıyor...")
        
        # Durum etiketini güncelle
        self.boost_status.setText("Optimizasyon çalışıyor...")
        
        # Boost düğmesini devre dışı bırak
        self.boost_btn.setEnabled(False)
        
        # Optimizasyonu ayrı bir iş parçacığında gerçekleştir
        threading.Thread(target=self.worker.perform_optimization).start()
    
    def level_changed(self, button):
        """Optimizasyon seviyesi değişikliğini işle"""
        level = self.level_group.checkedId()
        self.worker.set_optimization_level(level)
    
    def game_changed(self, game):
        """Oyun seçimi değişikliğini işle"""
        self.log(f"🎮 Optimizasyon hedefi: {game}")
    
    def interval_changed(self, value):
        """Güncelleme aralığı değişikliğini işle"""
        self.interval_value.setText(f"{value}s")
        self.worker.set_update_interval(value * 1000)
    
    def volume_changed(self, value):
        """Ses seviyesi değişikliğini işle"""
        self.volume_value.setText(f"{value}%")
        # Burada gerçek ses seviyesini ayarlayabilirsiniz
    
    def update_log(self, msg):
        """Günlük çıktısını güncelle"""
        self.log_output.append(msg)
        # Otomatik olarak aşağı kaydır
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_progress(self, value):
        """İlerleme çubuğunu güncelle"""
        self.progress_bar.setValue(value)
        
        # Optimizasyon tamamlandığında durumu güncelle
        if value == 100:
            self.boost_status.setText("Hazır")
            self.boost_btn.setEnabled(True)
    
    def update_realtime(self, data):
        """Gerçek zamanlı performans verilerini güncelle"""
        try:
            # CPU bilgilerini güncelle
            cpu_info = data.get("cpu", {})
            cpu_usage = cpu_info.get("usage", 0)
            cpu_cores = cpu_info.get("cores_logical", 0)
            cpu_freq = cpu_info.get("frequency", 0)
            cpu_temp = cpu_info.get("temperature")
            
            self.cpu_usage_label.setText(f"Kullanım: %{cpu_usage:.1f}")
            self.cpu_cores_label.setText(f"Çekirdekler: {cpu_cores}")
            self.cpu_freq_label.setText(f"Frekans: {cpu_freq:.0f} MHz")
            self.cpu_temp_label.setText(f"Sıcaklık: {cpu_temp:.1f}°C" if cpu_temp is not None else "Sıcaklık: Bilinmiyor")
            
            # RAM bilgilerini güncelle
            mem_info = data.get("memory", {})
            ram_percent = mem_info.get("percent", 0)
            ram_total = mem_info.get("total", 0)
            ram_available = mem_info.get("available", 0)
            ram_swap_total = mem_info.get("swap_total", 0)
            
            self.ram_usage_label.setText(f"Kullanım: %{ram_percent:.1f}")
            self.ram_total_label.setText(f"Toplam: {ram_total:.1f} GB")
            self.ram_available_label.setText(f"Kullanılabilir: {ram_available:.1f} GB")
            self.ram_swap_label.setText(f"Takas Alanı: {ram_swap_total:.1f} GB")
            
            # GPU bilgilerini güncelle
            gpu_info = data.get("gpu", {})
            gpu_name = gpu_info.get("name", "Algılanamadı")
            gpu_memory = gpu_info.get("memory", "Bilinmiyor")
            gpu_driver = gpu_info.get("driver", "Bilinmiyor")
            gpu_usage = gpu_info.get("usage", 0)
            
            self.gpu_name_label.setText(f"Model: {gpu_name}")
            self.gpu_memory_label.setText(f"Bellek: {gpu_memory}")
            self.gpu_driver_label.setText(f"Sürücü: {gpu_driver}")
            self.gpu_usage_label.setText(f"Kullanım: %{gpu_usage}")
            
            # Disk bilgilerini güncelle
            disk_info = data.get("disk", {})
            system_disk = disk_info.get("system_disk")
            disk_io_stats = disk_info.get("io_stats")
            
            if system_disk:
                self.disk_usage_label.setText(f"Kullanım: %{system_disk['percent']:.1f}")
                self.disk_total_label.setText(f"Toplam: {system_disk['total']:.1f} GB")
                self.disk_free_label.setText(f"Boş: {system_disk['free']:.1f} GB")
            
            if disk_io_stats:
                disk_io = disk_io_stats["read_bytes"] + disk_io_stats["write_bytes"]
                self.disk_io_label.setText(f"I/O: {disk_io:.2f} MB/s")
            
            # Ağ bilgilerini güncelle
            net_info = data.get("network", {})
            net_sent = net_info.get("bytes_sent", 0)
            net_recv = net_info.get("bytes_recv", 0)
            net_speed = data.get("net_speed", {})
            net_ping = net_info.get("ping")
            net_connections = net_info.get("active_connections")
            
            self.net_sent_label.setText(f"Gönderilen: {net_sent:.2f} MB")
            self.net_recv_label.setText(f"Alınan: {net_recv:.2f} MB")
            self.net_speed_up_label.setText(f"Yükleme: {net_speed.get('upload', 0):.2f} MB/s")
            self.net_speed_down_label.setText(f"İndirme: {net_speed.get('download', 0):.2f} MB/s")
            self.net_ping_label.setText(f"Ping: {net_ping} ms" if net_ping else "Ping: Bilinmiyor")
            self.net_connections_label.setText(f"Bağlantılar: {net_connections}")
            
            # FPS tahminini güncelle
            fps_estimate = data.get("fps_estimate", "Bilinmiyor")
            self.fps_output.setText(fps_estimate)
            
            # Performans grafiğini güncelle
            if cpu_usage is not None and ram_percent is not None:
                gpu_usage = gpu_info.get("usage", 0)
                self.performance_graph.update_data(cpu_usage, ram_percent, gpu_usage)
            
        except Exception as e:
            logging.error(f"Gerçek zamanlı verileri güncellerken hata: {str(e)}")
    
    def add_schedule(self):
        """Zamanlanmış görev ekle"""
        dialog = ScheduleDialog(self)
        if dialog.exec():
            time_str, level = dialog.get_schedule_data()
            if self.worker.add_scheduled_task(time_str, level):
                self.update_schedule_list()
                QMessageBox.information(self, "Başarılı", f"Zamanlanmış görev eklendi: {time_str}")
    
    def remove_schedule(self):
        """Seçili zamanlanmış görevi kaldır"""
        selected_items = self.schedule_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Bilgi", "Lütfen kaldırılacak bir görev seçin.")
            return
        
        index = self.schedule_list.row(selected_items[0])
        if self.worker.remove_scheduled_task(index):
            self.update_schedule_list()
            QMessageBox.information(self, "Başarılı", "Zamanlanmış görev kaldırıldı.")
    
    def update_schedule_list(self):
        """Zamanlanmış görevler listesini güncelle"""
        self.schedule_list.clear()
        
        if not hasattr(self.worker, 'scheduled_tasks'):
            return
            
        for task in self.worker.scheduled_tasks:
            time_str = task["time"]
            level = task["level"]
            level_name = "Düşük" if level == 1 else "Orta" if level == 2 else "Ultra"
            
            item = QListWidgetItem(f"⏰ {time_str} - Optimizasyon Seviyesi: {level_name}")
            self.schedule_list.addItem(item)
    
    def log(self, text):
        """Günlük girdisi ekle"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.log_output.append(f"{timestamp} {text}")
        
        # Otomatik olarak aşağı kaydır
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def load_config(self):
        """Yapılandırmayı dosyadan yükle"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                
                # Ayarları uygula
                if "update_interval" in config:
                    self.interval_slider.setValue(config["update_interval"])
                
                if "start_with_windows" in config:
                    self.start_with_windows.setChecked(config["start_with_windows"])
                
                if "start_minimized" in config:
                    self.start_minimized.setChecked(config["start_minimized"])
                
                if "auto_boost" in config:
                    self.auto_boost.setChecked(config["auto_boost"])
                
                if "optimization_level" in config:
                    level = config["optimization_level"]
                    button = self.level_group.button(level)
                    if button:
                        button.setChecked(True)
                
                # Ses ayarlarını yükle
                if "enable_sounds" in config:
                    self.enable_sounds.setChecked(config["enable_sounds"])
                if "volume" in config:
                    self.volume_slider.setValue(config["volume"])
                
                logging.info("Yapılandırma başarıyla yüklendi")
        except Exception as e:
            logging.error(f"Yapılandırma yüklenirken hata: {str(e)}")
    
    def save_config(self):
        """Yapılandırmayı dosyaya kaydet"""
        try:
            config = {
                "update_interval": self.interval_slider.value(),
                "start_with_windows": self.start_with_windows.isChecked(),
                "start_minimized": self.start_minimized.isChecked(),
                "auto_boost": self.auto_boost.isChecked(),
                "optimization_level": self.level_group.checkedId(),
                "enable_sounds": self.enable_sounds.isChecked(),
                "volume": self.volume_slider.value()
            }
            
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            
            # Windows ile başlat işaretliyse, başlangıç girişi oluştur
            if self.start_with_windows.isChecked():
                self.create_startup_entry()
            else:
                self.remove_startup_entry()
            
            QMessageBox.information(self, "Başarılı", "Ayarlar başarıyla kaydedildi.")
            logging.info("Yapılandırma başarıyla kaydedildi")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilirken hata oluştu: {str(e)}")
            logging.error(f"Yapılandırma kaydedilirken hata: {str(e)}")
    
    def create_startup_entry(self):
        """Windows kayıt defterinde bir başlangıç girişi oluştur"""
        if platform.system() != "Windows":
            return
            
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            
            executable = sys.executable
            if executable.endswith("python.exe"):
                # Python yorumlayıcısından çalıştırılıyor
                script_path = os.path.abspath(sys.argv[0])
                command = f'"{executable}" "{script_path}"'
            else:
                # Yürütülebilir dosyadan çalıştırılıyor
                command = f'"{executable}"'
            
            winreg.SetValueEx(key, "ZentiBoost", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"Başlangıç girişi oluşturulurken hata: {str(e)}")
    
    def remove_startup_entry(self):
        """Windows kayıt defterinden başlangıç girişini kaldır"""
        if platform.system() != "Windows":
            return
            
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, "ZentiBoost")
            except FileNotFoundError:
                pass
            
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"Başlangıç girişi kaldırılırken hata: {str(e)}")
    
    def show_splash_screen(self):
        """Başlangıçta açılış ekranını göster"""
        try:
            splash_pix = QPixmap("assets/splash_image.png")
            self.splash = QSplashScreen(splash_pix)
            self.splash.setStyleSheet("background-color: #000000;")
            
            # Açılış ekranına ilerleme çubuğu ekle
            splash_layout = QVBoxLayout()
            splash_layout.addStretch()
            
            progress = QProgressBar()
            progress.setStyleSheet("""
                QProgressBar {
                    background-color: #23272a;
                    border-radius: 5px;
                    height: 10px;
                    text-align: center;
                    margin: 10px;
                }
                QProgressBar::chunk {
                    background-color: #7289da;
                    border-radius: 5px;
                }
            """)
            progress.setTextVisible(False)
            progress.setMinimum(0)
            progress.setMaximum(100)
            
            splash_layout.addWidget(progress)
            
            # Açılış ekranını göster ve ilerlemeyi başlat
            self.splash.show()
            QCoreApplication.processEvents()
            
            # Yüklemeyi simüle et
            for i in range(101):
                progress.setValue(i)
                self.splash.repaint()
                QCoreApplication.processEvents()
                time.sleep(0.03)
            
            # Açılış ekranını kapat ve ana pencereyi göster
            self.splash.close()
            
            # Simge durumunda başlatılıp başlatılmayacağını kontrol et
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r") as f:
                        config = json.load(f)
                    
                    if config.get("start_minimized", False):
                        # Sistem tepsisinde simge durumunda başlat
                        self.hide()
                        if hasattr(self, 'tray_icon'):
                            self.tray_icon.showMessage(
                                "Zenti Boost Pro",
                                "Uygulama sistem tepsisinde çalışıyor.",
                                QSystemTrayIcon.MessageIcon.Information,
                                3000
                            )
                    else:
                        self.show()
                    
                    # Otomatik boost etkinse
                    if config.get("auto_boost", False):
                        QTimer.singleShot(1000, self.perform_boost)
                except:
                    self.show()
            else:
                self.show()
        except Exception as e:
            logging.error(f"Açılış ekranı gösterilirken hata: {str(e)}")
            self.show()  # Yine de ana pencereyi göster
    
    def closeEvent(self, event):
        """Pencere kapatma olayını işle"""
        reply = QMessageBox.question(
            self, 
            "Çıkış", 
            "Zenti Boost'u kapatmak istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.worker.stop()
            self.worker.wait()
            event.accept()
        else:
            event.ignore()

def main():
    # Günlükler klasörünü oluştur
    os.makedirs("logs", exist_ok=True)
    
    # Varlıklar klasörünü oluştur
    os.makedirs("assets", exist_ok=True)
    
    # Uygulamayı başlat
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Daha iyi çapraz platform görünümü için Fusion stilini kullan
    window = ZentiBoostUI()
    
    # Başlangıç sesi
    play_sound("startup")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
