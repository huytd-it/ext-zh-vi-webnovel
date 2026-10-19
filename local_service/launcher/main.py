import json
import os
import secrets
import socket
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import pystray
import uvicorn
from PIL import Image, ImageDraw

from local_service.app.api import PORT, create_app


def main():
    root = tk.Tk()
    root.withdraw()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        listener.bind(("127.0.0.1", PORT))
        listener.listen(128)
    except OSError:
        listener.close()
        messagebox.showerror("Novel Local", f"Cổng {PORT} đang được sử dụng. Chương trình chưa khởi động.")
        return
    # Own the port before creating a token: concurrent launches must not rotate each other's token.
    data = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "NovelLocal"
    try:
        data.mkdir(parents=True, exist_ok=True)
        settings = data / "connection.json"
        if settings.exists():
            token = json.loads(settings.read_text(encoding="utf-8"))["token"]
            if not isinstance(token, str) or not 32 <= len(token) <= 128:
                raise ValueError("Invalid token")
        else:
            token = secrets.token_urlsafe(32)
            temporary = settings.with_suffix(".tmp")
            temporary.write_text(json.dumps({"token": token}), encoding="utf-8")
            temporary.replace(settings)
    except (OSError, ValueError, KeyError):
        listener.close()
        messagebox.showerror("Novel Local", "Không đọc/ghi được dữ liệu ghép nối. Kiểm tra quyền ghi và connection.json trong thư mục dữ liệu.")
        return
    server = uvicorn.Server(uvicorn.Config(create_app(data, token), host="127.0.0.1", port=PORT,
                                           access_log=False, log_level="critical", log_config=None, limit_concurrency=32,
                                           timeout_keep_alive=5))
    server_thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    server_thread.start()

    def connection():
        window = tk.Toplevel(root)
        window.title("Novel Local · Ghép nối")
        window.geometry("580x240")
        tk.Label(window, text="Dán mã này vào phần Cài đặt của extension.", pady=16).pack()
        field = tk.Entry(window, width=64)
        field.insert(0, token)
        field.configure(state="readonly")
        field.pack(padx=16, pady=8)
        tk.Button(window, text="Sao chép mã ghép nối", command=lambda: (
            root.clipboard_clear(), root.clipboard_append(token))).pack(pady=8)
        tk.Label(window, text=f"Chỉ kết nối 127.0.0.1:{PORT} · Không tự chạy cùng Windows").pack()

    image = Image.new("RGB", (64, 64), "#183d35")
    draw = ImageDraw.Draw(image)
    draw.rectangle((17, 13, 46, 51), outline="#f8f4e9", width=3)
    draw.line((24, 24, 39, 24), fill="#f8f4e9", width=3)

    def stop(icon, item):
        server.should_exit = True
        icon.stop()
        root.after(0, root.quit)

    icon = pystray.Icon("NovelLocal", image, "Novel Local · Dịch Trung → Việt", menu=pystray.Menu(
        pystray.MenuItem("Thông tin ghép nối", lambda *_: root.after(0, connection), default=True),
        pystray.MenuItem("Dừng dịch vụ", stop),
    ))
    threading.Thread(target=icon.run, daemon=True).start()
    connection()
    root.mainloop()
    server.should_exit = True
    server_thread.join(timeout=10)
    root.destroy()


if __name__ == "__main__":
    main()
