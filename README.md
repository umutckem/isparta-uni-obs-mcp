# 🎓 Isparta Üniversitesi OBS MCP Tools

Bu proje, Isparta Üniversitesi'nin OBS (Öğrenci Bilgi Sistemi) sistemine erişim sağlayan MCP (Model Context Protocol) tools'larını içerir. Öğrencilerin bilgilerini, duyurularını ve akademik verilerini güvenli bir şekilde çekmek için kullanılır.

## ✨ Özellikler

- 🔐 **Güvenli Login Sistemi**: ASP.NET WebForms tabanlı login
- 📊 **Öğrenci Bilgileri**: Kişisel ve akademik bilgiler
- 📢 **Duyuru Sistemi**: Güncel duyuruları takip etme
- 📚 **Ders Bilgileri**: Ders listesi ve detayları
- 📋 **Transkript**: Not dökümü ve akademik kayıtlar
- 🔍 **HTML Parsing**: Otomatik veri çıkarma
- 🛡️ **Session Yönetimi**: Güvenli oturum kontrolü
- 🚀 **Akademik Analiz**: GPA trend analizi ve performans takibi
- 🎯 **Ders Seçim Asistanı**: Ön koşul kontrolü ve öneriler
- 🔔 **Bildirim Sistemi**: Akıllı uyarılar ve hatırlatıcılar
- 📤 **Veri Export**: JSON, CSV, PDF, Excel formatlarında export

## 📦 Özellikler ve Durum

Durum efsanesi: ✅ Hazır · 🧪 Deneysel · 🕓 Planlı · ⚠️ Sorunlu

### 🔐 Temel Fonksiyonlar
- ✅ Giriş/Çıkış İşlemleri — Güvenli oturum yönetimi
- ✅ Sayfa Navigasyonu — Farklı OBS sayfalarına erişim
- ✅ Debug Modları — Teknik sorunları tespit etme

### 📊 Akademik Bilgiler
- ✅ Öğrenci Profil Bilgileri — Kişisel bilgiler, fakülte, bölüm, danışman
- ✅ Akademik Transkript — Sınıf bazında kredi ve GPA bilgileri
- ✅ Dönem Dersleri — Mevcut dönem dersleri, notlar, öğretim görevlileri
- ✅ Aldığınız Dersler — Tüm derslerinizin detaylı listesi

### 🚀 Yeni Eklenen Özellikler
- ✅ **Akademik Analiz** — GPA trend analizi, kredi tamamlama oranı, ders başarı grafiği
- ✅ **Performans Takibi** — Akademik hedefler, ilerleme durumu, hedef önerileri
- ✅ **Ders Seçim Asistanı** — Ön koşul kontrolü, kredi hesaplama, ders çakışma kontrolü
- ✅ **Bildirim Sistemi** — Düşük not uyarıları, devamsızlık uyarıları, harç ödeme hatırlatıcıları
- ✅ **Veri Export** — JSON, CSV, PDF, Excel formatlarında kapsamlı raporlama

### 📬 İletişim ve Bilgilendirme
- 🕓 Mesaj Kutusu — Öğretim görevlileri ve öğrenci işleri mesajları
- ✅ Duyurular — Güncel üniversite duyuruları
- ✅ Sistem Menü Erişimi — Tüm mevcut sayfa linklerini görme

### 🟡 Program ve Takvim
- ✅ Ders Programı — Haftalık ders saatleri
- ⚠️ Sınav Programı — Sınav tarihleri (dinamik içerik kaynaklı teknik sorunlar)
- ✅ Devamsızlık Takibi — Yoklama bilgileri

### 💰 Mali Bilgiler
- ✅ Harç Bilgileri — Ödeme durumları
- ✅ Kütüphane/Malzeme Bilgileri — Borç durumu

### 📋 İşlemler ve Başvurular
- ✅ Kayıt Yenileme — Ders ekleme/bırakma
- ✅ Bitirme Tezi İşlemleri — Proje başvuruları
- ✅ Staj Başvuruları — Zorunlu/isteğe bağlı staj
- ✅ Dilekçe İşlemleri — Online başvuru formu

