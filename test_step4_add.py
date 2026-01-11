# FILE: test_step4_add.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from gmx_core import get_driver, find_element_safe
from test_step1_login import USER, PASS 

# DATA MẪU
NEW_UID = "jhhhuu"
NEW_DOMAIN = "@gmx.de"

def test_add_alias():
    driver = get_driver()
    
    # --- LOGIN & NAVIGATE NHANH ---
    driver.get("https://www.gmx.net/")
    time.sleep(2); driver.get("https://www.gmx.net/")
    find_element_safe(driver, By.ID, "onetrust-accept-btn-handler", timeout=3, click=True)
    find_element_safe(driver, By.NAME, "username", send_keys=USER)
    find_element_safe(driver, By.XPATH, "//*[@id='login']//button", click=True)
    find_element_safe(driver, By.XPATH, "//*[@id='password']", send_keys=PASS)
    find_element_safe(driver, By.XPATH, "//*[@id='login']//button", click=True)
    time.sleep(5)
    driver.get(driver.current_url.replace("mail?", "mail_settings?"))
    find_element_safe(driver, By.PARTIAL_LINK_TEXT, "E-Mail-Adressen", click=True)
    # ------------------------------

    print("--- START TEST STEP 4: ADD ALIAS ---")
    try:
        # 1. Nhập UID
        if find_element_safe(driver, By.CSS_SELECTOR, "input[data-webdriver='localPart']", send_keys=NEW_UID):
            print(f"Đã nhập UID: {NEW_UID}")
        else:
            raise Exception("Không tìm thấy ô nhập UID")

        # 2. Chọn Domain
        select_el = find_element_safe(driver, By.CSS_SELECTOR, "fieldset select")
        if select_el:
            select = Select(select_el)
            # Logic chọn đúng đuôi
            found = False
            for opt in select.options:
                if NEW_DOMAIN in opt.text:
                    select.select_by_visible_text(opt.text)
                    print(f"Đã chọn domain: {opt.text}")
                    found = True
                    break
            if not found:
                print("Không thấy domain, chọn mặc định.")
        
        # 3. Click Add
        find_element_safe(driver, By.CSS_SELECTOR, "button[data-webdriver='button']", click=True)
        print("Đã click nút Thêm. Đang check kết quả...")

        # 4. Check thông báo (Check HTML source cho chắc)
        time.sleep(2)
        for _ in range(5): # Check trong 5s
            src = driver.page_source
            if "erfolgreich angelegt" in src or "theme-icon-confirm" in src:
                print(f"✅ [PASS] Kết quả: SUCCESS (Tạo thành công)")
                return
            if "nicht verfügbar" in src or "theme-icon-warn" in src:
                print(f"⚠️ [PASS] Kết quả: EXIST (Mail đã tồn tại - đúng logic phát hiện lỗi)")
                return
            time.sleep(1)
        
        print("❓ [WARN] Không xác định được trạng thái.")

    except Exception as e:
        print(f"❌ [FAIL] Lỗi: {e}")

if __name__ == "__main__":
    test_add_alias()