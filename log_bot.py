import discord
import os
import datetime
from dotenv import load_dotenv # Giữ lại để có thể chạy thử local với file .env

# --- Cấu hình ---
# Tải biến môi trường từ file .env (nếu có, hữu ích khi chạy local)
# Trên Railway, biến môi trường sẽ được cung cấp trực tiếp
load_dotenv()

# Lấy token từ biến môi trường. Đây là cách an toàn và cần thiết cho Railway.
TOKEN = os.getenv('DISCORD_TOKEN')

# --- Khởi tạo Bot ---
# Xác định các Intents cần thiết. BẮT BUỘC phải bật trên Discord Developer Portal!
intents = discord.Intents.default()
intents.messages = True        # Cho phép nhận sự kiện tin nhắn
intents.message_content = True # Cho phép đọc NỘI DUNG tin nhắn (Privileged Intent)
intents.guilds = True          # Cho phép truy cập thông tin server/kênh
intents.members = True         # Cho phép truy cập thông tin thành viên (Privileged Intent - hữu ích để lấy tên đầy đủ)

# Tạo đối tượng bot với các Intents đã khai báo
client = discord.Client(intents=intents)

# --- Sự kiện Bot ---

@client.event
async def on_ready():
    """
    Sự kiện được kích hoạt một lần khi bot đã kết nối thành công
    với Discord và sẵn sàng hoạt động.
    """
    print(f'--------------------------------------------------')
    print(f'Đã đăng nhập thành công với tư cách:')
    print(f'Tên Bot: {client.user.name}')
    print(f'ID Bot : {client.user.id}')
    print(f'--------------------------------------------------')
    print(f'Bot đang lắng nghe tin nhắn và sẽ in logs ra console...')
    print('--------------------------------------------------')

@client.event
async def on_message(message):
    """
    Sự kiện được kích hoạt mỗi khi có một tin nhắn mới được gửi
    trong bất kỳ kênh nào mà bot có thể thấy.
    """
    # 1. Bỏ qua tin nhắn từ chính bot để tránh vòng lặp vô hạn
    if message.author == client.user:
        return

    # 2. Chỉ xử lý tin nhắn trong server (Guild), bỏ qua tin nhắn riêng (DM)
    if message.guild is None:
        print(f"[DM] [{message.author}]: {message.content[:50]}...") # Tùy chọn: Log cả DM nếu muốn
        return

    # 3. Lấy thông tin cần thiết từ tin nhắn
    try:
        server_name = message.guild.name
        # Đôi khi kênh bị xóa ngay sau khi nhắn, channel có thể là None
        channel_name = message.channel.name if message.channel else "Kênh_Không_Xác_Định"

        # Lấy thời gian tin nhắn được tạo (UTC) và định dạng nó
        timestamp_utc = message.created_at
        formatted_time = timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC") # Định dạng chuẩn ISO 8601 dễ đọc

        author_name = str(message.author) # Định dạng "Username#Discriminator"
        content = message.content         # Nội dung tin nhắn
        attachments = message.attachments # Danh sách các file đính kèm

        # 4. Định dạng dòng log để in ra console
        log_entry = f"[{formatted_time}] [{server_name} > #{channel_name}] [{author_name}]: {content}"

        # Nếu có file đính kèm, thêm thông tin vào log
        if attachments:
            # Lấy danh sách tên file và URL (URL có thể hết hạn sau một thời gian)
            attach_info = ", ".join([f"{att.filename} ({att.url})" for att in attachments])
            log_entry += f" [Attachments: {attach_info}]"

        # 5. In dòng log ra console (stdout)
        # Railway sẽ tự động bắt output này và hiển thị trong phần Logs của service
        print(log_entry)

    except AttributeError as e:
        # Xử lý trường hợp không thể truy cập thuộc tính nào đó (ví dụ: message.guild bị None?)
        print(f"[ERROR] Không thể xử lý tin nhắn ID {message.id}. Lỗi thuộc tính: {e}")
    except Exception as e:
        # Bắt các lỗi không mong muốn khác trong quá trình xử lý tin nhắn
        print(f"[ERROR] Lỗi không xác định khi xử lý tin nhắn ID {message.id}: {e}")


# --- Chạy Bot ---
if __name__ == "__main__":
    print("Đang khởi động bot...")
    if TOKEN is None:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("LỖI NGHIÊM TRỌNG: Không tìm thấy biến môi trường 'DISCORD_TOKEN'.")
        print("Trên Railway: Hãy đảm bảo bạn đã thêm biến 'DISCORD_TOKEN' trong tab 'Variables'.")
        print("Khi chạy local: Hãy đảm bảo bạn có file '.env' chứa 'DISCORD_TOKEN=YourTokenHere'.")
        print("Bot không thể khởi động.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    else:
        try:
            # Chạy bot bằng token đã lấy được
            client.run(TOKEN)
        except discord.errors.LoginFailure:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("LỖI: Token Discord không hợp lệ.")
            print("Vui lòng kiểm tra lại giá trị của biến môi trường 'DISCORD_TOKEN'.")
            print("Token có thể đã bị thay đổi hoặc nhập sai.")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        except discord.errors.PrivilegedIntentsRequired:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("LỖI: Bot thiếu Privileged Gateway Intents.")
            print("Vui lòng truy cập Discord Developer Portal -> Application của bạn -> Tab 'Bot'.")
            print("Bật CẢ HAI tùy chọn: 'MESSAGE CONTENT INTENT' và 'SERVER MEMBERS INTENT'.")
            print("Sau đó lưu thay đổi và deploy lại bot trên Railway (hoặc khởi động lại nếu chạy local).")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        except Exception as e:
            # Bắt các lỗi khác có thể xảy ra khi khởi động (ví dụ: lỗi mạng)
            print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"LỖI KHÔNG XÁC ĐỊNH KHI KHỞI ĐỘNG BOT: {e}")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")