# FILE: step1_login.py
import time
import json
import urllib.request
import urllib.parse
import re
import requests
import os
from dotenv import load_dotenv

load_dotenv()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from twocaptcha import TwoCaptcha

try:
    from gmx_core import get_driver, reload_if_ad_popup, close_driver_and_cleanup
except ImportError:
    from selenium import webdriver
    def get_driver(headless=False):
        options = webdriver.ChromeOptions()
        if headless: options.add_argument("--headless")
        return webdriver.Chrome(options=options)
    def reload_if_ad_popup(driver): return False
    def close_driver_and_cleanup(driver): 
        if driver: driver.quit()

# --- CONFIG ---
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "2651ba625c2b6da0697406bff9ffcab2")
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

def solve_gmx_captchafox(driver, api_key):
    """
    Sử dụng thư viện 2captcha-python chính thức.
    Ưu tiên lấy Dynamic SiteKey để tránh lỗi ERROR_SITEKEY.
    """
    print("--- DETECTED CAPTCHAFOX INTERACTION ---")

    # 1. CLICK CHECKBOX 'Ich bin ein Mensch'
    try:
        btn_xpath = "//*[contains(text(), 'Ich bin ein Mensch')]"
        element = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, btn_xpath))
        )
        element.click()
        print("-> Đã click Checkbox. Đang tìm SiteKey...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-sitekey]"))
        )
        time.sleep(3) # Chờ DOM render
    except Exception:
        print("-> Không thấy nút Checkbox (hoặc đã click).")

    # 2. TỰ ĐỘNG LẤY CANDIDATE SITEKEYS
    candidate_keys = []

    try:
        # Cách 1: Network Traffic Analysis (BẮT SỐNG GÓI TIN - CHÍNH XÁC NHẤT)
        print("-> Đang phân tích Network Log để tìm SiteKey thật...")
        logs = driver.get_log("performance")
        
        # Regex Capture:
        # 1. CaptchaFox Wrapper Key (sk_...)
        # 2. Cloudflare Turnstile Real Key (0x...) - Key này mới quan trọng để giải Turnstile!
        
        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
                if message["method"] == "Network.requestWillBeSent":
                    url = message["params"]["request"]["url"]
                    
                    # Pattern 1: Tìm Key CaptchaFox (sk_...)
                    m1 = re.search(r'captchafox\.com/captcha/(sk_[a-zA-Z0-9_-]+)/', url)
                    if m1:
                        key = m1.group(1)
                        if key not in candidate_keys:
                            print(f"-> [NETWORK] Found CaptchaFox Key: {key}")
                            candidate_keys.append(key)

                    # Pattern 2: Tìm Key Turnstile (0x...) trong URL params của Cloudflare
                    # VD: https://challenges.cloudflare.com/turnstile/.../api.js?onload=...&sitekey=0x4AAAAAAAC3DHQFLr1Gavgn
                    m2 = re.search(r'sitekey=(0x[A-Za-z0-9_-]+)', url)
                    if m2:
                        key = m2.group(1)
                        if key not in candidate_keys:
                            print(f"-> [NETWORK] Found Turnstile Key: {key} (PRIORITY!)")
                            candidate_keys.insert(0, key) # Ưu tiên tuyệt đối

            except: pass
        
        # Cách 1.5: Quét iframe src để tìm sitekey=0x... (Vì đôi khi nó nằm trong iframe)
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            try:
                src = frame.get_attribute("src")
                if src and "sitekey=" in src:
                    m = re.search(r'sitekey=(0x[A-Za-z0-9_-]+)', src)
                    if m:
                        k = m.group(1)
                        if k not in candidate_keys:
                            print(f"-> [PAGESOURCE] Found Key in Iframe: {k} (PRIORITY!)")
                            candidate_keys.insert(0, k)
            except: pass

        # Cách 2: Tìm trong element Checkbox/Widget
        print("-> Đang quét SiteKey từ DOM...")
        cf_elements = driver.find_elements(By.CSS_SELECTOR, "[data-sitekey]")
        if cf_elements:
            val = cf_elements[0].get_attribute("data-sitekey")
            if val and val not in candidate_keys: candidate_keys.append(val)
        
        # Cách 3: Tìm trong Page Source (Regex Clean)
        html = driver.page_source
        patterns = [
            r'captchafox\.com/captcha/([a-zA-Z0-9_-]+)',
            r'["\'](sk_uVvZ[a-zA-Z0-9_-]+)["\']', # Priority GMX Key
            r'sitekey["\']?\s*[:=]\s*["\'](sk_[a-zA-Z0-9_-]+)["\']',
            r'sitekey["\']?\s*[:=]\s*["\'](0x[a-zA-Z0-9_-]+)["\']', # Patterns cho 0x keys
        ]
        for p in patterns:
            param_matches = re.findall(p, html)
            for m in param_matches:
                 # Key CaptchaFox (sk_) or Turnstile (0x) length checks
                 if 20 < len(m) < 100 and " " not in m and m not in candidate_keys: 
                     if m.startswith("0x"):
                         candidate_keys.insert(0, m)
                     else:
                         candidate_keys.append(m)

    except Exception as e:
        print(f"-> Lỗi khi tìm SiteKey: {e}")

    # Fallback Keys
    # Key Turnstile gốc của GMX (nếu bắt được trước đây)
    fallback_cf = "0x4AAAAAAAC3DHQFLr1Gavgn"
    if fallback_cf not in candidate_keys: candidate_keys.append(fallback_cf)

    fallback_fox = "sk_uVvZFK06t1rgOKEXgJafrEXI4f9e4" # Key cứng GMX CaptchaFox
    if fallback_fox not in candidate_keys: candidate_keys.append(fallback_fox)
    
    # Remove duplicates
    candidate_keys = list(dict.fromkeys([k for k in candidate_keys if k]))
    print(f"-> Danh sách Key tiềm năng: {candidate_keys}")

    if not candidate_keys:
        print("❌ [ABORT] Không tìm thấy bất kỳ SiteKey nào.")
        return False

    # 3. GIẢI CAPTCHA (Loop Candidates)
    clean_url = driver.current_url.split('?')[0]
    solver = TwoCaptcha(apiKey=api_key, defaultTimeout=120, pollingInterval=5)
    token = None
    
    for s_key in candidate_keys:
        print(f"-> Đang thử giải với Key: {s_key} (URL: {clean_url})")
        try:
            result = solver.turnstile(sitekey=s_key, url=clean_url)
            token = result['code']
            print(f"-> [THÀNH CÔNG] SDK 2Captcha đã giải quyết xong! Token length: {len(token)}")
            break # Success
        except Exception as e:
            print(f"⚠️ Thất bại với key {s_key}: {e}")
            if "ERROR_SITEKEY" in str(e):
                continue # Try next key
            else:
                return False

    if not token:
        print("❌ [FAIL] Không giải được Captcha với danh sách Key hiện có.")
        return False

    # 4. TIÊM TOKEN VÀO TRÌNH DUYỆT
    try:
        # Script này xử lý cả cf-turnstile-response và g-recaptcha-response để chắc chắn
        driver.execute_script(f"""
            let token = '{token}';
            
            // 1. Tìm các input ẩn thường dùng
            let inputNames = ['cf-turnstile-response', 'g-recaptcha-response', 'captchafox-response'];
            let found = false;
            
            inputNames.forEach(name => {{
                let el = document.querySelector(`input[name="${{name}}"]`);
                if (el) {{
                    el.value = token;
                    found = true;
                }}
            }});

            // 2. Nếu không có, tạo mới input ẩn và append vào form
            if (!found) {{
                let form = document.querySelector('form');
                if (form) {{
                    let input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'cf-turnstile-response'; // Name phổ biến nhất hiện nay
                    input.value = token;
                    form.appendChild(input);
                }}
            }}
            
            // 3. Callback JS (nếu trang web dùng callback thay vì form submit)
            // Thử gọi callback của Cloudflare nếu tồn tại
            try {{
                if (typeof turnstile !== 'undefined' && typeof turnstile.render === 'function') {{
                    // Đây là tricky, thường chỉ cần điền input là đủ với selenium
                }}
            }} catch(e) {{}}
        """)
        print("-> Đã Inject Token vào DOM thành công.")
        return True
        
    except Exception as inject_err:
        print(f"❌ [EXCEPTION] Lỗi khi inject Token vào DOM: {inject_err}")
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

        # --- INTERMEDIATE CHECK: Captcha or Password ---
        print("-> Checking: Password field OR CaptchaFox (Wait up to 30s)...")
        time.sleep(2) # Give page a moment to render
        check_start = time.time()
        while time.time() - check_start < 30:
            # Case A: Password Field Found
            if len(driver.find_elements(By.ID, "password")) > 0 or len(driver.find_elements(By.CSS_SELECTOR, "input[data-testid='input-password']")) > 0:
                print("-> Password field found.")
                break
            
            # Case B: Captcha Found
            captcha_elems = driver.find_elements(By.XPATH, "//*[contains(text(), 'Ich bin ein Mensch')]")
            if len(captcha_elems) > 0 and captcha_elems[0].is_displayed():
                print("⚠️ CaptchaFox/Turnstile detected. Initiating solver...")
                
                # Wait a bit for captcha to fully load
                time.sleep(3)
                
                # Retry solving up to 3 times
                solved = False
                for solve_attempt in range(3):
                    if solve_gmx_captchafox(driver, CAPTCHA_API_KEY):
                        solved = True
                        break
                    else:
                        print(f"⚠️ Captcha solve failed (Attempt {solve_attempt+1}/3).")
                        if solve_attempt < 2:
                            print("-> Refreshing page to get new SiteKey/Challenge...")
                            driver.refresh()
                            time.sleep(5)
                            # Re-click 'Ich bin ein Mensch' if needed (Logic handled inside solve_gmx_captchafox or page reload flow)
                            # Note: Refreshing brings us back to Email or Captcha page depending on GMX state.
                            # We need to breaking the loop or handle state carefully.
                            # Actually, for GMX, Refresh usually resets the flow. 
                            # Safe strategy: Break this inner loop, let the outer 'while' checking loop handle rediscovery.
                            print("-> Page refreshed. Re-checking elements...")
                            break 
                        time.sleep(2)
                        
                if solved:
                    print("-> Solved. Waiting for transition to password...")
                    time.sleep(5) # Increased wait after solve
                    check_start = time.time() # Reset timer to wait for password
                    continue
                else:
                    print("❌ Failed to solve captcha after 3 attempts.")
            
            time.sleep(1)
            
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
            if "hilfe.gmx.net" in current_url or "consent-management" in current_url:
                print(f"⚠️ Redirected to Help/Error page. Force navigating to GMX Home...")
                driver.get("https://www.gmx.net/")
                time.sleep(2.5) 
                continue 

            # --- CASE C: VỀ TRANG CHỦ GMX (Cần xử lý Popup & Click Postfach) ---
            if "gmx.net" in current_url and "auth" not in current_url and "hilfe" not in current_url:
                time.sleep(2)
                driver.get("https://www.gmx.net/") 
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
        # Keep browser open for a bit if success to see result
        time.sleep(5)
    finally:
        # Cleanup temp profile to save disk space
        close_driver_and_cleanup(driver)