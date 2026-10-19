# Novel Local · giao diện hiện tại

Tài liệu từ mã và ảnh render thực của bản 0.1.0; không phải chứng nhận hoàn tất review.
Review độc lập được thử hai lần nhưng provider đều HTTP 502, chưa có kết luận độc lập.

## Ngữ cảnh và cấu trúc
Giao diện thao tác tiếng Việt, không phải landing page. Popup một cột 368px;
trang options tối đa 860px, thu nhỏ đến 360px. Ưu tiên kết nối → cấu hình → tiến độ
→ hành động; trang settings: ghép nối → model → glossary → cache.

## Tokens từ extension/src/ui/style.css
- Nền `#f5f7fa`, chữ `#182b3d`, chữ phụ `#526579`.
- Accent cobalt `#2055a5`, đường phân chia `#c7d0dc`, lỗi `#a22731`.
- Segoe UI / system-ui, 14px, line-height 1.5. H1 24px, H2 19px.
- Control tối thiểu 40px; radius control 5px, trạng thái 6px.
- Popup padding 24px; options 40px × 24px, mobile 24px × 16px.
- Nút chính nền cobalt chữ trắng; phụ nền trắng; focus outline 3px.

## Quy tắc
- Mọi kết quả model/glossary đưa vào DOM qua textContent/text node, không HTML.
- Không dùng icon Unicode, ảnh từ xa hoặc animation trang trí cho tiện ích.
- Nhãn luôn hiển thị, trạng thái có aria-live, lỗi có role alert/status.
- Bảng glossary có vùng cuộn ngang riêng khi hẹp để không làm cả trang tràn ngang.
- Không ghi “GPU đang chạy” từ lựa chọn thiết bị; hiển thị thiết bị thực do service trả.
- Model chưa rõ license hiển thị trạng thái khóa, không ẩn khỏi danh sách.

## Bằng chứng và phần chưa xác nhận
Ảnh kiểm tra desktop/mobile được tạo bằng browser E2E với TEST DOUBLE, không có weights thật.
Popup trong harness mở dạng extension tab nên không dùng ảnh đó để chứng nhận activeTab
hay trạng thái tiến độ của popup native. Kiểm tra thao tác toolbar native, độ dễ dùng thực tế,
screen reader, trạng thái tải thật và kết quả model còn nằm ở cổng nghiệm thu.
