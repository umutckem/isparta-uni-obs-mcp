"""
Isparta Üniversitesi OBS (Öğrenci Bilgi Sistemi) MCP Tools

Bu modül, Isparta Üniversitesi'nin OBS sistemine bağlanmak ve öğrenci bilgilerini
almak için gerekli fonksiyonları içerir.

Özellikler:
- ASP.NET WebForms tabanlı login sistemi
- Öğrenci bilgileri çekme ve parse etme
- Duyuru, ders ve transkript bilgileri alma
- Session yönetimi
"""

from typing import Optional, TypedDict, List, Dict, Any
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from datetime import datetime

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# TYPED DICT TANIMLARI
# =============================================================================




class StudentProfile(TypedDict, total=False):
    """Öğrenci profil bilgileri için tip tanımı"""
    student_id: str
    name: str
    email: str
    faculty: str
    department: str
    program: str
    class_level: str
    advisor: str


class AcademicRecord(TypedDict):
    """Akademik kayıt bilgileri için tip tanımı"""
    student_id: str
    first_name: str
    last_name: str
    class_level: str
    yearly_credits: str
    fall_credits: str
    spring_credits: str
    total_credits: str
    gpa: str


class MenuLink(TypedDict):
    """Menü linki bilgileri için tip tanımı"""
    text: str
    href: str
    tabindex: str


# =============================================================================
# GLOBAL DEĞİŞKENLER
# =============================================================================

# Öğrenci OBS (Öğrenci Bilgi Sistemi) oturumu
_student_obs_session: Optional[requests.Session] = None
_student_obs_base_url: Optional[str] = None

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def _extract_csrf_fields(html_text: str) -> Dict[str, str]:
    """
    Login sayfasındaki CSRF ve ASP.NET WebForms input alanlarını toplar.
    
    Args:
        html_text: HTML içeriği
        
    Returns:
        Hidden input alanlarının name-value çiftleri
    """
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        hidden_inputs = soup.find_all("input", {"type": "hidden"})
        fields: Dict[str, str] = {}
        
        for inp in hidden_inputs:
            name = inp.get("name")
            value = inp.get("value")
            if name and value:
                # Yaygın CSRF alanları önceliklidir
                if name in (
                    "__RequestVerificationToken",
                    "csrfmiddlewaretoken",
                    "__csrf",
                    "_csrf",
                    "csrf_token",
                    "CSRFToken",
                    "authenticity_token",
                    # ASP.NET WebForms field'ları
                    "__VIEWSTATE",
                    "__VIEWSTATEGENERATOR", 
                    "__EVENTVALIDATION",
                ):
                    fields[name] = value
                else:
                    # Diğer hidden alanları da ekle
                    fields.setdefault(name, value)
        return fields
    except Exception as e:
        logger.error(f"CSRF alanları çıkarma hatası: {e}")
        return {}


def _parse_home_announcements(html_text: str, base_url: str, limit: int) -> List[Dict[str, Any]]:
    """
    OBS ana sayfasındaki duyuruları HTML'den çıkarır.
    
    Args:
        html_text: HTML içeriği
        base_url: Temel URL
        limit: Maksimum duyuru sayısı
        
    Returns:
        Duyuru listesi
    """
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        
        # Önce ID ile dene
        grid = soup.find("table", id="Duyurular1_gridDuyuru")
        
        # ID bulunamazsa, duyuru kelimesi geçen tabloları ara
        if not grid:
            tables = soup.find_all("table")
            for table in tables:
                # Tablo içeriğinde "Duyuru" kelimesi geçiyor mu kontrol et
                if "duyuru" in table.get_text().lower():
                    grid = table
                    break
        
        if not grid:
            logger.warning("Duyuru tablosu bulunamadı")
            return []

        results: List[Dict[str, Any]] = []
        
        # Satırlardaki link ve tarihi topla
        for row in grid.find_all("tr"):
            if len(results) >= limit:
                break
                
            link = row.find("a")
            if not link:
                continue
                
            title = (link.get_text(strip=True) or "").strip()
            if not title:
                continue

            # Tarih genellikle aynı satır veya sonrasında id'si ...Label3 olan span'da
            date_span = row.find("span")
            date_text = (date_span.get_text(strip=True) if date_span else "")

            ann: Dict[str, Any] = {
                "id": link.get("id") or title or "",
                "title": title,
                "url": urljoin(base_url, link.get("href", "")),
                "date": date_text,
                "source": "OBS Ana Sayfa"
            }
            results.append(ann)

        return results
    except Exception as e:
        logger.error(f"Duyuru parse etme hatası: {e}")
        return []


def _parse_student_announcements(html_text: str, base_url: str, limit: int) -> List[Dict[str, Any]]:
    """Öğrenci panelindeki (logged-in) duyuru tablosunu parse eder.
    Beklenen tablo id: ctl00_ContentPlaceHolder1_Duyurular1_gridDuyuru
    Fallback: içeriğinde 'Duyuru' geçen tablo.
    """
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        grid = soup.find("table", id="ctl00_ContentPlaceHolder1_Duyurular1_gridDuyuru")
        if not grid:
            # Fallback: içerikte 'Duyuru' geçen tablo ara
            for table in soup.find_all("table"):
                if "duyuru" in table.get_text().lower():
                    grid = table
                    break
        if not grid:
            return []
        results: List[Dict[str, Any]] = []
        for row in grid.find_all("tr"):
            if len(results) >= limit:
                break
            link = row.find("a")
            if not link:
                continue
            title = (link.get_text(strip=True) or "").strip()
            if not title:
                continue
            date_span = row.find("span")
            date_text = (date_span.get_text(strip=True) if date_span else "")
            ann: Dict[str, Any] = {
                "id": link.get("id") or title or "",
                "title": title,
                "url": urljoin(base_url, link.get("href", "")),
                "date": date_text,
                "source": "OBS Öğrenci Sayfası",
            }
            results.append(ann)
        return results
    except Exception as e:
        logger.error(f"Öğrenci sayfası duyuru parse hatası: {e}")
        return []


# =============================================================================
# OBS LOGIN FONKSİYONLARI
# =============================================================================

def student_obs_login(
    base_url: str,
    username: str,
    password: str,
    login_path: str = "/",
    username_field: str = "textKulID",
    password_field: str = "textSifre"
) -> bool:
    """
    Isparta Üniversitesi OBS sistemine öğrenci girişi yapar.
    
    Args:
        base_url: OBS sisteminin temel URL'i
        username: Öğrenci numarası
        password: Şifre
        login_path: Login sayfasının yolu
        username_field: Kullanıcı adı alanının name'i
        password_field: Şifre alanının name'i
        
    Returns:
        Login başarılı ise True, değilse False
    """
    global _student_obs_session, _student_obs_base_url
    
    try:
        # Session oluştur
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # Login sayfasını al
        login_url = urljoin(base_url, login_path)
        resp = session.get(login_url, timeout=20)
        
        if resp.status_code >= 400:
            logger.error(f"Login sayfası erişim hatası: {resp.status_code}")
            return False
        
        # CSRF alanlarını çıkar
        csrf_fields = _extract_csrf_fields(resp.text)
        
        # Form action'ını bul
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form")
        form_action = form.get("action") if form else ""
        
        # Form payload'unu hazırla
        form_payload = {
            username_field: username,
            password_field: password,
            # ASP.NET WebForms için gerekli alanlar
            "__EVENTTARGET": "buttonTamam",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            # Submit button
            "buttonTamam": "Giriş"
        }
        
        # CSRF alanlarını ekle
        form_payload.update(csrf_fields)
        
        # Form action URL'ini çöz
        if form_action.startswith("/"):
            post_url = urljoin(base_url, form_action)
        else:
            post_url = urljoin(login_url, form_action)
        
        # Login isteği gönder
        login_resp = session.post(post_url, data=form_payload, timeout=20)
        
        # Login başarısını kontrol et
        has_cookies = bool(session.cookies)
        ok_status = 200 <= login_resp.status_code < 400
        ok_text = "Öğrenci Girişi" not in login_resp.text
        
        # Login sonrası sayfa kontrolü
        check_url = urljoin(base_url, "/Birimler/Ogrenci/")
        check = session.get(check_url, timeout=20)
        
        login_redirected_to_student_page = (
            "Birimler/Ogrenci/" in login_resp.url or
            "Ogrenci/" in login_resp.url or
            login_resp.url != login_url
        )
        
        not_on_login_page = (
            "Öğrenci Girişi" not in check.text and
            "textKulID" not in check.text and
            "textSifre" not in check.text
        )
        
        student_panel_indicators = (
            "Öğrenci Paneli" in check.text or
            "Hoşgeldiniz" in check.text or
            "Profil" in check.text or
            check.url != login_url
        )
        
        login_success = has_cookies and ok_status and ok_text and (
            login_redirected_to_student_page or 
            not_on_login_page or 
            student_panel_indicators
        )
        
        if login_success:
            _student_obs_session = session
            _student_obs_base_url = base_url
            logger.info(f"OBS login başarılı: {username}")
        else:
            logger.error(f"OBS login başarısız: {username}")
            
        return login_success
        
    except Exception as e:
        logger.error(f"OBS login hatası: {e}")
        return False


