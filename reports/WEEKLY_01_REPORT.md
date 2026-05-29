# Báo cáo tuần 01

## Thông tin chung

- Họ tên: Đặng Tiến Dũng
- Vai trò: AI Engineering
- Tuần: 01
- Mentor/Supervisor: Vương Trường Sơn
- Chủ đề/project: Automatic Speech Recognition (ASR) và các pipeline xung quanh

## 1. Tóm tắt tuần

Tuần này đã được giới thiệu về các dự án team AI cho robot đang làm, công nghệ team đang triển khai, các bài toàn team cần xử lý, và các công việc cần thực hiện.
Tìm hiểu về Inference (Backend cho model AI) cụ thể là Triton và Sherpa-onnx. Trả lời câu hỏi: là gì, hoạt động như thế nào, tại sao cần dùng và implement ra sao.  

## 2. Mục tiêu trong tuần

- Hiểu tổng quan bài toán Automatic Speech Recognition
- Xác định các thành phần chính của một pipeline ASR
- Hiểu về Inferrent để chạy model AI (Triton, Sherpa-onnx)
- Thiết lập format báo cáo tuần để theo dõi tiến độ học tập
- Ghi lại các câu hỏi kỹ thuật cần mentor hỗ trợ

## 3. Công việc đã thực hiện

| Công việc | Mô tả | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Xác định phạm vi học tập | Tập trung vào ASR, dữ liệu audio, inference pipeline và evaluation | Hoàn thành | Làm nền cho các tuần tiếp theo |
| Tìm hiểu về Triton | Hoàn thành tutorial Triton | Hoàn thành | Hiểu triton là gì và cách dùng |
| Tìm hiểu về Sherpa-onnx | Tìm hiểu tại sao lại có model này trong khi đã có asr-triton | Hoàn thành | Đã tự deploy được luồng stream |
| Call vào model đã có trong k8s của team | Làm được luồng ASR cơ bản | Đã call được dùng file wav, nhưng chưa stream được | Cần làm được luồng stream được và hiểu model đang chạy của team |

## 4. Ghi chú kỹ thuật

### Đã hiểu Conceptual của Triton bao gồm:

- model_repository
- model serving
- dynamic_batching
- instance_group
- triton-model-analyzer
- accelerating inference
- model ensembles
- Business Logic Scripting API (BLS)
- Iterative Scheduling
- sequence_batching (Stateful sequence batching)
- semantic cache (embedded vector)

### Đã làm được một luồng sherpa-onnx ASR chạy trên máy với model tiếng việt

- Pipeline ASR ở mức tổng quan (theo example sherpa-onnx)
- Dùng model sherpa-onnx-zipformer-vi-int8-2025-04-20
- Đã dùng VAD silero_vad.onnx tích hợp vào trong luồng


## 5. Kết quả và nhận định

- ASR không chỉ là gọi model speech-to-text, mà là một chuỗi xử lý dữ liệu.

## 6. Khó khăn và blocker

| Vấn đề | Ảnh hưởng | Hỗ trợ cần thiết |
| --- | --- | --- |
| Chưa chạy thưc tế Triton trên GPU | Không có GPU, đang chạy thử bằng CPU | Nếu mentor có môi trường chạy GPU thì tốt |
| Chưa stream được với model k8s của team | Chưa làm được 1 luồng end-to-end | Đang detect vấn đề tại sao mic on có log ghi chunk nhưng ghi thử file wav thì là 0s, không biết mentor có gợi ý gì không? |

## 7. Việc làm tuần sau (sẽ update thêm)

- Slide thuyết trình về Triton
- Làm được luồng end-to-end ASR

## 8. Câu hỏi cho mentor

- Luồng ASR mình đang test thì thấy sherpa-onnx dùng khá tốt mặc dù đang chạy local trên máy mình với model tiếng việt 2025, tại sao cần dùng cả asr-triton?
- Tại sao không VAD và ASR, và cả các model khác trong cùng 1 triton và cho luồng chạy 1 mạch thay vì gọi qua lại giữa triton với client? (không biết mình hiểu hệ thống hiện tại có đúng không nhỉ)

## Feedback từ mentor

- Điểm mạnh:
- Điểm cần cải thiện:
- Action items:
