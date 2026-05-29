# Hành trình học AI Engineering

## Tóm tắt

Repository này ghi lại quá trình học và thực hành AI Engineering, với trọng tâm hiện tại là Automatic Speech Recognition (ASR) và các pipeline liên quan.

Mục tiêu không chỉ là chạy được model, mà là hiểu cách đưa một hệ thống AI lên môi trường production có monitor: dữ liệu rõ ràng, pipeline tái lập được, có tiêu chí đánh giá cụ thể, log đầy đủ, triển khai có logic rõ ràng và tài liệu đủ tốt để người khác có thể tiếp tục phát triển.

## Phạm vi hiện tại

Project hiện tập trung vào:

- Automatic Speech Recognition (ASR)
- Voice Activity Detection (VAD)
- Pipeline chạy inference hoặc đánh giá model
- Baseline Triton và Sherpa-onnx trong ASR
- Báo cáo tiến độ học tập và thực hành theo tuần

## Cấu trúc repository

```text
.
├── README.md
└── reports/
    └── WEEKLY_01_REPORT.md
```

Quy ước đề xuất cho các báo cáo tiếp theo:

```text
reports/WEEKLY_01_REPORT.md
reports/WEEKLY_02_REPORT.md
reports/WEEKLY_03_REPORT.md
```

## Quy trình làm việc hằng tuần

Mỗi tuần nên có một vòng lặp rõ ràng:

1. Xác định mục tiêu học tập hoặc mục tiêu kỹ thuật của tuần
2. Đọc tài liệu, source code, paper hoặc ví dụ liên quan
3. Thực hành qua experiment, script, notebook hoặc prototype nhỏ
4. Ghi lại kết quả, lỗi gặp phải, giả định và quyết định kỹ thuật
5. Đánh giá bằng metric hoặc ví dụ cụ thể nếu có
6. Viết báo cáo tuần trong thư mục `reports/`
7. Chốt kế hoạch cho tuần tiếp theo

## Nguyên tắc kỹ thuật

- Ưu tiên hiểu bản chất trước khi tối ưu
- Mỗi experiment nên có input, output và điều kiện chạy rõ ràng
- Không xem một kết quả đơn lẻ là kết luận cuối cùng
- Luôn ghi lại dữ liệu, version model, tham số và cách đánh giá
- Tận dụng kinh nghiệm backend để xây dựng pipeline AI dễ vận hành
- Tài liệu cần ngắn gọn, có cấu trúc và phục vụ việc ra quyết định

## Kết quả mong muốn

Sau quá trình này, tôi kỳ vọng có thể:

- Hiểu cách một hệ thống ASR hoạt động từ dữ liệu đến inference
- Tự thiết kế và vận hành các pipeline AI cơ bản
- Đánh giá chất lượng model bằng phương pháp có căn cứ
- Kết nối AI component vào hệ thống backend một cách thực tế
- Giao tiếp tiến độ, rủi ro và kết quả kỹ thuật rõ ràng với mentor hoặc team
