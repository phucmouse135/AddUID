# FILE: test_step4_add.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from gmx_core import get_driver, find_element_safe
from step1_login import login_process
from test_step2_nav import step_2_navigate

# DATA TEST
USER = "saucycut1@gmx.de"
PASS = "muledok5P"
NEW_UID = "nubily"
NEW_DOMAIN = "@gmx.de" # Hoặc gmx.net tùy data

def step_4_add_alias(driver, uid, domain_full):
    print("\n--- START TEST STEP 4: ADD NEW ALIAS ---")
    
    # Retry Loop: 3 Times
    for attempt in range(1, 4):
        try:
            if attempt > 1:
                print(f"🔄 [RETRY] Lần {attempt}/3: Refreshing page...")
                driver.refresh()
                time.sleep(3)

            # 1. NHẬP UID
            print(f"-> Nhập UID (Attempt {attempt}): {uid}")
            if not find_element_safe(driver, By.CSS_SELECTOR, "input[data-webdriver='localPart']", send_keys=uid):
                # Nếu không thấy input, có thể do lỗi load trang -> Raise để trigger retry
                raise Exception("Không tìm thấy ô nhập UID")

            # 2. CHỌN ĐUÔI MAIL
            print(f"-> Chọn Domain: {domain_full}")
            select_element = find_element_safe(driver, By.CSS_SELECTOR, "fieldset select")
            
            if select_element:
                select = Select(select_element)
                found = False
                domain_part = domain_full.replace("@", "") 
                
                for opt in select.options:
                    if domain_part in opt.text:
                        select.select_by_visible_text(opt.text)
                        print(f"   Đã chọn: {opt.text}")
                        found = True
                        break
                
                if not found:
                    print("   ⚠️ Không tìm thấy đuôi chính xác, chọn mặc định cái đầu tiên.")
                    select.select_by_index(0)
            else:
                # Không thấy select chưa chắc đã chết, cứ thử tiếp
                print("⚠️ Không tìm thấy dropdown select.")

            # 3. NHẤN NÚT ADD
            print("-> Nhấn nút Hinzufügen...")
            if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-webdriver='button']", click=True):
                 raise Exception("Không tìm thấy nút Add.")

            # 4. CHECK KẾT QUẢ
            print("-> Đang kiểm tra kết quả...")
            time.sleep(3) # Chờ server phản hồi
            
            page_source = driver.page_source
            
            # Case Success
            if "erfolgreich" in page_source or "theme-icon-confirm" in page_source:
                print(f"✅ [PASS] SUCCESS: Đã thêm thành công {uid}{domain_full}")
                return "SUCCESS"
                
            # Case Fail: "nicht verfügbar"
            elif "nicht verfügbar" in page_source or "theme-icon-warn" in page_source:
                print(f"⚠️ [PASS] EXIST: Mail {uid}{domain_full} đã được sử dụng.")
                return "EXIST"
            
            # Fallback
            if uid in page_source:
                 print(f"✅ [PASS] SUCCESS: Tìm thấy mail trong bảng.")
                 return "SUCCESS"

            print(f"❓ [WARN] UNKNOWN: Không xác định được trạng thái (Attempt {attempt}).")
            # Không return, để loop chạy lại

        except Exception as e:
            print(f"❌ [FAIL] Lỗi Step 4 (Attempt {attempt}): {e}")
            # Loop tiếp tục

    return "ERROR"

if __name__ == "__main__":
    driver = get_driver()
    # Chạy full flow để test
    if login_process(driver, USER, PASS):
        if step_2_navigate(driver):
            step_4_add_alias(driver, NEW_UID, NEW_DOMAIN)