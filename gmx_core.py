# FILE: gmx_core.py
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

# --- CẤU HÌNH ---
TIMEOUT_MAX = 15  # Số giây tối đa chờ 1 element
SLEEP_INTERVAL = 1 # Thời gian nghỉ giữa các lần check

def get_driver():
    """Khởi tạo trình duyệt với cấu hình tối ưu"""
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-blink-features=AutomationControlled')
    # Tắt load ảnh để chạy nhanh
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    print("[CORE] Đang mở trình duyệt...")
    driver = uc.Chrome(options=options)
    return driver

def find_element_safe(driver, by, value, timeout=TIMEOUT_MAX, click=False, send_keys=None):
    """
    Hàm tìm kiếm an toàn (Polling Loop).
    - Tự động retry nếu không thấy.
    - Trả về Element nếu thành công.
    - Trả về None nếu timeout.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            element = driver.find_element(by, value)
            
            # Scroll nhẹ để element vào view (tránh bị che)
            # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            
            if click:
                element.click()
                return True
            
            if send_keys:
                element.clear()
                element.send_keys(send_keys)
                return True
            
            return element # Trả về element để xử lý tiếp
        except Exception:
            time.sleep(SLEEP_INTERVAL)
            continue
    
    print(f"[ERROR] Không tìm thấy hoặc không thao tác được: {value}")
    return None