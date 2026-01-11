# FILE: gui.py
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
import os
from queue import Queue

# Import logic từ main.py (cần điều chỉnh main.py một chút để hỗ trợ gọi từ GUI)
# Chúng ta sẽ cần chỉnh lại main.py để tách hàm process_single_account ra cho dễ gọi
# hoặc import nguyên logic xử lý.
# Để đơn giản và an toàn, ta sẽ import hàm xử lý 1 account từ main.py
try:
    from main import process_single_account
except ImportError as e:
    # Yêu cầu CHẠY THẬT: Nếu không thấy main.py thì báo lỗi và thoát
    # Không dùng Mock data nữa
    print(f"❌ [CRITICAL ERROR] Không thể import 'process_single_account' từ main.py!")
    print(f"Chi tiết lỗi: {e}")
    sys.exit(1)

# --- CONSTANTS ---
COLS = ["UID add", "MAIL LK IG", "USER", "PASS IG", "2FA", "PHÔI GỐC", "PASS MAIL", "MAIL KHÔI PHỤC", "NOTE"]
COL_KEYS = ["uid_new", "email_full_new", "user_ig", "pass_ig", "2fa", "login_user", "login_pass", "mail_khoi_phuc", "status"]

class GmxToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GMX Alias Tool - Automation")
        self.root.geometry("1100x600")

        # --- Variables ---
        self.file_path_var = tk.StringVar(value="input.txt")
        self.thread_count_var = tk.IntVar(value=1)
        self.headless_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.tasks_queue = Queue()
        self.results = []
        
        # Stats
        self.total_tasks = 0
        self.completed_tasks = 0
        self.success_count = 0

        self._setup_ui()

    def _setup_ui(self):
        # 1. Top Frame: Config & File Input
        top_frame = ttk.LabelFrame(self.root, text="Cấu hình & Input", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Row 1: File Selection
        ttk.Label(top_frame, text="File Path:").grid(row=0, column=0, padx=5, sticky="w")
        ttk.Entry(top_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="Browse...", command=self.browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="Load Data", command=self.load_data).grid(row=0, column=3, padx=5)
        ttk.Button(top_frame, text="Nhập Thủ Công", command=self.manual_input_dialog).grid(row=0, column=4, padx=5)

        # Row 2: Settings
        ttk.Label(top_frame, text="Số luồng (Threads):").grid(row=1, column=0, padx=5, sticky="w", pady=5)
        ttk.Spinbox(top_frame, from_=1, to=10, textvariable=self.thread_count_var, width=5).grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Checkbutton(top_frame, text="Chạy ẩn (Headless)", variable=self.headless_var).grid(row=1, column=2, sticky="w", padx=5)
        
        # Delete Buttons (Moved out of context menu)
        ttk.Button(top_frame, text="Xóa Dòng Chọn", command=self.delete_selected_rows).grid(row=1, column=3, padx=5)
        ttk.Button(top_frame, text="Xóa Tất Cả", command=self.clear_table).grid(row=1, column=4, padx=5)

        # 2. Middle Frame: Table Data
        mid_frame = ttk.Frame(self.root, padding=5)
        mid_frame.pack(fill="both", expand=True, padx=10)

        # Scrollbar
        scroll_y = ttk.Scrollbar(mid_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        
        scroll_x = ttk.Scrollbar(mid_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        # Treeview
        self.tree = ttk.Treeview(mid_frame, columns=COL_KEYS, show="headings", 
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Define Columns
        for i, col_name in enumerate(COLS):
            key = COL_KEYS[i]
            self.tree.heading(key, text=col_name)
            width = 100 if key != "email_full_new" else 150
            if key == "status": width = 150
            self.tree.column(key, width=width)
            
        self.tree.pack(fill="both", expand=True)
        
        # Context Menu cho Table (Click chuột phải)
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Xóa dòng chọn", command=self.delete_selected_rows)
        self.context_menu.add_command(label="Xóa tất cả", command=self.clear_table)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # 3. Bottom Frame: Controls & Stats
        bot_frame = ttk.LabelFrame(self.root, text="Điều khiển & Thống kê", padding=10)
        bot_frame.pack(fill="x", padx=10, pady=5)

        # Buttons
        self.btn_start = ttk.Button(bot_frame, text="▶ START", command=self.start_process)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(bot_frame, text="⏹ STOP", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        ttk.Separator(bot_frame, orient="vertical").pack(side="left", fill="y", padx=10)
        
        ttk.Button(bot_frame, text="Xuất Thành Công", command=lambda: self.export_data(only_success=True)).pack(side="right", padx=5)
        ttk.Button(bot_frame, text="Xuất Tất Cả", command=lambda: self.export_data(only_success=False)).pack(side="right", padx=5)

        # Labels Stats
        self.lbl_progress = ttk.Label(bot_frame, text="Progress: 0/0")
        self.lbl_progress.pack(side="left", padx=10)
        
        self.lbl_success = ttk.Label(bot_frame, text="Success: 0", foreground="green")
        self.lbl_success.pack(side="left", padx=10)
        
        self.lbl_status = ttk.Label(bot_frame, textvariable=self.status_var, foreground="blue")
        self.lbl_status.pack(side="left", padx=20)

    # --- ACTIONS ---
    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename:
            self.file_path_var.set(filename)
            self.load_data()

    def load_data(self):
        path = self.file_path_var.get()
        if not os.path.exists(path):
            messagebox.showerror("Error", "File không tồn tại!")
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            self.clear_table()
            count = 0
            for line in lines:
                line = line.strip()
                if not line or "UID" in line: continue # Skip header or empty
                
                parts = line.split('\t')
                if len(parts) < 2: parts = line.split() # Fallback space split
                
                # Fill missing columns
                while len(parts) < 8: parts.append("")
                
                # Insert to tree
                # Mapping: uid, mail_lk, user_ig, pass_ig, 2fa, phoi_goc, pass_mail, khoi_phuc, note
                # Chú ý logic index từ file: 
                # Col 0: uid_add
                # Col 1: mail_lk_ig
                # Col 2: user_ig
                # Col 3: pass_ig
                # Col 4: 2fa
                # Col 5: phoi_goc (login_user)
                # Col 6: pass_mail
                # Col 7: khoi_phuc
                
                # Safe get
                uid = parts[0] if len(parts)>0 else ""
                mail_lk = parts[1] if len(parts)>1 else ""
                user_ig = parts[2] if len(parts)>2 else ""
                pass_ig = parts[3] if len(parts)>3 else ""
                fa = parts[4] if len(parts)>4 else ""
                phoi_goc = parts[5] if len(parts)>5 else ""
                pass_mail = parts[6] if len(parts)>6 else ""
                kp = parts[7] if len(parts)>7 else ""

                values = (uid, mail_lk, user_ig, pass_ig, fa, phoi_goc, pass_mail, kp, "Pending")
                
                # Lưu raw line vào tag để dùng lại khi xử lý
                raw_line = line
                self.tree.insert("", "end", values=values, tags=(raw_line,))
                count += 1
                
            self.total_tasks = count
            self.update_stats()
            messagebox.showinfo("Info", f"Đã load {count} dòng.")
            
        except Exception as e:
            messagebox.showerror("Lỗi đọc file", str(e))

    def manual_input_dialog(self):
        help_text = "Định dạng: UID[tab]MAIL_LK[tab]USER[tab]PASS[tab]2FA[tab]PHÔI_GỐC[tab]PASS_MAIL[tab]MAIL_KP"
        inp = simpledialog.askstring("Nhập thủ công", f"{help_text}\n\nDán dữ liệu vào đây (mỗi dòng 1 acc):")
        if inp:
            self.clear_table()
            lines = inp.strip().split("\n")
            # Reuse logic load (quick hack: save to temp then load)
            for line in lines:
                parts = line.split('\t')
                if len(parts) < 2: parts = line.split()
                while len(parts) < 8: parts.append("")
                values = (*parts[:8], "Pending")
                self.tree.insert("", "end", values=values)
            self.total_tasks = len(self.tree.get_children())
            self.update_stats()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected_rows(self):
        for item in self.tree.selection():
            self.tree.delete(item)
        self.total_tasks = len(self.tree.get_children())
        self.update_stats()

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.total_tasks = 0
        self.completed_tasks = 0
        self.success_count = 0
        self.update_stats()

    def update_stats(self):
        self.lbl_progress.config(text=f"Progress: {self.completed_tasks}/{self.total_tasks}")
        self.lbl_success.config(text=f"Success: {self.success_count}")

    def update_row_status(self, item_id, status, error_msg=""):
        current_values = list(self.tree.item(item_id, "values"))
        msg = status
        if error_msg: msg += f" ({error_msg})"
        current_values[-1] = msg # Cột Note ở cuối
        self.tree.item(item_id, values=current_values)
        
        # LOGIC UPDATE STATS:
        # User yêu cầu: Khi đang chạy (Running) thì đã tính vào Progress (ví dụ 4 running -> 4/32)
        
        if status == "Running...":
            self.completed_tasks += 1
            self.tree.item(item_id, tags=()) # Reset tags
            
        is_finished = "Pending" not in status and "Running" not in status
        
        if is_finished:
            # Không cộng completed_tasks ở đây nữa (vì đã cộng lúc Running)
            if "SUCCESS" in status:
                self.success_count += 1
                self.tree.item(item_id, tags=("success",))
            else:
                self.tree.item(item_id, tags=("error",))
        
        self.tree.see(item_id) # Scroll to viewing
        self.update_stats()

    # --- PROCESS THREADING ---
    def start_process(self):
        if self.is_running: return
        
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Warning", "Chưa có dữ liệu để chạy!")
            return

        self.is_running = True
        self.stop_event.clear()
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_var.set("Đang chạy...")
        
        # Reset counter
        self.completed_tasks = 0
        self.success_count = 0
        
        # Build Queue
        self.tasks_queue = Queue()
        queued_count = 0

        for item_id in items:
            # Lấy data từ columns
            vals = self.tree.item(item_id, "values")
            status_note = vals[-1]

            # FILTER: Nếu đã SUCCESS_ADDED thì bỏ qua, không chạy lại
            if "SUCCESS_ADDED" in status_note:
                self.completed_tasks += 1
                self.success_count += 1
                continue
            
            queued_count += 1

            # Build task object giống main.py
            task = {
                "item_id": item_id,
                "uid_new": vals[0],
                "email_full_new": vals[1],
                "login_user": vals[5],
                "login_pass": vals[6],
                "raw_line": "\t".join(vals[:-1]),
                "headless": self.headless_var.get() # Pass headless option
            }
            # Update status pending (Note: update_row_status đã lọc ko cộng stats cho Pending)
            self.update_row_status(item_id, "Pending") 
            
            self.tasks_queue.put(task)
        
        self.update_stats()

        if queued_count == 0:
            self.is_running = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.status_var.set("Hoàn tất (Skip all)")
            messagebox.showinfo("Info", "Tất cả các dòng đều đã là SUCCESS_ADDED.\nKhông có gì để chạy!")
            return

        # Start Worker Threads
        num_threads = self.thread_count_var.get()
        threading.Thread(target=self.worker_manager, args=(num_threads,), daemon=True).start()

    def stop_process(self):
        if not self.is_running: return
        self.status_var.set("Đang dừng... Đợi các luồng kết thúc...")
        self.stop_event.set()
        # Drain queue
        with self.tasks_queue.mutex:
            self.tasks_queue.queue.clear()

    def worker_manager(self, num_threads):
        """Quản lý ThreadPoolExecutor với việc giới hạn số lượng task submit"""
        from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
        
        future_map = {}
        futures = set()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            
            # Loop loop until queue is empty AND no active futures are left
            while (not self.tasks_queue.empty() or futures) and not self.stop_event.is_set():
                
                # 1. Fill up the pool with tasks until we reach num_threads
                while len(futures) < num_threads and not self.tasks_queue.empty():
                    if self.stop_event.is_set(): break
                    
                    try:
                        task = self.tasks_queue.get_nowait()
                        
                        # UPDATE STATUS: Running (Only for the ones actively submitted)
                        self.root.after(0, self.update_row_status, task['item_id'], "Running...")
                        
                        future = executor.submit(process_single_account, task)
                        futures.add(future)
                        future_map[future] = task
                    except:
                        break # Queue empty
                
                if not futures:
                    break
                    
                # 2. Wait for at least one future to complete
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                
                # 3. Process completed futures
                for future in done:
                    futures.remove(future)
                    task = future_map.pop(future)
                    
                    try:
                        res_raw = future.result()
                        # res_raw format: "raw_line\tSTATUS"
                        status = res_raw.split('\t')[-1]
                        self.root.after(0, self.update_row_status, task['item_id'], status)
                    except Exception as e:
                        msg = str(e)
                        self.root.after(0, self.update_row_status, task['item_id'], "ERROR", msg)

        self.is_running = False
        self.root.after(0, self._on_process_finished)

    def _on_process_finished(self):
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_var.set("Hoàn tất!")
        messagebox.showinfo("Done", "Đã hoàn thành công việc.")

    def export_data(self, only_success=False):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not filename: return
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                # Write Header
                header = "\t".join(COLS)
                f.write(header + "\n")
                
                for item_id in self.tree.get_children():
                    vals = self.tree.item(item_id, "values")
                    status = vals[-1]
                    
                    if only_success and "SUCCESS" not in status:
                        continue
                        
                    line = "\t".join(vals)
                    f.write(line + "\n")
            
            messagebox.showinfo("Export", "Đã xuất file thành công!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    # Style customization (Optional)
    style = ttk.Style()
    style.configure("Treeview", rowheight=25)
    
    app = GmxToolApp(root)
    root.mainloop()
