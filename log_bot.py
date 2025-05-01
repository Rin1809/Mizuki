import discord
import os
import datetime
import psycopg2 
from dotenv import load_dotenv
import asyncio 

# --- Cấu hình ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
conn = None
cursor = None

# --- Khởi tạo Bot ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True 

client = discord.Client(intents=intents)

# --- Hàm Kết nối và Thiết lập Database ---
async def setup_database():
    """Kết nối đến database và tạo bảng nếu chưa tồn tại."""
    global conn, cursor
    if not DATABASE_URL:
        print("LỖI: Biến môi trường DATABASE_URL chưa được đặt.")
        return False

    try:
        print("Đang kết nối đến PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("Đã kết nối PostgreSQL thành công.")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_logs (
                message_id BIGINT PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                server_id BIGINT,
                server_name TEXT,
                channel_id BIGINT,
                channel_name TEXT,
                author_id BIGINT,
                author_name TEXT,
                content TEXT,
                attachment_urls TEXT
            )
        """)
        conn.commit() 
        print("Bảng 'discord_logs' đã được kiểm tra/tạo.")
        return True
    except psycopg2.Error as e:
        print(f"LỖI: Không thể kết nối hoặc thiết lập database: {e}")
        if conn:
            conn.close() # Đóng kết nối nếu có lỗi xảy ra
        conn = None
        cursor = None
        return False
    except Exception as e:
        print(f"LỖI không xác định khi thiết lập database: {e}")
        return False

async def close_database():
    """Đóng kết nối database khi bot tắt."""
    global conn, cursor
    if cursor:
        cursor.close()
        print("Đã đóng con trỏ database.")
    if conn:
        conn.close()
        print("Đã đóng kết nối database.")

# --- Hàm Ghi Log vào Database ---
def log_message_to_db(message):
    """Ghi thông tin tin nhắn vào database."""
    global conn, cursor
    if not conn or not cursor:
        print("CẢNH BÁO: Mất kết nối database, không thể ghi log.")
        return

    # Chuẩn bị dữ liệu
    message_id = message.id
    timestamp = message.created_at # discord.py trả về datetime timezone-aware (UTC)
    server_id = message.guild.id if message.guild else None
    server_name = message.guild.name if message.guild else 'Direct Message'
    channel_id = message.channel.id
    channel_name = message.channel.name if hasattr(message.channel, 'name') else f'DM with {message.author}'
    author_id = message.author.id
    author_name = str(message.author) # "Username#Discriminator"
    content = message.content
    # Ghép các URL đính kèm thành một chuỗi, phân tách bằng dấu phẩy hoặc ký tự khác
    attachment_urls = ", ".join([att.url for att in message.attachments]) if message.attachments else None

    # Câu lệnh SQL INSERT (sử dụng placeholders %s để tránh SQL injection)
    sql = """
        INSERT INTO discord_logs (
            message_id, timestamp, server_id, server_name, channel_id,
            channel_name, author_id, author_name, content, attachment_urls
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (message_id) DO NOTHING; -- Bỏ qua nếu message_id đã tồn tại (hiếm khi xảy ra với on_message)
    """
    # Dữ liệu dạng tuple theo đúng thứ tự placeholders
    data = (
        message_id, timestamp, server_id, server_name, channel_id,
        channel_name, author_id, author_name, content, attachment_urls
    )

    try:
        cursor.execute(sql, data)
        conn.commit()

    except psycopg2.Error as e:
        print(f"LỖI DB khi ghi log tin nhắn {message_id}: {e}")
        conn.rollback()

    except Exception as e:
        print(f"LỖI không xác định khi ghi log DB: {e}")
        conn.rollback()


# --- Sự kiện Bot ---
@client.event
async def on_ready():
    """Sự kiện khi bot kết nối thành công."""
    print(f'Đã đăng nhập với tư cách {client.user.name} (ID: {client.user.id})')
    print('------')
    # Thiết lập kết nối database khi bot sẵn sàng
    if not await setup_database():
        print("LỖI NGHIÊM TRỌNG: Không thể thiết lập database. Bot có thể không hoạt động đúng.")

    else:
        print("Bot đã sẵn sàng ghi log vào database.")


@client.event
async def on_message(message):
    """Sự kiện khi có tin nhắn mới."""
    # Bỏ qua tin nhắn từ chính bot
    if message.author == client.user:
        return
    log_message_to_db(message)

@client.event
async def on_disconnect():
    """Sự kiện khi bot mất kết nối."""
    print("Bot đã mất kết nối với Discord.")
    # Không cần đóng DB ở đây vì có thể kết nối lại

@client.event
async def on_resumed():
    """Sự kiện khi bot kết nối lại thành công."""
    print("Bot đã kết nối lại với Discord.")
    # Kiểm tra và có thể thiết lập lại kết nối DB 
    global conn
    if conn is None or conn.closed != 0: # Kiểm tra nếu kết nối bị đóng
        print("Kết nối database đã mất, đang thử kết nối lại...")
        await setup_database()


# --- Chạy Bot ---
async def main():
    if TOKEN is None:
        print("LỖI: Không tìm thấy DISCORD_TOKEN trong biến môi trường.")
        return
    if DATABASE_URL is None:
         print("LỖI: Không tìm thấy DATABASE_URL trong biến môi trường.")


    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure:
            print("LỖI: Token không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired:
             print("LỖI: Bot yêu cầu Privileged Gateway Intents.")
        except Exception as e:
            print(f"Đã xảy ra lỗi không xác định khi chạy bot: {e}")
        finally:
            # Đảm bảo đóng kết nối DB khi bot dừng hẳn
            await close_database()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Đã nhận tín hiệu dừng (Ctrl+C). Đang tắt bot...")
