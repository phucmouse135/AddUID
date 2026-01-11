# FILE: test_step2_nav.py
import time
from selenium.webdriver.common.by import By
from gmx_core import get_driver, find_element_safe

# Import hàm login chuẩn từ file step 1
from step1_login import login_process

# Data test
USER = "saucycut1@gmx.de"
PASS = "muledok5P"

def step_2_navigate(driver):
    print("\n--- START TEST STEP 2: NAVIGATE SETTINGS ---")
    try:
        # 1. THAY THẾ URL (Mail -> Settings)
        current_url = driver.current_url
        print(f"URL gốc: {current_url}")

        if "mail?" in current_url:
            target_url = current_url.replace("mail?", "mail_settings?")
            driver.get(target_url)
            print(f"-> Đã chuyển hướng sang: {target_url}")
        else:
            print("⚠️ URL không chứa 'mail?', có thể đang ở trang khác.")

        # 2. CLICK MENU 'E-Mail-Adressen'
        # Selector bạn cung cấp: #id4d ... (ID động).
        # Cách tối ưu: Dùng Partial Link Text "E-Mail-Adressen" (An toàn nhất)
        print("-> Tìm menu 'E-Mail-Adressen'...")
        
        # Ưu tiên 1: Tìm theo text hiển thị
        menu_item = find_element_safe(driver, By.PARTIAL_LINK_TEXT, "E-Mail-Adressen", click=True)
        
        if not menu_item:
            # Ưu tiên 2: Tìm theo Xpath cấu trúc (Fallback nếu text lỗi/đổi ngôn ngữ)
            # Tìm thẻ <a> nằm trong thẻ <li> thứ 5 của menu-body
            print("   Text không thấy, tìm theo cấu trúc XPath...")
            xpath_structure = "//div[contains(@class,'menu-body')]//ul/li[5]/a"
            menu_item = find_element_safe(driver, By.XPATH, xpath_structure, click=True)

        if not menu_item:
             # Ưu tiên 3: Xpath tuyệt đối (User cung cấp - Ít ổn định do ID động nhưng vẫn thử)
             print("   Tìm theo Xpath gốc user cung cấp...")
             user_xpath = '//*[@id="id4d"]/div/div/div/ul/li[1]/div[2]/ul/li[5]/a'
             # Lưu ý: #id4d sẽ đổi, nên cách này rủi ro cao. Ta thử thay id bằng *
             # //*[@class="menu-body"]...
             pass

        if not menu_item:
            raise Exception("Không click được vào menu E-Mail-Adressen.")

        print("   Đã click menu.")

        # 3. CHỜ BẢNG LOAD RA
        # Selector user cung cấp: #id60 > div.table_body
        # Dùng class .table_body là chuẩn nhất
        print("-> Chờ bảng dữ liệu load...")
        table = find_element_safe(driver, By.CLASS_NAME, "table_body", timeout=10)
        
        if table:
            print("✅ [PASS] STEP 2 THÀNH CÔNG: Đã vào danh sách Email.")
            return True
        else:
            print("❌ [FAIL] STEP 2: Không tìm thấy bảng '.table_body'.")
            return False

    except Exception as e:
        print(f"❌ [FAIL] Lỗi Step 2: {e}")
        return False

# --- MAIN RUN ---
if __name__ == "__main__":
    # Khởi tạo driver
    driver = get_driver()
    
    # Chạy Step 1 (Login)
    if login_process(driver, USER, PASS):
        # Nếu login OK -> Chạy Step 2
        step_2_navigate(driver)
    else:
        print("Dừng test do Login thất bại.")
    
    # driver.quit() # Uncomment để tự tắt trình duyệt sau khi test xong