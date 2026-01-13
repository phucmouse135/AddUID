# FILE: test_step3_clean.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from gmx_core import get_driver, find_element_safe, reload_if_ad_popup
from step1_login import login_process
from test_step2_nav import step_2_navigate

USER = "saucycut1@gmx.de"
PASS = "muledok5P"
EMAIL_TO_ADD = "nubily@gmx.de"

def step_3_cleanup(driver, original_email, email_to_add):
    print("\n--- START TEST STEP 3: CLEANUP EMAILS ---")
    action = ActionChains(driver)
    target_email = (email_to_add or "").strip()
    target_email_lower = target_email.lower()
    
    try:
        if reload_if_ad_popup(driver):
            print("?? Ad popup detected. Reloaded to GMX home.")
            return

        # Loop "Scan -> Delete -> Re-scan" to avoid DOM errors
        while True:
            if reload_if_ad_popup(driver):
                print("?? Ad popup detected. Reloaded to GMX home.")
                return

            time.sleep(2) # Wait for table stability
            
            # Find all rows in table
            # Selector: .table_body .table_body-row
            rows = driver.find_elements(By.CSS_SELECTOR, ".table_body .table_body-row")
            
            print(f"-> Scanning {len(rows)} rows...")
            found_trash = False

            if target_email_lower:
                for row in rows:
                    try:
                        try:
                            email_text = row.find_element(By.CSS_SELECTOR, ".table_field strong").text.strip()
                        except:
                            email_text = row.text.strip() # Fallback get full row text

                        if target_email_lower in email_text.lower():
                            print(f"? [PASS] STEP 3: {target_email} already exists. Skip cleanup/add.")
                            return "EXIST"
                    except Exception as e:
                        print(f"   Row read error (maybe DOM changed): {e}")
                        continue

                # Refresh rows to avoid stale elements after pre-scan
                rows = driver.find_elements(By.CSS_SELECTOR, ".table_body .table_body-row")
            
            for row in rows:
                try:
                    # Get text in row. Structure: .table_field strong
                    # <div class="table_field ..."> <strong> saucycut1@gmx.de </strong> ... </div>
                    try:
                        email_text = row.find_element(By.CSS_SELECTOR, ".table_field strong").text.strip()
                    except:
                        email_text = row.text.strip() # Fallback get full row text
                    
                    if original_email in email_text:
                        # This is original mail -> Skip
                        continue
                    
                    
                    
                    # If reaches here, it's Trash Mail
                    print(f"-> Detected trash: {email_text}")
                    found_trash = True
                    
                    # 1. MOUSE HOVER (Required to show delete button)
                    action.move_to_element(row).perform()
                    time.sleep(0.5)
                    
                    # 2. CLICK DELETE BUTTON
                    # Delete button selector: a[title='E-Mail-Adresse löschen']
                    # Ta tìm nút này *bên trong* dòng row hiện tại
                    trash_btn = row.find_element(By.CSS_SELECTOR, "a[title='E-Mail-Adresse löschen']")
                    trash_btn.click()
                    print("   Đã click nút xóa.")
                    
                    # 3. XỬ LÝ POPUP XÁC NHẬN (MỚI)
                    # Chờ và click nút OK
                    print("   Đang chờ Popup xác nhận...")
                    # Selector: button data-webdriver="primary" HOẶC nút chứa chữ "OK"
                    if find_element_safe(driver, By.CSS_SELECTOR, "button[data-webdriver='primary']", timeout=5, click=True):
                        print("   -> Đã Confirm OK.")
                    elif find_element_safe(driver, By.XPATH, "//button[contains(text(), 'OK')]", timeout=3, click=True):
                        print("   -> Đã Confirm OK (backup).")
                    else:
                        print("   ⚠️ Không thấy Popup confirm (Có thể đã tự tắt?).")

                    # Sau khi xóa, bảng sẽ reload. Break vòng lặp for để scan lại từ đầu
                    break 
                    
                except Exception as e:
                    print(f"   Lỗi thao tác dòng (có thể do DOM đổi): {e}")
                    continue # Thử dòng tiếp theo

            if not found_trash:
                print("✅ [PASS] STEP 3: Đã sạch mail rác. Chỉ còn mail gốc.")
                break

    except Exception as e:
        print(f"❌ [FAIL] Lỗi Step 3: {e}")

if __name__ == "__main__":
    driver = get_driver()
    if login_process(driver, USER, PASS):
        if step_2_navigate(driver):
            step_3_cleanup(driver, USER, EMAIL_TO_ADD)
