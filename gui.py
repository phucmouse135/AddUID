# FILE: gui.py
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
import os
from queue import Queue

# Import logic from main.py
try:
    from main import process_single_account, load_backup_uids, backup_uids_queue
except ImportError as e:
    print(f"❌ [CRITICAL ERROR] Cannot import 'process_single_account' from main.py!")
    print(f"Detail: {e}")
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
        self.proxy_port_var = tk.StringVar(value="") # New 9Proxy Port
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
        top_frame = ttk.LabelFrame(self.root, text="Configuration & Input", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Row 0: File Parsing
        ttk.Label(top_frame, text="File Path:").grid(row=0, column=0, padx=5, sticky="w")
        ttk.Entry(top_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="Browse...", command=self.browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="Load Data", command=self.load_data).grid(row=0, column=3, padx=5)
        ttk.Button(top_frame, text="Manual Input", command=self.manual_input_dialog).grid(row=0, column=4, padx=5)

        # Row 1: Settings (Threads, Headless, Proxy)
        ttk.Label(top_frame, text="Threads:").grid(row=1, column=0, padx=5, sticky="w", pady=5)
        ttk.Spinbox(top_frame, from_=1, to=10, textvariable=self.thread_count_var, width=5).grid(row=1, column=1, sticky="w", padx=5)
        
        # Checkbox Headless
        ttk.Checkbutton(top_frame, text="Run Headless", variable=self.headless_var).grid(row=1, column=2, sticky="w", padx=5)
        
        # New: 9Proxy Port Input
        proxy_frame = ttk.Frame(top_frame)
        proxy_frame.grid(row=1, column=3, padx=5, sticky="w")
        ttk.Label(proxy_frame, text="9Proxy Port:").pack(side="left")
        ttk.Entry(proxy_frame, textvariable=self.proxy_port_var, width=10).pack(side="left", padx=5)

        # Helper buttons
        ttk.Button(top_frame, text="Delete Selected", command=self.delete_selected_rows).grid(row=1, column=4, padx=5)
        ttk.Button(top_frame, text="Delete All", command=self.clear_table).grid(row=1, column=5, padx=5)

        # 2. Middle Frame: Notebook (Tabs)
        mid_frame = ttk.Frame(self.root, padding=5)
        mid_frame.pack(fill="both", expand=True, padx=10)

        self.notebook = ttk.Notebook(mid_frame)
        self.notebook.pack(fill="both", expand=True)

        # TAB 1: MAIN LIST
        self.tab_main = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_main, text="Account List")
        
        # Scrollbar Tab 1
        scroll_y_main = ttk.Scrollbar(self.tab_main, orient="vertical")
        scroll_y_main.pack(side="right", fill="y")
        scroll_x_main = ttk.Scrollbar(self.tab_main, orient="horizontal")
        scroll_x_main.pack(side="bottom", fill="x")

        # Treeview Tab 1
        self.tree = ttk.Treeview(self.tab_main, columns=COL_KEYS, show="headings", 
                                 yscrollcommand=scroll_y_main.set, xscrollcommand=scroll_x_main.set)
        
        scroll_y_main.config(command=self.tree.yview)
        scroll_x_main.config(command=self.tree.xview)

        # Define Columns Main
        for i, col_name in enumerate(COLS):
            key = COL_KEYS[i]
            self.tree.heading(key, text=col_name)
            width = 100 if key != "email_full_new" else 150
            if key == "status": width = 150
            self.tree.column(key, width=width)
        self.tree.pack(fill="both", expand=True)

        # TAB 2: BACKUP UID
        self.tab_backup = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_backup, text="Backup UID (Retry)")
        
        # Controls Backup
        bak_ctrl_frame = ttk.Frame(self.tab_backup, padding=5)
        bak_ctrl_frame.pack(fill="x")
        ttk.Button(bak_ctrl_frame, text="Load Backup File", command=self.load_backup_data).pack(side="left", padx=5)
        ttk.Button(bak_ctrl_frame, text="Save Backup File", command=self.save_backup_data).pack(side="left", padx=5)
        ttk.Button(bak_ctrl_frame, text="Clear Backup", command=self.clear_backup_table).pack(side="left", padx=5)
        ttk.Button(bak_ctrl_frame, text="Manual Backup Input", command=self.manual_backup_input).pack(side="left", padx=5)

        # Treeview Backup
        scroll_y_bak = ttk.Scrollbar(self.tab_backup, orient="vertical")
        scroll_y_bak.pack(side="right", fill="y")
        
        bak_cols = ["UID", "EMAIL", "NOTE"]
        self.tree_backup = ttk.Treeview(self.tab_backup, columns=bak_cols, show="headings", yscrollcommand=scroll_y_bak.set)
        scroll_y_bak.config(command=self.tree_backup.yview)
        
        self.tree_backup.heading("UID", text="UID Backup")
        self.tree_backup.heading("EMAIL", text="Email Full")
        self.tree_backup.heading("NOTE", text="Note")
        self.tree_backup.column("UID", width=150)
        self.tree_backup.column("EMAIL", width=250)
        self.tree_backup.column("NOTE", width=150)
        self.tree_backup.pack(fill="both", expand=True)

        # load default backup if exists
        self.root.after(500, self.load_backup_data)

        # Context Menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Delete Selected", command=self.delete_selected_rows)
        self.context_menu.add_command(label="Delete All", command=self.clear_table)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # 3. Bottom Frame: Controls & Stats
        bot_frame = ttk.LabelFrame(self.root, text="Controls & Stats", padding=10)
        bot_frame.pack(fill="x", padx=10, pady=5)

        # Buttons
        self.btn_start = ttk.Button(bot_frame, text="▶ START", command=self.start_process)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(bot_frame, text="⏹ STOP", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        ttk.Separator(bot_frame, orient="vertical").pack(side="left", fill="y", padx=10)
        
        ttk.Button(bot_frame, text="Export Failed", command=lambda: self.export_data(filter_mode="FAIL")).pack(side="right", padx=5)
        ttk.Button(bot_frame, text="Export Success", command=lambda: self.export_data(filter_mode="SUCCESS")).pack(side="right", padx=5)
        ttk.Button(bot_frame, text="Export All", command=lambda: self.export_data(filter_mode="ALL")).pack(side="right", padx=5)

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
            messagebox.showerror("Error", "File not found!")
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
                uid = parts[0] if len(parts)>0 else ""
                mail_lk = parts[1] if len(parts)>1 else ""
                user_ig = parts[2] if len(parts)>2 else ""
                pass_ig = parts[3] if len(parts)>3 else ""
                fa = parts[4] if len(parts)>4 else ""
                phoi_goc = parts[5] if len(parts)>5 else ""
                pass_mail = parts[6] if len(parts)>6 else ""
                kp = parts[7] if len(parts)>7 else ""

                values = (uid, mail_lk, user_ig, pass_ig, fa, phoi_goc, pass_mail, kp, "Pending")
                
                # Save raw line for later use
                raw_line = line
                self.tree.insert("", "end", values=values, tags=(raw_line,))
                count += 1
                
            self.total_tasks = count
            self.update_stats()
            messagebox.showinfo("Info", f"Loaded {count} rows.")
            
        except Exception as e:
            messagebox.showerror("Read Error", str(e))

    def manual_input_dialog(self):
        help_text = "Format: UID[tab]MAIL_LK[tab]USER[tab]PASS[tab]2FA[tab]ORIG_MAIL[tab]PASS_MAIL[tab]RECOVERY_MAIL"
        inp = simpledialog.askstring("Manual Input", f"{help_text}\n\nPaste data here (one per line):")
        if inp:
            lines = inp.strip().split("\n")
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

    # --- BACKUP UTILS ---
    def load_backup_data(self):
        # Default path
        path = "backup_uids.txt"
        if not os.path.exists(path): return

        # Clear old
        self.clear_backup_table()
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                parts = line.split('\t')
                if len(parts) < 2: parts = line.split() # attempt space split
                
                uid = parts[0] if len(parts)>0 else ""
                mail = parts[1] if len(parts)>1 else ""
                note = "Ready"
                self.tree_backup.insert("", "end", values=(uid, mail, note))
        except Exception as e:
            print(f"Load backup error: {e}")

    def save_backup_data(self):
        path = "backup_uids.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                for item in self.tree_backup.get_children():
                    vals = self.tree_backup.item(item, "values")
                    # Save format: UID \t MAIL
                    line = f"{vals[0]}\t{vals[1]}"
                    f.write(line + "\n")
            messagebox.showinfo("Backup", "Backup list saved!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_backup_table(self):
        for item in self.tree_backup.get_children():
            self.tree_backup.delete(item)

    def manual_backup_input(self):
        inp = simpledialog.askstring("Input Backup", "Paste backup list (UID [tab] MAIL):")
        if inp:
            lines = inp.strip().split("\n")
            for line in lines:
                parts = line.split('\t')
                if len(parts)<2: parts = line.split()
                if len(parts)>=1:
                    uid = parts[0]
                    mail = parts[1] if len(parts)>1 else ""
                    self.tree_backup.insert("", "end", values=(uid, mail, "Ready"))
            self.save_backup_data() # Auto save

    def update_row_status(self, item_id, status, error_msg=""):
        current_values = list(self.tree.item(item_id, "values"))
        msg = status
        if error_msg: msg += f" ({error_msg})"
        current_values[-1] = msg # Note column at end
        self.tree.item(item_id, values=current_values)
        
        if status == "Running...":
            self.completed_tasks += 1
            self.tree.item(item_id, tags=()) # Reset tags
            
        is_finished = "Pending" not in status and "Running" not in status
        
        if is_finished:
            # Stats (completed) already incremented at Running phase
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
            messagebox.showwarning("Warning", "No data to run!")
            return

        self.is_running = True
        self.stop_event.clear()
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_var.set("Running...")
        
        # Reset counter
        self.completed_tasks = 0
        self.success_count = 0
        
        # Build Queue
        self.tasks_queue = Queue()
        queued_count = 0

        # Get Proxy Port
        proxy_port_val = self.proxy_port_var.get().strip()
        if not proxy_port_val: proxy_port_val = None
        input_path = self.file_path_var.get()
        if not os.path.exists(input_path):
            input_path = None

        for item_id in items:
            # Get data from columns
            vals = self.tree.item(item_id, "values")
            status_note = vals[-1]

            # FILTER: If already SUCCESS_ADDED, skip
            if "SUCCESS_ADDED" in status_note:
                self.completed_tasks += 1
                self.success_count += 1
                continue
            
            queued_count += 1

            # Build task object
            task = {
                "item_id": item_id,
                "uid_new": vals[0],
                "email_full_new": vals[1],
                "login_user": vals[5],
                "login_pass": vals[6],
                "raw_line": "\t".join(vals[:-1]),
                "headless": self.headless_var.get(),
                "proxy_port": proxy_port_val, # Pass Port
                "input_path": input_path
            }
            
            self.update_row_status(item_id, "Pending") 
            self.tasks_queue.put(task)
        
        self.update_stats()

        if queued_count == 0:
            self.is_running = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.status_var.set("Finished (Skip all)")
            messagebox.showinfo("Info", "All rows are already SUCCESS_ADDED.\nNothing to run!")
            return

        self.save_backup_data() 
        with backup_uids_queue.mutex:
            backup_uids_queue.queue.clear()
        load_backup_uids()

        # Start Worker Threads
        num_threads = self.thread_count_var.get()
        threading.Thread(target=self.worker_manager, args=(num_threads,), daemon=True).start()

    def stop_process(self):
        if not self.is_running: return
        self.status_var.set("Stopping... Waiting for threads...")
        self.stop_event.set()
        # Drain queue
        with self.tasks_queue.mutex:
            self.tasks_queue.queue.clear()

    def worker_manager(self, num_threads):
        """Manage ThreadPoolExecutor with task submission limit"""
        from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
        
        future_map = {}
        futures = set()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            
            while (not self.tasks_queue.empty() or futures) and not self.stop_event.is_set():
                
                # 1. Fill up the pool
                while len(futures) < num_threads and not self.tasks_queue.empty():
                    if self.stop_event.is_set(): break
                    
                    try:
                        task = self.tasks_queue.get_nowait()
                        self.root.after(0, self.update_row_status, task['item_id'], "Running...")
                        
                        future = executor.submit(process_single_account, task)
                        futures.add(future)
                        future_map[future] = task
                    except:
                        break 
                
                if not futures:
                    break
                    
                # 2. Wait
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                
                # 3. Process completed
                for future in done:
                    futures.remove(future)
                    task = future_map.pop(future)
                    
                    try:
                        res_raw = future.result()
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
        self.status_var.set("Completed!")
        messagebox.showinfo("Done", "Job finished.")

    def export_data(self, filter_mode="ALL"):
        # filter_mode: "ALL", "SUCCESS", "FAIL"
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not filename: return
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                # Write Header
                header = "\t".join(COLS)
                f.write(header + "\n")
                
                count = 0
                for item_id in self.tree.get_children():
                    vals = self.tree.item(item_id, "values")
                    status = vals[-1]
                    
                    is_success = "SUCCESS" in status
                    is_running_pending = "Pending" in status or "Running" in status
                    
                    # Logic Filter
                    if filter_mode == "SUCCESS":
                        if not is_success: continue
                    
                    elif filter_mode == "FAIL":
                        if is_success or is_running_pending: continue
                        
                    # filter_mode == "ALL" -> Take all
                        
                    line = "\t".join(vals)
                    f.write(line + "\n")
                    count += 1
            
            messagebox.showinfo("Export", f"Exported {count} lines ({filter_mode})!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.configure("Treeview", rowheight=25)
    
    app = GmxToolApp(root)
    root.mainloop()
