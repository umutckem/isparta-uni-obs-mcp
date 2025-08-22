"""
Isparta Üniversitesi OBS MCP Server

Bu modül, Isparta Üniversitesi'nin OBS sistemine erişim sağlayan MCP (Model Context Protocol) 
tools'larını sunar. Öğrencilerin bilgilerini, duyurularını ve akademik verilerini 
güvenli bir şekilde çekmek için kullanılır.

Özellikler:
- Öğrenci login/logout işlemleri
- Öğrenci bilgileri çekme ve parse etme
- Duyuru, ders ve transkript bilgileri alma
- Session yönetimi ve güvenlik
"""

import asyncio
from typing import Any, Dict, List
from fastmcp import FastMCP

# Core modülünden fonksiyonları import et
from core import (
    # OBS login fonksiyonları
    student_obs_login,
    student_obs_logout,
    student_obs_login_debug,
    
    # OBS veri çekme fonksiyonları
    student_obs_navigate_to_page,
    student_obs_get_profile,
    student_obs_get_announcements,
    student_obs_get_courses,
    student_obs_get_transcript,
    student_obs_get_student_info,
    student_obs_get_student_info_parsed,
    student_obs_parse_student_info,
    # Yeni özellikler
    student_obs_get_weekly_schedule,
    student_obs_get_attendance,
    student_obs_get_fees,
    student_obs_get_library,
    student_obs_get_registration,
    student_obs_get_thesis,
    student_obs_get_internships,
    student_obs_get_petitions,
    student_obs_get_materials,
    student_obs_get_online_education_links,
    student_obs_get_events,
    # Yeni eklenen özellikler
    student_obs_get_academic_analytics,
    student_obs_get_performance_tracking,
    student_obs_get_course_advisor,
    student_obs_get_notifications,
    student_obs_get_notification_settings,
    student_obs_mark_notification_read,
    student_obs_export_data,
    student_obs_get_export_formats,
)

# MCP server'ı oluştur
mcp = FastMCP("uni-mcp")




# =============================================================================
# OBS LOGIN FONKSİYONLARI
# =============================================================================

@mcp.tool
def student_login(
    base_url: str,
    username: str,
    password: str,
    login_path: str = "/",
    username_field: str = "textKulID",
    password_field: str = "textSifre"
) -> Dict[str, Any]:
    """
    Öğrenci Bilgi Sistemi'ne giriş yapar ve oturumu saklar.
    
    Args:
        base_url: OBS sisteminin temel URL'i (örn: https://obs.isparta.edu.tr)
        username: Öğrenci numarası
        password: Şifre
        login_path: Login sayfasının yolu (varsayılan: /)
        username_field: Kullanıcı adı alanının name'i (varsayılan: textKulID)
        password_field: Şifre alanının name'i (varsayılan: textSifre)
        
    Returns:
        Login sonucu ({"result": true/false})
    """
    try:
        success = student_obs_login(
            base_url=base_url,
            username=username,
            password=password,
            login_path=login_path,
            username_field=username_field,
            password_field=password_field
        )
        return {"result": success}
    except Exception as e:
        return {"result": False, "error": str(e)}


