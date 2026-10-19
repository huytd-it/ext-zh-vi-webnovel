# Trạng thái triển khai 0.1.0 — chưa nghiệm thu toàn bộ

Cập nhật 19/10/2026. Đây là bản phát triển, không phải thông báo hoàn thành 8 bước.
Chỉ checklist **bước 2** của kế hoạch đã được tick; không đổi nội dung kế hoạch khác.

## Có thể dùng để tiếp tục kiểm chứng
- Extension đã build: `dist/extension`, Load unpacked trong Chrome.
- Runtime Windows: `dist/NovelLocal/NovelLocal.exe`, giữ nguyên cả thư mục.
- Mã nguồn, fixture, test, spec PyInstaller, script Inno CPU và add-on NVIDIA riêng.
- Hướng dẫn chạy/cài/ghép nối: `README.md`, `docs/USAGE.md`, `docs/WINDOWS.md`.
- Không chứa weights và không tự tải model. Chọn và xác nhận tải trong Cài đặt.
- Chưa có bộ cài `*-setup.exe`: máy hiện tại thiếu Inno Setup/ISCC.
- ZIP bản phát triển: `artifacts/NovelLocal-0.1.0-Windows-x64-preview.zip`,
  extension riêng: `artifacts/NovelLocal-extension-0.1.0.zip`. ZIP không phải bộ cài đã nghiệm thu.

## Đã triển khai
- API `/v1`: health/capabilities, model/download, CRUD glossary, cache, job/hủy/ưu tiên.
- Loopback `127.0.0.1:17865`, Bearer token, Host/Origin guard, payload và hàng đợi có giới hạn;
  không CORS wildcard. Website không được yêu cầu background truy cập URL tùy ý.
- MV3 chỉ `activeTab`, `scripting`, `storage`, quyền host loopback; token chỉ trusted contexts.
  Job ID và snapshot cấu hình được giữ trong session storage để worker có thể thức lại.
- Registry ba model với SHA cố định; Hirashiba được giữ nhưng khóa theo cổng giấy phép.
  Adapter SentencePiece/JSON, chunk theo token không truncation, phát hiện output chạm trần,
  giữ ranh giới newline, CPU int8 và CUDA float32 với warm check/fallback CPU.
- Tải có xác nhận dung lượng, trạng thái tiến độ, checksum SHA256/Git blob + kích thước,
  retry file hỏng/dở. Nạp offline kiểm tra snapshot trước sử dụng.
- SQLite schema versioned, glossary snapshot, chuẩn hóa NFC + phồn thể → giản thể,
  cụm dài ưu tiên, phát hiện lỗi marker và retry thường kèm cảnh báo trong cache.
- Cache tách model/revision/decode/device/pipeline/glossary, LRU và xóa riêng khỏi glossary/model.
- Text node grouping theo khối, tách tương tác/BR, giữ phần tử và listener, bảo vệ source/version,
  ưu tiên vùng nhìn, phát hiện lazy-load/website sửa nguồn, Gốc/Dịch, Dừng, SPA reset.
  Open shadow root được duyệt/theo dõi khi phát hiện; không đọc closed shadow root.
- Popup/options tiếng Việt và launcher Windows có ghép nối, tray, dừng dịch vụ;
  không startup task, không gửi nội dung truyện ra mạng, không ghi source/token vào access log.

## Bằng chứng đã chạy
- `npm run build`: qua TypeScript và bundle MV3.
- `npm test`: **16 test qua**, DOM/protocol/background; có mock Chrome API.
- `python -m pytest -q`: **19 test qua**, API/storage/glossary/chunk/download/queue/device;
  inference và tải trong test dùng test double/MockTransport, không phải weights thật.
- Ruff: qua. npm audit và pip-audit: không có advisory đã biết ở lần kiểm tra cuối;
  không đồng nghĩa đã pentest hoặc không còn lỗ hổng.
