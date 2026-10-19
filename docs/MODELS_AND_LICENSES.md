# Model và giấy phép

Kiểm tra trực tiếp API HF, danh sách file và README ngày 19/10/2026.
Mã chương trình được tự triển khai; không sao chép mã demo.

## HachimiMT-60 (mặc định)
- Tác giả: ngocdang83.
- Repo: https://huggingface.co/ngocdang83/HachimiMT-60-zh-vi
- Revision: `50cd988cefa7773c2663337e54829df8bb036659`.
- CT2: `ct2-int8_float32/`, weights 58,057,231 byte; dung lượng tải đầy đủ
  được đọc từ metadata revision khi người dùng chủ động kiểm tra.
- Model card khai báo **CC BY 4.0**: https://creativecommons.org/licenses/by/4.0/
- Ghi công bắt buộc; bản CT2 có sẵn của tác giả, không huấn luyện/sửa weights trong dự án này.
- Card có lưu ý dữ liệu teacher và điều khoản nguồn: cần rà soát trước phát hành thương mại.
- SentencePiece source/target riêng theo file repo. Input chunk 159 token + EOS;
  beam 4, repetition penalty 1.2, no-repeat ngram 2, output tối đa 400.
- Phồn thể được chuyển sang giản thể trên đầu vào engine; nguồn DOM không thay đổi.

## MoxhiMT-60
- Tác giả: DanVP.
- Repo: https://huggingface.co/DanVP/MoxhiMT-60
- Revision: `a68cc65218ddea2adac1ce508512953306936c51`.
- CT2: `ct2-int8/`, weights 58,130,959 byte.
- Model card: **Apache 2.0**, https://www.apache.org/licenses/LICENSE-2.0
- SentencePiece source và target không giống nhau; không dùng chung tokenizer Hachimi.
- Input chunk 159 token + EOS, beam 4, output tối đa 512.

## HirashibaMT-Medium — BLOCKER, không phát hành/tải
- Alias `Moleys/hirashiba-mt-medium` chuyển hướng sang:
  https://huggingface.co/Moleys/hirashiba-mt-medium-old
- Revision gốc: `3c9afb8e0c16f734a774ed126a3fe34c245aec0a`.
- CT2: https://huggingface.co/ngungodan/hirashiba-mt-medium-ct2
- Revision CT2: `239b98c59cb50c0e3660dcfc0fa62b4b0c471174`.
- Không có license trong metadata/card CT2; bản gốc không có README.
- `tokenizer.json` gốc và bản CT2 có cùng Git blob
  `bdaffc6da5e696b5389617ebacb2d55685af3ef1`.
  Đây chỉ là bằng chứng file tokenizer trùng, **không chứng minh runtime tương thích**.
- Registry và adapter tokenizer JSON được giữ; nút tải/API bị khóa đến khi quyền
  sử dụng được xác minh. Không coi việc công khai weights là quyền phân phối.
- Giới hạn bảo thủ đang dự kiến: input 95 + EOS, output 128, beam 4;
  cần đo thiếu đuôi/chất lượng trên weights thật trước khi khóa cấu hình.

## Nguồn demo tham khảo
https://huggingface.co/spaces/ngocdang83/HachimiMT-demo
revision `7437fd074264ef6d56d7f8e40e8473009cb96912`.
Không thấy license ở card hoặc file LICENSE trong danh sách repo.
Chỉ khảo sát cấu hình/tên repo; không đóng gói hoặc tái sử dụng mã nguồn demo.

## Runtime và attribution
CTranslate2 4.8.3 (MIT), SentencePiece (Apache-2.0), tokenizers (Apache-2.0),
FastAPI (MIT), SQLite (public domain), các phụ thuộc khác xem bản inventory
và file license sinh bởi `scripts/licenses.py`. Cần review inventory trước phát hành.
Gói CPU không chứa weights model, DLL NVIDIA, Gradio hoặc PyTorch.