def student_obs_login_debug(
    base_url: str,
    username: str,
    password: str,
    login_path: str = "/",
    username_field: str = "textKulID",
    password_field: str = "textSifre",
    check_path: str = "/",
    success_text: Optional[str] = None,
    payload_json: bool = False,
    extra_fields: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    OBS login işlemini detaylı debug bilgileriyle gerçekleştirir.
    
    Args:
        base_url: OBS sisteminin temel URL'i
        username: Öğrenci numarası
        password: Şifre
        login_path: Login sayfasının yolu
        username_field: Kullanıcı adı alanının name'i
        password_field: Şifre alanının name'i
        check_path: Login sonrası kontrol edilecek sayfa
        success_text: Başarılı login'de bulunması gereken metin
        payload_json: Payload'u JSON olarak döndür
        extra_fields: Ek form alanları
        
    Returns:
        Debug bilgileri içeren sözlük
    """
    global _student_obs_session, _student_obs_base_url
    
    report = {
        "base_url": base_url,
        "username": username,
        "login_path": login_path,
        "username_field": username_field,
        "password_field": password_field,
        "check_path": check_path,
        "success_text": success_text,
        "payload_json": payload_json,
        "extra_fields": extra_fields,
        "ok": False,
        "error": None,
        "login_response_status": None,
        "login_response_url": None,
        "login_url": None,
        "post_url": None,
        "form_action": None,
        "csrf_fields": {},
        "form_payload": {},
        "check_response_status": None,
        "check_response_url": None,
        "check_text_contains_login_form": None,
        "check_text_contains_success_indicators": None,
        "has_cookies": False,
        "login_redirected_to_student_page": False,
        "not_on_login_page": False,
        "student_panel_indicators": False
    }
    
    try:
        # Session oluştur
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # Login sayfasını al
        login_url = urljoin(base_url, login_path)
        report["login_url"] = login_url
        
        resp = session.get(login_url, timeout=20)
        report["login_response_status"] = resp.status_code
        
        if resp.status_code >= 400:
            report["error"] = f"Login sayfası erişim hatası: {resp.status_code}"
            return report
        
        # CSRF alanlarını çıkar
        csrf_fields = _extract_csrf_fields(resp.text)
        report["csrf_fields"] = csrf_fields
        
        # Form action'ını bul
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form")
        form_action = form.get("action") if form else ""
        report["form_action"] = form_action
        
        # Form payload'unu hazırla
        form_payload = {
            username_field: username,
            password_field: password,
            # ASP.NET WebForms için gerekli alanlar
            "__EVENTTARGET": "buttonTamam",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            # Submit button
            "buttonTamam": "Giriş"
        }
        
        # CSRF alanlarını ekle
        form_payload.update(csrf_fields)
        
        # Ek alanları ekle
        if extra_fields:
            form_payload.update(extra_fields)

        report["form_payload"] = form_payload
        
        # Form action URL'ini çöz
        if form_action.startswith("/"):
            post_url = urljoin(base_url, form_action)
        else:
            post_url = urljoin(login_url, form_action)
        
        report["post_url"] = post_url
        
        # Login isteği gönder
        login_resp = session.post(post_url, data=form_payload, timeout=20)
        report["login_response_status"] = login_resp.status_code
        report["login_response_url"] = login_resp.url
        
        # Login başarısını kontrol et
        has_cookies = bool(session.cookies)
        report["has_cookies"] = has_cookies
        
        ok_status = 200 <= login_resp.status_code < 400
        ok_text = "Öğrenci Girişi" not in login_resp.text
        
        # Login sonrası sayfa kontrolü
        check_url = urljoin(base_url, check_path)
        check = session.get(check_url, timeout=20)
        report["check_response_status"] = check.status_code
        report["check_response_url"] = check.url
        
        report["check_text_contains_login_form"] = (
            "Öğrenci Girişi" in check.text or
            "textKulID" in check.text or
            "textSifre" in check.text
        )
        
        report["check_text_contains_success_indicators"] = (
            "Öğrenci Paneli" in check.text or
            "Hoşgeldiniz" in check.text or
            "Profil" in check.text
        )
        
        login_redirected_to_student_page = (
            "Birimler/Ogrenci/" in login_resp.url or
            "Ogrenci/" in login_resp.url or
            login_resp.url != login_url
        )
        report["login_redirected_to_student_page"] = login_redirected_to_student_page
        
        not_on_login_page = (
            "Öğrenci Girişi" not in check.text and
            "textKulID" not in check.text and
            "textSifre" not in check.text
        )
        report["not_on_login_page"] = not_on_login_page
        
        student_panel_indicators = (
            "Öğrenci Paneli" in check.text or
            "Hoşgeldiniz" in check.text or
            "Profil" in check.text or
            check.url != login_url
        )
        report["student_panel_indicators"] = student_panel_indicators
        
        login_success = has_cookies and ok_status and ok_text and (
            login_redirected_to_student_page or 
            not_on_login_page or 
            student_panel_indicators
        )
        
        report["ok"] = login_success

        if login_success:
            _student_obs_session = session
            _student_obs_base_url = base_url
            logger.info(f"OBS login başarılı: {username}")
        else:
            logger.error(f"OBS login başarısız: {username}")
            
        return report

    except Exception as e:
        report["error"] = str(e)
        logger.error(f"OBS login debug hatası: {e}")
        return report


def student_obs_logout() -> bool:
    """
    OBS oturumunu kapatır.
    
    Returns:
        Logout başarılı ise True, değilse False
    """
    global _student_obs_session, _student_obs_base_url
    
    try:
        if _student_obs_session and _student_obs_base_url:
            logout_url = urljoin(_student_obs_base_url, "/Birimler/Ogrenci/Cikis.aspx")
            _student_obs_session.get(logout_url, timeout=10)
            
        _student_obs_session = None
        _student_obs_base_url = None
        logger.info("OBS logout başarılı")
        return True
        
    except Exception as e:
        logger.error(f"OBS logout hatası: {e}")
        return False


# =============================================================================
# OBS VERİ ÇEKME FONKSİYONLARI
# =============================================================================

def student_obs_navigate_to_page(page_path: str = "/") -> Dict[str, Any]:
    """
    OBS'de belirli bir sayfaya gider ve içeriği döndürür.
    
    Args:
        page_path: Gidilecek sayfanın yolu
        
    Returns:
        Sayfa bilgileri içeren sözlük
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        url = urljoin(_student_obs_base_url, page_path)
        resp = _student_obs_session.get(url, timeout=20)
        
        return {
            "status_code": resp.status_code,
            "url": resp.url,
            "content": resp.text[:1000] + "..." if len(resp.text) > 1000 else resp.text
        }
        
    except Exception as e:
        logger.error(f"Sayfa navigasyon hatası: {e}")
        return {"error": str(e)}


def student_obs_get_profile(profile_path: str = "/api/profile") -> Dict[str, Any]:
    """
    OBS'den öğrenci profil bilgilerini alır.
    
    Args:
        profile_path: Profil sayfasının yolu
        
    Returns:
        Profil bilgileri içeren sözlük
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        url = urljoin(_student_obs_base_url, profile_path)
        resp = _student_obs_session.get(url, timeout=20)
        
        if resp.status_code >= 400:
            return {"error": f"Profil erişim hatası: {resp.status_code}"}
        
        return {"raw": resp.text}
        
    except Exception as e:
        logger.error(f"Profil alma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_announcements(path: str = "/api/announcements", limit: int = 10) -> Dict[str, Any]:
    """
    OBS'den duyuruları alır.
    
    Args:
        path: Duyuru sayfasının yolu
        limit: Maksimum duyuru sayısı
        
    Returns:
        Duyuru listesi içeren sözlük
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        url = urljoin(_student_obs_base_url, path)
        resp = _student_obs_session.get(url, timeout=20)
        
        if resp.status_code >= 400:
            return {"error": f"Duyuru erişim hatası: {resp.status_code}"}
        
        announcements = _parse_home_announcements(resp.text, _student_obs_base_url, limit)
        
        return {
            "announcements": announcements,
            "count": len(announcements),
            "source": "OBS"
        }
        
    except Exception as e:
        logger.error(f"Duyuru alma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_student_announcements(limit: int = 10) -> Dict[str, Any]:
    """Giriş yapıldıktan sonra öğrenci sayfasındaki duyuruları döndürür."""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    try:
        url = urljoin(_student_obs_base_url, "/Birimler/Ogrenci/Bilgilerim.aspx")
        resp = _student_obs_session.get(url, timeout=20)
        if resp.status_code >= 400:
            return {"error": f"Duyuru sayfası erişim hatası: {resp.status_code}"}
        announcements = _parse_student_announcements(resp.text, _student_obs_base_url, limit)
        return {
            "announcements": announcements,
            "count": len(announcements),
            "source": "OBS Öğrenci Sayfası",
        }
    except Exception as e:
        logger.error(f"Öğrenci sayfası duyuru alma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_messages() -> Dict[str, Any]:
    """Mesajlarim.aspx sayfasından mesajları parse eder."""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    try:
        url = urljoin(_student_obs_base_url, "/Birimler/Ogrenci/Mesajlarim.aspx")
        resp = _student_obs_session.get(url, timeout=20)
        if resp.status_code >= 400:
            return {"error": f"Mesaj sayfası erişim hatası: {resp.status_code}"}
        soup = BeautifulSoup(resp.text, "html.parser")
        messages: List[Dict[str, Any]] = []
        # Heuristik: satırları olan tabloları gez ve anlamlı hücreleri mesaj olarak ekle
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows or len(rows) < 2:
                continue
            headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
            for tr in rows[1:]:
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if not tds:
                    continue
                if headers and len(headers) == len(tds):
                    row = {headers[i] or f"col_{i}": tds[i] for i in range(len(tds))}
                else:
                    # İlk hücreyi başlık veya konu varsayalım
                    row = {f"col_{i}": tds[i] for i in range(len(tds))}
                # Basit filtre: anlamlı görünümlü satırlar
                if any(len(val) > 2 for val in row.values()):
                    messages.append(row)
        return {"url": url, "messages": messages}
    except Exception as e:
        logger.error(f"Mesajlar parse hatası: {e}")
        return {"error": str(e)}


def student_obs_get_courses(path: str = "/api/courses") -> Dict[str, Any]:
    """
    OBS'den ders bilgilerini alır.
    
    Args:
        path: Ders sayfasının yolu
        
    Returns:
        Ders bilgileri içeren sözlük
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        url = urljoin(_student_obs_base_url, path)
        resp = _student_obs_session.get(url, timeout=20)
        
        if resp.status_code >= 400:
            return {"error": f"Ders erişim hatası: {resp.status_code}"}
        
        return {"raw": resp.text}
        
    except Exception as e:
        logger.error(f"Ders alma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_transcript(path: str = "/api/transcript") -> Dict[str, Any]:
    """
    OBS'den transkript bilgilerini alır.
    
    Args:
        path: Transkript sayfasının yolu
        
    Returns:
        Transkript bilgileri içeren sözlük
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        url = urljoin(_student_obs_base_url, path)
        resp = _student_obs_session.get(url, timeout=20)
        
        if resp.status_code >= 400:
            return {"error": f"Transkript erişim hatası: {resp.status_code}"}
        
        return {"raw": resp.text}
        
    except Exception as e:
        logger.error(f"Transkript alma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_student_info() -> Dict[str, Any]:
    """
    OBS'den öğrenci bilgilerini çeker (HTML parsing ile).
    
    Returns:
        Öğrenci bilgileri içeren sözlük
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        # Öğrenci bilgileri sayfasına git
        student_info_url = _student_obs_base_url + "/Birimler/Ogrenci/Bilgilerim.aspx"
        resp = _student_obs_session.get(student_info_url, timeout=20)
        
        if resp.status_code >= 400:
            return {"error": f"Öğrenci bilgileri sayfası erişim hatası: {resp.status_code}"}
        
        # HTML'i parse et
        parsed_info = student_obs_parse_student_info(resp.text)
        
        if "error" in parsed_info:
            return parsed_info
        
        # Başarılı ise ek bilgiler ekle
        parsed_info["source_url"] = student_info_url
        parsed_info["parsed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return parsed_info
        
    except Exception as e:
        logger.error(f"OBS öğrenci bilgileri alma hatası: {e}")
        return {"error": str(e)}


def student_obs_parse_student_info(html_content: str) -> Dict[str, Any]:
    """
    HTML'den öğrenci bilgilerini parse eder.
    
    Args:
        html_content: HTML içeriği
        
    Returns:
        Parse edilmiş öğrenci bilgileri
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Öğrenci temel bilgileri
        student_info = {}
        
        # Öğrenci numarası
        ogrenci_no = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textOgrenciNo"})
        if ogrenci_no:
            student_info["student_id"] = ogrenci_no.get_text(strip=True)
        
        # Ad
        adi = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textAdi"})
        if adi:
            student_info["first_name"] = adi.get_text(strip=True)
        
        # Soyad
        soyadi = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textSoyadi"})
        if soyadi:
            student_info["last_name"] = soyadi.get_text(strip=True)
        
        # TC Kimlik
        tc = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textTC"})
        if tc:
            student_info["tc_identity"] = tc.get_text(strip=True)
        
        # Fakülte
        fakulte = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textFakulte"})
        if fakulte:
            student_info["faculty"] = fakulte.get_text(strip=True)
        
        # Bölüm
        bolum = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textBolum"})
        if bolum:
            student_info["department"] = bolum.get_text(strip=True)
        
        # Alt Program
        alt_program = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textAltProgram"})
        if alt_program:
            student_info["sub_program"] = alt_program.get_text(strip=True)
        
        # Sınıf
        sinif = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textSinif"})
        if sinif:
            student_info["class_level"] = sinif.get_text(strip=True)
        
        # Öğretim
        ogretim = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textOgretim"})
        if ogretim:
            student_info["education_type"] = ogretim.get_text(strip=True)
        
        # Şube
        sube = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textSube"})
        if sube:
            student_info["section"] = sube.get_text(strip=True)
        
        # Danışman
        danisman = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textDanisman"})
        if danisman:
            student_info["advisor"] = danisman.get_text(strip=True)
        
        # Durum
        durum = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textDurum"})
        if durum:
            student_info["status"] = durum.get_text(strip=True)
        
        # E-posta
        email = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_OgrenciTemelBilgiler1_textSDUMail"})
        if email:
            student_info["email"] = email.get_text(strip=True)
        
        # Akademik bilgiler (tablo)
        academic_info = []
        table = soup.find("table", {"id": "ctl00_ContentPlaceHolder1_gridOgrenciKnt"})
        if table:
            rows = table.find_all("tr")[1:]  # İlk satır başlık
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 9:
                    academic_info.append({
                        "student_id": cells[0].get_text(strip=True),
                        "first_name": cells[1].get_text(strip=True),
                        "last_name": cells[2].get_text(strip=True),
                        "class_level": cells[3].get_text(strip=True),
                        "yearly_credits": cells[4].get_text(strip=True),
                        "fall_credits": cells[5].get_text(strip=True),
                        "spring_credits": cells[6].get_text(strip=True),
                        "total_credits": cells[7].get_text(strip=True),
                        "gpa": cells[8].get_text(strip=True)
                    })
        
        student_info["academic_records"] = academic_info
        
        # Menü linkleri
        menu_links = []
        menu_div = soup.find("div", {"id": "anamenu"})
        if menu_div:
            links = menu_div.find_all("a")
            for link in links:
                menu_links.append({
                    "text": link.get_text(strip=True),
                    "href": link.get("href", ""),
                    "tabindex": link.get("tabindex", "")
                })
        
        student_info["menu_links"] = menu_links
        
        return student_info
        
    except Exception as e:
        logger.error(f"Öğrenci bilgilerini parse etme hatası: {e}")
        return {"error": str(e)}


def student_obs_get_student_info_parsed() -> Dict[str, Any]:
    """
    OBS'den öğrenci bilgilerini alır ve parse eder.
    
    Returns:
        Parse edilmiş öğrenci bilgileri
    """
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}

    try:
        # Öğrenci bilgileri sayfasına git
        student_info_url = _student_obs_base_url + "/Birimler/Ogrenci/Bilgilerim.aspx"
        resp = _student_obs_session.get(student_info_url, timeout=20)
        
        if resp.status_code >= 400:
            return {"error": f"Öğrenci bilgileri sayfası erişim hatası: {resp.status_code}"}
        
        # HTML'i parse et
        parsed_info = student_obs_parse_student_info(resp.text)
        
        if "error" in parsed_info:
            return parsed_info
        
        # Başarılı ise ek bilgiler ekle
        parsed_info["source_url"] = student_info_url
        parsed_info["parsed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return parsed_info

    except Exception as e:
        logger.error(f"OBS öğrenci bilgileri alma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_term_courses() -> Dict[str, Any]:
    """DonemDersleri.aspx sayfasından dönem derslerini çeker ve parse eder."""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    try:
        url = urljoin(_student_obs_base_url, "/Birimler/Ogrenci/DonemDersleri.aspx")
        resp = _student_obs_session.get(url, timeout=20)
        if resp.status_code >= 400:
            return {"error": f"Erişim hatası: {resp.status_code}"}
        soup = BeautifulSoup(resp.text, "html.parser")
        # Basit tablo parse: tüm tabloları gez ve hücre metinlerini çıkar
        tables: list[dict] = []
        for table in soup.find_all("table"):
            rows_out: list[list[str]] = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                if cells:
                    rows_out.append(cells)
            if rows_out:
                tables.append({"rows": rows_out})
        return {"url": url, "tables": tables}
    except Exception as e:
        logger.error(f"Dönem dersleri parse hatası: {e}")
        return {"error": str(e)}


def student_obs_get_my_courses() -> Dict[str, Any]:
    """Derslerim.aspx sayfasından öğrencinin derslerini çeker ve parse eder."""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    try:
        url = urljoin(_student_obs_base_url, "/Birimler/Ogrenci/Derslerim.aspx")
        resp = _student_obs_session.get(url, timeout=20)
        if resp.status_code >= 400:
            return {"error": f"Erişim hatası: {resp.status_code}"}
        soup = BeautifulSoup(resp.text, "html.parser")
        # Olası ders tablolarını yakala
        courses: list[dict] = []
        for table in soup.find_all("table"):
            headers: list[str] = []
            first_tr = table.find("tr")
            if first_tr:
                headers = [th.get_text(strip=True) for th in first_tr.find_all("th")]
            for tr in table.find_all("tr")[1:]:
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if not tds:
                    continue
                # header ile eşleştir
                if headers and len(headers) == len(tds):
                    row = {headers[i] or f"col_{i}": tds[i] for i in range(len(tds))}
                else:
                    row = {f"col_{i}": tds[i] for i in range(len(tds))}
                courses.append(row)
        return {"url": url, "courses": courses}
    except Exception as e:
        logger.error(f"Derslerim parse hatası: {e}")
        return {"error": str(e)}


# =============================================================================
# GENEL AMAÇLI PARSE/YARDIMCI FONKSİYONLAR
# =============================================================================

def _parse_all_tables(html_text: str) -> List[Dict[str, Any]]:
    """HTML içinden tüm tabloları satır listeleri şeklinde döndürür.
    Her tablo: {"rows": [[hücre1, hücre2, ...], ...]}
    """
    soup = BeautifulSoup(html_text, "html.parser")
    tables: List[Dict[str, Any]] = []
    for table in soup.find_all("table"):
        rows_out: List[List[str]] = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows_out.append(cells)
        if rows_out:
            tables.append({"rows": rows_out})
    return tables


def _try_fetch_tables(candidate_paths: List[str]) -> Dict[str, Any]:
    """Aday sayfa yollarından ilk başarılı olanı getirip tüm tabloları döndürür."""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    last_error: Optional[str] = None
    for rel_path in candidate_paths:
        try:
            url = urljoin(_student_obs_base_url, rel_path)
            resp = _student_obs_session.get(url, timeout=20)
            if resp.status_code >= 400:
                last_error = f"Erişim hatası: {resp.status_code} ({rel_path})"
                continue
            tables = _parse_all_tables(resp.text)
            return {"url": url, "tables": tables}
        except Exception as e:
            last_error = str(e)
            continue
    return {"error": last_error or "Sayfa bulunamadı"}


# =============================================================================
# EKSİK ÖZELLİKLER: PROGRAM, DEVAMSIZLIK, MALİ, İŞLEMLER, İÇERİKLER
# =============================================================================

def student_obs_get_weekly_schedule() -> Dict[str, Any]:
    """Haftalık ders programını döndürür (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/DersProgrami.aspx",
        "/Birimler/Ogrenci/DersProgram.aspx",
        "/Birimler/Ogrenci/Program.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_attendance() -> Dict[str, Any]:
    """Devamsızlık/Yoklama bilgilerini döndürür (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/Devamsizlik.aspx",
        "/Birimler/Ogrenci/Yoklama.aspx",
        "/Birimler/Ogrenci/DevamsizlikTakip.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_fees() -> Dict[str, Any]:
    """Harç/ödeme bilgilerini döndürür (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/HarcBilgileri.aspx",
        "/Birimler/Ogrenci/Odemeler.aspx",
        "/Birimler/Ogrenci/MaliIsler.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_library() -> Dict[str, Any]:
    """Kütüphane/Malzeme borç bilgilerini döndürür (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/Kutuphane.aspx",
        "/Birimler/Ogrenci/Malzeme.aspx",
        "/Birimler/Ogrenci/Material.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_registration() -> Dict[str, Any]:
    """Kayıt yenileme / Ders kayıt sayfalarındaki tabloları döndürür."""
    candidates = [
        "/Birimler/Ogrenci/KayitYenileme.aspx",
        "/Birimler/Ogrenci/DersKayit.aspx",
        "/Birimler/Ogrenci/DersEkleCikar.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_thesis() -> Dict[str, Any]:
    """Bitirme tezi işlemleri/başvuruları (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/BitirmeTezi.aspx",
        "/Birimler/Ogrenci/TezIslemleri.aspx",
        "/Birimler/Ogrenci/TezBasvurulari.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_internships() -> Dict[str, Any]:
    """Staj başvuruları (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/ZorunluStajBasvuru.aspx",
        "/Birimler/Ogrenci/StajBasvurulari.aspx",
        "/Birimler/Ogrenci/Staj.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_petitions() -> Dict[str, Any]:
    """Dilekçe işlemleri (tablo olarak)."""
    candidates = [
        "/Birimler/Ogrenci/DilekceIslemleri.aspx",
        "/Birimler/Ogrenci/Dilekce.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_materials() -> Dict[str, Any]:
    """Ders dökümanları (tablo veya link listesi olarak)."""
    candidates = [
        "/Birimler/Ogrenci/DersDokumanlari.aspx",
        "/Birimler/Ogrenci/Dokumanlar.aspx",
    ]
    return _try_fetch_tables(candidates)


def student_obs_get_online_education_links() -> Dict[str, Any]:
    """Menüden uzaktan eğitim/öğrenme platform linklerini çıkarır."""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    try:
        # Ana öğrenci sayfası menüsünü kullan
        url = urljoin(_student_obs_base_url, "/Birimler/Ogrenci/")
        resp = _student_obs_session.get(url, timeout=20)
        if resp.status_code >= 400:
            return {"error": f"Erişim hatası: {resp.status_code}"}
        soup = BeautifulSoup(resp.text, "html.parser")
        links_out: List[Dict[str, str]] = []
        keywords = ["uzaktan", "moodle", "lms", "uzem", "canvas", "online eğitim", "öğrenme"]
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            href = a.get("href", "")
            t = text.lower()
            if any(k in t for k in keywords):
                links_out.append({
                    "text": text,
                    "href": urljoin(_student_obs_base_url, href),
                })
        return {"url": resp.url, "links": links_out}
    except Exception as e:
        logger.error(f"Online eğitim linkleri çıkarma hatası: {e}")
        return {"error": str(e)}


def student_obs_get_events() -> Dict[str, Any]:
    """Etkinlikler sayfasındaki tabloları döndürür."""
    candidates = [
        "/Birimler/Ogrenci/Etkinlikler.aspx",
        "/Birimler/Ogrenci/Etkinlik.aspx",
    ]
    return _try_fetch_tables(candidates)


# =============================================================================
# AKADEMİK ANALİZ VE İSTATİSTİKLER
# =============================================================================

def student_obs_get_academic_analytics() -> Dict[str, Any]:
    """Öğrencinin akademik performans analizini yapar"""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    
    try:
        # Transkript bilgilerini al
        transcript_data = student_obs_get_transcript()
        if "error" in transcript_data:
            return transcript_data
        
        # Dönem derslerini al
        term_courses = student_obs_get_term_courses()
        if "error" in term_courses:
            return term_courses
        
        # Öğrenci bilgilerini al
        student_info = student_obs_get_student_info()
        if "error" in student_info:
            return student_info
        
        # Analiz verilerini hazırla
        analytics = _calculate_academic_analytics(transcript_data, term_courses, student_info)
        
        return {
            "success": True,
            "analytics": analytics,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Akademik analiz hatası: {e}")
        return {"error": str(e)}


def _calculate_academic_analytics(transcript: Dict[str, Any], term_courses: Dict[str, Any], student_info: Dict[str, Any]) -> Dict[str, Any]:
    """Akademik analiz hesaplamalarını yapar"""
    try:
        # GPA trend analizi
        gpa_trend = _analyze_gpa_trend(transcript)
        
        # Kredi tamamlama analizi
        credit_analysis = _analyze_credit_completion(transcript, student_info)
        
        # Ders başarı analizi
        course_success = _analyze_course_success(transcript, term_courses)
        
        # Genel performans skoru
        overall_score = _calculate_overall_score(gpa_trend, credit_analysis, course_success)
        
        return {
            "gpa_trend": gpa_trend,
            "credit_analysis": credit_analysis,
            "course_success": course_success,
            "overall_score": overall_score,
            "recommendations": _generate_recommendations(gpa_trend, credit_analysis, course_success)
        }
        
    except Exception as e:
        logger.error(f"Analiz hesaplama hatası: {e}")
        return {"error": str(e)}


def _analyze_gpa_trend(transcript: Dict[str, Any]) -> Dict[str, Any]:
    """GPA trend analizini yapar"""
    try:
        if "academic_records" not in transcript:
            return {"error": "Transkript verisi bulunamadı"}
        
        records = transcript["academic_records"]
        gpa_data = []
        
        for record in records:
            if "gpa" in record and record["gpa"]:
                try:
                    gpa = float(record["gpa"].replace(",", "."))
                    gpa_data.append({
                        "class_level": record.get("class_level", ""),
                        "gpa": gpa,
                        "year": record.get("year", "")
                    })
                except (ValueError, AttributeError):
                    continue
        
        if not gpa_data:
            return {"error": "GPA verisi bulunamadı"}
        
        # GPA trend hesaplama
        gpa_data.sort(key=lambda x: x["class_level"])
        current_gpa = gpa_data[-1]["gpa"] if gpa_data else 0
        trend = "stable"
        
        if len(gpa_data) >= 2:
            first_gpa = gpa_data[0]["gpa"]
            if current_gpa > first_gpa + 0.5:
                trend = "improving"
            elif current_gpa < first_gpa - 0.5:
                trend = "declining"
        
        return {
            "current_gpa": current_gpa,
            "trend": trend,
            "gpa_history": gpa_data,
            "improvement_potential": max(0, 4.0 - current_gpa)
        }
        
    except Exception as e:
        logger.error(f"GPA trend analiz hatası: {e}")
        return {"error": str(e)}


def _analyze_credit_completion(transcript: Dict[str, Any], student_info: Dict[str, Any]) -> Dict[str, Any]:
    """Kredi tamamlama analizini yapar"""
    try:
        if "academic_records" not in transcript:
            return {"error": "Transkript verisi bulunamadı"}
        
        records = transcript["academic_records"]
        total_credits = 0
        completed_credits = 0
        
        for record in records:
            if "total_credits" in record and record["total_credits"]:
                try:
                    credits = float(record["total_credits"].replace(",", "."))
                    total_credits = max(total_credits, credits)
                    completed_credits = credits
                except (ValueError, AttributeError):
                    continue
        
        # Mezuniyet için gerekli kredi (genellikle 240)
        required_credits = 240
        completion_rate = (completed_credits / required_credits) * 100 if required_credits > 0 else 0
        
        # Kalan kredi hesaplama
        remaining_credits = max(0, required_credits - completed_credits)
        
        # Tahmini mezuniyet süresi
        avg_credits_per_semester = 30  # Ortalama dönem kredisi
        estimated_semesters = remaining_credits / avg_credits_per_semester if avg_credits_per_semester > 0 else 0
        
        return {
            "total_credits": total_credits,
            "completed_credits": completed_credits,
            "remaining_credits": remaining_credits,
            "completion_rate": round(completion_rate, 2),
            "required_credits": required_credits,
            "estimated_semesters_to_graduation": round(estimated_semesters, 1),
            "on_track": completion_rate >= 75  # %75 üzeri iyi durumda
        }
        
    except Exception as e:
        logger.error(f"Kredi analiz hatası: {e}")
        return {"error": str(e)}


def _analyze_course_success(transcript: Dict[str, Any], term_courses: Dict[str, Any]) -> Dict[str, Any]:
    """Ders başarı analizini yapar"""
    try:
        # Transkript'ten ders başarı oranları
        course_success_rates = {}
        total_courses = 0
        successful_courses = 0
        
        if "academic_records" in transcript:
            for record in transcript["academic_records"]:
                if "courses" in record:
                    for course in record["courses"]:
                        total_courses += 1
                        grade = course.get("grade", "")
                        if grade and grade not in ["F", "FF", "FD", "DD"]:
                            successful_courses += 1
        
        # Mevcut dönem dersleri analizi
        current_courses = []
        if "tables" in term_courses:
            for table in term_courses["tables"]:
                if "rows" in table:
                    for row in table["rows"]:
                        if len(row) >= 4:  # Ders adı, kredi, not, öğretim görevlisi
                            course_info = {
                                "name": row[0] if len(row) > 0 else "",
                                "credits": row[1] if len(row) > 1 else "",
                                "grade": row[2] if len(row) > 2 else "",
                                "instructor": row[3] if len(row) > 3 else ""
                            }
                            current_courses.append(course_info)
        
        success_rate = (successful_courses / total_courses * 100) if total_courses > 0 else 0
        
        return {
            "total_courses_taken": total_courses,
            "successful_courses": successful_courses,
            "overall_success_rate": round(success_rate, 2),
            "current_semester_courses": current_courses,
            "current_courses_count": len(current_courses),
            "performance_level": _get_performance_level(success_rate)
        }
        
    except Exception as e:
        logger.error(f"Ders başarı analiz hatası: {e}")
        return {"error": str(e)}


def _get_performance_level(success_rate: float) -> str:
    """Başarı oranına göre performans seviyesi belirler"""
    if success_rate >= 90:
        return "Mükemmel"
    elif success_rate >= 80:
        return "Çok İyi"
    elif success_rate >= 70:
        return "İyi"
    elif success_rate >= 60:
        return "Orta"
    else:
        return "Geliştirilmeli"


def _calculate_overall_score(gpa_trend: Dict[str, Any], credit_analysis: Dict[str, Any], course_success: Dict[str, Any]) -> Dict[str, Any]:
    """Genel performans skorunu hesaplar"""
    try:
        score = 0
        max_score = 100
        
        # GPA skoru (40 puan)
        if "current_gpa" in gpa_trend and not "error" in gpa_trend:
            gpa = gpa_trend["current_gpa"]
            gpa_score = min(40, (gpa / 4.0) * 40)
            score += gpa_score
        
        # Kredi tamamlama skoru (30 puan)
        if "completion_rate" in credit_analysis and not "error" in credit_analysis:
            completion = credit_analysis["completion_rate"]
            credit_score = min(30, (completion / 100) * 30)
            score += credit_score
        
        # Ders başarı skoru (30 puan)
        if "overall_success_rate" in course_success and not "error" in course_success:
            success = course_success["overall_success_rate"]
            success_score = min(30, (success / 100) * 30)
            score += success_score
        
        # Performans seviyesi
        if score >= 85:
            level = "A+"
        elif score >= 75:
            level = "A"
        elif score >= 65:
            level = "B+"
        elif score >= 55:
            level = "B"
        elif score >= 45:
            level = "C+"
        else:
            level = "C"
        
        return {
            "total_score": round(score, 1),
            "max_score": max_score,
            "percentage": round((score / max_score) * 100, 1),
            "level": level,
            "grade": _get_letter_grade(score)
        }
        
    except Exception as e:
        logger.error(f"Genel skor hesaplama hatası: {e}")
        return {"error": str(e)}


def _get_letter_grade(score: float) -> str:
    """Sayısal skoru harf notuna çevirir"""
    if score >= 90:
        return "AA"
    elif score >= 80:
        return "BA"
    elif score >= 70:
        return "BB"
    elif score >= 60:
        return "CB"
    elif score >= 50:
        return "CC"
    else:
        return "FF"


def _generate_recommendations(gpa_trend: Dict[str, Any], credit_analysis: Dict[str, Any], course_success: Dict[str, Any]) -> List[str]:
    """Analiz sonuçlarına göre öneriler üretir"""
    recommendations = []
    
    try:
        # GPA önerileri
        if "current_gpa" in gpa_trend and not "error" in gpa_trend:
            current_gpa = gpa_trend["current_gpa"]
            if current_gpa < 2.0:
                recommendations.append("GPA'nız 2.0'ın altında. Ders çalışma planınızı gözden geçirin.")
            elif current_gpa < 2.5:
                recommendations.append("GPA'nızı 2.5'ın üzerine çıkarmak için ek çaba gösterin.")
        
        # Kredi önerileri
        if "completion_rate" in credit_analysis and not "error" in credit_analysis:
            completion = credit_analysis["completion_rate"]
            if completion < 50:
                recommendations.append("Kredi tamamlama oranınız düşük. Daha fazla ders almayı düşünün.")
            elif completion > 80:
                recommendations.append("Kredi tamamlama oranınız iyi. Mezuniyet için planlı ilerleyin.")
        
        # Ders başarı önerileri
        if "overall_success_rate" in course_success and not "error" in course_success:
            success = course_success["overall_success_rate"]
            if success < 70:
                recommendations.append("Ders başarı oranınız düşük. Çalışma yöntemlerinizi gözden geçirin.")
        
        # Genel öneriler
        if not recommendations:
            recommendations.append("Akademik performansınız iyi durumda. Bu seviyeyi koruyun.")
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Öneri üretme hatası: {e}")
        return ["Analiz sırasında hata oluştu. Lütfen tekrar deneyin."]


# =============================================================================
# PERFORMANS TAKİBİ VE HEDEFLER
# =============================================================================

def student_obs_get_performance_tracking() -> Dict[str, Any]:
    """Akademik hedefler ve performans takibi"""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    
    try:
        # Akademik analiz verilerini al
        analytics = student_obs_get_academic_analytics()
        if "error" in analytics:
            return analytics
        
        # Performans hedeflerini hesapla
        performance_goals = _calculate_performance_goals(analytics)
        
        # İlerleme durumunu hesapla
        progress_status = _calculate_progress_status(analytics)
        
        # Hedef önerilerini üret
        goal_recommendations = _generate_goal_recommendations(analytics)
        
        return {
            "success": True,
            "performance_goals": performance_goals,
            "progress_status": progress_status,
            "goal_recommendations": goal_recommendations,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performans takibi hatası: {e}")
        return {"error": str(e)}


def _calculate_performance_goals(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """Performans hedeflerini hesaplar"""
    try:
        goals = {}
        
        # GPA hedefleri
        if "gpa_trend" in analytics and "analytics" in analytics:
            gpa_data = analytics["analytics"]["gpa_trend"]
            if "current_gpa" in gpa_data and not "error" in gpa_data:
                current_gpa = gpa_data["current_gpa"]
                
                # Kısa vadeli hedef (1 dönem)
                short_term_gpa = min(4.0, current_gpa + 0.3)
                
                # Orta vadeli hedef (1 yıl)
                medium_term_gpa = min(4.0, current_gpa + 0.5)
                
                # Uzun vadeli hedef (mezuniyet)
                long_term_gpa = min(4.0, current_gpa + 0.8)
                
                goals["gpa"] = {
                    "current": current_gpa,
                    "short_term": round(short_term_gpa, 2),
                    "medium_term": round(medium_term_gpa, 2),
                    "long_term": round(long_term_gpa, 2),
                    "achievable": current_gpa < 4.0
                }
        
        # Kredi hedefleri
        if "credit_analysis" in analytics and "analytics" in analytics:
            credit_data = analytics["analytics"]["credit_analysis"]
            if "completion_rate" in credit_data and not "error" in credit_data:
                completion = credit_data["completion_rate"]
                remaining = credit_data.get("remaining_credits", 0)
                
                # Dönem kredi hedefi
                semester_goal = min(30, max(15, remaining / 4))  # Kalan krediyi 4 döneme böl
                
                goals["credits"] = {
                    "current_completion": completion,
                    "semester_goal": round(semester_goal, 1),
                    "target_completion": min(100, completion + 25),  # %25 artış hedefi
                    "graduation_timeline": credit_data.get("estimated_semesters_to_graduation", 0)
                }
        
        # Ders başarı hedefleri
        if "course_success" in analytics and "analytics" in analytics:
            success_data = analytics["analytics"]["course_success"]
            if "overall_success_rate" in success_data and not "error" in success_data:
                current_success = success_data["overall_success_rate"]
                
                goals["course_success"] = {
                    "current_rate": current_success,
                    "target_rate": min(100, current_success + 10),  # %10 artış hedefi
                    "excellent_threshold": 90,
                    "good_threshold": 80
                }
        
        return goals
        
    except Exception as e:
        logger.error(f"Hedef hesaplama hatası: {e}")
        return {"error": str(e)}


def _calculate_progress_status(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """İlerleme durumunu hesaplar"""
    try:
        status = {
            "overall_progress": 0,
            "gpa_progress": 0,
            "credit_progress": 0,
            "success_progress": 0,
            "status_level": "Unknown"
        }
        
        if "analytics" not in analytics:
            return status
        
        analytics_data = analytics["analytics"]
        
        # GPA ilerlemesi
        if "gpa_trend" in analytics_data and not "error" in analytics_data["gpa_trend"]:
            gpa_data = analytics_data["gpa_trend"]
            if "current_gpa" in gpa_data:
                current_gpa = gpa_data["current_gpa"]
                gpa_progress = (current_gpa / 4.0) * 100
                status["gpa_progress"] = round(gpa_progress, 1)
        
        # Kredi ilerlemesi
        if "credit_analysis" in analytics_data and not "error" in analytics_data["credit_analysis"]:
            credit_data = analytics_data["credit_analysis"]
            if "completion_rate" in credit_data:
                status["credit_progress"] = credit_data["completion_rate"]
        
        # Ders başarı ilerlemesi
        if "course_success" in analytics_data and not "error" in analytics_data["course_success"]:
            success_data = analytics_data["course_success"]
            if "overall_success_rate" in success_data:
                status["success_progress"] = success_data["overall_success_rate"]
        
        # Genel ilerleme (ortalama)
        progress_values = [status["gpa_progress"], status["credit_progress"], status["success_progress"]]
        valid_values = [v for v in progress_values if v > 0]
        
        if valid_values:
            status["overall_progress"] = round(sum(valid_values) / len(valid_values), 1)
        
        # İlerleme seviyesi
        overall = status["overall_progress"]
        if overall >= 90:
            status["status_level"] = "Mükemmel"
        elif overall >= 80:
            status["status_level"] = "Çok İyi"
        elif overall >= 70:
            status["status_level"] = "İyi"
        elif overall >= 60:
            status["status_level"] = "Orta"
        elif overall >= 50:
            status["status_level"] = "Geliştirilmeli"
        else:
            status["status_level"] = "Kritik"
        
        return status
        
    except Exception as e:
        logger.error(f"İlerleme durumu hesaplama hatası: {e}")
        return {"error": str(e)}


def _generate_goal_recommendations(analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Hedef önerilerini üretir"""
    recommendations = []
    
    try:
        if "analytics" not in analytics:
            return recommendations
        
        analytics_data = analytics["analytics"]
        
        # GPA hedefleri
        if "gpa_trend" in analytics_data and not "error" in analytics_data["gpa_trend"]:
            gpa_data = analytics_data["gpa_trend"]
            if "current_gpa" in gpa_data:
                current_gpa = gpa_data["current_gpa"]
                
                if current_gpa < 2.0:
                    recommendations.append({
                        "category": "GPA",
                        "priority": "Yüksek",
                        "goal": "GPA'yı 2.0'ın üzerine çıkarın",
                        "timeline": "1 dönem",
                        "actions": [
                            "Ders çalışma planınızı gözden geçirin",
                            "Öğretim görevlileriyle görüşün",
                            "Ek kaynaklar kullanın"
                        ]
                    })
                elif current_gpa < 2.5:
                    recommendations.append({
                        "category": "GPA",
                        "priority": "Orta",
                        "goal": "GPA'yı 2.5'ın üzerine çıkarın",
                        "timeline": "2 dönem",
                        "actions": [
                            "Zayıf olduğunuz derslere odaklanın",
                            "Çalışma grupları oluşturun"
                        ]
                    })
        
        # Kredi hedefleri
        if "credit_analysis" in analytics_data and not "error" in analytics_data["credit_analysis"]:
            credit_data = analytics_data["credit_analysis"]
            if "completion_rate" in credit_data:
                completion = credit_data["completion_rate"]
                
                if completion < 50:
                    recommendations.append({
                        "category": "Kredi",
                        "priority": "Yüksek",
                        "goal": "Kredi tamamlama oranını artırın",
                        "timeline": "2 dönem",
                        "actions": [
                            "Daha fazla ders almayı düşünün",
                            "Yaz okulu seçeneklerini değerlendirin"
                        ]
                    })
        
        # Ders başarı hedefleri
        if "course_success" in analytics_data and not "error" in analytics_data["course_success"]:
            success_data = analytics_data["course_success"]
            if "overall_success_rate" in success_data:
                success_rate = success_data["overall_success_rate"]
                
                if success_rate < 70:
                    recommendations.append({
                        "category": "Ders Başarısı",
                        "priority": "Yüksek",
                        "goal": "Ders başarı oranını %80'in üzerine çıkarın",
                        "timeline": "1 dönem",
                        "actions": [
                            "Çalışma yöntemlerinizi gözden geçirin",
                            "Ödev ve projelere daha fazla zaman ayırın",
                            "Öğretim görevlileriyle düzenli görüşün"
                        ]
                    })
        
        # Genel hedefler
        if not recommendations:
            recommendations.append({
                "category": "Genel",
                "priority": "Düşük",
                "goal": "Mevcut performansınızı koruyun",
                "timeline": "Sürekli",
                "actions": [
                    "Düzenli çalışma alışkanlığınızı sürdürün",
                    "Akademik hedeflerinizi gözden geçirin"
                ]
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Hedef önerisi üretme hatası: {e}")
        return [{
            "category": "Hata",
            "priority": "Bilinmiyor",
            "goal": "Analiz sırasında hata oluştu",
            "timeline": "Bilinmiyor",
            "actions": ["Lütfen tekrar deneyin"]
        }]


# =============================================================================
# DERS SEÇİM ASISTANI
# =============================================================================

def student_obs_get_course_advisor() -> Dict[str, Any]:
    """Akademik danışmanlık ve ders seçim önerileri"""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    
    try:
        # Mevcut ders bilgilerini al
        current_courses = student_obs_get_term_courses()
        if "error" in current_courses:
            return current_courses
        
        # Transkript bilgilerini al
        transcript = student_obs_get_transcript()
        if "error" in transcript:
            return transcript
        
        # Öğrenci bilgilerini al
        student_info = student_obs_get_student_info()
        if "error" in student_info:
            return student_info
        
        # Ders seçim analizini yap
        course_analysis = _analyze_course_selection(current_courses, transcript, student_info)
        
        # Önerileri üret
        recommendations = _generate_course_recommendations(course_analysis)
        
        return {
            "success": True,
            "course_analysis": course_analysis,
            "recommendations": recommendations,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ders seçim asistanı hatası: {e}")
        return {"error": str(e)}


def _analyze_course_selection(current_courses: Dict[str, Any], transcript: Dict[str, Any], student_info: Dict[str, Any]) -> Dict[str, Any]:
    """Ders seçim analizini yapar"""
    try:
        analysis = {
            "current_semester": {},
            "prerequisites": {},
            "credit_analysis": {},
            "conflicts": {},
            "graduation_requirements": {}
        }
        
        # Mevcut dönem analizi
        if "tables" in current_courses:
            current_semester_courses = []
            total_credits = 0
            
            for table in current_courses["tables"]:
                if "rows" in table:
                    for row in table["rows"]:
                        if len(row) >= 4:
                            course = {
                                "name": row[0] if len(row) > 0 else "",
                                "credits": row[1] if len(row) > 1 else "",
                                "grade": row[2] if len(row) > 2 else "",
                                "instructor": row[3] if len(row) > 3 else ""
                            }
                            current_semester_courses.append(course)
                            
                            # Kredi hesaplama
                            try:
                                if course["credits"]:
                                    credits = float(course["credits"].replace(",", "."))
                                    total_credits += credits
                            except (ValueError, AttributeError):
                                pass
            
            analysis["current_semester"] = {
                "courses": current_semester_courses,
                "total_courses": len(current_semester_courses),
                "total_credits": total_credits,
                "is_balanced": 15 <= total_credits <= 30  # Dengeli kredi yükü
            }
        
        # Ön koşul analizi
        analysis["prerequisites"] = _analyze_prerequisites(current_semester_courses, transcript)
        
        # Kredi analizi
        analysis["credit_analysis"] = _analyze_credit_requirements(transcript, student_info)
        
        # Ders çakışma kontrolü
        analysis["conflicts"] = _check_course_conflicts(current_semester_courses)
        
        # Mezuniyet gereksinimleri
        analysis["graduation_requirements"] = _analyze_graduation_requirements(transcript, student_info)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Ders seçim analiz hatası: {e}")
        return {"error": str(e)}


def _analyze_prerequisites(current_courses: List[Dict[str, Any]], transcript: Dict[str, Any]) -> Dict[str, Any]:
    """Ön koşul kontrolünü yapar"""
    try:
        prerequisite_analysis = {
            "met_prerequisites": [],
            "missing_prerequisites": [],
            "warnings": []
        }
        
        # Basit ön koşul kontrolü (gerçek sistemde daha detaylı olabilir)
        completed_courses = set()
        
        if "academic_records" in transcript:
            for record in transcript["academic_records"]:
                if "courses" in record:
                    for course in record["courses"]:
                        course_name = course.get("name", "").lower()
                        grade = course.get("grade", "")
                        
                        # Başarılı tamamlanan dersler
                        if grade and grade not in ["F", "FF", "FD", "DD"]:
                            completed_courses.add(course_name)
        
        # Mevcut dersler için ön koşul kontrolü
        for course in current_courses:
            course_name = course.get("name", "").lower()
            
            # Temel dersler için ön koşul kontrolü
            if any(keyword in course_name for keyword in ["ii", "2", "advanced", "ileri"]):
                # İkinci seviye dersler için temel ders kontrolü
                base_course = course_name.replace("ii", "i").replace("2", "1").replace("advanced", "basic")
                
                if base_course in completed_courses:
                    prerequisite_analysis["met_prerequisites"].append({
                        "course": course["name"],
                        "prerequisite": base_course,
                        "status": "Met"
                    })
                else:
                    prerequisite_analysis["missing_prerequisites"].append({
                        "course": course["name"],
                        "prerequisite": base_course,
                        "status": "Missing"
                    })
                    
                    prerequisite_analysis["warnings"].append(
                        f"{course['name']} dersi için {base_course} ön koşulu eksik"
                    )
            else:
                # Temel dersler için ön koşul yok
                prerequisite_analysis["met_prerequisites"].append({
                    "course": course["name"],
                    "prerequisite": "None",
                    "status": "No prerequisite"
                })
        
        return prerequisite_analysis
        
    except Exception as e:
        logger.error(f"Ön koşul analiz hatası: {e}")
        return {"error": str(e)}


def _analyze_credit_requirements(transcript: Dict[str, Any], student_info: Dict[str, Any]) -> Dict[str, Any]:
    """Kredi gereksinimlerini analiz eder"""
    try:
        credit_analysis = {
            "current_credits": 0,
            "required_credits": 240,  # Standart lisans programı
            "remaining_credits": 0,
            "semester_recommendation": 0,
            "graduation_timeline": 0
        }
        
        # Mevcut kredileri hesapla
        if "academic_records" in transcript:
            for record in transcript["academic_records"]:
                if "total_credits" in record and record["total_credits"]:
                    try:
                        credits = float(record["total_credits"].replace(",", "."))
                        credit_analysis["current_credits"] = max(credit_analysis["current_credits"], credits)
                    except (ValueError, AttributeError):
                        continue
        
        # Kalan kredileri hesapla
        credit_analysis["remaining_credits"] = max(0, credit_analysis["required_credits"] - credit_analysis["current_credits"])
        
        # Dönem kredi önerisi
        if credit_analysis["remaining_credits"] > 0:
            # Kalan krediyi 4 döneme böl (2 yıl)
            credit_analysis["semester_recommendation"] = min(30, max(15, credit_analysis["remaining_credits"] / 4))
            credit_analysis["graduation_timeline"] = credit_analysis["remaining_credits"] / credit_analysis["semester_recommendation"]
        
        return credit_analysis
        
    except Exception as e:
        logger.error(f"Kredi gereksinim analiz hatası: {e}")
        return {"error": str(e)}


def _check_course_conflicts(current_courses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Ders çakışmalarını kontrol eder"""
    try:
        conflicts = {
            "schedule_conflicts": [],
            "workload_conflicts": [],
            "level_conflicts": []
        }
        
        # Ders seviyesi kontrolü
        course_levels = {}
        for course in current_courses:
            course_name = course.get("name", "").lower()
            
            # Ders seviyesini belirle
            if any(keyword in course_name for keyword in ["i", "1", "basic", "temel"]):
                level = "Basic"
            elif any(keyword in course_name for keyword in ["ii", "2", "intermediate", "orta"]):
                level = "Intermediate"
            elif any(keyword in course_name for keyword in ["iii", "3", "advanced", "ileri"]):
                level = "Advanced"
            else:
                level = "Unknown"
            
            if level in course_levels:
                course_levels[level].append(course["name"])
            else:
                course_levels[level] = [course["name"]]
        
        # Seviye dengesizliği kontrolü
        for level, courses in course_levels.items():
            if len(courses) > 3:  # Aynı seviyede çok fazla ders
                conflicts["level_conflicts"].append({
                    "type": "Too many courses at same level",
                    "level": level,
                    "courses": courses,
                    "recommendation": f"{level} seviyesinde ders sayısını azaltın"
                })
        
        # İş yükü kontrolü
        total_credits = sum(
            float(course.get("credits", "0").replace(",", ".")) 
            for course in current_courses 
            if course.get("credits")
        )
        
        if total_credits > 30:
            conflicts["workload_conflicts"].append({
                "type": "High credit load",
                "current_credits": total_credits,
                "recommendation": "Kredi yükünü azaltmayı düşünün"
            })
        elif total_credits < 15:
            conflicts["workload_conflicts"].append({
                "type": "Low credit load",
                "current_credits": total_credits,
                "recommendation": "Daha fazla ders almayı düşünün"
            })
        
        return conflicts
        
    except Exception as e:
        logger.error(f"Çakışma kontrol hatası: {e}")
        return {"error": str(e)}


def _analyze_graduation_requirements(transcript: Dict[str, Any], student_info: Dict[str, Any]) -> Dict[str, Any]:
    """Mezuniyet gereksinimlerini analiz eder"""
    try:
        graduation_requirements = {
            "core_courses": {"required": 0, "completed": 0, "remaining": 0},
            "elective_courses": {"required": 0, "completed": 0, "remaining": 0},
            "total_credits": {"required": 240, "completed": 0, "remaining": 0},
            "gpa_requirement": {"required": 2.0, "current": 0, "met": False},
            "graduation_status": "Unknown"
        }
        
        # Mevcut kredileri hesapla
        if "academic_records" in transcript:
            for record in transcript["academic_records"]:
                if "total_credits" in record and record["total_credits"]:
                    try:
                        credits = float(record["total_credits"].replace(",", "."))
                        graduation_requirements["total_credits"]["completed"] = max(
                            graduation_requirements["total_credits"]["completed"], 
                            credits
                        )
                    except (ValueError, AttributeError):
                        continue
                
                # GPA hesaplama
                if "gpa" in record and record["gpa"]:
                    try:
                        gpa = float(record["gpa"].replace(",", "."))
                        graduation_requirements["gpa_requirement"]["current"] = gpa
                        graduation_requirements["gpa_requirement"]["met"] = gpa >= 2.0
                    except (ValueError, AttributeError):
                        continue
        
        # Kalan kredileri hesapla
        graduation_requirements["total_credits"]["remaining"] = max(
            0, 
            graduation_requirements["total_credits"]["required"] - graduation_requirements["total_credits"]["completed"]
        )
        
        # Mezuniyet durumu
        total_met = graduation_requirements["gpa_requirement"]["met"]
        credits_met = graduation_requirements["total_credits"]["remaining"] <= 0
        
        if total_met and credits_met:
            graduation_requirements["graduation_status"] = "Eligible"
        elif credits_met:
            graduation_requirements["graduation_status"] = "GPA requirement not met"
        elif total_met:
            graduation_requirements["graduation_status"] = "Credit requirement not met"
        else:
            graduation_requirements["graduation_status"] = "Multiple requirements not met"
        
        return graduation_requirements
        
    except Exception as e:
        logger.error(f"Mezuniyet gereksinim analiz hatası: {e}")
        return {"error": str(e)}


def _generate_course_recommendations(course_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ders seçim önerilerini üretir"""
    recommendations = []
    
    try:
        # Ön koşul uyarıları
        if "prerequisites" in course_analysis and "warnings" in course_analysis["prerequisites"]:
            for warning in course_analysis["prerequisites"]["warnings"]:
                recommendations.append({
                    "type": "Prerequisite Warning",
                    "priority": "High",
                    "message": warning,
                    "action": "Ön koşul dersleri tamamlayın"
                })
        
        # Kredi yükü önerileri
        if "current_semester" in course_analysis:
            current = course_analysis["current_semester"]
            if not current.get("is_balanced", True):
                if current.get("total_credits", 0) > 30:
                    recommendations.append({
                        "type": "Credit Load",
                        "priority": "Medium",
                        "message": "Kredi yükünüz yüksek",
                        "action": "Bazı dersleri sonraki döneme bırakın"
                    })
                elif current.get("total_credits", 0) < 15:
                    recommendations.append({
                        "type": "Credit Load",
                        "priority": "Medium",
                        "message": "Kredi yükünüz düşük",
                        "action": "Daha fazla ders almayı düşünün"
                    })
        
        # Çakışma önerileri
        if "conflicts" in course_analysis:
            conflicts = course_analysis["conflicts"]
            
            for conflict_type, conflict_list in conflicts.items():
                for conflict in conflict_list:
                    recommendations.append({
                        "type": f"Conflict: {conflict_type}",
                        "priority": "Medium",
                        "message": conflict.get("type", ""),
                        "action": conflict.get("recommendation", "")
                    })
        
        # Mezuniyet önerileri
        if "graduation_requirements" in course_analysis:
            grad_req = course_analysis["graduation_requirements"]
            
            if grad_req.get("graduation_status") == "GPA requirement not met":
                recommendations.append({
                    "type": "Graduation",
                    "priority": "High",
                    "message": "GPA gereksinimi karşılanmıyor",
                    "action": "GPA'nızı 2.0'ın üzerine çıkarın"
                })
            
            if grad_req.get("total_credits", {}).get("remaining", 0) > 0:
                remaining = grad_req["total_credits"]["remaining"]
                recommendations.append({
                    "type": "Graduation",
                    "priority": "Medium",
                    "message": f"{remaining} kredi eksik",
                    "action": "Eksik kredileri tamamlayın"
                })
        
        # Genel öneriler
        if not recommendations:
            recommendations.append({
                "type": "General",
                "priority": "Low",
                "message": "Ders seçiminiz uygun",
                "action": "Mevcut planınızı sürdürün"
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Öneri üretme hatası: {e}")
        return [{
            "type": "Error",
            "priority": "Unknown",
            "message": "Analiz sırasında hata oluştu",
            "action": "Lütfen tekrar deneyin"
        }]


# =============================================================================
# BİLDİRİM VE UYARI SİSTEMİ
# =============================================================================

def student_obs_get_notifications() -> Dict[str, Any]:
    """Önemli bildirimleri ve uyarıları listeler"""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    
    try:
        # Çeşitli veri kaynaklarından bildirimleri topla
        notifications = []
        
        # Akademik uyarılar
        academic_warnings = _get_academic_warnings()
        notifications.extend(academic_warnings)
        
        # Devamsızlık uyarıları
        attendance_warnings = _get_attendance_warnings()
        notifications.extend(attendance_warnings)
        
        # Mali uyarılar
        financial_warnings = _get_financial_warnings()
        notifications.extend(financial_warnings)
        
        # Sistem uyarıları
        system_warnings = _get_system_warnings()
        notifications.extend(system_warnings)
        
        # Bildirimleri öncelik sırasına göre sırala
        notifications.sort(key=lambda x: _get_priority_score(x.get("priority", "Low")), reverse=True)
        
        # Özet istatistikler
        summary = {
            "total_notifications": len(notifications),
            "high_priority": len([n for n in notifications if n.get("priority") == "High"]),
            "medium_priority": len([n for n in notifications if n.get("priority") == "Medium"]),
            "low_priority": len([n for n in notifications if n.get("priority") == "Low"])
        }
        
        return {
            "success": True,
            "notifications": notifications,
            "summary": summary,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bildirim sistemi hatası: {e}")
        return {"error": str(e)}


def _get_academic_warnings() -> List[Dict[str, Any]]:
    """Akademik uyarıları getirir"""
    warnings = []
    
    try:
        # Transkript bilgilerini al
        transcript = student_obs_get_transcript()
        if "error" in transcript:
            return warnings
        
        # Düşük not uyarıları
        if "academic_records" in transcript:
            for record in transcript["academic_records"]:
                if "courses" in record:
                    for course in record["courses"]:
                        grade = course.get("grade", "")
                        course_name = course.get("name", "")
                        
                        if grade in ["F", "FF", "FD", "DD"]:
                            warnings.append({
                                "id": f"academic_{len(warnings)}",
                                "type": "Academic Warning",
                                "category": "Low Grade",
                                "priority": "High",
                                "title": f"Düşük Not: {course_name}",
                                "message": f"{course_name} dersinde {grade} notu aldınız",
                                "details": {
                                    "course": course_name,
                                    "grade": grade,
                                    "semester": record.get("class_level", ""),
                                    "year": record.get("year", "")
                                },
                                "action_required": True,
                                "action_text": "Ders tekrarı veya ek çalışma gerekli",
                                "timestamp": datetime.now().isoformat()
                            })
        
        # GPA uyarıları
        if "academic_records" in transcript:
            for record in transcript["academic_records"]:
                if "gpa" in record and record["gpa"]:
                    try:
                        gpa = float(record["gpa"].replace(",", "."))
                        if gpa < 2.0:
                            warnings.append({
                                "id": f"academic_{len(warnings)}",
                                "type": "Academic Warning",
                                "category": "Low GPA",
                                "priority": "High",
                                "title": "Düşük GPA Uyarısı",
                                "message": f"GPA'nız {gpa} ile 2.0'ın altında",
                                "details": {
                                    "current_gpa": gpa,
                                    "required_gpa": 2.0,
                                    "semester": record.get("class_level", ""),
                                    "year": record.get("year", "")
                                },
                                "action_required": True,
                                "action_text": "Akademik danışmanla görüşün",
                                "timestamp": datetime.now().isoformat()
                            })
                    except (ValueError, AttributeError):
                        continue
        
        return warnings
        
    except Exception as e:
        logger.error(f"Akademik uyarı hatası: {e}")
        return []


def _get_attendance_warnings() -> List[Dict[str, Any]]:
    """Devamsızlık uyarılarını getirir"""
    warnings = []
    
    try:
        # Devamsızlık bilgilerini al
        attendance = student_obs_get_attendance()
        if "error" in attendance:
            return warnings
        
        # Devamsızlık tablolarını analiz et
        if "tables" in attendance:
            for table in attendance["tables"]:
                if "rows" in table:
                    for row in table["rows"]:
                        if len(row) >= 3:  # Ders adı, devamsızlık sayısı, limit
                            course_name = row[0] if len(row) > 0 else ""
                            absences = row[1] if len(row) > 1 else ""
                            limit = row[2] if len(row) > 2 else ""
                            
                            try:
                                absences_count = int(absences) if absences.isdigit() else 0
                                limit_count = int(limit) if limit.isdigit() else 10
                                
                                # Devamsızlık oranı hesapla
                                if limit_count > 0:
                                    absence_rate = (absences_count / limit_count) * 100
                                    
                                    if absence_rate >= 80:
                                        priority = "High"
                                        action_required = True
                                    elif absence_rate >= 60:
                                        priority = "Medium"
                                        action_required = True
                                    else:
                                        priority = "Low"
                                        action_required = False
                                    
                                    if absence_rate >= 60:
                                        warnings.append({
                                            "id": f"attendance_{len(warnings)}",
                                            "type": "Attendance Warning",
                                            "category": "High Absence Rate",
                                            "priority": priority,
                                            "title": f"Devamsızlık Uyarısı: {course_name}",
                                            "message": f"{course_name} dersinde %{absence_rate:.1f} devamsızlık oranı",
                                            "details": {
                                                "course": course_name,
                                                "absences": absences_count,
                                                "limit": limit_count,
                                                "rate": round(absence_rate, 1)
                                            },
                                            "action_required": action_required,
                                            "action_text": "Devamsızlık oranınızı düşürün",
                                            "timestamp": datetime.now().isoformat()
                                        })
                            except (ValueError, AttributeError):
                                continue
        
        return warnings
        
    except Exception as e:
        logger.error(f"Devamsızlık uyarı hatası: {e}")
        return []


def _get_financial_warnings() -> List[Dict[str, Any]]:
    """Mali uyarıları getirir"""
    warnings = []
    
    try:
        # Harç bilgilerini al
        fees = student_obs_get_fees()
        if "error" in fees:
            return warnings
        
        # Harç tablolarını analiz et
        if "tables" in fees:
            for table in fees["tables"]:
                if "rows" in table:
                    for row in table["rows"]:
                        if len(row) >= 4:  # Dönem, tutar, ödenen, kalan
                            semester = row[0] if len(row) > 0 else ""
                            amount = row[1] if len(row) > 1 else ""
                            paid = row[2] if len(row) > 2 else ""
                            remaining = row[3] if len(row) > 3 else ""
                            
                            try:
                                # Kalan borç kontrolü
                                if remaining and remaining != "0" and remaining != "0,00":
                                    remaining_amount = float(remaining.replace(",", "."))
                                    
                                    if remaining_amount > 0:
                                        priority = "Medium" if remaining_amount < 1000 else "High"
                                        
                                        warnings.append({
                                            "id": f"financial_{len(warnings)}",
                                            "type": "Financial Warning",
                                            "category": "Outstanding Balance",
                                            "priority": priority,
                                            "title": f"Harç Borcu: {semester}",
                                            "message": f"{semester} dönemi için {remaining_amount:.2f} TL borç",
                                            "details": {
                                                "semester": semester,
                                                "total_amount": amount,
                                                "paid_amount": paid,
                                                "remaining_amount": remaining_amount
                                            },
                                            "action_required": True,
                                            "action_text": "Harç borcunuzu ödeyin",
                                            "timestamp": datetime.now().isoformat()
                                        })
                            except (ValueError, AttributeError):
                                continue
        
        # Kütüphane borçları
        library = student_obs_get_library()
        if "error" not in library and "tables" in library:
            for table in library["tables"]:
                if "rows" in table:
                    for row in table["rows"]:
                        if len(row) >= 2:  # Malzeme, borç
                            item = row[0] if len(row) > 0 else ""
                            debt = row[1] if len(row) > 1 else ""
                            
                            if debt and debt != "0" and debt != "0,00":
                                try:
                                    debt_amount = float(debt.replace(",", "."))
                                    if debt_amount > 0:
                                        warnings.append({
                                            "id": f"financial_{len(warnings)}",
                                            "type": "Financial Warning",
                                            "category": "Library Debt",
                                            "priority": "Low",
                                            "title": f"Kütüphane Borcu: {item}",
                                            "message": f"{item} için {debt_amount:.2f} TL borç",
                                            "details": {
                                                "item": item,
                                                "debt_amount": debt_amount
                                            },
                                            "action_required": True,
                                            "action_text": "Kütüphane borcunuzu ödeyin",
                                            "timestamp": datetime.now().isoformat()
                                        })
                                except (ValueError, AttributeError):
                                    continue
        
        return warnings
        
    except Exception as e:
        logger.error(f"Mali uyarı hatası: {e}")
        return []


def _get_system_warnings() -> List[Dict[str, Any]]:
    """Sistem uyarılarını getirir"""
    warnings = []
    
    try:
        # Öğrenci bilgilerini al
        student_info = student_obs_get_student_info()
        if "error" in student_info:
            return warnings
        
        # Öğrenci durumu kontrolü
        if "status" in student_info:
            status = student_info["status"]
            if status and "OKUYAN" not in status.upper():
                warnings.append({
                    "id": f"system_{len(warnings)}",
                    "type": "System Warning",
                    "category": "Student Status",
                    "priority": "High",
                    "title": "Öğrenci Durumu Uyarısı",
                    "message": f"Öğrenci durumunuz: {status}",
                    "details": {
                        "current_status": status,
                        "expected_status": "OKUYAN"
                    },
                    "action_required": True,
                    "action_text": "Öğrenci işleri ile iletişime geçin",
                    "timestamp": datetime.now().isoformat()
                })
        
        # E-posta kontrolü
        if "email" in student_info:
            email = student_info["email"]
            if not email or "@" not in email:
                warnings.append({
                    "id": f"system_{len(warnings)}",
                    "type": "System Warning",
                    "category": "Contact Information",
                    "priority": "Medium",
                    "title": "E-posta Adresi Eksik",
                    "message": "E-posta adresiniz güncel değil",
                    "details": {
                        "current_email": email or "Yok"
                    },
                    "action_required": True,
                    "action_text": "E-posta adresinizi güncelleyin",
                    "timestamp": datetime.now().isoformat()
                })
        
        return warnings
        
    except Exception as e:
        logger.error(f"Sistem uyarı hatası: {e}")
        return []


def _get_priority_score(priority: str) -> int:
    """Öncelik skorunu hesaplar"""
    priority_scores = {
        "High": 3,
        "Medium": 2,
        "Low": 1
    }
    return priority_scores.get(priority, 0)


def student_obs_get_notification_settings() -> Dict[str, Any]:
    """Bildirim ayarlarını getirir"""
    try:
        # Varsayılan bildirim ayarları
        default_settings = {
            "academic_warnings": {
                "enabled": True,
                "priority_threshold": "Low",  # Low, Medium, High
                "email_notifications": False,
                "push_notifications": False
            },
            "attendance_warnings": {
                "enabled": True,
                "absence_threshold": 60,  # %60 devamsızlık oranı
                "email_notifications": False,
                "push_notifications": False
            },
            "financial_warnings": {
                "enabled": True,
                "debt_threshold": 100,  # 100 TL üzeri borç
                "email_notifications": True,
                "push_notifications": False
            },
            "system_warnings": {
                "enabled": True,
                "priority_threshold": "Medium",
                "email_notifications": True,
                "push_notifications": False
            },
            "general_settings": {
                "notification_frequency": "daily",  # daily, weekly, monthly
                "quiet_hours": {
                    "start": "22:00",
                    "end": "08:00"
                },
                "language": "tr"
            }
        }
        
        return {
            "success": True,
            "settings": default_settings,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bildirim ayarları hatası: {e}")
        return {"error": str(e)}


def student_obs_mark_notification_read(notification_id: str) -> Dict[str, Any]:
    """Bildirimi okundu olarak işaretler"""
    try:
        # Bu fonksiyon gerçek uygulamada veritabanında okundu durumunu günceller
        # Şimdilik sadece başarı mesajı döndürüyoruz
        
        return {
            "success": True,
            "message": f"Bildirim {notification_id} okundu olarak işaretlendi",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bildirim işaretleme hatası: {e}")
        return {"error": str(e)}


# =============================================================================
# RAPORLAMA VE EXPORT
# =============================================================================

def student_obs_export_data(format: str = "json", data_type: str = "all") -> Dict[str, Any]:
    """Verileri farklı formatlarda export eder"""
    if not _student_obs_session or not _student_obs_base_url:
        return {"error": "Giriş yapılmamış"}
    
    try:
        # Export formatını kontrol et
        if format.lower() not in ["json", "csv", "pdf", "excel"]:
            return {"error": "Desteklenmeyen format. Kullanılabilir: json, csv, pdf, excel"}
        
        # Veri tipini kontrol et
        if data_type.lower() not in ["all", "academic", "financial", "personal", "schedule"]:
            return {"error": "Desteklenmeyen veri tipi. Kullanılabilir: all, academic, financial, personal, schedule"}
        
        # Verileri topla
        export_data = _collect_export_data(data_type)
        if "error" in export_data:
            return export_data
        
        # Format'a göre export yap
        if format.lower() == "json":
            result = _export_to_json(export_data)
        elif format.lower() == "csv":
            result = _export_to_csv(export_data)
        elif format.lower() == "pdf":
            result = _export_to_pdf(export_data)
        elif format.lower() == "excel":
            result = _export_to_excel(export_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Veri export hatası: {e}")
        return {"error": str(e)}


def _collect_export_data(data_type: str) -> Dict[str, Any]:
    """Export için verileri toplar"""
    try:
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "data_type": data_type,
                "student_id": None
            },
            "data": {}
        }
        
        # Öğrenci bilgilerini al
        student_info = student_obs_get_student_info()
        if "error" not in student_info:
            export_data["export_info"]["student_id"] = student_info.get("student_id", "Unknown")
            
            if data_type in ["all", "personal"]:
                export_data["data"]["personal_info"] = student_info
        
        # Akademik veriler
        if data_type in ["all", "academic"]:
            # Transkript
            transcript = student_obs_get_transcript()
            if "error" not in transcript:
                export_data["data"]["transcript"] = transcript
            
            # Dönem dersleri
            term_courses = student_obs_get_term_courses()
            if "error" not in term_courses:
                export_data["data"]["term_courses"] = term_courses
            
            # Akademik analiz
            analytics = student_obs_get_academic_analytics()
            if "error" not in analytics:
                export_data["data"]["academic_analytics"] = analytics
        
        # Mali veriler
        if data_type in ["all", "financial"]:
            # Harç bilgileri
            fees = student_obs_get_fees()
            if "error" not in fees:
                export_data["data"]["fees"] = fees
            
            # Kütüphane borçları
            library = student_obs_get_library()
            if "error" not in library:
                export_data["data"]["library"] = library
        
        # Program verileri
        if data_type in ["all", "schedule"]:
            # Haftalık program
            schedule = student_obs_get_weekly_schedule()
            if "error" not in schedule:
                export_data["data"]["weekly_schedule"] = schedule
            
            # Devamsızlık
            attendance = student_obs_get_attendance()
            if "error" not in attendance:
                export_data["data"]["attendance"] = attendance
        
        return export_data
        
    except Exception as e:
        logger.error(f"Veri toplama hatası: {e}")
        return {"error": str(e)}


def _export_to_json(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verileri JSON formatında export eder"""
    try:
        import json
        
        # JSON string'e çevir
        json_string = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
        
        # Dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"student_data_{timestamp}.json"
        
        return {
            "success": True,
            "format": "json",
            "filename": filename,
            "data": json_string,
            "size_bytes": len(json_string.encode('utf-8')),
            "download_ready": True
        }
        
    except Exception as e:
        logger.error(f"JSON export hatası: {e}")
        return {"error": str(e)}


def _export_to_csv(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verileri CSV formatında export eder"""
    try:
        import csv
        import io
        
        # CSV string buffer oluştur
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Ana bilgileri yaz
        writer.writerow(["Export Bilgileri"])
        writer.writerow(["Tarih", export_data["export_info"]["timestamp"]])
        writer.writerow(["Veri Tipi", export_data["export_info"]["data_type"]])
        writer.writerow(["Öğrenci ID", export_data["export_info"]["student_id"]])
        writer.writerow([])
        
        # Veri bölümlerini yaz
        for section_name, section_data in export_data["data"].items():
            writer.writerow([f"=== {section_name.upper()} ==="])
            
            if isinstance(section_data, dict):
                _write_dict_to_csv(writer, section_data, "")
            elif isinstance(section_data, list):
                _write_list_to_csv(writer, section_data, "")
            
            writer.writerow([])
        
        # CSV string'i al
        csv_string = output.getvalue()
        output.close()
        
        # Dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"student_data_{timestamp}.csv"
        
        return {
            "success": True,
            "format": "csv",
            "filename": filename,
            "data": csv_string,
            "size_bytes": len(csv_string.encode('utf-8')),
            "download_ready": True
        }
        
    except Exception as e:
        logger.error(f"CSV export hatası: {e}")
        return {"error": str(e)}


def _write_dict_to_csv(writer, data: Dict[str, Any], prefix: str = ""):
    """Dictionary'yi CSV'ye yazar"""
    for key, value in data.items():
        if isinstance(value, dict):
            writer.writerow([f"{prefix}{key}", ""])
            _write_dict_to_csv(writer, value, prefix + "  ")
        elif isinstance(value, list):
            writer.writerow([f"{prefix}{key}", ""])
            _write_list_to_csv(writer, value, prefix + "  ")
        else:
            writer.writerow([f"{prefix}{key}", str(value)])


def _write_list_to_csv(writer, data: List[Any], prefix: str = ""):
    """List'i CSV'ye yazar"""
    for i, item in enumerate(data):
        if isinstance(item, dict):
            writer.writerow([f"{prefix}[{i}]", ""])
            _write_dict_to_csv(writer, item, prefix + "  ")
        elif isinstance(item, list):
            writer.writerow([f"{prefix}[{i}]", ""])
            _write_list_to_csv(writer, item, prefix + "  ")
        else:
            writer.writerow([f"{prefix}[{i}]", str(item)])


def _export_to_pdf(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verileri PDF formatında export eder"""
    try:
        # PDF oluşturma için basit HTML template
        html_content = _generate_pdf_html(export_data)
        
        # Dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"student_data_{timestamp}.html"  # PDF yerine HTML döndürüyoruz
        
        return {
            "success": True,
            "format": "pdf",
            "filename": filename,
            "data": html_content,
            "size_bytes": len(html_content.encode('utf-8')),
            "download_ready": True,
            "note": "HTML formatında döndürüldü. PDF'e çevirmek için tarayıcıda yazdır > PDF olarak kaydet kullanın."
        }
        
    except Exception as e:
        logger.error(f"PDF export hatası: {e}")
        return {"error": str(e)}


def _generate_pdf_html(export_data: Dict[str, Any]) -> str:
    """PDF için HTML içeriği oluşturur"""
    try:
        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Öğrenci Veri Raporu</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 20px; }}
        .section-title {{ background-color: #f0f0f0; padding: 10px; font-weight: bold; }}
        .data-row {{ margin: 5px 0; }}
        .key {{ font-weight: bold; color: #333; }}
        .value {{ margin-left: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Öğrenci Veri Raporu</h1>
        <p>Oluşturulma Tarihi: {export_data['export_info']['timestamp']}</p>
        <p>Öğrenci ID: {export_data['export_info']['student_id']}</p>
        <p>Veri Tipi: {export_data['export_info']['data_type']}</p>
    </div>
"""
        
        # Her veri bölümü için HTML oluştur
        for section_name, section_data in export_data["data"].items():
            html += f"""
    <div class="section">
        <div class="section-title">{section_name.upper()}</div>
        {_generate_section_html(section_data)}
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html
        
    except Exception as e:
        logger.error(f"HTML oluşturma hatası: {e}")
        return f"<html><body><h1>Hata</h1><p>{str(e)}</p></body></html>"


def _generate_section_html(section_data: Any) -> str:
    """Bölüm verilerini HTML'e çevirir"""
    try:
        if isinstance(section_data, dict):
            html = ""
            for key, value in section_data.items():
                if isinstance(value, dict):
                    html += f'<div class="data-row"><span class="key">{key}:</span></div>'
                    html += f'<div class="value">{_generate_section_html(value)}</div>'
                elif isinstance(value, list):
                    html += f'<div class="data-row"><span class="key">{key}:</span></div>'
                    html += f'<div class="value">{_generate_section_html(value)}</div>'
                else:
                    html += f'<div class="data-row"><span class="key">{key}:</span> <span class="value">{str(value)}</span></div>'
            return html
        
        elif isinstance(section_data, list):
            if section_data and isinstance(section_data[0], dict):
                # Tablo formatında göster
                if section_data:
                    keys = list(section_data[0].keys())
                    html = '<table><thead><tr>'
                    for key in keys:
                        html += f'<th>{key}</th>'
                    html += '</tr></thead><tbody>'
                    
                    for item in section_data:
                        html += '<tr>'
                        for key in keys:
                            html += f'<td>{str(item.get(key, ""))}</td>'
                        html += '</tr>'
                    
                    html += '</tbody></table>'
                    return html
                else:
                    return '<p>Veri bulunamadı</p>'
            else:
                # Basit liste
                html = '<ul>'
                for item in section_data:
                    html += f'<li>{str(item)}</li>'
                html += '</ul>'
                return html
        
        else:
            return f'<span class="value">{str(section_data)}</span>'
            
    except Exception as e:
        logger.error(f"Bölüm HTML oluşturma hatası: {e}")
        return f'<p>Hata: {str(e)}</p>'


def _export_to_excel(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verileri Excel formatında export eder"""
    try:
        # Excel için CSV formatında döndür (gerçek Excel için openpyxl gerekli)
        csv_result = _export_to_csv(export_data)
        if "error" in csv_result:
            return csv_result
        
        # Dosya adını Excel olarak değiştir
        csv_result["format"] = "excel"
        csv_result["filename"] = csv_result["filename"].replace(".csv", ".xlsx")
        csv_result["note"] = "CSV formatında döndürüldü. Excel'de açmak için: Veri > Metin'den Sütunlara > Virgülle ayrılmış"
        
        return csv_result
        
    except Exception as e:
        logger.error(f"Excel export hatası: {e}")
        return {"error": str(e)}


def student_obs_get_export_formats() -> Dict[str, Any]:
    """Desteklenen export formatlarını listeler"""
    try:
        formats = {
            "json": {
                "name": "JSON",
                "description": "JavaScript Object Notation - Yapılandırılmış veri formatı",
                "extension": ".json",
                "best_for": "API entegrasyonu, veri işleme",
                "file_size": "Küçük-Orta"
            },
            "csv": {
                "name": "CSV",
                "description": "Comma Separated Values - Tablo formatında veri",
                "extension": ".csv",
                "best_for": "Excel, Google Sheets, veri analizi",
                "file_size": "Küçük"
            },
            "pdf": {
                "name": "PDF",
                "description": "Portable Document Format - Yazdırılabilir rapor",
                "extension": ".pdf",
                "best_for": "Resmi belgeler, yazdırma, paylaşım",
                "file_size": "Orta-Büyük"
            },
            "excel": {
                "name": "Excel",
                "description": "Microsoft Excel formatı - Gelişmiş tablo özellikleri",
                "extension": ".xlsx",
                "best_for": "Veri analizi, grafikler, hesaplamalar",
                "file_size": "Orta"
            }
        }
        
        return {
            "success": True,
            "formats": formats,
            "recommendations": {
                "data_analysis": ["csv", "excel"],
                "sharing": ["pdf", "json"],
                "programming": ["json", "csv"],
                "printing": ["pdf"]
            }
        }
        
    except Exception as e:
        logger.error(f"Export format listesi hatası: {e}")
        return {"error": str(e)}