- Browser E2E trên Chromium `156.0.8078.4`: bridge HTTPS→MV3→loopback, đóng popup,
  worker restart bằng CDP, hai tab và Dừng cô lập, toàn fixture, lazy-load, Gốc/Dịch nhiều lần,
  giữ input/code/link/listener, không lộ token ra trang, request website bị chặn, reset SPA.
  **Engine TEST DOUBLE ONLY.** Manifest bản sao test chỉ thêm origin HTTPS giả trong thư mục tạm;
  manifest phân phối không bị thêm quyền website.
- PyInstaller đã build, chẩn đoán CT2 4.8.3, SQLite, OpenCC, tokenizers, SentencePiece,
  import API và Tcl chạy từ runtime đóng gói với PATH chỉ còn thư mục Windows, không có Python.
  Smoke có đường dẫn thử chứa ký tự ngoài ASCII. Đây **không phải Windows sạch**.
- API từ chính EXE `--serve` đã trả health 200 với token, trả 401 khi không có token;
  kiểm tra socket thuộc process thử và chỉ bind `127.0.0.1`. Chế độ EXE không có console
  đã tắt logging config phụ thuộc stdout/stderr. Kiểm tra này không nạp weights.
- Máy thực: Windows AMD64, Intel UHD, CT2 báo **0 CUDA device**.
- UI đã xem ảnh desktop/mobile, detector không có finding; review độc lập thử hai lần
  đều lỗi provider HTTP 502. Chưa có kết luận review độc lập.
- Pytest còn một cảnh báo deprecation của Starlette TestClient dùng httpx thay vì httpx2;
  không phải test thất bại.

## Các cổng còn thiếu — không loại khỏi phạm vi
1. **Weights thật, offline, chất lượng và benchmark ba model:** chưa tải vì không tự chọn/
   xác nhận thay người dùng. Sau khi tải có xác nhận, chạy `scripts/benchmark.py` cùng mẫu;
   đo cold/warm, tải/nạp riêng, viewport đầu và toàn trang trên browser. Chưa có số tốc độ/SLA.
2. **Hirashiba:** repo gốc đổi tên và tokenizer có Git blob trùng với CT2, nhưng cả gốc/CT2
   chưa rõ license. Không tải hoặc phát hành trước khi có quyền phù hợp; xem MODELS_AND_LICENSES.
3. **NVIDIA:** chưa có phần cứng để xác nhận. Test fallback hiện là test double và máy hiện tại
   báo không GPU; chưa được coi là nghiệm thu GPU. Add-on DLL NVIDIA chưa được duyệt/đóng gói.
4. **Windows installer/sạch:** cần ISCC, bootstrapper/prerequisite VC++ phù hợp, kiểm tra cài/gỡ
   per-user, quyền ghi, cổng chiếm, shortcut/tray, Unicode path, máy không Python, có/không NVIDIA.
5. **Chrome native:** browser test không bấm được nút toolbar để cấp activeTab; còn phải kiểm tra
   đúng popup native và Chrome ổn định. Không lấy manifest nâng quyền của harness làm bằng chứng này.
6. **Website và stress:** chưa có URL truyện thật. Cần đo trang dài/DOM lớn, starvation, scroll nhanh,
   framework render lại, shadow root gắn muộn. Discovery hiện đồng bộ nên cần đo/đổi sang chia lượt
   nếu gây long task. Không coi fixture là chứng minh mọi website.
7. **Cache và UX:** giới hạn 128 MiB là chặn an toàn tạm, chưa chốt từ workload bản dịch thực.
   Cần đo để chốt ngưỡng, kiểm tra trạng thái tải thật, accessibility thực tế và review UI độc lập.
8. **Release:** review inventory/notices runtime, điều khoản nguồn model, quyền NVIDIA và kiểm thử
   artifacts cuối. Không phát hành Hirashiba hoặc mã demo không rõ quyền; không công bố bản ổn định
   khi các mục nghiệm thu trên còn thiếu.

Không tạo commit, không thay đổi các dự án/changes bên ngoài thư mục này trong repo cha `D:/Projects`.
