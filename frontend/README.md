# Ứng Dụng Chatbot Hỏi Đáp Pháp Luật

Ứng dụng chatbot hỏi đáp pháp luật với giao diện hiện đại, hỗ trợ 2 nhân vật trả lời và nhiều tùy chọn tùy chỉnh.

## 🚀 Khởi Động Nhanh

### Yêu Cầu Hệ Thống
- Node.js phiên bản 18 trở lên
- npm hoặc yarn

### Cài Đặt

```bash
# Di chuyển vào thư mục Frontend
cd Frontend

# Cài đặt các gói phụ thuộc
npm install

# Chạy ứng dụng ở chế độ phát triển
npm run dev
```

### Truy Cập
Mở trình duyệt và truy cập: **http://localhost:5174/**

## ✨ Tính Năng

### 1. Chọn Nhân Vật Trả Lời
| Nhân Vật | Phong Cách |
|----------|------------|
| 👨‍⚖️ **Luật sư** | Nghiêm túc, trích dẫn điều luật, cấu trúc rõ ràng |
| 👤 **Người bình thường** | Dễ hiểu, ví dụ đời thường, thân thiện |

### 2. Thanh Trượt Điều Chỉnh Giọng Văn
- **0-30%**: Đời thường
- **30-70%**: Cân bằng  
- **70-100%**: Pháp lý chuyên sâu

### 3. Hình Minh Họa
- ❌ Không có hình
- 📖 Truyện tranh - Dễ ghi nhớ, dễ chia sẻ
- 📢 Áp phích tuyên truyền - Giáo dục pháp luật

### 4. Nút Kéo Lên Đầu Trang
- Xuất hiện khi cuộn xuống
- Nhấn để quay về đầu trang

## 📁 Cấu Trúc Dự Án

```
Frontend/
├── index.html          # Trang HTML chính
├── package.json        # Các gói phụ thuộc
├── vite.config.js      # Cấu hình Vite
├── README.md           # Tài liệu hướng dẫn
└── src/
    ├── main.jsx        # Điểm vào React
    ├── App.jsx         # Thành phần chính
    ├── index.css       # Kiểu dáng toàn cục
    └── services/
        └── mockApi.js  # Dịch vụ API giả lập
```

## 🛠 Công Nghệ Sử Dụng

- **React 18** - Thư viện giao diện
- **Vite 5** - Công cụ xây dựng
- **CSS Variables** - Hệ thống giao diện
- **Inter Font** - Phông chữ

## 📝 Dữ Liệu Mẫu

Hiện tại sử dụng API giả lập với các câu hỏi mẫu:
- Thuê nhà cần lưu ý gì?
- Thủ tục ly hôn như thế nào?
- Bị tai nạn giao thông phải làm sao?
- Viết di chúc thế nào cho đúng?

## Hệ Thống Tính Điểm Phiên Tòa

Điểm được tính dựa trên dữ liệu thực tế từ phiên tranh tụng, gồm 5 hạng mục (mỗi hạng mục 0–100, tổng tối đa 500 điểm).

### Dữ liệu đầu vào

Khi kết thúc phiên tòa, hệ thống sử dụng dữ liệu sau để tính điểm:

| Dữ liệu | Mô tả |
|----------|-------|
| `messages[]` | Danh sách tin nhắn (user, opponent, system) |
| `strategy.arguments[]` | Luận điểm đã chuẩn bị ở bước Strategy |
| `strategy.evidences[]` | Chứng cứ đã chuẩn bị (có thể liên kết luận điểm) |
| `roundsCompleted` | Số vòng tranh luận đã hoàn thành |
| `settings.roundLimit` | Tổng số vòng (mặc định 4) |
| `timeRemaining` | Thời gian còn lại (giây) |
| `settings.timeLimit` | Thời gian giới hạn (phút) |
| `role` | Vai trò: `defendant` (bào chữa) hoặc `plaintiff` (nguyên đơn) |

### 5 hạng mục điểm

