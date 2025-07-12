# 🔑 Hướng dẫn lấy API Keys

## 1. 🤖 Together AI (LLM) - **BẮT BUỘC**

### Cách lấy:
1. Truy cập: https://api.together.xyz/
2. Đăng ký tài khoản (có thể dùng GitHub)
3. Vào phần **API Keys** 
4. Click **Create new key**
5. Copy API key

### Chi phí:
- **Free tier**: $5 credit khi đăng ký
- **Qwen2.5-72B**: ~$0.9/1M tokens
- **Dự tính**: Khoảng $2-5 cho cả hackathon

---

## 2. 🔍 SerpAPI (Web Search) - **BẮT BUỘC**

### Cách lấy:
1. Truy cập: https://serpapi.com/
2. Đăng ký free account
3. Vào **Dashboard** → **API Key**
4. Copy key

### Chi phí:
- **Free tier**: 100 searches/tháng
- **Paid**: $50/tháng cho 5000 searches
- **Tip**: Dùng free tier cho demo

---

## 3. 💱 ExchangeRate-API (Currency) - **BẮT BUỘC**

### Cách lấy:
1. Truy cập: https://app.exchangerate-api.com/
2. Đăng ký free account
3. Copy API key từ dashboard

### Chi phí:
- **Free tier**: 2000 requests/tháng
- **Hoàn toàn đủ** cho hackathon

---

## 4. 📧 SendGrid (Email) - **BẮT BUỘC**

### Cách lấy:
1. Truy cập: https://sendgrid.com/
2. Đăng ký free account
3. Vào **Settings** → **API Keys**
4. Create new API key với **Full Access**
5. **Verify email domain** (quan trọng!)

### Chi phí:
- **Free tier**: 100 emails/ngày
- **Đủ dùng** cho hackathon

---

## 🚀 Setup nhanh:

### Bước 1: Copy file môi trường
```bash
cp .env.example .env
```

### Bước 2: Điền API keys vào file .env
```bash
# Mở file .env và điền:
TOGETHER_API_KEY=sk-xxx... 
SERPAPI_KEY=xxx...
EXCHANGE_RATE_API_KEY=xxx...
SENDGRID_API_KEY=SG.xxx...
SENDGRID_FROM_EMAIL=your-email@gmail.com
```

### Bước 3: Test APIs
```bash
python -m src.utils.test_apis
```

---

## ⚠️ Lưu ý quan trọng:

### 🔒 Bảo mật:
- **KHÔNG commit** file `.env` lên GitHub
- File `.env` đã được add vào `.gitignore`

### 💰 Tiết kiệm chi phí:
- Dùng **free tiers** cho demo
- **Cache results** để giảm API calls
- **Rate limiting** đã được implement

### 🛠️ Backup plan:
- Nếu SerpAPI hết free quota → dùng Google Custom Search API
- Nếu SendGrid có vấn đề → dùng SMTP Gmail
- Nếu Together AI chậm → fallback local LLM

---

## 📞 Hỗ trợ:

Nếu gặp vấn đề khi lấy API keys:
1. Check **spam folder** cho email verification
2. **VPN** nếu bị block geo-location  
3. Dùng **GitHub account** để đăng ký nhanh hơn

**Tổng thời gian setup**: ~15-20 phút
**Tổng chi phí**: $0-10 (chủ yếu là free tiers)