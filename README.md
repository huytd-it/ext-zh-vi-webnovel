# Novel Local · Trung → Việt

Extension Chrome MV3 + dịch vụ local Windows cho web novel. **Bản phát triển 0.1.0,
chưa nghiệm thu/phát hành hoàn chỉnh.** Xem [trạng thái kiểm chứng](docs/STATUS.md).

## Chạy từ mã nguồn (máy phát triển)

Windows x64, Python 3.11, Node 22:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e '.[dev]'
npm ci --legacy-peer-deps
npm run build
.venv/Scripts/python -m local_service
```

Chrome → `chrome://extensions` → Developer mode → Load unpacked →
chọn `dist/extension`. Mở Cài đặt extension, nhập mã ghép nối từ chương trình local.
Chọn model, kiểm tra dung lượng rồi xác nhận tải. Không tự tải model khi cài/chạy.

Mở trang HTTP/HTTPS, bấm extension → Dịch trang này. Gốc/Dịch không tải lại trang;
Dừng giữ các đoạn đã dịch; Dịch lại áp dụng cấu hình mới từ nguồn gốc.

## Kiểm thử và build

```powershell
npm run build
npm test
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check local_service tests scripts
npx playwright install chromium
npm run test:e2e
.venv/Scripts/python -m PyInstaller packaging/windows/novel-local.spec --noconfirm
.venv/Scripts/python scripts/licenses.py --fetch-missing
```

Browser E2E dùng **test double**, không chứng minh chất lượng/suy luận model.
Bản manifest test ở thư mục tạm được cấp đúng một origin HTTPS giả để thay thao tác
bấm toolbar native; manifest phân phối không có quyền đó.

Build installer cần Inno Setup 6: `packaging/windows/build.ps1`.
Người dùng bản runtime đã đóng gói không phải cài Python.
Đóng gói ZIP thử nghiệm sau khi thu thập notice: `packaging/windows/package-preview.ps1`.

## Tài liệu
- [Hướng dẫn sử dụng và dữ liệu](docs/USAGE.md)
- [Giấy phép và revision](docs/MODELS_AND_LICENSES.md)
- [CPU / NVIDIA và đóng gói](docs/WINDOWS.md)
- [Trạng thái, giới hạn và nghiệm thu còn thiếu](docs/STATUS.md)

Nội dung truyện chỉ đến API `127.0.0.1:17865`. Internet chỉ dùng khi người dùng
chủ động kiểm tra dung lượng/tải model. Không gọi HF Space để dịch.
