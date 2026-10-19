# Windows và phân phối

## Phạm vi đã chạy
Máy phát triển Windows AMD64, Python 3.11.9. CT2 4.6.0 đã kiểm tra CPU import;
chuyển sang CTranslate2 4.8.3 vì 4.6.0 cần `pkg_resources` đã bị setuptools mới loại bỏ.
Không giữ setuptools cũ có advisory chỉ để duy trì phiên bản CT2 ban đầu.
Driver hiện có: Intel UHD, số CUDA device = 0. Không dùng Intel UHD làm CUDA.
Chưa công bố cấu hình Windows tối thiểu hay cam kết tất cả Windows 10/11.

## Runtime không cần Python của người dùng
PyInstaller one-directory: `dist/NovelLocal/NovelLocal.exe`. Giữ **cả thư mục**,
không chỉ sao chép exe. Chạy chẩn đoán:

```powershell
dist/NovelLocal/NovelLocal.exe --diagnose --diagnostic-output "$env:TEMP/novel-diagnostic.json"
```

Sau build, chạy `scripts/licenses.py --fetch-missing` để thu thập notice của runtime trước đóng gói.
Lệnh này chủ động tải license từ repo chính thức khi wheel không kèm văn bản license;
không thuộc đường chạy dịch/offline của ứng dụng.
Bộ cài Inno Setup: per-user, shortcut Start/Desktop, không startup task, không tải model.
Chưa có ISCC trong máy triển khai hiện tại: script installer có sẵn nhưng chưa xác minh
bộ cài trên Windows sạch, đường dẫn có dấu hoặc quyền ghi bằng tài khoản thường.
VC++ runtime có thể cần trên máy sạch; phải kiểm tra và bổ sung bootstrapper chính thức
theo license Microsoft trước nghiệm thu. Không yêu cầu người dùng tự cài Python.

## NVIDIA là phụ thuộc riêng
CT2 wheel 4.8.3 hỗ trợ Windows GPU qua CUDA 12.x:
https://github.com/OpenNMT/CTranslate2/blob/v4.8.3/docs/installation.md

CPU installer không kèm CUDA. Có hai đường dự kiến cần nghiệm thu NVIDIA:
- NVIDIA driver và CUDA 12.x được người dùng cài từ NVIDIA, thư mục DLL nằm trên PATH.
- Add-on riêng `packaging/windows/gpu-addon.iss`, lấy từ một thư mục redistributables
  đã được người đóng gói kiểm tra giấy phép, có cuBLAS/cuBLASLt/cudart và LICENSE.
  Compile bằng `ISCC /DCudaSource="..." packaging/windows/gpu-addon.iss`.
  Launcher thêm `%LOCALAPPDATA%/NovelLocal/cuda` vào DLL search path trước import CT2.

Chưa có DLL NVIDIA được duyệt/đóng gói trong repo; **chưa có add-on GPU phát hành**.
Chưa kiểm thử NVIDIA thật. Với Marian không có convolution, không mặc định kéo bộ cuDNN
chỉ để làm dịch; dependency thực tế cần kiểm chứng trên máy mục tiêu.
Runtime yêu cầu CUDA bằng float32 trước, khi nạp thất bại sẽ chạy CPU int8 và cảnh báo.
Khởi động lại chương trình sau khi cài phụ thuộc NVIDIA để nạp lại DLL.
Thực tế thiết bị hiển thị lấy từ nhánh đã nạp, không chỉ từ lựa chọn trong UI.

## Đo kiểm trước phát hành
Sau khi đã tải model qua UI (có xác nhận):

```powershell
.venv/Scripts/python scripts/benchmark.py --data "$env:LOCALAPPDATA/NovelLocal" --model HachimiMT-60 --device cpu --output artifacts/hachimi-cpu.json
```

Lặp cùng mẫu cho Moxhi và Hirashiba sau khi hết blocker giấy phép; báo nạp riêng với
inference, cold/warm, không trộn thời gian tải vào dịch. Script không tự tải, chỉ chạy
offline trên snapshot đã có. Thời gian viewport/toàn trang cần đo trình duyệt riêng,
không lấy số engine thay thế. Cần review chất lượng người đọc trên cùng các mẫu.
