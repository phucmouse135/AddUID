# FILE: gmx_core.py
import time
import os
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent

# --- CẤU HÌNH ---
TIMEOUT_MAX = 15  # Max seconds wait for element
SLEEP_INTERVAL = 1 
PROXY_HOST = "127.0.0.1"
CHROMEDRIVER_PATH = "chromedriver.exe" # Đường dẫn tương đối hoặc tuyệt đối tới chromedriver.exe

def get_driver(headless=False, proxy_port=None):
    """Initialize browser with config + Proxy + Fake UA + Local ChromeDriver + Temp Profile"""
    
    # 1. Tạo thư mục User Data tạm thời (tránh xung đột và rác)
    user_data_dir = tempfile.mkdtemp(prefix="gmx_chrome_profile_")
    
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # 2. Fake IP (9Proxy)
    if proxy_port:
        proxy_server = f"http://{PROXY_HOST}:{proxy_port}"
        options.add_argument(f'--proxy-server={proxy_server}')
        print(f"[CORE] Proxy set to: {proxy_server}")
    else:
        # Default fallback or no proxy
        pass 
    
    # 3. Static User Agent (Updated for better stealth)
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    print(f"[CORE] UserAgent: {user_agent}")
    options.add_argument(f'--user-agent={user_agent}')

    # 4. Chống detect cơ bản & Cấu hình
    # Tắt dòng 'Chrome is being controlled by automated test software' and logging
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument('--headless=new') # New headless mode (harder to detect)
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-blink-features=AutomationControlled') # Important for Cloudflare
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    
    # Tắt load ảnh để chạy nhanh
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    print(f"[CORE] Opening Browser (Headless: {headless}) using {CHROMEDRIVER_PATH}...")
    
    # Khởi tạo Service với Chromedriver có sẵn
    if os.path.exists(CHROMEDRIVER_PATH):
        service = Service(executable_path=os.path.abspath(CHROMEDRIVER_PATH))
    else:
        # Nếu path tương đối không thấy, thử tìm trong PATH hệ thống hoặc để mặc định
        service = Service(executable_path=CHROMEDRIVER_PATH) 

    try:
        driver = webdriver.Chrome(service=service, options=options)

        # 5. CDP MAGIC (QUAN TRỌNG NHẤT CHO CAPTCHA)
        # Tiêm JS để xóa hoàn toàn dấu vết navigator.webdriver trước khi load bất kỳ trang nào
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })

    except Exception as e:
        print(f"[CORE-ERROR] Could not start driver: {e}")
        # Clean up temp dir if start fails
        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except: pass
        raise e
    
    # Lưu path temp dir vào object driver để dùng cho hàm cleanup sau này
    driver.my_temp_user_data_dir = user_data_dir
    
    return driver

def close_driver_and_cleanup(driver):
    """Đóng driver và xóa thư mục User Data tạm"""
    if not driver:
        return

    # Lấy path temp từ driver (đã gán lúc init)
    temp_dir = getattr(driver, 'my_temp_user_data_dir', None)
    
    print("[CORE] Closing driver...")
    try:
        driver.quit()
    except Exception as e:
        print(f"[CORE-ERROR] Driver quit error: {e}")

    if temp_dir and os.path.exists(temp_dir):
        print(f"[CORE] Cleaning up temp dir: {temp_dir}")
        msg = f"[CORE] Removed temp dir: {temp_dir}"
        # Thử xóa vài lần vì Windows hay lock file
        for i in range(3):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                break
            except Exception:
                time.sleep(1)
        print(msg)

def find_element_safe(driver, by, value, timeout=TIMEOUT_MAX, click=False, send_keys=None):
    """
    Hàm tìm kiếm an toàn (Polling Loop).
    - Tự động retry nếu không thấy.
    - Trả về Element nếu thành công.
    - Trả về None nếu timeout.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if reload_if_ad_popup(driver):
            return None
        try:
            element = driver.find_element(by, value)
            
            # Scroll nhẹ để element vào view (tránh bị che)
            # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            
            if click:
                element.click()
                return True
            
            if send_keys:
                element.clear()
                element.send_keys(send_keys)
                return True
            
            return element # Trả về element để xử lý tiếp
        except Exception:
            time.sleep(SLEEP_INTERVAL)
            continue
    
    print(f"[ERROR] Không tìm thấy hoặc không thao tác được: {value}")
    return None

def reload_if_ad_popup(driver, url="https://www.gmx.net/"):
    """Reload to GMX home if ad-consent popup is shown."""
    try:
        try:
            current_url = driver.current_url
        except Exception:
            current_url = ""

        if current_url.startswith("https://suche.gmx.net/web"):
            driver.get(url)
            time.sleep(2)
            return True

        for element in driver.find_elements(By.CSS_SELECTOR, "span.title"):
            try:
                text = element.text.strip()
            except Exception:
                text = ""
            if "Wir finanzieren uns" in text:
                driver.get(url)
                time.sleep(2)
                return True

        for button in driver.find_elements(By.TAG_NAME, "button"):
            try:
                text = button.text.strip()
            except Exception:
                text = ""
            if text in ("Akzeptieren und weiter", "Zum Abo ohne Fremdwerbung"):
                driver.get(url)
                time.sleep(2)
                return True

        try:
            page_source = driver.page_source
        except Exception:
            page_source = ""

        page_lower = page_source.lower()
        if "wir finanzieren uns" in page_lower:
            popup_hints = [
                "werbung",
                "akzeptieren und weiter",
                "zum abo ohne fremdwerbung",
                "postfach ohne fremdwerbebanner",
                "abfrage nochmals anzeigen",
            ]
            if any(hint in page_lower for hint in popup_hints):
                driver.get(url)
                time.sleep(2)
                return True
        elif "wir finanzieren uns" in page_source and "Werbung" in page_source:
            driver.get(url)
            time.sleep(2)
            return True
    except Exception:
        pass
    return False
