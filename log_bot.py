import discord
import os
import datetime
import psycopg2 
from dotenv import load_dotenv
import asyncio


# --- Cấu hình Cơ bản & Database ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID') # Lấy ID Admin

# --- Cấu hình Từ khóa Cần Thông báo ---
# Thêm bất kỳ từ khóa nào  muốn theo dõi
ALERT_KEYWORDS = ["admin", "rin", "misuzu", "Rin", "Mizusu", "ad", "Ad", "Admin"]
print(f"Sẽ cảnh báo khi phát hiện các từ khóa: {ALERT_KEYWORDS}")

# --- Chuyển đổi ID Admin ---
ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
        print(f"Đã cấu hình gửi DM tới Admin ID: {ADMIN_USER_ID}")
    except ValueError:
        print("LỖI: ADMIN_USER_ID không phải là số hợp lệ.")
else:
    print("CẢNH BÁO: ADMIN_USER_ID chưa được đặt. Bot sẽ không thể gửi DM.")

# Biến toàn cục
conn = None
cursor = None

# --- Khởi tạo Bot Discord ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True 
intents.guilds = True


client = discord.Client(intents=intents)

# --- Hàm Kết nối và Thiết lập Database (Giữ nguyên) ---
async def setup_database():
    """Kết nối đến database và tạo bảng discord_logs nếu chưa tồn tại."""
    global conn, cursor
    if not DATABASE_URL:
        print("LỖI: DATABASE_URL chưa được đặt.")
        return False
    try:
        print("Đang kết nối đến PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Đã kết nối PostgreSQL thành công.")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_logs (
                message_id BIGINT PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL,
                server_id BIGINT, server_name TEXT, channel_id BIGINT, channel_name TEXT,
                author_id BIGINT, author_name TEXT, content TEXT, attachment_urls TEXT
            )
        """)
        print("Bảng 'discord_logs' đã được kiểm tra/tạo.")
        return True
    except psycopg2.OperationalError as e:
         print(f"LỖI DB: Không thể kết nối (OperationalError): {e}")
         conn, cursor = None, None
         return False
    except psycopg2.Error as e:
        print(f"LỖI DB: Không thể thiết lập bảng discord_logs: {e}")
        if conn: conn.close()
        conn, cursor = None, None
        return False
    except Exception as e:
        print(f"LỖI không xác định khi thiết lập database: {e}")
        return False

async def close_database():
    """Đóng kết nối database."""
    global conn, cursor
    if cursor: cursor.close(); print("Đã đóng con trỏ DB.")
    if conn: conn.close(); print("Đã đóng kết nối DB.")
    conn, cursor = None, None

# --- Hàm Ghi Log vào Database  ---
def log_message_to_db_sync(message):
    """Ghi thông tin tin nhắn vào bảng discord_logs (phiên bản đồng bộ)."""
    global conn, cursor
    if conn is None or conn.closed != 0:
        print("CẢNH BÁO: Mất kết nối DB, không thể ghi log tin nhắn.")
        return

    if not cursor or cursor.closed:
         try:
             cursor = conn.cursor() 
         except Exception as e:
             print(f"Lỗi khi tạo lại cursor DB: {e}")
             return


    data = (
        message.id, message.created_at,
        message.guild.id if message.guild else None,
        message.guild.name if message.guild else 'Direct Message',
        message.channel.id,
        message.channel.name if hasattr(message.channel, 'name') else f'DM with {message.author}',
        message.author.id, str(message.author), message.content,
        ", ".join([att.url for att in message.attachments]) if message.attachments else None
    )
    sql = """
        INSERT INTO discord_logs (message_id, timestamp, server_id, server_name, channel_id,
        channel_name, author_id, author_name, content, attachment_urls)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (message_id) DO NOTHING;
    """
    try:
        cursor.execute(sql, data)
    except psycopg2.Error as e:
        print(f"LỖI DB khi ghi log msg {message.id}: {e}")
        # Không rollback nếu autocommit
        # Cân nhắc đóng và mở lại kết nối nếu lỗi nghiêm trọng
    except Exception as e:
        print(f"LỖI không xác định khi ghi log DB: {e}")

# --- Sự kiện Bot Discord ---
@client.event
async def on_ready():
    """Sự kiện khi bot kết nối thành công."""
    print(f'Đã đăng nhập với tư cách {client.user.name} (ID: {client.user.id})')
    print('------')
    if not await setup_database():
        print("CẢNH BÁO: Không thể thiết lập database. Log tin nhắn sẽ không hoạt động.")

    print("Bot đã sẵn sàng!")
    if not ADMIN_USER_ID:
        print(">>> LƯU Ý: ADMIN_USER_ID chưa được cấu hình, bot không thể gửi DM thông báo! <<<")


@client.event
async def on_message(message: discord.Message):
    """Sự kiện khi có tin nhắn mới."""
    # Bỏ qua tin nhắn từ bot hoặc DM
    if message.author.bot or message.guild is None:
        return

    # --- BƯỚC 1: Ghi log gốc vào DB (chạy nền) ---
    asyncio.create_task(client.loop.run_in_executor(None, log_message_to_db_sync, message))

    # --- BƯỚC 2: Kiểm tra Từ khóa và Gửi DM cho Admin ---
    if ADMIN_USER_ID: # Chỉ chạy nếu ID Admin được cấu hình
        content_lower = message.content.lower() # Chuyển sang chữ thường để kiểm tra
        found_keyword = None

        # Kiểm tra từng từ khóa
        for keyword in ALERT_KEYWORDS:
            if keyword in content_lower:
                found_keyword = keyword
                break # Dừng lại ngay khi tìm thấy một từ khóa

        # Nếu tìm thấy từ khóa
        if found_keyword:
            print(f"Phát hiện từ khóa '{found_keyword}' trong tin nhắn từ {message.author}.")

            # Lấy đối tượng User của Admin
            admin_user = client.get_user(ADMIN_USER_ID)
            if not admin_user:
                try:
                    admin_user = await client.fetch_user(ADMIN_USER_ID)
                except discord.NotFound:
                    print(f"LỖI: Không tìm thấy Admin với ID {ADMIN_USER_ID}.")
                    return
                except discord.HTTPException:
                     print(f"LỖI: Lỗi mạng khi fetch Admin ID {ADMIN_USER_ID}.")
                     return

            # Tạo nội dung DM
            dm_content = (
                f"**ℹ️ Phát hiện từ khóa '{found_keyword}':**\n"
                f"👤 **Người gửi:** {message.author.mention} (`{message.author}`)\n"
                f"📌 **Kênh:** {message.channel.mention} (`#{message.channel.name}`)\n"
                f"🔗 **Link:** {message.jump_url}\n"
                f"💬 **Nội dung:**\n```\n{message.content}\n```"
            )

            # Gửi DM cho Admin
            try:
                await admin_user.send(dm_content)
                print(f"Đã gửi DM thông báo từ khóa cho Admin (ID: {ADMIN_USER_ID}).")
            except discord.Forbidden:
                print(f"LỖI: Không thể gửi DM cho Admin (ID: {ADMIN_USER_ID}). Kiểm tra cài đặt chặn/DM.")
            except discord.HTTPException as e:
                 print(f"LỖI: Lỗi mạng khi gửi DM cho Admin: {e}")
            except Exception as e:
                print(f"Lỗi không xác định khi gửi DM: {e}")



# --- Hàm Chính để Chạy Bot ---
async def main():
    if not TOKEN: print("LỖI: DISCORD_TOKEN chưa được đặt."); return
    if not ADMIN_USER_ID: print("CẢNH BÁO: ADMIN_USER_ID chưa được đặt, không thể gửi DM.");

    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure: print("LỖI: Token Discord không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired: print("LỖI: Bot yêu cầu Privileged Gateway Intent 'Message Content'.")
        except Exception as e: print(f"Lỗi nghiêm trọng khi chạy bot: {e}")
        finally:
            print("Đang đóng kết nối database...")
            await close_database()

if __name__ == "__main__":
    print("Đang khởi động bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã nhận tín hiệu dừng (Ctrl+C). Bot đang tắt...")
    finally:
        print("Bot đã tắt.")