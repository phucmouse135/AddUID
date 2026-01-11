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

        # 3. TÌM IFRAME THEO ĐƯỜNG DẪN BẠN CUNG CẤP
        print("-> Đang tìm Iframe theo path...")
        iframe_selector = "#app > div > div.main-content > div:nth-child(3) > section:nth-child(4) > div > iframe"
        iframe_element = find_element_safe(driver, By.CSS_SELECTOR, iframe_selector)
        
        if not iframe_element:
            print("⚠️ Path chính xác không thấy, thử tìm iframe trong main-content...")
            iframe_element = find_element_safe(driver, By.CSS_SELECTOR, ".main-content iframe")

        if not iframe_element:
            print("❌ Không tìm thấy Iframe Login.")
            return False

        # 4. SWITCH VÀO IFRAME
        driver.switch_to.frame(iframe_element)
        print("   Đã Switch vào bên trong Iframe.")

        # 5. TÌM USERNAME
        print("-> Đang điền Username...")
        if not find_element_safe(driver, By.CSS_SELECTOR, "#login #username", send_keys=user):
            if not find_element_safe(driver, By.NAME, "username", send_keys=user):
                 print("❌ Không tìm thấy input #username.")
                 return False
        print(f"   Đã nhập: {user}")

        # 6. CLICK NÚT WEITER
        find_element_safe(driver, By.CSS_SELECTOR, "#login button[type='submit']", click=True)
        print("-> Đã nhấn Weiter.")

        # 7. TÌM PASSWORD
        print("-> Đang điền Password...")
        if not find_element_safe(driver, By.CSS_SELECTOR, "#login #password", timeout=10, send_keys=password):
             print("❌ Không tìm thấy input #password.")
             return False
        print("   Đã nhập Password.")

        # 8. CLICK LOGIN LẦN CUỐI
        find_element_safe(driver, By.CSS_SELECTOR, "#login button[type='submit']", click=True)
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