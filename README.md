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

## 📦 Özellikler ve Durum

Durum efsanesi: ✅ Hazır · 🧪 Deneysel · 🕓 Planlı · ⚠️ Sorunlu

### 📊 Akademik Bilgiler
- ✅ Öğrenci Profil Bilgileri — Kişisel bilgiler, fakülte, bölüm, danışman
- ✅ Akademik Transkript — Sınıf bazında kredi ve GPA bilgileri
- ✅ Dönem Dersleri — Mevcut dönem dersleri, notlar, öğretim görevlileri
- ✅ Aldığınız Dersler — Tüm derslerinizin detaylı listesi

### 📬 İletişim ve Bilgilendirme
- 🕓 Mesaj Kutusu — Öğretim görevlileri ve öğrenci işleri mesajları
- ✅ Duyurular — Güncel üniversite duyuruları
- ✅ Sistem Menü Erişimi — Tüm mevcut sayfa linklerini görme

### 🔐 Sistem Yönetimi
- ✅ Giriş/Çıkış İşlemleri — Güvenli oturum yönetimi
- ✅ Sayfa Navigasyonu — Farklı OBS sayfalarına erişim
- ✅ Debug Modları — Teknik sorunları tespit etme

### 🟡 Program ve Takvim (Deneyebilirim)
- ✅ Ders Programı — Haftalık ders saatleri (tool: `student_weekly_schedule`)
- ⚠️ Sınav Programı — Sınav tarihleri (dinamik içerik kaynaklı teknik sorunlar)
- ✅ Devamsızlık Takibi — Yoklama bilgileri (tool: `student_attendance`)

### 💰 Mali Bilgiler
- ✅ Harç Bilgileri — Ödeme durumları (tool: `student_fees`)
- ✅ Kütüphane/Malzeme Bilgileri — Borç durumu (tool: `student_library`)

### 📋 İşlemler ve Başvurular
- ✅ Kayıt Yenileme — Ders ekleme/bırakma (tool: `student_registration`)
- ✅ Bitirme Tezi İşlemleri — Proje başvuruları (tool: `student_thesis`)
- ✅ Staj Başvuruları — Zorunlu/isteğe bağlı staj (tool: `student_internships`)
- ✅ Dilekçe İşlemleri — Online başvuru formu (tool: `student_petitions`)

### 📚 Eğitim İçerikleri
- ✅ Ders Dökümanları — Ders materyalleri (tool: `student_materials`)
- ✅ Online Eğitim Platformu — Uzaktan eğitim erişimi (tool: `student_online_education_links`)
- ✅ Etkinlikler — Katıldığınız etkinlikler (tool: `student_events`)

### ❌ Şu Anda Sorun Yaşananlar
- ⚠️ Not Ortalaması Hesaplama — JavaScript tabanlı sayfa
- ⚠️ Sınav Programı — Dinamik içerik yükleme sorunu
- ⚠️ Bazı raporlar — İçerik görüntüleme sorunları

## 🚀 Kurulum

### Gereksinimler

- Python 3.8+
- pip veya uv

### Adımlar

1. **Projeyi klonlayın:**
```bash
git clone <repository-url>
cd uni-mcp
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

### 🔍 Genel Fonksiyonlar

```python
# Bölüm listesi
departments = get_departments()

# Duyuru arama
announcements = get_announcements(query="sınav", limit=5)
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

### Yardımcı Fonksiyonlar

| Fonksiyon | Açıklama | Parametreler |
|-----------|----------|--------------|
| `parse_student_info()` | HTML parse | `html_content` |
| `get_departments()` | Bölüm listesi | Yok |
| `get_announcements()` | Duyuru arama | `query`, `limit` |

## 📋 Örnek Çıktılar

### Öğrenci Bilgileri
```json
{
  "student_id": "**********",
  "first_name": "***",
  "last_name": "***",
  "tc_identity": "***********",
  "faculty": "Teknoloji Fakültesi",
  "department": "Bilgisayar Mühendisliği",
  "class_level": "1",
  "education_type": "1.Öğretim",
  "section": "A",
  "advisor": "******",
  "status": "OKUYAN",
  "email": "*********@isparta.edu.tr",
  "academic_records": [...],
  "menu_links": [...]
}
```

### Duyuru Listesi
```json
{
  "announcements": [
    {
      "id": "1",
      "title": "2025-2026 AKADEMİK TAKVİMİ",
      "url": "https://obs.isparta.edu.tr/...",
      "date": "Pzt, 18.Ağu.2025",
      "source": "OBS Ana Sayfa"
    }
  ],
  "count": 1,
  "source": "OBS"
}
```

## 🔧 Geliştirme

### Proje Yapısı

```
uni-mcp/
├── core.py              # Ana fonksiyonlar
├── server.py            # MCP server
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