@mcp.tool
def student_login_debug(
    base_url: str,
    username: str,
    password: str,
    login_path: str = "/",
    username_field: str = "textKulID",
    password_field: str = "textSifre",
    check_path: str = "/",
    success_text: str = None,
    payload_json: bool = False,
    extra_fields: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Login denemesini ayrıntılarıyla raporlar (CSRF, status, redirect, cookie).
    
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
        Detaylı debug bilgileri
    """
    try:
        return student_obs_login_debug(
            base_url=base_url,
            username=username,
            password=password,
            login_path=login_path,
            username_field=username_field,
            password_field=password_field,
            check_path=check_path,
            success_text=success_text,
            payload_json=payload_json,
            extra_fields=extra_fields
        )
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_logout() -> Dict[str, Any]:
    """
    Öğrenci Bilgi Sistemi oturumunu kapatır.
    
    Returns:
        Logout sonucu ({"result": true/false})
    """
    try:
        success = student_obs_logout()
        return {"result": success}
    except Exception as e:
        return {"result": False, "error": str(e)}


# =============================================================================
# OBS VERİ ÇEKME FONKSİYONLARI
# =============================================================================

@mcp.tool
def student_navigate_to_page(page_path: str = "/") -> Dict[str, Any]:
    """
    OBS'de belirli bir sayfaya git ve içeriği döndür.
    
    Args:
        page_path: Gidilecek sayfanın yolu (varsayılan: /)
        
    Returns:
        Sayfa bilgileri (status_code, url, content)
    """
    try:
        return student_obs_navigate_to_page(page_path)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_profile(profile_path: str = "/api/profile") -> Dict[str, Any]:
    """
    OBS'den (öğrenci) profil bilgilerini alır.
    
    Args:
        profile_path: Profil sayfasının yolu (varsayılan: /api/profile)
        
    Returns:
        Profil bilgileri
    """
    try:
        return student_obs_get_profile(profile_path)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_announcements(path: str = "/api/announcements", limit: int = 10) -> Dict[str, Any]:
    """
    OBS'den (öğrenci) duyuruları alır.
    
    Args:
        path: Duyuru sayfasının yolu (varsayılan: /api/announcements)
        limit: Maksimum duyuru sayısı (varsayılan: 10)
        
    Returns:
        Duyuru listesi
    """
    try:
        return student_obs_get_announcements(path, limit)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_courses(path: str = "/api/courses") -> Dict[str, Any]:
    """
    OBS'den (öğrenci) ders listesini alır.
    
    Args:
        path: Ders sayfasının yolu (varsayılan: /api/courses)
        
    Returns:
        Ders listesi
    """
    try:
        return student_obs_get_courses(path)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_transcript(path: str = "/api/transcript") -> Dict[str, Any]:
    """
    OBS'den (öğrenci) transkript bilgisini alır.
    
    Args:
        path: Transkript sayfasının yolu (varsayılan: /api/transcript)
        
    Returns:
        Transkript bilgileri
    """
    try:
        return student_obs_get_transcript(path)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_info() -> Dict[str, Any]:
    """
    OBS'den öğrenci bilgilerini çeker (HTML parsing ile).
    
    Returns:
        Öğrenci bilgileri
    """
    try:
        return student_obs_get_student_info()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_info_parsed() -> Dict[str, Any]:
    """
    OBS'den öğrenci bilgilerini alır ve parse eder.
    
    Returns:
        Parse edilmiş öğrenci bilgileri
    """
    try:
        return student_obs_get_student_info_parsed()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def parse_student_info(html_content: str) -> Dict[str, Any]:
    """
    HTML içeriğinden öğrenci bilgilerini parse eder.
    
    Args:
        html_content: HTML içeriği
        
    Returns:
        Parse edilmiş öğrenci bilgileri
    """
    try:
        return student_obs_parse_student_info(html_content)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_term_courses() -> Dict[str, Any]:
    """DonemDersleri.aspx sayfasından dönem derslerini getirir (parse edilmiş)."""
    try:
        from core import student_obs_get_term_courses
        return student_obs_get_term_courses()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_my_courses() -> Dict[str, Any]:
    """Derslerim.aspx sayfasından öğrencinin derslerini getirir (parse edilmiş)."""
    try:
        from core import student_obs_get_my_courses
        return student_obs_get_my_courses()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_announcements_loggedin(limit: int = 10) -> Dict[str, Any]:
    """Öğrenci panelindeki duyuruları döndürür (giriş gerekli)."""
    try:
        from core import student_obs_get_student_announcements
        return student_obs_get_student_announcements(limit)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_messages() -> Dict[str, Any]:
    """Mesajlarim.aspx sayfasından mesajları döndürür (giriş gerekli)."""
    try:
        from core import student_obs_get_messages
        return student_obs_get_messages()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# EKSİK ÖZELLİKLERİ MCP OLARAK DIŞA AÇMA
# =============================================================================

@mcp.tool
def student_weekly_schedule() -> Dict[str, Any]:
    """Haftalık ders programını döndürür (giriş gerekli)."""
    try:
        return student_obs_get_weekly_schedule()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_attendance() -> Dict[str, Any]:
    """Devamsızlık/Yoklama bilgilerini döndürür (giriş gerekli)."""
    try:
        return student_obs_get_attendance()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_fees() -> Dict[str, Any]:
    """Harç/ödeme bilgilerini döndürür (giriş gerekli)."""
    try:
        return student_obs_get_fees()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_library() -> Dict[str, Any]:
    """Kütüphane/Malzeme borç bilgilerini döndürür (giriş gerekli)."""
    try:
        return student_obs_get_library()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_registration() -> Dict[str, Any]:
    """Kayıt yenileme / Ders kayıt tablolarını döndürür (giriş gerekli)."""
    try:
        return student_obs_get_registration()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_thesis() -> Dict[str, Any]:
    """Bitirme tezi işlemleri/başvuruları bilgilerini döndürür (giriş gerekli)."""
    try:
        return student_obs_get_thesis()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_internships() -> Dict[str, Any]:
    """Staj başvuruları bilgilerini döndürür (giriş gerekli)."""
    try:
        return student_obs_get_internships()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_petitions() -> Dict[str, Any]:
    """Dilekçe işlemleri tablolarını döndürür (giriş gerekli)."""
    try:
        return student_obs_get_petitions()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_materials() -> Dict[str, Any]:
    """Ders dökümanları tablolarını döndürür (giriş gerekli)."""
    try:
        return student_obs_get_materials()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_online_education_links() -> Dict[str, Any]:
    """Uzaktan eğitim/öğrenme platform linklerini döndürür (giriş gerekli)."""
    try:
        return student_obs_get_online_education_links()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_events() -> Dict[str, Any]:
    """Etkinlikler tablolarını döndürür (giriş gerekli)."""
    try:
        return student_obs_get_events()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# YENİ EKLENEN ÖZELLİKLER
# =============================================================================

@mcp.tool
def student_academic_analytics() -> Dict[str, Any]:
    """
    Öğrencinin akademik performans analizini yapar.
    
    Returns:
        GPA trend analizi, kredi tamamlama oranı ve ders başarı grafiği
    """
    try:
        return student_obs_get_academic_analytics()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_performance_tracking() -> Dict[str, Any]:
    """
    Akademik hedefler ve performans takibi.
    
    Returns:
        Performans hedefleri, ilerleme durumu ve hedef önerileri
    """
    try:
        return student_obs_get_performance_tracking()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_course_advisor() -> Dict[str, Any]:
    """
    Akademik danışmanlık ve ders seçim önerileri.
    
    Returns:
        Ders seçim analizi, ön koşul kontrolü ve öneriler
    """
    try:
        return student_obs_get_course_advisor()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_notifications() -> Dict[str, Any]:
    """
    Önemli bildirimleri ve uyarıları listeler.
    
    Returns:
        Akademik, devamsızlık, mali ve sistem uyarıları
    """
    try:
        return student_obs_get_notifications()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_notification_settings() -> Dict[str, Any]:
    """
    Bildirim ayarlarını getirir.
    
    Returns:
        Bildirim tercihleri ve ayarları
    """
    try:
        return student_obs_get_notification_settings()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_mark_notification_read(notification_id: str) -> Dict[str, Any]:
    """
    Bildirimi okundu olarak işaretler.
    
    Args:
        notification_id: Bildirim ID'si
        
    Returns:
        İşlem sonucu
    """
    try:
        return student_obs_mark_notification_read(notification_id)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_export_data(format: str = "json", data_type: str = "all") -> Dict[str, Any]:
    """
    Verileri farklı formatlarda export eder.
    
    Args:
        format: Export formatı (json, csv, pdf, excel)
        data_type: Veri tipi (all, academic, financial, personal, schedule)
        
    Returns:
        Export edilmiş veri
    """
    try:
        return student_obs_export_data(format, data_type)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def student_export_formats() -> Dict[str, Any]:
    """
    Desteklenen export formatlarını listeler.
    
    Returns:
        Kullanılabilir formatlar ve öneriler
    """
    try:
        return student_obs_get_export_formats()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# SERVER BAŞLATMA
# =============================================================================

if __name__ == "__main__":
    try:
        print("🚀 Isparta Üniversitesi OBS MCP Server başlatılıyor...")
        print("📚 Kullanılabilir tools:")
        print("🔐 TEMEL FONKSİYONLAR:")
        print("   • student_login() - Öğrenci girişi")
        print("   • student_logout() - Öğrenci çıkışı")
        print("   • student_login_debug() - Debug login")
        print()
        print("📊 VERİ ÇEKME:")
        print("   • student_profile() - Öğrenci profili")
        print("   • student_info() - Öğrenci bilgileri")
        print("   • student_info_parsed() - Parse edilmiş öğrenci bilgileri")
        print("   • student_announcements() - Öğrenci duyuruları")
        print("   • student_courses() - Öğrenci dersleri")
        print("   • student_transcript() - Öğrenci transkripti")
        print("   • student_navigate_to_page() - Sayfa navigasyonu")
        print("   • parse_student_info() - HTML parse etme")
        print()
        print("📅 PROGRAM VE TAKVİM:")
        print("   • student_weekly_schedule() - Haftalık ders programı")
        print("   • student_attendance() - Devamsızlık bilgileri")
        print("   • student_events() - Etkinlikler")
        print()
        print("💰 MALİ BİLGİLER:")
        print("   • student_fees() - Harç bilgileri")
        print("   • student_library() - Kütüphane borçları")
        print()
        print("📋 İŞLEMLER VE BAŞVURULAR:")
        print("   • student_registration() - Kayıt yenileme")
        print("   • student_thesis() - Tez işlemleri")
        print("   • student_internships() - Staj başvuruları")
        print("   • student_petitions() - Dilekçe işlemleri")
        print("   • student_materials() - Ders materyalleri")
        print("   • student_online_education_links() - Online eğitim linkleri")
        print()
        print("🚀 YENİ EKLENEN ÖZELLİKLER:")
        print("   • student_academic_analytics() - Akademik performans analizi")
        print("   • student_performance_tracking() - Performans takibi ve hedefler")
        print("   • student_course_advisor() - Ders seçim asistanı")
        print("   • student_notifications() - Bildirim ve uyarı sistemi")
        print("   • student_notification_settings() - Bildirim ayarları")
        print("   • student_mark_notification_read() - Bildirim okundu işaretleme")
        print("   • student_export_data() - Veri export (JSON, CSV, PDF, Excel)")
        print("   • student_export_formats() - Desteklenen export formatları")
        print()
        
        # Server'ı başlat
        asyncio.run(mcp.run())
        
    except KeyboardInterrupt:
        print("\n👋 Server kapatılıyor...")
    except Exception as e:
        print(f"❌ Server hatası: {e}")
