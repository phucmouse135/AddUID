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
    try:
        # 1. NHẬP UID
        # Element bạn đưa: <input ... data-webdriver="localPart" ...>
        print(f"-> Nhập UID: {uid}")
        
        # Selector: input[data-webdriver='localPart']
        if not find_element_safe(driver, By.CSS_SELECTOR, "input[data-webdriver='localPart']", send_keys=uid):
            raise Exception("Không tìm thấy ô nhập UID")

        # 2. CHỌN ĐUÔI MAIL
        # Dropdown nằm cạnh input. Xpath bạn đưa: .../span[1]/select
        # Ta tìm thẻ <select> nằm trong cùng <fieldset> với input cho chắc
        print(f"-> Chọn Domain: {domain_full}")
        
        # Tìm thẻ select
        select_element = find_element_safe(driver, By.CSS_SELECTOR, "fieldset select")
        
        if select_element:
            select = Select(select_element)
            # Logic chọn: Duyệt qua options xem cái nào chứa text đuôi mail
            found = False
            domain_part = domain_full.replace("@", "") # Bỏ @ để so sánh lỏng
            
            for opt in select.options:
                # So sánh: ví dụ "gmx.de" nằm trong "@gmx.de"
                if domain_part in opt.text:
                    select.select_by_visible_text(opt.text)
                    print(f"   Đã chọn: {opt.text}")
                    found = True
                    break
            
            if not found:
                print("   ⚠️ Không tìm thấy đuôi chính xác, chọn mặc định cái đầu tiên.")
                select.select_by_index(0)
        else:
            print("⚠️ Không tìm thấy dropdown select.")

        # 3. NHẤN NÚT ADD
        # Element bạn đưa: <button ... data-webdriver="button">
        print("-> Nhấn nút Hinzufügen...")
        if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-webdriver='button']", click=True):
             raise Exception("Không tìm thấy nút Add.")

        # 4. CHECK KẾT QUẢ (Handle Exception Success/Fail)
        print("-> Đang kiểm tra kết quả...")
        time.sleep(3) # Chờ server phản hồi
        
        page_source = driver.page_source
        
        # Case Success: Thường có icon confirm hoặc text "erfolgreich"
        if "erfolgreich" in page_source or "theme-icon-confirm" in page_source:
            print(f"✅ [PASS] SUCCESS: Đã thêm thành công {uid}{domain_full}")
            return "SUCCESS"
            
        # Case Fail: "nicht verfügbar" hoặc icon warn
        elif "nicht verfügbar" in page_source or "theme-icon-warn" in page_source:
            print(f"⚠️ [PASS] EXIST: Mail {uid}{domain_full} đã được sử dụng (Đúng logic).")
            return "EXIST"
            
        else:
            # Fallback: Check lại trong bảng xem có dòng mới chưa
            if uid in page_source:
                 print(f"✅ [PASS] SUCCESS: Tìm thấy mail trong bảng.")
                 return "SUCCESS"
                 
            print("❓ [WARN] UNKNOWN: Không xác định được trạng thái.")
            return "UNKNOWN"

    except Exception as e:
        print(f"❌ [FAIL] Lỗi Step 4: {e}")
        return "ERROR"

if __name__ == "__main__":
    driver = get_driver()
    # Chạy full flow để test
    if login_process(driver, USER, PASS):
        if step_2_navigate(driver):
            step_4_add_alias(driver, NEW_UID, NEW_DOMAIN)