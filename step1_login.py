# FILE: step1_login.py
import time
from selenium.webdriver.common.by import By
from gmx_core import get_driver, find_element_safe

# --- DATA TEST DEFAULT ---
DEF_USER = "saucycut1@gmx.de"
DEF_PASS = "muledok5P"

def login_process(driver, user, password):
    """
    Standard Login Function.
    Returns True if login success, False if failed.
    """
    try:
        print(f"--- START LOGIN PROCESS: {user} ---")
        
        # 1. Enter site
        driver.get("https://www.gmx.net/")
        time.sleep(2)
        driver.get("https://www.gmx.net/") # Reload
        
        # 2. Handle Consent
        print("-> Check Consent...")
        find_element_safe(driver, By.ID, "onetrust-accept-btn-handler", timeout=5, click=True)

        # 3. LOGIC FIND LOGIN FORM (AUTO-SCAN)
        print("-> Scanning for Login Form (Main or Iframe)...")
        
        # List of potential selectors for username
        user_selectors = [
            (By.CSS_SELECTOR, "input[data-testid='input-email']"),
            (By.NAME, "username"),
            (By.ID, "username"), 
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.XPATH, "//input[@autocomplete='username']")
        ]

        found_input = False
        
        # 3.1. Check Main Content
        for by_m, val_m in user_selectors:
            if find_element_safe(driver, by_m, val_m, timeout=1):
                print(f"✅ Found Login Input in Main Content ({val_m})")
                found_input = True
                break
        
        # 3.2. If not found, scan Iframes
        if not found_input:
            print("   Not found in Main, scanning Iframes...")
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"   Found {len(iframes)} iframes.")
            
            for index, iframe in enumerate(iframes):
                try:
                    driver.switch_to.default_content() # Reset to main before switch
                    driver.switch_to.frame(iframe)
                    
                    # Check for login input
                    for by_f, val_f in user_selectors:
                        # Quick check (short timeout)
                        elem = find_element_safe(driver, by_f, val_f, timeout=1)
                        if elem:
                            print(f"✅ Found Login Input in Iframe #{index+1}")
                            found_input = True
                            break
                    
                    if found_input: break # Found correct iframe, stay in this context
                    
                except Exception:
                    continue # Iframe error or blocked, skip
            
            if not found_input:
                # If scan fails, try old fallback (main-content iframe)
                driver.switch_to.default_content()
                print("⚠️ Scan failed. Trying fallback selector...")
                iframe_fallback = find_element_safe(driver, By.CSS_SELECTOR, ".main-content iframe")
                if iframe_fallback:
                    driver.switch_to.frame(iframe_fallback)

        # 5. ENTER USERNAME (Context is correct after scan)
        print("-> Entering Username...")
        # (Retry safe fill logic)
        filled = False
        for by_u, val_u in user_selectors:
            if find_element_safe(driver, by_u, val_u, send_keys=user):
                filled = True
                break
                
        if not filled:
             print("❌ Still cannot enter Username after scan.")
             return False

        print(f"   Entered: {user}")

        # 6. CLICK NEXT/WEITER
        print("-> Clicking Next/Weiter...")
        # Priority: data-testid -> type=submit -> id
        if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-testid='login-submit']", click=True):
            if not find_element_safe(driver, By.CSS_SELECTOR, "button[type='submit']", click=True):
                 if not find_element_safe(driver, By.ID, "login-submit", click=True):
                     print("❌ Next button not found.")
                     # return False # Try continuing

        # 7. ENTER PASSWORD
        print("-> Entering Password...")
        # Priority: data-testid -> id -> name -> xpath
        if not find_element_safe(driver, By.CSS_SELECTOR, "input[data-testid='input-password']", timeout=10, send_keys=password):
            if not find_element_safe(driver, By.ID, "password", send_keys=password):
                if not find_element_safe(driver, By.NAME, "password", send_keys=password):
                    # Fallback XPath
                     if not find_element_safe(driver, By.XPATH, "//input[@type='password']", send_keys=password):
                         print("❌ Password input not found.")
                         return False
        print("   Password entered.")

        # 8. CLICK LOGIN FINAL
        # Priority: data-testid -> type=submit
        if not find_element_safe(driver, By.CSS_SELECTOR, "button[data-testid='login-submit']", click=True):
            find_element_safe(driver, By.CSS_SELECTOR, "button[type='submit']", click=True)
        print("-> Clicked Login.")

        # 9. CHECK RESULT
        driver.switch_to.default_content()
        print("-> Waiting for redirection...")
        
        for _ in range(20):
            if "navigator" in driver.current_url:
                print(f"✅ [PASS] Login Success! URL: {driver.current_url}")
                return True
            time.sleep(1)
            
        print("❌ [FAIL] Timeout: Did not reach navigator page.")
        return False

    except Exception as e:
        print(f"❌ [FAIL] Login Error: {e}")
        return False

# Test run if file executed directly
if __name__ == "__main__":
    import os
    INPUT_TEST = "input.txt"
    
    if os.path.exists(INPUT_TEST):
        print(f"--- BULK TEST MODE: Reading {INPUT_TEST} ---")

        output_path = "output.txt"
        try:
            with open(INPUT_TEST, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Skip header if present
            start_line = 0
            if len(lines) > 0 and "UID" in lines[0]:
                start_line = 1
            # Prepare output file (overwrite)
            with open(output_path, "w", encoding="utf-8") as fout:
                fout.write("uid\tresult\n")
                for idx, line in enumerate(lines[start_line:]):
                    line = line.strip()
                    if not line: continue
                    parts = line.split('\t')
                    if len(parts) < 2: parts = line.split()
                    # Assume Format: ... [User Col 5] [Pass Col 6]
                    if len(parts) >= 7:
                        t_uid = parts[0]
                        t_user = parts[5]
                        t_pass = parts[6]
                        print(f"\n[{idx+1}] Testing Account: {t_user}")
                        driver = get_driver(headless=False)
                        try:
                            login_success = login_process(driver, t_user, t_pass)
                            print(f"Result {t_user}: {'OK' if login_success else 'FAIL'}")
                            fout.write(f"{t_uid}\t{'success' if login_success else 'fail'}\n")
                        except Exception as e:
                            print(f"Error {t_user}: {e}")
                            fout.write(f"{t_uid}\tfail\n")
                        finally:
                            try: driver.quit()
                            except: pass
                    else:
                        print(f"Skipping invalid line: {line}")
        except Exception as e:
            print(f"File read error: {e}")
            
    else:
        print("--- SINGLE TEST DEFAULT ---")
        driver = get_driver()
        try:
            login_process(driver, DEF_USER, DEF_PASS)
        except Exception:
            pass
        finally:
            try: driver.quit()
            except: pass