### 📚 Eğitim İçerikleri
- ✅ Ders Dökümanları — Ders materyalleri
- ✅ Online Eğitim Platformu — Uzaktan eğitim erişimi
- ✅ Etkinlikler — Katıldığınız etkinlikler

### ❌ Şu Anda Sorun Yaşananlar
- ⚠️ Not Ortalaması Hesaplama — JavaScript tabanlı sayfa
- ⚠️ Sınav Programı — Dinamik içerik yükleme sorunu
- ⚠️ Bazı raporlar — İçerik görüntüleme sorunları

## 🚀 Kurulum

### Gereksinimler

- Python 3.10+
- pip veya uv

### Adımlar

1. **Projeyi klonlayın:**
```bash
git clone https://github.com/kullanici-adi/isparta-uni-obs-mcp.git
cd isparta-uni-obs-mcp
```

2. **Bağımlılıkları yükleyin:**
```bash
# pip ile
pip install -r requirements.txt

# veya uv ile
uv sync
```

3. **MCP Server'ı başlatın:**
```bash
python server.py
```

## 📖 Kullanım

### 🔐 Login İşlemleri

#### Öğrenci Girişi
```python
# Temel login
result = student_login(
    base_url="https://obs.isparta.edu.tr",
    username="**********",
    password="your_password"
)

# Debug login (detaylı bilgi)
debug_info = student_login_debug(
    base_url="https://obs.isparta.edu.tr",
    username="**********", 
    password="your_password"
)
```

#### Çıkış
```python
result = student_logout()
```

### 📊 Veri Çekme

#### Öğrenci Bilgileri
```python
# Temel bilgiler
info = student_info()

# Parse edilmiş bilgiler
parsed_info = student_info_parsed()

# HTML parse etme
html_content = "..."
parsed = parse_student_info(html_content)
```

#### Duyurular
```python
# Duyuru listesi
announcements = student_announcements(limit=10)

# Belirli sayfadan duyurular
announcements = student_announcements(path="/custom/path", limit=5)
```

#### Dersler ve Transkript
```python
# Ders listesi
courses = student_courses()

# Transkript
transcript = student_transcript()
```

#### Öğrenci Sayfaları (Parse edilmiş)
```python
# Dönem dersleri (DonemDersleri.aspx)
term_courses = student_term_courses()

# Derslerim (Derslerim.aspx)
my_courses = student_my_courses()
```

#### Sayfa Navigasyonu
```python
# Belirli sayfaya git
page_info = student_navigate_to_page("/Birimler/Ogrenci/Derslerim.aspx")
```

### 🚀 Yeni Özellikler

#### Akademik Analiz
```python
# Kapsamlı akademik analiz
analytics = student_academic_analytics()

# Performans takibi
performance = student_performance_tracking()

# Ders seçim asistanı
course_advisor = student_course_advisor()
```

#### Bildirim Sistemi
```python
# Tüm bildirimleri al
notifications = student_notifications()

# Bildirim ayarları
settings = student_notification_settings()

# Bildirimi okundu işaretle
result = student_mark_notification_read("notification_id")
```

#### Veri Export
```python
# JSON formatında export
json_data = student_export_data(format="json", data_type="academic")

# CSV formatında export
csv_data = student_export_data(format="csv", data_type="all")

# Desteklenen formatları listele
formats = student_export_formats()
```

## 🛠️ API Referansı

### Login Fonksiyonları

| Fonksiyon | Açıklama | Parametreler |
|-----------|----------|--------------|
| `student_login()` | Öğrenci girişi | `base_url`, `username`, `password`, `login_path`, `username_field`, `password_field` |
| `student_login_debug()` | Debug login | Aynı + `check_path`, `success_text`, `payload_json`, `extra_fields` |
| `student_logout()` | Çıkış | Yok |

### Veri Çekme Fonksiyonları

| Fonksiyon | Açıklama | Parametreler |
|-----------|----------|--------------|
| `student_info()` | Öğrenci bilgileri | Yok |
| `student_info_parsed()` | Parse edilmiş bilgiler | Yok |
| `student_announcements()` | Duyurular | `path`, `limit` |
| `student_courses()` | Dersler | `path` |
| `student_transcript()` | Transkript | `path` |
| `student_profile()` | Profil | `profile_path` |
| `student_navigate_to_page()` | Sayfa navigasyonu | `page_path` |

