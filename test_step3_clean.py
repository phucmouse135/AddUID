# FILE: test_step3_clean.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from gmx_core import get_driver, find_element_safe
from test_step1_login import USER, PASS 

def test_cleanup():
    driver = get_driver()
    action = ActionChains(driver)
    
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
    find_element_safe(driver, By.CLASS_NAME, "table_body")
    # ------------------------------

    print("--- START TEST STEP 3: CLEANUP ---")
    try:
        # Vòng lặp xóa an toàn
        while True:
            time.sleep(2) # Chờ bảng ổn định
            rows = driver.find_elements(By.CSS_SELECTOR, ".table_body .table_body-row")
            found_trash = False
            
            print(f"Đang quét {len(rows)} dòng...")

            for row in rows:
                try:
                    txt = row.text
                    if USER in txt:
                        print(f"-> Giữ lại: {USER}")
                        continue
                    
                    print(f"-> Phát hiện rác: {txt.splitlines()[0]}")
                    found_trash = True
                    
                    # Hover chuột vào dòng
                    action.move_to_element(row).perform()
                    time.sleep(0.5)
                    
                    # Tìm nút xóa trong dòng đó
                    trash_btn = row.find_element(By.CSS_SELECTOR, "a[title='E-Mail-Adresse löschen']")
                    trash_btn.click()
                    print("   Đã click xóa.")
                    
                    # GMX có thể hiện popup confirm hoặc tự reload.
                    # Nếu tự reload -> break loop để find_elements lại từ đầu
                    break 
                except Exception as e:
                    print(f"   Lỗi thao tác dòng: {e}")
                    continue

            if not found_trash:
                print("✅ [PASS] Đã sạch mail rác.")
                break

    except Exception as e:
        print(f"❌ [FAIL] Lỗi: {e}")

if __name__ == "__main__":
    test_cleanup()