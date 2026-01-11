# FILE: main.py
import sys
import threading
import time
import queue
import traceback
import undetected_chromedriver as uc
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import các module chức năng (đã tối ưu ở các bước trước)
from gmx_core import get_driver
from step1_login import login_process
from test_step2_nav import step_2_navigate
from test_step3_clean import step_3_cleanup
from test_step4_add import step_4_add_alias

# --- CẤU HÌNH ---
INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.txt"
MAX_THREADS = 2  # Số luồng chạy song song (Tăng lên nếu máy mạnh, cẩn thận IP)

# Patch lỗi WinError 6 khó chịu của undetected_chromedriver
def _del_patch(self):
    try: self.quit() 
    except: pass
uc.Chrome.__del__ = _del_patch

# Thread-safe Print lock
print_lock = threading.Lock()
# Lock để đồng bộ hóa việc khởi tạo driver (tránh lỗi WinError 183 khi patch file)
driver_init_lock = threading.Lock()

def log_safe(msg, type="INFO"):
    """In log thread-safe để tránh bị đè chữ khi chạy nhiều luồng"""
    prefix = ""
    if type == "INFO": prefix = "[INFO]"
    elif type == "SUCCESS": prefix = "✅ [SUCCESS]"
    elif type == "ERROR": prefix = "❌ [ERROR]"
    elif type == "WARN": prefix = "⚠️ [WARN]"
    
    with print_lock:
        print(f"{prefix} {msg}")

def save_output_safe(result_line):
    """Ghi file thread-safe"""
    with print_lock:
        try:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(result_line + "\n")
        except Exception as e:
            print(f"Lỗi ghi file: {e}")

def read_input(file_path):
    """Đọc file input dạng tab-separated hoặc text lines"""
    tasks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        header = lines[0].strip() # Giả sử dòng đầu là header
        for line in lines[1:]:
            line = line.strip()
            if not line: continue
            
            # Tách cột bằng Tab
            parts = line.split('\t')
            # Fallback split space
            if len(parts) < 2: parts = line.split()
            
            # Mapping dữ liệu (Col 5: User Gốc, Col 6: Pass)
            if len(parts) >= 7:
                item = {
                    "uid_new": parts[0],
                    "email_full_new": parts[1],
                    "login_user": parts[5],
                    "login_pass": parts[6],
                    "raw_line": line
                }
                tasks.append(item)
    except Exception as e:
        log_safe(f"Lỗi đọc input: {e}", "ERROR")
    return tasks

def process_single_account(task):
    """Hàm worker xử lý 1 tài khoản (sẽ chạy trong thread riêng)"""
    driver = None
    user = task['login_user']
    headless_mode = task.get('headless', False) # Lấy config headless từ task
    log_safe(f"Thread Start: {user} (Headless: {headless_mode})")
    
    # === RETRY LOGIN LOGIC (3 Attempts) ===
    # Cơ chế: Thử login -> Fail -> Quit Driver -> Init Driver Mới -> Thử lại
    login_success = False
    
    for attempt in range(1, 4):
        try:
            if attempt > 1:
                log_safe(f"[{user}] Retrying Login (Attempt {attempt}/3)...", "WARN")
            
            # 1. Khởi tạo Driver (New Context)
            with driver_init_lock:
                driver = get_driver(headless=headless_mode)
                time.sleep(1)
            
            # 2. Login
            if login_process(driver, user, task['login_pass']):
                login_success = True
                break # Login OK -> Break loop, keep driver for next steps
            else:
                # Login Failed -> Quit driver immediately to prepare for next attempt
                driver.quit()
                driver = None
                
        except Exception as e:
            log_safe(f"[{user}] Setup/Login Exception (Attempt {attempt}): {e}", "ERROR")
            if driver:
                try: driver.quit()
                except: pass
            driver = None
            
    if not login_success:
        return f"{task['raw_line']}\tLOGIN_FAILED_3_TIMES"

    # === STEPS SAU KHI LOGIN LOGIN THÀNH CÔNG ===
    try:
        # 3. Navigate Settings
        if not step_2_navigate(driver):
            return f"{task['raw_line']}\tNAV_FAILED"

        # 4. Clean (Xóa mail cũ)
        step_3_cleanup(driver, user)

        # 5. Add New Alias
        domain_part = "@" + task['email_full_new'].split('@')[-1]
        status = step_4_add_alias(driver, task['uid_new'], domain_part)
        
        # 6. Logout / Cleanup session (Quan trọng khi chạy multithread)
        try: driver.delete_all_cookies()
        except: pass

        if status == "SUCCESS":
            return f"{task['raw_line']}\tSUCCESS_ADDED"
        elif status == "EXIST":
            return f"{task['raw_line']}\tALREADY_EXIST"
        else:
            return f"{task['raw_line']}\tADD_ERROR"

    except Exception as e:
        log_safe(f"Crash {user}: {e}", "ERROR")
        return f"{task['raw_line']}\tCRASH_ERROR"
        
    finally:
        if driver:
            try: driver.quit()
            except: pass
            
def main():
    log_safe(f"TOOL ADD ALIAS GMX - MULTI THREAD ({MAX_THREADS})")
    
    # 1. Đọc dữ liệu
    tasks = read_input(INPUT_FILE)
    if not tasks:
        log_safe("Không có dữ liệu đầu vào.", "WARN")
        return
        
    log_safe(f"Đã load {len(tasks)} tài khoản. Bắt đầu chạy...")
    
    # 2. Chạy ThreadPool
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Submit tất cả task vào pool
        future_to_task = {executor.submit(process_single_account, task): task for task in tasks}
        
        # Dùng as_completed để xử lý ngay khi có thread xong việc (bất kể thứ tự)
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            user = task['login_user']
            try:
                result = future.result()
                log_safe(f"Done {user} -> {result.split('\t')[-1]}", "SUCCESS")
                save_output_safe(result)
            except Exception as exc:
                log_safe(f"Task generated an exception: {exc}", "ERROR")

    log_safe("HOÀN TẤT TOÀN BỘ CÔNG VIỆC.", "SUCCESS")

if __name__ == "__main__":
    main()