### Öğrenci Sayfa Fonksiyonları

| Fonksiyon | Açıklama | Parametreler |
|-----------|----------|--------------|
| `student_term_courses()` | Dönem dersleri | Yok |
| `student_my_courses()` | Derslerim | Yok |
| `student_weekly_schedule()` | Haftalık program | Yok |
| `student_attendance()` | Devamsızlık | Yok |
| `student_fees()` | Harç bilgileri | Yok |
| `student_library()` | Kütüphane borçları | Yok |
| `student_registration()` | Kayıt yenileme | Yok |
| `student_thesis()` | Tez işlemleri | Yok |
| `student_internships()` | Staj başvuruları | Yok |
| `student_petitions()` | Dilekçe işlemleri | Yok |
| `student_materials()` | Ders materyalleri | Yok |
| `student_online_education_links()` | Online eğitim linkleri | Yok |
| `student_events()` | Etkinlikler | Yok |

### 🚀 Yeni Eklenen Özellikler

| Fonksiyon | Açıklama | Parametreler |
|-----------|----------|--------------|
| `student_academic_analytics()` | Akademik performans analizi | Yok |
| `student_performance_tracking()` | Performans takibi ve hedefler | Yok |
| `student_course_advisor()` | Ders seçim asistanı | Yok |
| `student_notifications()` | Bildirim ve uyarı sistemi | Yok |
| `student_notification_settings()` | Bildirim ayarları | Yok |
| `student_mark_notification_read()` | Bildirim okundu işaretleme | `notification_id` |
| `student_export_data()` | Veri export | `format`, `data_type` |
| `student_export_formats()` | Desteklenen export formatları | Yok |

## 📋 Örnek Çıktılar

### Akademik Analiz
```json
{
  "success": true,
  "analytics": {
    "gpa_trend": {
      "current_gpa": 3.45,
      "trend": "improving",
      "improvement_potential": 0.55
    },
    "credit_analysis": {
      "completion_rate": 75.5,
      "remaining_credits": 60,
      "estimated_semesters_to_graduation": 2.0
    },
    "overall_score": {
      "total_score": 82.3,
      "level": "A",
      "grade": "BA"
    }
  }
}
```

### Bildirim Sistemi
```json
{
  "success": true,
  "notifications": [
    {
      "type": "Academic Warning",
      "priority": "High",
      "title": "Düşük GPA Uyarısı",
      "message": "GPA'nız 1.85 ile 2.0'ın altında",
      "action_required": true
    }
  ],
  "summary": {
    "total_notifications": 3,
    "high_priority": 1,
    "medium_priority": 2
  }
}
```

### Veri Export
```json
{
  "success": true,
  "format": "csv",
  "filename": "student_data_20241201_143022.csv",
  "size_bytes": 15420,
  "download_ready": true
}
```

## 🔧 Geliştirme

### Proje Yapısı

```
uni-mcp/
├── core.py              # Ana fonksiyonlar ve yeni özellikler
├── server.py            # MCP server ve tool tanımları
├── requirements.txt     # Python bağımlılıkları
├── requirements-mcp.txt # MCP bağımlılıkları
├── pyproject.toml      # Proje konfigürasyonu
└── README.md           # Bu dosya
```

### Yeni Fonksiyon Ekleme

1. `core.py` dosyasına fonksiyonu ekleyin
2. `server.py` dosyasına MCP tool'u ekleyin
3. Dokümantasyonu güncelleyin
4. Test edin

### Hata Ayıklama

Debug modunda çalıştırmak için:
```python
debug_info = student_login_debug(...)
print(json.dumps(debug_info, indent=2))
```

## 🛡️ Güvenlik

- Şifreler güvenli şekilde saklanır
- Session yönetimi otomatiktir
- HTTPS bağlantıları zorunludur
- CSRF token'ları otomatik işlenir

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📞 İletişim

Sorularınız için issue açabilir veya iletişime geçebilirsiniz.

---

**Not**: Bu araç sadece eğitim amaçlıdır. Kullanım sorumluluğu kullanıcıya aittir.
