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

## 🔧 Các Lệnh Chạy

```bash
npm run dev      # Chạy ở chế độ phát triển
npm run build    # Xây dựng bản chính thức
npm run preview  # Xem trước bản chính thức
```

## 📄 Giấy Phép

MIT
