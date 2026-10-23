# hermes-deepseek2api

Hermes Agent Provider & CLI for DeepSeek Web (`chat.deepseek.com`).
Reverse-engineered Web API gateway bypassing Cloud Code/Antigravity and providing fast OpenAI SSE completion streams for `deepseek-chat` (V3) and `deepseek-reasoner` (R1).

## Features

- **Direct Web API Authentication**: Automatic login with Email or Mobile + Password (Android client headers).
- **High-Performance PoW Engine**: Solves DeepSeek `DeepSeekHashV1` Proof-of-Work challenge using WebAssembly runtime (`sha3_wasm_bg.wasm`).
- **OpenAI Compatible Client**: Plugs directly into Hermes Agent via runtime interceptor and provider registry (`deepseek-web`, `deepseek`, `deepseek2api`).
- **Session Auto-Management**: Creates and cleans up chat sessions automatically per request.

## CLI Usage

### Cách 1: Dùng trực tiếp userToken từ trình duyệt (Khuyên dùng để né OTP/Captcha)

1. Mở [chat.deepseek.com](https://chat.deepseek.com) trên trình duyệt và đăng nhập.
2. Bấm **F12** -> Chuyển sang tab **Console** và chạy:
   ```javascript
   JSON.parse(localStorage.getItem("userToken")).value
   ```
   (hoặc vào tab **Application** -> **Local Storage** -> `https://chat.deepseek.com` -> copy giá trị key `userToken`).
3. Chạy lệnh:
   ```bash
   hermes deepseek set-token
   ```
   (Dán token vừa copy vào).

### Cách 2: Đăng nhập bằng Email/SĐT + Mật khẩu
```bash
hermes deepseek login
```
*(Nếu DeepSeek bắt xác minh OTP hoặc Captcha, hãy chuyển sang Cách 1)*

### Quản lý & Kiểm thử
```bash
# Danh sách tài khoản
hermes deepseek list

# Test chat completion
hermes deepseek test --prompt "Hello DeepSeek" --model deepseek-chat
```
