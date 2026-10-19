# Sử dụng

1. Mở `NovelLocal.exe` hoặc shortcut Novel Local. Chương trình chỉ lắng nghe
   `127.0.0.1:17865`, không tự chạy cùng Windows.
2. Chrome → `chrome://extensions` → Developer mode → Load unpacked → chọn thư mục
   extension đã build. Với bộ cài: `%LOCALAPPDATA%/Programs/NovelLocal/extension`.
3. Mở Cài đặt extension. Sao chép mã trong cửa sổ ghép nối local, dán và lưu.
   Không đưa mã lên website; bất kỳ ứng dụng biết mã đều có thể gọi API local.
4. Kiểm tra dung lượng của model muốn dùng → xác nhận tải. Theo dõi tiến độ;
   tải lỗi có thể tải lại. Không tải Hirashiba trước khi giấy phép được làm rõ.
5. Mở một trang HTTP/HTTPS. Chọn model, CPU/NVIDIA và bộ thuật ngữ (hoặc không dùng),
   bấm Dịch trang này. Vùng nhìn trước, sau đó các đoạn còn lại.

## Điều khiển
- Popup không cần mở liên tục. Job chạy ở dịch vụ; content script theo dõi job qua background.
- Xem gốc phục hồi nguồn và không áp bản dịch đang về vào DOM. Xem bản dịch trở lại
  hiển thị các kết quả đã có. Không hover nguồn và không song ngữ.
- Dừng: dừng xếp/áp đoạn mới, giữ phần đã dịch. Dịch lại tạo lượt mới từ nguồn gốc.
- Đổi model/glossary, sửa thuật ngữ không đổi lượt đang chạy. Bấm Dịch lại để áp dụng.
- Chương/trang mới, reload hoặc URL SPA thay đổi cần bấm Dịch lại. Nội dung mới tải
  trong trang đang dịch được tự xử lý.
- Lỗi đoạn giữ nguồn; bấm Dịch lại để thử lại. Glossary lỗi bảo vệ được dịch lại thường,
  có cảnh báo, không đưa marker nội bộ ra trang.

## Glossary
Tạo bộ đặt tên trong Cài đặt, thêm/sửa/xóa các cặp Trung–Việt và bật/tắt từng mục.
Không chấp nhận mục rỗng, nguồn trùng/xung đột sau chuẩn hóa NFC và phồn thể → giản thể.
Cụm dài được ưu tiên khi chồng lấn. Chưa nhập/xuất file. Marker có giới hạn 128/đoạn;
không bảo đảm ép thuật ngữ tuyệt đối: khi không bảo vệ an toàn sẽ fallback.

## Dữ liệu và gỡ
- Runtime: `%LOCALAPPDATA%/Programs/NovelLocal` (bộ cài per-user).
- Dữ liệu: `%LOCALAPPDATA%/NovelLocal` gồm `connection.json`, `data.sqlite3`, `models/`,
  và tùy chọn `cuda/`. Không lưu vào thư mục cài đặt.
- Token extension lưu trong `chrome.storage.local`, chỉ trusted contexts truy cập;
  không chuyển token vào content script/DOM trang truyện.
- Cache lưu kết quả theo hash nguồn + model/revision/config + device + pipeline + glossary;
  **kết quả truyện có trên đĩa, không được mã hóa**. Giới hạn logic 128 MiB tạm thời,
  SQLite có thêm overhead. Xóa cache không xóa glossary hay model.
- Mặc định không log truyện, token hay request access log. Báo benchmark do bạn chủ động
  tạo có chứa mẫu và bản dịch; không công khai nếu chứa nội dung riêng tư.
- Gỡ chương trình không tự xóa dữ liệu. Muốn xóa hoàn toàn: dừng chương trình, gỡ extension,
  gỡ ứng dụng rồi chủ động xóa đúng thư mục `%LOCALAPPDATA%/NovelLocal`.

## Giới hạn
Không OCR, PDF, chrome://, iframe khác miền, shadow DOM đóng, input, editable hoặc code.
Inline đậm/nghiêng là best effort: bản dịch có thể nằm ở text node đầu trong nhóm,
nhưng các phần tử và event handler được giữ, phục hồi được nguồn.
Website framework render lại liên tục có thể cần giải pháp riêng; fixture không chứng minh
hỗ trợ mọi trang. Chưa có URL truyện thật để nghiệm thu.

## Lỗi thường gặp
- Chưa kết nối: mở shortcut; nếu cổng bị chiếm chương trình báo lỗi và không chạy.
- Ghép nối sai: lấy mã từ khay → Thông tin ghép nối và nhập lại.
- Model chưa tải: tải có xác nhận trong Cài đặt; chỉ lần tải cần Internet.
- GPU không dùng được: hiển thị cảnh báo và CPU thực, không giả tăng tốc.
- Hàng đợi đầy: chờ hoặc dừng lượt khác. Tối đa 16 job hoạt động, 32 đơn vị/API batch.
