import time
import re
import sys
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

# --- CẤU HÌNH ---
TIMEOUT_DEFAULT = 15  # Thời gian chờ tối đa cho các element

class GMXAutomation:
    def __init__(self):
        # Cấu hình Chrome tối ưu
        options = uc.ChromeOptions()
        # options.add_argument('--headless') # Bật dòng này nếu muốn chạy ẩn (không hiện trình duyệt)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        # Tắt load ảnh để chạy nhanh hơn
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        
        print("[INFO] Đang khởi động trình duyệt...")
        self.driver = uc.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, TIMEOUT_DEFAULT)
        self.action = ActionChains(self.driver)

    def log(self, msg, type="INFO"):
        print(f"[{type}] {msg}")

    def close(self):
        self.driver.quit()

    def check_exists_by_xpath(self, xpath):
        try:
            self.driver.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False

    def handle_login(self, email, password):
        try:
            self.log(f"Bắt đầu đăng nhập: {email}")
            
            # Bước 1: Truy cập và reload chống quảng cáo
            self.driver.get("https://www.gmx.net/")
            time.sleep(3)
            self.driver.get("https://www.gmx.net/")
            
            # Xử lý Cookie Consent (thường gặp ở GMX) nếu có
            try:
                cookie_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                cookie_btn.click()
            except:
                pass

            # Bước 2: Nhập Email
            # Sử dụng data-testid hoặc name sẽ ổn định hơn ID động
            email_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            email_input.clear()
            email_input.send_keys(email)
            
            # Click nút login đầu tiên
            login_btn_1 = self.driver.find_element(By.XPATH, "//*[@id='login']//button")
            login_btn_1.click()

            # Bước 3: Nhập Password (chờ element xuất hiện)
            pass_input = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='password']")))
            pass_input.send_keys(password)

            # Click nút login thứ 2
            login_btn_2 = self.driver.find_element(By.XPATH, "//*[@id='login']//button")
            login_btn_2.click()

            # Chờ vào giao diện mail (check URL hoặc element đặc trưng)
            self.wait.until(EC.url_contains("navigator"))
            self.log("Đăng nhập thành công.")
            return True

        except TimeoutException:
            self.log("Timeout: Không thể đăng nhập hoặc load trang quá lâu.", "ERROR")
            return False
        except Exception as e:
            self.log(f"Lỗi đăng nhập: {str(e)}", "ERROR")
            return False

    def navigate_to_settings(self):
        try:
            current_url = self.driver.current_url
            if "mail?" in current_url:
                new_url = current_url.replace("mail?", "mail_settings?")
                self.driver.get(new_url)
                self.log("Đã chuyển sang trang Settings.")
            else:
                self.log("URL không đúng định dạng mong đợi, cố gắng tìm menu thủ công.", "WARN")
                # Fallback nếu URL không khớp
                return False

            # Vào mục E-Mail-Adresse
            # Selector này khá dài, nên dùng text contains để an toàn hơn
            try:
                menu_item = self.wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "E-Mail-Adressen")))
                menu_item.click()
            except:
                # Fallback theo xpath người dùng cung cấp nếu tìm theo tên thất bại
                self.driver.find_element(By.XPATH, "//*[@id='id4d']//li[5]/a").click()
            
            # Chờ bảng load xong
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table_body")))
            return True
        except Exception as e:
            self.log(f"Lỗi điều hướng settings: {str(e)}", "ERROR")
            return False

    def cleanup_emails(self, original_email):
        try:
            self.log("Đang kiểm tra danh sách email...")
            # Lấy danh sách các dòng trong bảng
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".table_body .table_body-row")
            
            # Duyệt ngược từ dưới lên để tránh lỗi index khi DOM thay đổi sau khi xóa
            for i in range(len(rows) - 1, -1, -1):
                # Refresh lại list rows để tránh StaleElementReferenceException
                rows = self.driver.find_elements(By.CSS_SELECTOR, ".table_body .table_body-row")
                row = rows[i]
                
                try:
                    email_text = row.find_element(By.CSS_SELECTOR, ".table_field strong").text.strip()
                except:
                    email_text = row.text.strip() # Fallback

                if original_email in email_text:
                    self.log(f"Giữ lại email gốc: {email_text}")
                    continue
                else:
                    self.log(f"Phát hiện email rác: {email_text}. Đang xóa...")
                    # Hover vào row để hiện nút xóa
                    self.action.move_to_element(row).perform()
                    time.sleep(0.5) # Chờ animation

                    # Tìm nút xóa (icon thùng rác) trong row đó
                    try:
                        delete_btn = row.find_element(By.CSS_SELECTOR, "a[title='E-Mail-Adresse löschen']")
                        delete_btn.click()
                        
                        # Xử lý confirm xóa (thường sẽ có popup confirm, nếu không có thì bỏ qua)
                        # Ở đây code theo logic người dùng: Click delete -> Xong. 
                        # Nếu có popup confirm, cần thêm đoạn code click "Ok/Ja" ở đây.
                        time.sleep(2) # Chờ reload sau khi xóa
                    except Exception as del_e:
                        self.log(f"Không nhấn được nút xóa: {str(del_e)}", "WARN")

        except Exception as e:
            self.log(f"Lỗi trong quá trình dọn dẹp email: {str(e)}", "ERROR")

    def add_new_alias(self, uid_add, domain_full):
        try:
            self.log(f"Đang thêm alias mới: {uid_add}@{domain_full}")
            
            # Tách domain (ví dụ jhhhuu@gmx.de -> lấy gmx.de)
            domain_part = domain_full.split('@')[-1]

            # Điền UID vào input
            # Sử dụng data-webdriver để ổn định hơn ID động
            input_field = self.wait.until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "input[data-webdriver='localPart']")
            ))
            input_field.clear()
            input_field.send_keys(uid_add)

            # Chọn domain từ Dropdown
            select_element = self.driver.find_element(By.CSS_SELECTOR, "select")
            select = Select(select_element)
            
            try:
                select.select_by_visible_text(f"@{domain_part}")
            except:
                # Nếu không tìm thấy text chính xác, thử tìm text chứa domain
                options = select.options
                for opt in options:
                    if domain_part in opt.text:
                        select.select_by_visible_text(opt.text)
                        break

            # Click nút Thêm (Hinzufügen)
            add_btn = self.driver.find_element(By.CSS_SELECTOR, "button[data-webdriver='button']")
            add_btn.click()
            
            time.sleep(2) # Chờ kết quả trả về

            # --- KIỂM TRA KẾT QUẢ ---
            page_source = self.driver.page_source

            # Case 1: Thành công
            if "erfolgreich angelegt" in page_source or "theme-icon-confirm" in page_source:
                self.log(f"SUCCESS: Đã thêm thành công {uid_add}@{domain_part}", "SUCCESS")
                return "SUCCESS"
            
            # Case 2: Đã tồn tại / Không khả dụng
            elif "nicht verfügbar" in page_source or "theme-icon-warn" in page_source:
                self.log(f"FAILED: Mail {uid_add}@{domain_part} đã được sử dụng.", "WARN")
                return "EXIST"
            
            else:
                # Check lại trong list xem có chưa
                if self.check_exists_by_xpath(f"//*[contains(text(), '{uid_add}@{domain_part}')]"):
                    self.log(f"SUCCESS: Tìm thấy mail trong danh sách.", "SUCCESS")
                    return "SUCCESS"
                
                self.log("UNKNOWN: Không xác định được trạng thái.", "WARN")
                return "UNKNOWN"

        except Exception as e:
            self.log(f"Lỗi khi thêm alias: {str(e)}", "ERROR")
            return "ERROR"

