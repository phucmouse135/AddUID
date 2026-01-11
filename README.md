# GMX Alias Automation Tool

Tool tự động hóa việc thêm Alias cho tài khoản GMX, hỗ trợ đa luồng (Multi-threading), giao diện đồ họa (GUI), và chế độ chạy ẩn (Headless).

## Yêu cầu hệ thống

*   Python 3.10 trở lên.
*   Google Chrome mới nhất.

## Hướng dẫn cài đặt & Chạy tool

Làm theo các bước sau để thiết lập môi trường và chạy tool.

### 1. Tạo môi trường ảo (Virtual Environment)
Mở Terminal tại thư mục dự án và chạy lệnh sau để tạo thư mục `venv`:

```bash
python -m venv venv
```

### 2. Kích hoạt môi trường ảo
*   **Windows (Command Prompt / Powershell):**
    ```powershell
    .\venv\Scripts\activate
    ```
    *(Nếu gặp lỗi script, chạy lệnh này trước: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

*   **Linux / macOS:**
    ```bash
    source venv/bin/activate
    ```

Khi kích hoạt thành công, bạn sẽ thấy `(venv)` xuất hiện ở đầu dòng lệnh.

### 3. Cài đặt thư viện (Dependencies)
Cài đặt các thư viện cần thiết từ file `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Chạy Tool
Khởi động giao diện chương trình:

```bash
python gui.py
```

---

## Chức năng chính
*   **Multi-threading:** Chạy nhiều tài khoản cùng lúc.
*   **Headless Mode:** Chạy ẩn không hiện trình duyệt.
*   **Retry Logic:** Tự động thử lại 3 lần nếu Login thất bại.
*   **Export:** Xuất kết quả Thành công / Thất bại riêng biệt.
*   **Resume:** Tự động bỏ qua các case đã chạy thành công khi bấm Start lại.
