# FILE: main.py
import sys
import threading
import time
import queue
import traceback
import undetected_chromedriver as uc
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import functional modules (optimized in previous steps)
from gmx_core import get_driver
from step1_login import login_process
from test_step2_nav import step_2_navigate
from test_step3_clean import step_3_cleanup
from test_step4_add import step_4_add_alias

# --- CONFIG ---
INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.txt"
BACKUP_UI_FILE = "backup_uids.txt" # New config
MAX_THREADS = 2  # Parallel threads (Increase if powerful machine, careful with IP)

# Patch annoying WinError 6 from undetected_chromedriver
def _del_patch(self):
    try: self.quit() 
    except: pass
uc.Chrome.__del__ = _del_patch

# Thread-safe Print lock
print_lock = threading.Lock()
# Lock for file updates (input/backup)
file_update_lock = threading.Lock()
# Lock for driver init synchronization (avoid WinError 183 when patching file)
driver_init_lock = threading.Lock()
backup_uids_queue = queue.Queue() # Queue backup uid
backup_uid_call_lock = threading.Lock()
backup_uid_call_count = 0

def log_safe(msg, type="INFO"):
    """Thread-safe log printing to avoid mixed text"""
    prefix = ""
    if type == "INFO": prefix = "[INFO]"
    elif type == "SUCCESS": prefix = "✅ [SUCCESS]"
    elif type == "ERROR": prefix = "❌ [ERROR]"
    elif type == "WARN": prefix = "⚠️ [WARN]"
    
    with print_lock:
        print(f"{prefix} {msg}")

