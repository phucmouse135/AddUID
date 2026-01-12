# FILE: step1_login.py
import time
from selenium.webdriver.common.by import By
from gmx_core import get_driver, find_element_safe

# --- DATA TEST MẶC ĐỊNH ---
DEF_USER = "saucycut1@gmx.de"
DEF_PASS = "muledok5P"

def login_process(driver, user, password):
    """
    Hàm Login chuẩn (Code đã chốt).
    Trả về True nếu login thành công, False nếu thất bại.
    """
    try:
        print(f"--- START LOGIN PROCESS: {user} ---")
        
        # 1. Vào trang
        driver.get("https://www.gmx.net/")
        time.sleep(2)
        driver.get("https://www.gmx.net/") # Reload
        
        # 2. Xử lý Consent
        print("-> Check Consent...")
        find_element_safe(driver, By.ID, "onetrust-accept-btn-handler", timeout=5, click=True)

        # 3. LOGIC TÌM LOGIN FORM (AUTO-SCAN)
        print("-> Đang quét tìm vị trí Login Form (Main hoặc Iframe)...")
        
        # Danh sách selector tiềm năng cho username
        user_selectors = [
            (By.CSS_SELECTOR, "input[data-testid='input-email']"),
            (By.NAME, "username"),
            (By.ID, "username"), 
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.XPATH, "//input[@autocomplete='username']")
        ]

        found_input = False
        
        # 3.1. Kiểm tra ngay tại Main Content
        for by_m, val_m in user_selectors:
            if find_element_safe(driver, by_m, val_m, timeout=1):
                print(f"✅ Tìm thấy Login Input ở Main Content ({val_m})")
                found_input = True
                break
        
        # 3.2. Nếu chưa thấy, quét từng Iframe
        if not found_input:
            print("   Không thấy ở Main, bắt đầu quét các Iframe...")
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"   Tìm thấy {len(iframes)} iframes.")
            
            for index, iframe in enumerate(iframes):
                try:
                    driver.switch_to.default_content() # Reset về main trước khi switch cái mới
                    driver.switch_to.frame(iframe)
                    
                    # Kiểm tra thử xem có input login không
                    for by_f, val_f in user_selectors:
                        # Chỉ check nhanh (timeout ngắn)
                        elem = find_element_safe(driver, by_f, val_f, timeout=1)
                        if elem:
                            print(f"✅ Đã tìm thấy Login Input trong Iframe thứ {index+1}")
                            found_input = True
                            break
                    
                    if found_input: break # Đã tìm thấy đúng iframe, giữ nguyên context ở đây
                    
                except Exception:
                    continue # Iframe lỗi hoặc chặn access, bỏ qua
            
            if not found_input:
                # Nếu quét hết vẫn không thấy, thử lại fallback cũ (iframe main-content)
                driver.switch_to.default_content()
                print("⚠️ Quét thất bại. Thử fallback selector cũ...")
                iframe_fallback = find_element_safe(driver, By.CSS_SELECTOR, ".main-content iframe")
                if iframe_fallback:
                    driver.switch_to.frame(iframe_fallback)

        # 5. ĐIỀN USERNAME (Context đã ở đúng chỗ sau luồng quét trên)
        print("-> Thực hiện điền Username...")
        # (Lặp lại logic điền an toàn)
        filled = False
        for by_u, val_u in user_selectors:
            if find_element_safe(driver, by_u, val_u, send_keys=user):
                filled = True
                break
                
        if not filled:
             print("❌ Vẫn không thể điền Username sau khi quét.")
             return False

        print(f"   Đã nhập: {user}")

        # 6. CLICK NÚT WEITER
        print("-> Nhấn nút Weiter...")
        # Priority: data-testid -> type=submit -> id
        if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-testid='login-submit']", click=True):
            if not find_element_safe(driver, By.CSS_SELECTOR, "button[type='submit']", click=True):
                 if not find_element_safe(driver, By.ID, "login-submit", click=True):
                     print("❌ Không tìm thấy nút Weiter.")
                     # return False # Có thể thử tiếp, ko return vội

        # 7. TÌM PASSWORD
        print("-> Đang điền Password...")
        # Priority: data-testid -> id -> name -> xpath
        if not find_element_safe(driver, By.CSS_SELECTOR, "input[data-testid='input-password']", timeout=10, send_keys=password):
            if not find_element_safe(driver, By.ID, "password", send_keys=password):
                if not find_element_safe(driver, By.NAME, "password", send_keys=password):
                    # Fallback XPath chung
                     if not find_element_safe(driver, By.XPATH, "//input[@type='password']", send_keys=password):
                         print("❌ Không tìm thấy input #password.")
                         return False
        print("   Đã nhập Password.")

        # 8. CLICK LOGIN LẦN CUỐI
        # Priority: data-testid -> type=submit
        if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-testid='login-submit']", click=True):
            find_element_safe(driver, By.CSS_SELECTOR, "button[type='submit']", click=True)
        print("-> Đã nhấn Login.")

        # 9. CHECK KẾT QUẢ
        driver.switch_to.default_content()
        print("-> Đang chờ chuyển trang...")
        
        for _ in range(20):
            if "navigator" in driver.current_url:
                print(f"✅ [PASS] Đăng nhập thành công! URL: {driver.current_url}")
                return True
            time.sleep(1)
            
        print("❌ [FAIL] Timeout: Không vào được trang navigator.")
        return False

    except Exception as e:
        print(f"❌ [FAIL] Lỗi Login: {e}")
        return False

# Code chạy thử nếu chạy file này trực tiếp
if __name__ == "__main__":
    driver = get_driver()
    try:
        login_process(driver, DEF_USER, DEF_PASS)
        # Giữ lại trình duyệt một chút để kịp nhìn thấy kết quả trước khi đóng (nếu muốn)
        # time.sleep(5) 
    except Exception:
        pass
    finally:
        # Chủ động đóng driver để tránh lỗi [WinError 6] trong __del__
        try:
            driver.quit()
        except OSError:
            pass  # Bỏ qua lỗi handle invalid nếu driver đã chết thực sự