#### 1. Độ chính xác pháp lý (`legalAccuracy`)
- Điểm gốc: 50
- +0–20: Tỷ lệ vòng hoàn thành (`roundsCompleted / totalRounds * 20`)
- +5/+10/+15: Độ dài trung bình tin nhắn (>50 / >100 / >200 ký tự)
- +0–15: Số luận điểm đã chuẩn bị (mỗi luận điểm +5, tối đa 15)

#### 2. Sử dụng chứng cứ (`evidenceUse`)
- Điểm gốc: 40
- +0–30: Số chứng cứ chuẩn bị (mỗi chứng cứ +10, tối đa 30)
- +0–16: Chứng cứ liên kết với luận điểm (mỗi liên kết +8, tối đa 16)
- +0–14: Tin nhắn đề cập từ khóa chứng cứ ("chứng cứ", "bằng chứng", "tài liệu", "chứng minh", "căn cứ", "minh chứng") — mỗi tin +5, tối đa 14

#### 3. Sức thuyết phục (`persuasion`)
- Điểm gốc: 45
- +0–15: Tỷ lệ vòng hoàn thành
- +0–16: Số tin nhắn người dùng gửi (mỗi tin +4, tối đa 16)
- +0–12: Số luận điểm chuẩn bị (mỗi luận điểm +4, tối đa 12)
- +7/+12: Độ dài tin nhắn trung bình (>80 / >150 ký tự)

#### 4. Quản lý thời gian (`timeManagement`)
- Điểm gốc: 40
- Hoàn thành tất cả vòng + còn thời gian: +30, thêm +10/+20 nếu pacing tốt (dùng 50–90% thời gian)
- Kết thúc sớm nhưng còn thời gian: +15 + bonus theo vòng hoàn thành
- Hết thời gian: +0–20 theo vòng hoàn thành
- +0–10: Tỷ lệ thời gian còn lại

#### 5. Phong thái ứng xử (`etiquette`)
- Điểm gốc: 70
- +0–25: Dùng từ lịch sự ("thưa", "kính", "hội đồng", "xét xử", "tòa", "đề nghị", "xin phép", "trân trọng") — mỗi tin +5, tối đa 25
- -15 mỗi lần: Dùng từ thô lỗ ("ngu", "vớ vẩn", "nhảm", "láo", "bậy")
- +5: Hoàn thành tất cả vòng (không bỏ cuộc)

### Xếp hạng tổng điểm

| Hạng | Khoảng điểm | Nhãn |
|------|-------------|------|
| S | >= 450 | Xuất sắc! |
| A | >= 400 | Rất tốt! |
| B | >= 350 | Tốt |
| C | >= 300 | Khá |
| D | < 300 | Cần cải thiện |

## Hệ Thống 12 Huy Hiệu

Huy hiệu được trao tự động dựa trên kết quả phiên tòa. Một số huy hiệu dựa trên điểm số phiên hiện tại, một số dựa trên lịch sử tích lũy (lưu trong `localStorage`).

**Ngưỡng "Thắng" (Win):** Tổng điểm >= 350/500.

### Huy hiệu theo điểm số

| Huy hiệu | Điều kiện |
|-----------|-----------|
| Luật sư xuất sắc | Tổng điểm >= 450 |
| Bậc thầy chứng cứ | Điểm sử dụng chứng cứ >= 90 |
| Nhà hùng biện | Điểm thuyết phục >= 90 |
| Chính xác tuyệt đối | Điểm pháp lý >= 95 |
| Lịch thiệp | Điểm phong thái >= 95 |

### Huy hiệu theo hiệu suất phiên

| Huy hiệu | Điều kiện |
|-----------|-----------|
| Tốc độ ánh sáng | Hoàn thành tất cả vòng tranh luận VÀ còn >= 40% thời gian |
| Người bảo vệ | Thắng (>= 350 điểm) với vai trò bào chữa (defendant) |
| Công tố viên | Thắng (>= 350 điểm) với vai trò nguyên đơn (plaintiff) |
| Lội ngược dòng | Thắng (>= 350 điểm) dù có >= 2 hạng mục điểm dưới 60 |

### Huy hiệu tích lũy (dựa trên lịch sử)

