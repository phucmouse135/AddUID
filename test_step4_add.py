# FILE: test_step4_add.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from gmx_core import get_driver, find_element_safe, reload_if_ad_popup
from step1_login import login_process
from test_step2_nav import step_2_navigate

# LOG TEST DATA
USER = "saucycut1@gmx.de"
PASS = "muledok5P"
NEW_UID = "nubily"
NEW_DOMAIN = "@gmx.de" # Or gmx.net depending on data

def step_4_add_alias(driver, uid, domain_full):
    print("\n--- START TEST STEP 4: ADD NEW ALIAS ---")
    
    # Retry Loop: 3 Times
    for attempt in range(1, 4):
        if reload_if_ad_popup(driver):
            print("?? Ad popup detected. Reloaded to GMX home.")
            return "ERROR"

        try:
            if attempt > 1:
                print(f"🔄 [RETRY] Attempt {attempt}/3: Refreshing page...")
                driver.refresh()
                time.sleep(3)

            # 1. ENTER UID
            print(f"-> Enter UID (Attempt {attempt}): {uid}")
            if not find_element_safe(driver, By.CSS_SELECTOR, "input[data-webdriver='localPart']", send_keys=uid):
                # If input not found, load error -> Raise to trigger retry
                raise Exception("UID Input not found")

            # 2. SELECT DOMAIN
            print(f"-> Select Domain: {domain_full}")
            select_element = find_element_safe(driver, By.CSS_SELECTOR, "fieldset select")
            
            if select_element:
                select = Select(select_element)
                found = False
                domain_part = domain_full.replace("@", "") 
                
                for opt in select.options:
                    if domain_part in opt.text:
                        select.select_by_visible_text(opt.text)
                        print(f"   Selected: {opt.text}")
                        found = True
                        break
                
                if not found:
                    print("   ⚠️ Exact domain not found, selecting default first option.")
                    select.select_by_index(0)
            else:
                # Missing select might not be fatal, try continuing
                print("⚠️ Dropdown select not found.")

            # 3. CLICK ADD BUTTON
            print("-> Clicking Add Button...")
            if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-webdriver='button']", click=True):
                 raise Exception("Add Button not found.")

            # 4. CHECK RESULT
            print("-> Checking result...")
            time.sleep(3) # Wait for server response

            def _has_icon(selector):
                try:
                    return len(driver.find_elements(By.CSS_SELECTOR, selector)) > 0
                except Exception:
                    return False

            result = None
            end_time = time.time() + 6
            while time.time() < end_time:
                page_source = driver.page_source
                page_lower = page_source.lower()

                warn_icon = _has_icon(".theme-icon-warn")
                ok_icon = _has_icon(".theme-icon-confirm")

                if warn_icon or "theme-icon-warn" in page_lower or "nicht verf" in page_lower:
                    result = "EXIST"
                    break

                if ok_icon or "theme-icon-confirm" in page_lower or "erfolgreich" in page_lower:
                    result = "SUCCESS"
                    break

                time.sleep(0.5)

            if result == "SUCCESS":
                print(f"? [PASS] SUCCESS: Successfully added {uid}{domain_full}")
                return "SUCCESS"

            if result == "EXIST":
                print(f"?? [PASS] EXIST: Mail {uid}{domain_full} is already used.")
                return "EXIST"

            print(f"? [WARN] UNKNOWN: Cannot determine status (Attempt {attempt}).")
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