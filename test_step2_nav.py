# FILE: test_step2_nav.py
import time
from selenium.webdriver.common.by import By
from gmx_core import get_driver, find_element_safe
from step1_login import login_process

# --- DATA TEST ---
USER = "saucycut1@gmx.de"
PASS = "muledok5P"

def step_2_navigate(driver):
    print("\n--- START TEST STEP 2: NAVIGATE SETTINGS ---")
    try:
        # 1. Trick đổi URL: mail -> mail_settings
        current_url = driver.current_url
        print(f"-> URL hiện tại: {current_url}")
        if "mail?" in current_url:
            target_url = current_url.replace("mail?", "mail_settings?")
            driver.get(target_url)
            print(f"-> Đã chuyển hướng sang: {target_url}")
            time.sleep(3) # Chờ page settings load hẳn
        else:
            print("⚠️ URL không chứa 'mail?', cố gắng tìm menu thủ công.")

        # --- LOGIC TÌM MENUS (TINH GỌN & IM LẶNG) ---
        print("-> Đang quét tìm menu 'E-Mail-Adressen' (ẩn lỗi)...")
        
        target_element = None
        
        # Danh sách XPATH cần thử (theo thứ tự ưu tiên)
        search_xpaths = [
            "//a[.//span[contains(text(), 'E-Mail-Adressen')]]",     # 1. Theo Text hiển thị (Chuẩn nhất)
            "//a[@data-webdriver='ALL_EMAIL_ADDRESSES']",            # 2. Theo Attribute ẩn
            "//a[contains(@href, 'allEmailAddresses')]"              # 3. Theo Link
        ]

        def scan_current_frame_silent():
            """Hàm tìm nhanh trả về element đầu tiên thấy, không in lỗi"""
            for xpath in search_xpaths:
                elems = driver.find_elements(By.XPATH, xpath)
                if elems:
                    return elems[0]
            return None

        # A. Check Main Frame
        target_element = scan_current_frame_silent()
        
        # B. Check Iframes (Nếu Main Frame không có)
        if not target_element:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            # print(f"   (Đang quét {len(iframes)} iframes...)")
            
            for index, frame in enumerate(iframes):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    target_element = scan_current_frame_silent()
                    if target_element:
                        print(f"   ✅ Tìm thấy Menu trong Iframe #{index}")
                        break
                except:
                    continue
        
        if not target_element:
             driver.switch_to.default_content()
             raise Exception("Ngõ cụt: Không tìm thấy menu E-Mail-Adressen (Đã check Main & Iframes).")

        # --- THỰC HIỆN HÀNH ĐỘNG ---
        # Ưu tiên lấy HREF để đi tắt (nhanh & không bị che)
        href = target_element.get_attribute("href")
        if href:
            print(f"   => Lấy được Link: {href}")
            driver.get(href)
        else:
            print("   => Không có Link, dùng JS Click.")
            driver.execute_script("arguments[0].click();", target_element)

        # 3. Chờ bảng load

        # 3. Chờ bảng load
        print("-> Chờ bảng dữ liệu load (Timeout 15s)...")
        # Selector dựa trên user provide: div.table_body
        table = find_element_safe(driver, By.CSS_SELECTOR, ".table_body", timeout=15)
        print("-> Kiểm tra kết quả...", table)
        if table:
            print("✅ [PASS] STEP 2: Đã vào danh sách Email.")
            return True
        else:
            print("❌ [FAIL] STEP 2: Không thấy bảng dữ liệu (.table_body).")
            return False

    except Exception as e:
        print(f"❌ [FAIL] Lỗi Step 2: {e}")
        return False

if __name__ == "__main__":
    # PATCH: Tắt lỗi __del__ khó chịu của undetected_chromedriver trên Windows
    import undetected_chromedriver as uc
    def _del_patch(self):
        try:
            self.quit()
        except Exception:
            pass
    uc.Chrome.__del__ = _del_patch

    driver = get_driver()
    try:
        if login_process(driver, USER, PASS):
            step_2_navigate(driver)
    except Exception:
        pass
    finally:
        try:
            driver.quit()
        except Exception:
            pass