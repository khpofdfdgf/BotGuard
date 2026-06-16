# Discord Moderation Bot – Nội Quy Server

Bot Discord tự động kiểm duyệt và hỗ trợ staff thực thi nội quy máy chủ.

## Cài Đặt

### 1. Cài Python packages
```bash
pip install -r requirements.txt
```

### 2. Cấu hình môi trường
```bash
# Sao chép file mẫu
copy .env.example .env
```

Mở `.env` và điền thông tin:

| Biến | Mô tả | Cách lấy |
|------|-------|----------|
| `DISCORD_TOKEN` | Token bot | [Discord Developer Portal](https://discord.com/developers/applications) |
| `GUILD_ID` | ID server | Chuột phải server → Copy Server ID |
| `MOD_LOG_CHANNEL_ID` | ID kênh mod-log | Chuột phải kênh → Copy Channel ID |
| `RULES_CHANNEL_ID` | ID kênh rules | Chuột phải kênh → Copy Channel ID |
| `APPEAL_CHANNEL_ID` | ID kênh kháng cáo | Chuột phải kênh → Copy Channel ID |
| `MOD_ROLE_ID` | ID role Moderator | Server Settings → Roles → Copy ID |
| `ADMIN_ROLE_ID` | ID role Admin | Server Settings → Roles → Copy ID |
| `MUTED_ROLE_ID` | ID role Muted | Tạo role "Muted" → Copy ID |

> **Lưu ý:** Bật **Developer Mode** trong Discord Settings → Advanced → Developer Mode

### 3. Bật Privileged Intents
Vào [Discord Developer Portal](https://discord.com/developers/applications) → Bot → Privileged Gateway Intents → Bật:
- ✅ Server Members Intent
- ✅ Message Content Intent

### 4. Mời Bot vào Server
Trong Developer Portal → OAuth2 → URL Generator:
- Scopes: `bot`, `applications.commands`
- Bot Permissions: `Administrator` (hoặc chọn từng quyền cụ thể)

### 5. Chạy bot
```bash
python bot.py
```

---

## Lệnh

### 📋 Cho tất cả thành viên
| Lệnh | Mô tả |
|------|-------|
| `/rules` hoặc `!rules` | Xem nội quy server |
| `/appeal` | Gửi kháng cáo (form Modal) |
| `/case [id]` | Xem thông tin case |
| `!help` | Xem danh sách lệnh |

### ⚖️ Cho Staff (Mod/Admin)
| Lệnh | Mô tả |
|------|-------|
| `/warn @user [lý do]` | Cảnh cáo thành viên |
| `/mute @user [phút] [lý do]` | Mute (timeout) |
| `/unmute @user` | Bỏ mute |
| `/kick @user [lý do]` | Kick thành viên |
| `/ban @user [lý do]` | Ban vĩnh viễn |
| `/unban [user_id] [lý do]` | Bỏ ban |
| `/warns @user` | Xem lịch sử cảnh cáo |
| `/clearwarns @user` | Xóa cảnh cáo |
| `/purge [số lượng]` | Xóa nhiều tin nhắn |

### 🛡️ Chỉ Admin
| Lệnh | Mô tả |
|------|-------|
| `/postrules` | Đăng nội quy vào kênh #rules chính thức |

---

## Hệ Thống Xử Phạt Tự Động

| Số Warn | Hành động |
|---------|-----------|
| 1 | Cảnh cáo + DM |
| 2 | Mute **1 giờ** |
| 3 | Mute **24 giờ** |
| 4 | Mute **7 ngày** |
| 5+ | **Ban** |

## Auto-Moderation

Bot tự động phát hiện và xử lý:
- 🚫 **Spam** – Gửi tin nhắn lặp lại ≥5 lần trong 5 giây
- 🔗 **Link độc hại** – IP grabbers, link Nitro giả
- 📢 **Quảng cáo** – Link invite Discord, Telegram
- 💬 **Ngôn từ thù ghét** – Từ khóa xúc phạm
- 🏛️ **Nội dung chính trị** – Bị xóa ngay
- 📱 **Thông tin cá nhân** – Số điện thoại người khác
- 📣 **Mention spam** – @mention quá nhiều người
- 😀 **Emoji spam** – Quá nhiều emoji

## Tùy Chỉnh

Chỉnh sửa `config.py` để:
- Thêm từ khóa vào `HATE_KEYWORDS` hoặc `POLITICS_KEYWORDS`
- Thêm domain vào `SUSPICIOUS_DOMAINS`
- Thay đổi ngưỡng spam (`SPAM_THRESHOLD`, `SPAM_WINDOW`)
- Thay đổi mức phạt trong `WARN_PUNISHMENTS`

---

## Cấu Trúc Dự Án

```
discord-bot/
├── bot.py                  # Entry point chính
├── config.py               # Cấu hình tập trung
├── utils.py                # Tiện ích dùng chung
├── requirements.txt
├── .env.example            # Template biến môi trường
├── .env                    # Cấu hình thực (KHÔNG commit lên git!)
├── bot.log                 # Log file
├── cogs/
│   ├── automod.py          # Kiểm duyệt tự động
│   ├── moderation.py       # Lệnh mod thủ công
│   ├── rules.py            # Hiển thị nội quy
│   ├── appeals.py          # Hệ thống kháng cáo
│   └── logging_events.py   # Ghi log sự kiện
└── data/
    ├── warnings.json       # Dữ liệu cảnh cáo
    └── cases.json          # Lịch sử cases
```
