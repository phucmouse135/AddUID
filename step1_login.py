import time
from selenium.webdriver.common.by import By
from gmx_core import get_driver, find_element_safe

# --- DATA TEST ---
USER = "saucycut1@gmx.de"
PASS = "muledok5P"

def login_process(driver, user, password):
    driver = get_driver()
    try:
        print("--- START TEST STEP 1: LOGIN (PATH FIX) ---")
        
        # 1. Vào trang
        driver.get("https://www.gmx.net/")
        time.sleep(2)
        
        driver.get("https://www.gmx.net/")
        
        # 2. Xử lý Consent Cookie (Thường nó chặn trước khi hiện iframe login)
        print("-> Check Consent...")
        find_element_safe(driver, By.ID, "onetrust-accept-btn-handler", timeout=5, click=True)

        # 3. TÌM IFRAME THEO ĐƯỜNG DẪN BẠN CUNG CẤP
        print("-> Đang tìm Iframe theo path...")
        
        # Path cụ thể bạn đưa
        iframe_selector = "#app > div > div.main-content > div:nth-child(3) > section:nth-child(4) > div > iframe"
        
        # Thử tìm iframe bằng selector chính xác
        iframe_element = find_element_safe(driver, By.CSS_SELECTOR, iframe_selector)
        
        # Fallback: Nếu cấu trúc web thay đổi (ví dụ có thêm banner quảng cáo làm lệch nth-child)
        # Ta tìm iframe dựa trên class cha 'main-content' cho an toàn
        if not iframe_element:
            print("⚠️ Path chính xác không thấy, thử tìm iframe trong main-content...")
            iframe_element = find_element_safe(driver, By.CSS_SELECTOR, ".main-content iframe")

        if not iframe_element:
            raise Exception("Không tìm thấy Iframe Login (iframe).")

        # 4. SWITCH VÀO IFRAME
        driver.switch_to.frame(iframe_element)
        print("   Đã Switch vào bên trong Iframe.")

        # 5. TÌM USERNAME (Bên trong iframe)
        # Giờ ta đang ở trong iframe, tìm trực tiếp #login #username
        print("-> Đang điền Username...")
        
        # input#username nằm trong form#login
        # Ta dùng CSS selector: #login input#username hoặc input[name='username']
        if not find_element_safe(driver, By.CSS_SELECTOR, "#login #username", send_keys=user):
            # Fallback nếu ID username đổi
            if not find_element_safe(driver, By.NAME, "username", send_keys=user):
                 raise Exception("Không tìm thấy input #username trong iframe.")
        
        print(f"   Đã nhập: {user}")

        # 6. CLICK NÚT WEITER (Tiếp tục)
        # Tìm nút button trong form #login
        find_element_safe(driver, By.CSS_SELECTOR, "#login button[type='submit']", click=True)
        print("-> Đã nhấn Weiter.")

        # 7. TÌM PASSWORD
        print("-> Đang điền Password...")
        # Chờ input password hiện ra (thường mất 1s animation)
        # Selector: #login input#password
        if not find_element_safe(driver, By.CSS_SELECTOR, "#login #password", timeout=10, send_keys=password):
             raise Exception("Không tìm thấy input #password.")
        
        print("   Đã nhập Password.")

        # 8. CLICK LOGIN LẦN CUỐI
        find_element_safe(driver, By.CSS_SELECTOR, "#login button[type='submit']", click=True)
        print("-> Đã nhấn Login.")

        # 9. CHECK KẾT QUẢ
        # Sau khi login, trang sẽ reload lại main page -> cần thoát khỏi iframe
        driver.switch_to.default_content()
        
        print("-> Đang chờ chuyển trang...")
        for _ in range(20):
            if "navigator" in driver.current_url:
                print(f"✅ [PASS] Đăng nhập thành công! URL: {driver.current_url}")
                return
            
            # Check lỗi hiển thị (phải switch lại iframe nếu muốn check text lỗi bên trong, 
            # nhưng thường GMX reload lại trang nếu sai pass)
            time.sleep(1)
            
        print("❌ [FAIL] Timeout: Không vào được trang navigator.")

    except Exception as e:
        print(f"❌ [FAIL] Lỗi: {e}")
        # Chụp màn hình để debug nếu lỗi
        driver.save_screenshot("debug_error.png")

if __name__ == "__main__":
    login_process(get_driver(), USER, PASS)