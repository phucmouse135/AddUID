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
# PROXY CONFIG (CaptchaFox yêu cầu Proxy)
PROXY_TYPE = os.getenv("PROXY_TYPE", "http") # http, socks4, socks5
PROXY_ADDRESS = os.getenv("PROXY_ADDRESS", "") # IP
PROXY_PORT = os.getenv("PROXY_PORT", "")       # Port
PROXY_LOGIN = os.getenv("PROXY_LOGIN", "")     # Optional
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "") # Optional

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

def api_solve_captchafox_task(api_key, site_url, site_key, user_agent):
    """
    Direct API Call to 2Captcha for CaptchaFox via in.php (Standard API provided in docs)
    Ref: https://2captcha.com/api-docs/captchafox
    Method: captchafox
    """
    print(f"-> [SPEC] Gọi API 2captcha.com/in.php giải CaptchaFox (Key: {site_key})...")
    
    # 1. Construct Proxy String (Required format: login:password@IP:Port or IP:Port)
    if not (PROXY_ADDRESS and PROXY_PORT):
        print("❌ [ERROR] CaptchaFox YÊU CẦU PROXY nhưng không tìm thấy cấu hình trong .env")
        print("   Vui lòng điền PROXY_ADDRESS, PROXY_PORT (và LOGIN/PASS nếu có) vào file .env")
        return None

    proxy_str = f"{PROXY_ADDRESS}:{PROXY_PORT}"
    if PROXY_LOGIN and PROXY_PASSWORD:
        proxy_str = f"{PROXY_LOGIN}:{PROXY_PASSWORD}@{PROXY_ADDRESS}:{PROXY_PORT}"
    
    print(f"-> [PROXY] Proxy String: {proxy_str} (Type: {PROXY_TYPE})")

    # 2. Create Task
    try:
        url_in = "https://2captcha.com/in.php"
        
        payload = {
            "key": api_key,
            "method": "captchafox",
            "sitekey": site_key,
            "pageurl": site_url,
            "proxy": proxy_str,
            "proxytype": PROXY_TYPE,
            "useragent": user_agent,
            "json": 1
        }
        
        # Gửi request POST JSON
        # Lưu ý: Tài liệu mẫu ghi JSON payload, nên ta dùng json=payload
        res = requests.post(url_in, json=payload, timeout=30).json()
        
        if res.get("status") != 1:
            err_desc = res.get("request")
            print(f"❌ Upload Failed: {err_desc}")
            if "ERROR_ZERO_BALANCE" in str(err_desc):
                print("⚠️  Tài khoản 2Captcha không đủ tiền.")
            if "ERROR_PROXY" in str(err_desc):
                print("⚠️  Lỗi Proxy (Kết nối timeout hoặc sai định dạng).")
            return None
            
        task_id = res["request"]
        print(f"-> Task Created successfully. Task ID: {task_id}")
        
        # 3. Get Result Loop
        url_res = "https://2captcha.com/res.php"
        poll_payload = {
            "key": api_key,
            "action": "get",
            "id": task_id,
            "json": 1
        }

        for i in range(40): # Wait up to 200s
            time.sleep(5)
            try:
                # 2Captcha res.php thường support cả GET và POST
                r = requests.post(url_res, json=poll_payload, timeout=10).json()
            except:
                continue
            
            status = r.get("status")
            request_frame = r.get("request")

            if status == 1:
                token = request_frame
                print(f"✅ Giải CaptchaFox thành công! Token: {token[:20]}...")
                return token
            
            if request_frame == "CAPCHA_NOT_READY":
                 print(f"   ... Waiting for CaptchaFox solution ({i*5}s)")
                 continue
            
            if status == 0:
                 print(f"❌ Pooling Error: {request_frame}")
                 return None
            
        print("❌ Timeout waiting for CaptchaFox result")
        return None
        
    except Exception as e:
        print(f"❌ Exception in api_solve_captchafox_task: {e}")
        return None

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
        
        # Cách 1.5: Quét iframe (Sâu & Recursive)
        # Vì Cloudflare Turnstile thường ẩn trong iframe lồng nhau
        try:
            original_window = driver.current_window_handle
            
            def scan_frames(depth=0):
                if depth > 3: return # Limit depth
                
                # Check current frame's source
                try:
                    src = driver.page_source
                    matches = re.findall(r'sitekey=["\']?(0x[A-Za-z0-9_-]+)', src)
                    for k in matches:
                        if k not in candidate_keys:
                            print(f"-> [FRAME-SCAN] Found Key in Frame Source: {k} (PRIORITY!)")
                            candidate_keys.insert(0, k)
                except: pass

                # Loop children frames
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i, frame in enumerate(iframes):
                    try:
                        # Check src attribute first (fast)
                        f_src = frame.get_attribute("src") or ""
                        m_src = re.search(r'sitekey=(0x[A-Za-z0-9_-]+)', f_src)
                        if m_src:
                            k = m_src.group(1)
                            if k not in candidate_keys:
                                print(f"-> [FRAME-ATTR] Found Key in Iframe Src: {k} (PRIORITY!)")
                                candidate_keys.insert(0, k)

                        # Switch and recurse
                        driver.switch_to.frame(frame)
                        scan_frames(depth + 1)
                        driver.switch_to.parent_frame()
                    except:
                        driver.switch_to.parent_frame()
            
            # Start scan
            scan_frames()
            driver.switch_to.window(original_window) # Restore
            
        except Exception as e:
            print(f"-> Frame scan error: {e}")
            try: driver.switch_to.default_content() 
            except: pass

        # Cách 1.75: Quét Shadow DOM (Deep Scan bằng JS)
        # Cloudflare Turnstile thường ẩn trong Shadow Root để tránh bot
        print("-> Đang quét Shadow DOM để tìm SiteKey ẩn...")
        shadow_key = driver.execute_script("""
            function findKey(root) {
                if (!root) return null;
                
                // 1. Check elements in this root having sitekey
                let selector = '[sitekey^="0x"], [data-sitekey^="0x"], div[id^="cf-"]';
                let els = root.querySelectorAll(selector);
                for (let el of els) {
                    if (el.getAttribute('sitekey')) return el.getAttribute('sitekey');
                    if (el.getAttribute('data-sitekey')) return el.getAttribute('data-sitekey');
                }

                // 2. Check iframe srcs in this root
                let frames = root.querySelectorAll('iframe');
                for (let f of frames) {
                    try {
                        if (f.src && f.src.includes('sitekey=0x')) {
                            let m = f.src.match(/sitekey=(0x[A-Za-z0-9_-]+)/);
                            if (m) return m[1];
                        }
                    } catch(e){}
                }

                // 3. Recurse into children's shadow roots
                // TreeWalker is faster than full recursion on all nodes
                let walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null, false);
                while(walker.nextNode()) {
                    let node = walker.currentNode;
                    if (node.shadowRoot) {
                        let found = findKey(node.shadowRoot);
                        if (found) return found;
                    }
                }
                return null;
            }
            return findKey(document) || findKey(document.body);
        """)
        
        if shadow_key and shadow_key not in candidate_keys:
            print(f"-> [SHADOW-DOM] Found Hidden Turnstile Key: {shadow_key} (PRIORITY!)")
            candidate_keys.insert(0, shadow_key)

        # Cách 2: Tìm trong element Checkbox/Widget
        print("-> Đang quét SiteKey từ DOM...")
        cf_elements = driver.find_elements(By.CSS_SELECTOR, "[data-sitekey]")
        if cf_elements:
            val = cf_elements[0].get_attribute("data-sitekey")
            if val and val not in candidate_keys: candidate_keys.append(val)
        
        # Cách 3: Tìm trong Page Source (Regex Clean)
        html = driver.page_source
        patterns = [
            r'sitekey["\']?\s*[:=]\s*["\'](0x[a-zA-Z0-9_-]+)["\']', # CHỈ LẤY Key 0x
        ]
        for p in patterns:
            param_matches = re.findall(p, html)
            for m in param_matches:
                 # Chỉ nhận key 0x, bỏ qua key sk_
                 if 20 < len(m) < 100 and " " not in m and m.startswith("0x"): 
                     if m not in candidate_keys:
                         candidate_keys.insert(0, m)

    except Exception as e:
        print(f"-> Lỗi khi tìm SiteKey: {e}")

    # --- [NEW] CÁCH 4: Quét Chậm Iframe SRC (Quan trọng nhất cho GMX) ---
    print("-> Đang đợi iframe Turnstile xuất hiện (Max 10s)...")
    found_real_key = False
    
    # Retry loop để bắt key khi iframe vừa load xong
    for attempt in range(10):
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for f in iframes:
                src = f.get_attribute("src") or ""
                # Turnstile iframe luôn có sitekey trong URL
                if "sitekey=0x" in src:
                    m = re.search(r'sitekey=(0x[A-Za-z0-9_-]+)', src)
                    if m: 
                        real_key = m.group(1)
                        if real_key not in candidate_keys:
                            candidate_keys.insert(0, real_key) # Ưu tiên số 1
                            print(f"-> [IFRAME-DETECT] Tìm thấy SiteKey chuẩn trong src: {real_key}")
                            found_real_key = True
        except: pass
        
        if found_real_key: break
        time.sleep(1)

    # Lọc danh sách: Giữ cả 0x (Turnstile) và sk_ (CaptchaFox)
    # Vì giờ ta đã có solver riêng cho từng loại
    candidate_keys = list(dict.fromkeys([k for k in candidate_keys if k and (k.startswith("0x") or k.startswith("sk_"))]))

    # Fallback Keys
    if not candidate_keys:
        print(f"⚠️ Không tìm thấy key động, dùng bộ Fallback.")
        candidate_keys.append("0x4AAAAAAAC3DHQFLr1Gavgn") # Turnstile GMX
        candidate_keys.append("sk_uVvZFK06t1rgOKEXgJafrEXI4f9e4") # CaptchaFox GMX
    
    print(f"-> Danh sách Key tiềm năng: {candidate_keys}")

    # 3. GIẢI CAPTCHA (Phân loại Key)
    clean_url = driver.current_url.split('?')[0]
    solver = TwoCaptcha(apiKey=api_key, defaultTimeout=120, pollingInterval=5)
    
    # [QUAN TRỌNG] Lấy User-Agent hiện tại
    current_ua = driver.execute_script("return navigator.userAgent;")
    token = None
    
    for s_key in candidate_keys:
        print(f"-> Quyết định giải với Key: {s_key}")
        
        try:
            # CASE 1: CaptchaFox Native (sk_...)
            if s_key.startswith("sk_"):
                print("   [MODE] Phát hiện Key CaptchaFox -> Dùng api_solve_captchafox_task")
                token = api_solve_captchafox_task(api_key, clean_url, s_key, current_ua)
            
            # CASE 2: Cloudflare Turnstile (0x...)
            else:
                print("   [MODE] Phát hiện Key Turnstile -> Dùng solver.turnstile")
                result = solver.turnstile(
                    sitekey=s_key, 
                    url=clean_url,
                    userAgent=current_ua
                )
                token = result['code']
            
            if token:
                print(f"-> [THÀNH CÔNG] Đã lấy được Token! Length: {len(token)}")
                break 

        except Exception as e:
            print(f"⚠️ Thất bại với key {s_key}: {e}")
            if "ERROR_SITEKEY" in str(e) or "UNSOLVABLE" in str(e):
                continue
            else:
                pass # Try next key

    if not token:
        print("❌ [FAIL] Không giải được Captcha với danh sách Key hiện có.")
        return False

    # 4. TIÊM TOKEN VÀO TRÌNH DUYỆT (NÂNG CAO CHO GMX)
    try:
        # Script này xử lý cả việc gửi request API ngầm (giống request người dùng cung cấp)
        driver.execute_script(f"""
            let token = '{token}';
            
            // 1. Tìm các input ẩn thường dùng
            let inputNames = ['cf-turnstile-response', 'g-recaptcha-response', 'captchafox-response'];
            let found = false;
            
            inputNames.forEach(name => {{
                let el = document.querySelector(`input[name="${{name}}"]`);
                if (el) {{
                    el.value = token;
                    // Trigger events để GMX nhận diện thay đổi
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    found = true;
                }}
            }});

            // 2. Nếu không có, tạo mới input ẩn và append vào form
            if (!found) {{
                let form = document.querySelector('form');
                if (form) {{
                    let input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'cf-turnstile-response'; 
                    input.id = 'cf-turnstile-response';
                    input.value = token;
                    form.appendChild(input);
                    // Force submit form if needed (đôi khi cần thiết)
                    // console.log("Force Injecting Input");
                }}
            }}
            
            // 3. XỬ LÝ ĐẶC BIỆT CHO GMX (QUAN TRỌNG)
            // GMX dùng cơ chế lắng nghe message từ iframe hoặc callback global
            try {{
               // Giả lập callback của Turnstile/CaptchaFox
               if (typeof turnstile !== 'undefined' && turnstile.execute) {{
                   console.log("Calling turnstile.execute()...");
               }}
               
               // Tìm callback function trong window global (thường tên ngẫu nhiên hoặc 'onSuccess')
               // Nhưng quan trọng nhất: GMX thường check biến toàn cục, ta gán token vào đó
               window.captchafox_token = token; 
            }} catch(e) {{}}
        """)
        
        # 5. GỬI REQUEST XÁC MINH TRỰC TIẾP (Backdoor giống cURL người dùng cung cấp)
        # GMX có endpoint API riêng để xác nhận captcha, ta sẽ gọi fetch() trực tiếp từ console browser.
        # Dữ liệu lấy từ gói tin mẫu người dùng cung cấp.
        print("-> Đang thử gửi API Verification ngầm (Phương pháp cURL Sim)...")
        driver.execute_script(f"""
            (async () => {{
                try {{
                    // Lấy sessionId từ URL hoặc cookie (LS-...)
                    let sessionId = new URLSearchParams(window.location.search).get('state') || 'ls-unknown';
                    
                    // Thử tìm sessionId trong cookie ls.rec hoặc tương tự
                    let cookies = document.cookie.split(';');
                    let ls_rec = '';
                    for(let c of cookies) {{
                        if(c.trim().startsWith('__Host-ls.rec=')) {{
                            ls_rec = c.trim().split('=')[1];
                        }}
                    }}
                    
                    // Construct payload giống mẫu cURL
                    // Lưu ý: sessionId thực tế của GMX rất phức tạp, ta thử dùng 'state' param hoặc ls-token
                    // API Endpoint: https://login.gmx.net/rest/login-flow/captchafox-verification
                    
                    let payload = {{
                        "captcha": {{
                            "response": "{token}",
                            "siteKey": "{site_key}"
                        }},
                        "sessionId": "ls-" + ls_rec // Cố gắng build lại sessionId hợp lệ
                    }};

                    // Gửi fetch request
                    await fetch("https://login.gmx.net/rest/login-flow/captchafox-verification", {{
                        method: "POST",
                        headers: {{
                            "content-type": "application/json",
                            "accept": "application/json, text/plain, */*"
                        }},
                        body: JSON.stringify(payload)
                    }});
                    console.log("Sent verification request");
                }} catch(e) {{ console.error("Fetch error", e); }}
            }})();
        """)
        
        print("-> Đã Inject Token và trigger API Verification.")
        return True
        
    except Exception as inject_err:
        print(f"❌ [EXCEPTION] Lỗi khi inject Token vào DOM: {inject_err}")
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