# --- MAIN EXECUTION ---

def parse_data(raw_data):
    lines = raw_data.strip().split('\n')
    data_list = []
    # Giả sử dòng đầu là header, bỏ qua
    for line in lines[1:]:
        parts = line.split() # Tách theo khoảng trắng hoặc tab
        if len(parts) >= 11: # Đảm bảo đủ cột
            # Map dữ liệu dựa trên mô tả cột của người dùng
            # UID add (col 0), MAIL LK IG (col 1), ... PHÔI GỐC (col 5), PASS MAIL (col 6)
            # Lưu ý: Index mảng bắt đầu từ 0
            item = {
                "uid_add": parts[0],
                "mail_lk_ig": parts[1],
                "phoi_goc": parts[5], # Email login
                "pass_mail": parts[6] # Pass login
            }
            data_list.append(item)
    return data_list

def main():
    # DATA MẪU (Bạn có thể đọc từ file txt)
    raw_data = """
UID add	MAIL LK IG	USER	PASS IG	2FA	PHÔI GỐC	PASS MAIL	MAIL KHÔI PHỤC
jhhhuu	jhhhuu@gmx.de	u	p	2fa	saucycut1@gmx.de	muledok5P	saucycut1@teml.net
    """
    
    tasks = parse_data(raw_data)
    
    bot = GMXAutomation()

    for task in tasks:
        bot.log(f"--- Đang xử lý tài khoản: {task['phoi_goc']} ---")
        
        try:
            # 1. Login
            if not bot.handle_login(task['phoi_goc'], task['pass_mail']):
                continue # Bỏ qua nếu login lỗi
            
            # 2. Vào Settings
            if not bot.navigate_to_settings():
                continue

            # 3. Xóa mail rác
            bot.cleanup_emails(task['phoi_goc'])

            # 4. Thêm mail mới
            bot.add_new_alias(task['uid_add'], task['mail_lk_ig'])
            
            # Logout hoặc clear cookies cho acc tiếp theo (để an toàn thì nên xóa session)
            bot.driver.delete_all_cookies()
            time.sleep(2)

        except Exception as e:
            bot.log(f"Lỗi không xác định ở vòng lặp chính: {str(e)}", "CRITICAL")
            # Nếu lỗi browser crash thì khởi tạo lại
            try:
                bot.driver.quit()
            except:
                pass
            bot = GMXAutomation()

    bot.close()
    print("Hoàn tất toàn bộ công việc.")

if __name__ == "__main__":
    main()