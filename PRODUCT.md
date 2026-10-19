# Novel Local
<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Theo kế hoạch đã được người dùng xác nhận: extension Chrome MV3 dùng TypeScript;
dịch vụ Windows dùng Python, FastAPI, CTranslate2 và SQLite.

## Users
Người đọc web novel Trung muốn đọc tiếng Việt ngay trên trang đang mở.

## Product Purpose
Dịch tại chỗ bằng model local, giữ tương tác và cho phép phục hồi nguồn.

## Operating Context
Mở chương trình local bằng shortcut, ghép nối extension, chọn và xác nhận tải model,
bấm Dịch trên từng trang. Không tự bật theo website, không khởi động cùng Windows.

## Capabilities and Constraints
Ba model theo kế hoạch; Hirashiba chưa rõ quyền phân phối nên chưa được phép tải.
CPU là baseline, NVIDIA là nhánh cần nghiệm thu trên phần cứng thật.
Glossary đặt tên, cache ổ đĩa, snapshot cấu hình mỗi lượt. Gốc/Dịch không reload.
Không OCR, PDF, chrome://, iframe khác miền, code, input hay contenteditable.

## Evidence on Hand
Kế hoạch đã xác nhận; metadata/revision và model card HF được kiểm tra trực tiếp.
Chưa có URL truyện thật hay máy NVIDIA được xác nhận.

## Product Principles
- Không gửi nội dung truyện ra Internet.
- Không làm hỏng tương tác để lấy ngữ cảnh.
- Không khẳng định hiệu năng hay hỗ trợ khi chưa đo/kiểm thử.
- Không phát hành tài nguyên chưa xác minh quyền sử dụng.

## Open decisions
Tên “Novel Local” là tên triển khai tạm; không phải tên thương hiệu đã chốt.
Ngôn ngữ UI tiếng Việt theo yêu cầu. Không bổ sung vòng hỏi quyết định đã chốt.