| Huy hiệu | Điều kiện |
|-----------|-----------|
| Chiến thắng đầu tiên | Lần đầu tiên đạt tổng điểm >= 350 (chưa có phiên win nào trước đó) |
| Chuỗi 3 trận | Thắng phiên hiện tại + 2 phiên gần nhất đều thắng (3 phiên liên tiếp) |
| Bậc thầy tranh tụng | Tổng số phiên tòa đã hoàn thành >= 10 |

## 🔌 API Endpoints

Ứng dụng giao tiếp với backend server tại `http://localhost:8000`.

### 1. Chat — Hỏi đáp pháp luật

**`POST /chat`**

Gửi câu hỏi pháp luật và nhận câu trả lời từ hệ thống RAG.

**Request body:**
```json
{
    "question": "Thuê nhà cần lưu ý gì?",
    "options": {
        "character": "lawyer",
        "toneValue": 50,
        "illustrationType": "none"
    }
}
```

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `question` | `string` | Câu hỏi của người dùng |
| `options.character` | `string` | Nhân vật trả lời: `"lawyer"` hoặc `"normal"` |
| `options.toneValue` | `number` | Mức độ giọng văn (0–100): 0 = đời thường, 100 = pháp lý chuyên sâu |
| `options.illustrationType` | `string` | Loại hình minh họa: `"none"`, `"comic"`, `"poster"` |

**Response:**
```json
{
    "answer": "Khi thuê nhà, bạn cần lưu ý các điểm sau..."
}
```

### 2. Evaluate — Đánh giá phiên tòa

**`POST /courtroom/evaluate`**

Gửi dữ liệu phiên tranh tụng để AI đánh giá điểm số 5 hạng mục. Nếu backend không khả dụng, frontend sẽ tự động fallback sang tính điểm cục bộ (heuristic).

**Request body:**
```json
{
    "scenarioId": "contract_dispute",
    "role": "defendant",
    "scenario": {
        "name": "Tranh chấp hợp đồng mua bán",
        "summary": "...",
        "facts": ["..."]
    },
    "messages": [
        { "type": "user", "text": "Thưa tòa, tôi xin trình bày...", "round": 1 },
        { "type": "opponent", "text": "Tôi phản đối...", "round": 1 }
    ],
    "strategy": {
        "arguments": [{ "text": "Hợp đồng vi phạm Điều 492..." }],
        "evidences": [{ "text": "Biên bản giao nhận", "linkedArguments": [0] }]
    },
    "roundsCompleted": 4,
    "totalRounds": 4,
    "timeRemaining": 180,
    "totalTime": 600
}
```

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `scenarioId` | `string` | ID kịch bản |
| `role` | `string` | Vai trò: `"defendant"` (bào chữa) hoặc `"plaintiff"` (nguyên đơn) |
| `scenario` | `object` | Thông tin kịch bản (tên, tóm tắt, dữ kiện) |
| `messages` | `array` | Danh sách tin nhắn trong phiên (type: `user`/`opponent`/`system`) |
| `strategy` | `object` | Luận điểm và chứng cứ đã chuẩn bị |
| `roundsCompleted` | `number` | Số vòng tranh luận đã hoàn thành |
| `totalRounds` | `number` | Tổng số vòng |
| `timeRemaining` | `number` | Thời gian còn lại (giây) |
| `totalTime` | `number` | Tổng thời gian (giây) |

**Response:**
```json
{
    "legalAccuracy": 85,
    "evidenceUse": 78,
    "persuasion": 82,
    "timeManagement": 90,
    "etiquette": 88
}
```

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `legalAccuracy` | `number` (0–100) | Độ chính xác pháp lý |
| `evidenceUse` | `number` (0–100) | Sử dụng chứng cứ |
| `persuasion` | `number` (0–100) | Sức thuyết phục |
| `timeManagement` | `number` (0–100) | Quản lý thời gian |
| `etiquette` | `number` (0–100) | Phong thái ứng xử |

## 🔧 Các Lệnh Chạy

```bash
npm run dev      # Chạy ở chế độ phát triển
npm run build    # Xây dựng bản chính thức
npm run preview  # Xem trước bản chính thức
```

## 📄 Giấy Phép

MIT