def load_backup_uids():
    """Load backup UIDs into a queue"""
    global backup_uid_call_count
    if not backup_uids_queue.empty(): return
    try:
        with open(BACKUP_UI_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                # Parse: UID [tab] MAIL ...
                parts = line.split('\t')
                if len(parts) < 2: parts = line.split() # Fallback space
                
                uid = parts[0].strip()
                if uid: backup_uids_queue.put(uid)

        with backup_uid_call_lock:
            backup_uid_call_count = 0

        count = backup_uids_queue.qsize()
        if count: log_safe(f"Loaded {count} backup UIDs from {BACKUP_UI_FILE}")
    except FileNotFoundError:
        log_safe(f"File {BACKUP_UI_FILE} not found. Retry UID feature disabled.", "WARN")
    except Exception as e:
        log_safe(f"Error reading backup UIDs: {e}", "ERROR")

def _remove_backup_uid_from_file(uid):
    if not uid:
        return
    with file_update_lock:
        try:
            with open(BACKUP_UI_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return
        except Exception as e:
            log_safe(f"Error reading backup file: {e}", "ERROR")
            return

        removed = False
        new_lines = []
        for line in lines:
            parts = line.strip().split('\t')
            if not removed and parts and parts[0].strip() == uid:
                removed = True
                continue
            new_lines.append(line)

        if removed:
            try:
                with open(BACKUP_UI_FILE, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            except Exception as e:
                log_safe(f"Error writing backup file: {e}", "ERROR")

def get_backup_uid():
    """Get a backup UID safely"""
    global backup_uid_call_count
    try:
        uid = backup_uids_queue.get_nowait()
        _remove_backup_uid_from_file(uid)
        with backup_uid_call_lock:
            backup_uid_call_count += 1
        return uid
    except queue.Empty:
        return None

def save_output_safe(result_line):
    """Thread-safe file writing"""
    with print_lock:
        try:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(result_line + "\n")
        except Exception as e:
            print(f"File writing error: {e}")

def read_input(file_path):
    """Read input file (tab-separated or text lines)"""
    tasks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        header = lines[0].strip() # Assume first line is header
        for line in lines[1:]:
            line = line.strip()
            if not line: continue
            
            # Split columns by Tab
            parts = line.split('\t')
            # Fallback split space
            if len(parts) < 2: parts = line.split()
            
            # Data Mapping (Col 5: User Original, Col 6: Pass)
            if len(parts) >= 7:
                item = {
                    "uid_new": parts[0],
                    "email_full_new": parts[1],
                    "login_user": parts[5],
                    "login_pass": parts[6],
                    "raw_line": line,
                    "input_path": file_path
                }
                tasks.append(item)
    except Exception as e:
        log_safe(f"Error reading input: {e}", "ERROR")
    return tasks

def update_input_line(input_path, raw_line, orig_uid, orig_email, new_uid, new_email):
    if not input_path:
        return False
    with file_update_lock:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return False
        except Exception as e:
            log_safe(f"Error reading input file: {e}", "ERROR")
            return False

        def split_line(line_text):
            if "\t" in line_text:
                return line_text.split("\t"), "\t"
            parts = line_text.split()
            return parts, " "

        updated = False

        if raw_line:
            for idx, line in enumerate(lines):
                stripped = line.rstrip("\r\n")
                if stripped != raw_line:
                    continue
                parts, delim = split_line(stripped)
                while len(parts) < 2:
                    parts.append("")
                parts[0] = new_uid
                parts[1] = new_email
                suffix = line[len(stripped):]
                lines[idx] = delim.join(parts) + suffix
                updated = True
                break

        if not updated and orig_uid and orig_email:
            for idx, line in enumerate(lines):
                stripped = line.rstrip("\r\n")
                if not stripped:
                    continue
                parts, delim = split_line(stripped)
                if len(parts) >= 2 and parts[0] == orig_uid and parts[1] == orig_email:
                    parts[0] = new_uid
                    parts[1] = new_email
                    suffix = line[len(stripped):]
                    lines[idx] = delim.join(parts) + suffix
                    updated = True
                    break

        if not updated:
            return False

        try:
            with open(input_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            log_safe(f"Error writing input file: {e}", "ERROR")
            return False

    return True

def process_single_account(task):
    """Worker function processing 1 account (runs in separate thread)"""
    driver = None
    user = task['login_user']
    headless_mode = task.get('headless', False) # Get headless config from task
    proxy_port = task.get('proxy_port', None)
    
    log_safe(f"Thread Start: {user} (Headless: {headless_mode}, Port: {proxy_port})")
    
    # === RETRY LOGIN LOGIC (3 Attempts) ===
    # Mechanism: Try login -> Fail -> Quit Driver -> Init New Driver -> Retry
    login_success = False
    
    for attempt in range(1, 4):
        try:
            if attempt > 1:
                log_safe(f"[{user}] Retrying Login (Attempt {attempt}/3)...", "WARN")
            
            # 1. Initialize Driver (New Context)
            with driver_init_lock:
                driver = get_driver(headless=headless_mode, proxy_port=proxy_port)
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

        # 4. Clean (Delete old mail)
        step_3_cleanup(driver, user)

        # 5. Add New Alias (Modified Logic for Backup UIDs)
        domain_part = "@" + task['email_full_new'].split('@')[-1]
        
        status = "UNKNOWN"
        used_uid = task['uid_new']
        orig_uid = task['uid_new']

        # Retry Loop: 0 (Original) -> 1, 2, 3 (Backups)
        for i in range(4):
            if i > 0:
                # Find backup from stock
                backup = get_backup_uid()
                if not backup:
                    log_safe(f"[{user}] Out of backup UIDs. Stopping retry.", "WARN")
                    status = "EXIST" # Keep allow fail
                    break
                
                log_safe(f"[{user}] ALREADY_EXIST -> Retrying with backup UID: {backup}", "WARN")
                used_uid = backup
                
                # Refresh page to clear form
                driver.refresh()
                # May add navigation step again
                step_2_navigate(driver)

            # Execute Add
            status = step_4_add_alias(driver, used_uid, domain_part)
            
            if status == "SUCCESS":
                break # Success -> Exit
            elif status == "EXIST":
                # If duplicate -> Continue loop to get another backup
                continue
            else:
                # If other ERROR (not duplicate), could be network or site error -> break immediately
                break
        
        # 6. Logout / Cleanup session (Important for multithreading)
        try: driver.delete_all_cookies()
        except: pass

        # Update Output Line if UID Changed
        final_line = task['raw_line']
        if status == "SUCCESS" and used_uid != orig_uid:
            new_email = used_uid + domain_part
            # Replace UID in the output string
            parts = final_line.split('\t')
            if len(parts) >= 2:
                parts[0] = used_uid
                parts[1] = new_email
                final_line = "\t".join(parts)
            update_input_line(
                task.get("input_path", INPUT_FILE),
                task.get("raw_line"),
                orig_uid,
                task.get("email_full_new"),
                used_uid,
                new_email,
            )
            log_safe(f"[{user}] Swapped original UID {orig_uid} -> {used_uid}", "SUCCESS")

        if status == "SUCCESS":
            success_note = "SUCCESS_ADDED"
            if used_uid != orig_uid:
                success_note = f"SUCCESS_ADDED {orig_uid} -> {used_uid}"
            return f"{final_line}\t{success_note}"
        elif status == "EXIST":
            return f"{final_line}\tALREADY_EXIST"
        else:
            return f"{final_line}\tADD_ERROR"

    except Exception as e:
        log_safe(f"Crash {user}: {e}", "ERROR")
        return f"{task['raw_line']}\tCRASH_ERROR"
        
    finally:
        if driver:
            try: driver.quit()
            except: pass
            
def main():
    log_safe(f"TOOL ADD ALIAS GMX - MULTI THREAD ({MAX_THREADS})")
    
    # 0. Load Backup UIDs
    load_backup_uids()
    
    # 1. Read data
    tasks = read_input(INPUT_FILE)
    if not tasks:
        log_safe("No input data.", "WARN")
        return
        
    log_safe(f"Loaded {len(tasks)} accounts. Starting...")
    
    # 2. Run ThreadPool
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Submit all tasks to pool
        future_to_task = {executor.submit(process_single_account, task): task for task in tasks}
        
        # Use as_completed to process as soon as a thread finishes (regardless of order)
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            user = task['login_user']
            try:
                result = future.result()
                log_safe(f"Done {user} -> {result.split('\t')[-1]}", "SUCCESS")
                save_output_safe(result)
            except Exception as exc:
                log_safe(f"Task generated an exception: {exc}", "ERROR")

    log_safe("ALL TASKS COMPLETED.", "SUCCESS")

if __name__ == "__main__":
    main()
