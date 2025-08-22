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




