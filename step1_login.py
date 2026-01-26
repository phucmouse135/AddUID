# FILE: step1_login.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException

try:
    from gmx_core import get_driver, reload_if_ad_popup
except ImportError:
    from selenium import webdriver
    def get_driver(headless=False):
        options = webdriver.ChromeOptions()
        if headless: options.add_argument("--headless")
        return webdriver.Chrome(options=options)
    def reload_if_ad_popup(driver): return False

# --- CONFIG ---
DEF_USER = "saucycut1@gmx.de"
DEF_PASS = "muledok5P"
AUTH_URL = "https://auth.gmx.net/login?prompt=none&state=eyJpZCI6ImVlOTk4N2NmLWE2ZjYtNGQzMy04NjA3LWEwZDFmMTFlMDU0NSIsImNsaWVudElkIjoiZ214bmV0X2FsbGlnYXRvcl9saXZlIiwieFVpQXBwIjoiZ214bmV0LmFsbGlnYXRvci8xLjEwLjEiLCJwYXlsb2FkIjoiZXlKa1l5STZJbUp6SWl3aWRHRnlaMlYwVlZKSklqb2lhSFIwY0hNNkx5OXNhVzVyTG1kdGVDNXVaWFF2YldGcGJDOXphRzkzVTNSaGNuUldhV1YzSWl3aWNISnZZMlZ6YzBsa0lqb2liMmxmY0d0alpWOWpNVGRtTjJNNE55SjkifQ%3D%3D&authcode-context=CcbxFUyzH0"

# --- HELPER FUNCTIONS ---

def safe_click(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return True
    except:
        try:
            element = driver.find_element(by, value)
            driver.execute_script("arguments[0].click();", element)
            return True
        except:
            return False

def safe_send_keys(driver, by, value, text, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        element.clear()
        element.send_keys(text)
        return True
    except:
        try:
            element = driver.find_element(by, value)
            driver.execute_script("arguments[0].value = arguments[1];", element, text)
            return True
        except:
            return False

def check_blocking_popup(driver):
    """
    Chỉ trả về True nếu phát hiện Popup CHẶN MÀN HÌNH thực sự.
    (Đã loại bỏ check iframe chung chung để tránh loop vô hạn)
    """
    # Các selector chính xác của GMX Consent/Overlay
    blocking_selectors = [
        (By.ID, "permission-layer"),        # Consent form chính
        (By.ID, "onetrust-banner-sdk"),    # Cookie banner
        (By.CSS_SELECTOR, ".be-layer-container"), # Lớp phủ đen
        (By.CSS_SELECTOR, "div[class*='permission-layer']")
    ]
    
    for by, val in blocking_selectors:
        try:
            elems = driver.find_elements(by, val)
            for el in elems:
                # Điều kiện chặt: Phải hiển thị VÀ kích thước lớn (chặn màn hình)
                if el.is_displayed() and el.size['height'] > 300 and el.size['width'] > 300:
                    return True
        except: pass
    
    return False
# --- MAIN LOGIN LOGIC ---

def login_process(driver, user, password):
    print(f"--- START LOGIN PROCESS: {user} ---")
    
    try:
        # 1. TRUY CẬP LINK AUTH
        driver.get(AUTH_URL)
        
        # 2. NHẬP EMAIL
        if not safe_send_keys(driver, By.ID, "username", user):
             if not safe_send_keys(driver, By.CSS_SELECTOR, "input[data-testid='input-username']", user):
                 print("❌ [FAIL] Không tìm thấy ô nhập Email.")
                 return False
        
        # 3. NHẤN WEITER
        if not safe_click(driver, By.CSS_SELECTOR, "button[data-testid='button-next']"):
            print("❌ [FAIL] Không nhấn được nút Weiter.")
            return False
            
        # 4. NHẬP PASSWORD
        if not safe_send_keys(driver, By.ID, "password", password, timeout=5):
            if not safe_send_keys(driver, By.CSS_SELECTOR, "input[data-testid='input-password']", password):
                print("❌ [FAIL] Không tìm thấy ô nhập Password.")
                return False

        # 5. NHẤN LOGIN
        print("-> Clicking Login...")
        if not safe_click(driver, By.CSS_SELECTOR, "button[data-testid='button-next']"):
            print("❌ [FAIL] Không nhấn được nút Login.")
            return False

        # 6. XỬ LÝ REDIRECT & POPUP (LOOP CHECK)
        driver.switch_to.default_content()
        print("-> Waiting for redirection...")
        
        end_time = time.time() + 120 # Tăng timeout vì có thể phải redirect vòng vo
        
        while time.time() < end_time:
            current_url = driver.current_url.lower()
            
            # --- CASE A: THÀNH CÔNG ---
            if "navigator" in current_url:
                print(f"✅ [PASS] Login Success! URL: {driver.current_url}")
                return True
            
            # --- CASE B: GẶP LỖI HILFE / ERROR -> CHUYỂN VỀ GMX.NET ---
            # Logic mới: Gặp lỗi này không return False mà redirect về trang chủ
            if "hilfe.gmx.net" in current_url or "consent-management" in current_url:
                print(f"⚠️ Redirected to Help/Error page. Force navigating to GMX Home...")
                driver.get("https://www.gmx.net/")
                time.sleep(2.5) # Chờ load trang chủ
                continue # Quay lại đầu vòng lặp để xử lý logic trang chủ (CASE C)

            # --- CASE C: VỀ TRANG CHỦ GMX (Cần xử lý Popup & Click Postfach) ---
            if "gmx.net" in current_url and "auth" not in current_url and "hilfe" not in current_url:
                time.sleep(2)
                driver.get("https://www.gmx.net/") # Refresh để chắc chắn trang sạch
                time.sleep(2)
                
                # B2: Trang sạch -> Tìm nút 'Zum Postfach'
                btn_selectors = [
                    (By.XPATH, "//span[contains(text(), 'Zum Postfach')]/parent::button"),
                    (By.CSS_SELECTOR, "a[href*='navigator']"),
                    (By.CSS_SELECTOR, "button[data-component='button']")
                ]
                
                found_btn = False
                for b_by, b_val in btn_selectors:
                    if safe_click(driver, b_by, b_val, timeout=1):
                        print(f"-> Clicked 'Zum Postfach' using {b_val}")
                        found_btn = True
                        time.sleep(1) 
                
                # B3: Force Navigate (Nếu đã login, không có popup, nhưng không thấy nút)
                if not found_btn:
                    page_source = driver.page_source.lower()
                    if "logout" in page_source or "abmelden" in page_source:
                        print("ℹ️ Logged in but button hidden. Force navigating...")
                        driver.get("https://navigator.gmx.net/")
                        time.sleep(1)

            time.sleep(0.5)

        print("❌ [FAIL] Timeout: Không thể vào trang Navigator.")
        return False

    except Exception as e:
        print(f"❌ [EXCEPTION] Lỗi nghiêm trọng: {e}")
        return False

if __name__ == "__main__":
    driver = get_driver(headless=False)
    try:
        login_process(driver, DEF_USER, DEF_PASS)
    finally:
        pass # driver.quit()