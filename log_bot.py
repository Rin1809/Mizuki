import discord
import os
import datetime
from dotenv import load_dotenv

# --- Cấu hình ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_DIR = os.getenv('LOG_DIRECTORY', './server_logs') # Mặc định là ./server_logs nếu không có trong .env

# Tạo thư mục log nếu chưa tồn tại
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    print(f"Đã tạo thư mục log tại: {LOG_DIR}")

# --- Khởi tạo Bot ---
# Xác định các Intents cần thiết (Quan trọng!)
intents = discord.Intents.default()
intents.messages = True        # Để nhận sự kiện tin nhắn
intents.message_content = True # Để đọc nội dung tin nhắn (Cần bật trong Developer Portal)
intents.guilds = True          # Để truy cập thông tin server/kênh
intents.members = True         # Để lấy thông tin thành viên (tùy chọn, hữu ích nếu muốn log tên đầy đủ)

# Tạo đối tượng bot
client = discord.Client(intents=intents)

# --- Hàm ghi log ---
def write_log(server_name, channel_name, timestamp, author, content, attachments):
    """Ghi một dòng log vào file tương ứng."""
    try:
        # Tạo đường dẫn thư mục cho server
        server_log_dir = os.path.join(LOG_DIR, sanitize_filename(server_name))
        if not os.path.exists(server_log_dir):
            os.makedirs(server_log_dir)

        # Tạo tên file log cho kênh
        log_file_path = os.path.join(server_log_dir, f"{sanitize_filename(channel_name)}.log")

        # Định dạng thời gian
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Định dạng nội dung log
        log_entry = f"[{formatted_time}] [{author}]: {content}"

        # Thêm thông tin về tệp đính kèm (nếu có)
        if attachments:
            attach_info = ", ".join([f"{att.filename} ({att.url})" for att in attachments])
            log_entry += f" [Attachments: {attach_info}]"

        # Ghi vào file (chế độ append 'a', encoding utf-8 để hỗ trợ ký tự đặc biệt)
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    except Exception as e:
        print(f"LỖI khi ghi log cho kênh {channel_name} trong server {server_name}: {e}")

def sanitize_filename(name):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')
    # name = name[:100] # Ví dụ giới hạn 100 ký tự
    return name

# --- Sự kiện Bot ---

@client.event
async def on_ready():
    """Sự kiện được kích hoạt khi bot kết nối thành công với Discord."""
    print(f'Đã đăng nhập với tư cách {client.user.name} (ID: {client.user.id})')
    print(f'Bot đang theo dõi logs...')
    print('------')

@client.event
async def on_message(message):
    """Sự kiện được kích hoạt mỗi khi có tin nhắn mới."""
    # Bỏ qua tin nhắn từ chính bot để tránh vòng lặp vô hạn
    if message.author == client.user:
        return

    # Chỉ xử lý tin nhắn trong server (bỏ qua tin nhắn riêng)
    if message.guild is None:
        return

    # Lấy thông tin cần thiết
    server_name = message.guild.name
    channel_name = message.channel.name
    timestamp = message.created_at # Đây là thời gian UTC
    author_name = str(message.author) # Định dạng "Username#Discriminator"
    content = message.content
    attachments = message.attachments # Danh sách các tệp đính kèm

    # Ghi log
    print(f"Log: [{server_name} > #{channel_name}] {author_name}: {content[:50]}...") # In ra console để biết bot đang chạy
    write_log(server_name, channel_name, timestamp, author_name, content, attachments)

# --- Chạy Bot ---
if __name__ == "__main__":
    if TOKEN is None:
        print("LỖI: Không tìm thấy DISCORD_TOKEN trong file .env hoặc biến môi trường.")
    else:
        try:
            client.run(TOKEN)
        except discord.errors.LoginFailure:
            print("LỖI: Token không hợp lệ. Vui lòng kiểm tra lại token trong file .env.")
        except discord.errors.PrivilegedIntentsRequired:
             print("LỖI: Bot yêu cầu Privileged Gateway Intents (Message Content, Server Members).")
             print("Vui lòng bật các Intent này trong Discord Developer Portal cho bot của bạn.")
        except Exception as e:
            print(f"Đã xảy ra lỗi không xác định khi chạy bot: {e}")