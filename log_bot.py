import discord
import os
import datetime
import psycopg2 
from dotenv import load_dotenv
import asyncio
import time
import google.generativeai as genai

# --- Cấu hình Cơ bản & Database ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID') # Lấy ID Admin từ biến môi trường

# --- Cấu hình AI ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TARGET_USERNAMES = ["rin", "am_lyn_"]
AI_MODEL_NAME = "gemini-1.5-flash-latest"
AI_CALL_COOLDOWN = 3 # Giây - Giãn cách gọi API Gemini

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
ai_model = None
last_ai_call_time = 0

# --- Khởi tạo Bot Discord ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True # BẮT BUỘC
intents.guilds = True
# intents.members = True # Không cần quyền members nữa nếu chỉ gửi DM

client = discord.Client(intents=intents)

# --- Hàm Kết nối và Thiết lập Database ---
async def setup_database():
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
        # Chỉ tạo bảng discord_logs
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

# --- Hàm Ghi Log vào Database (Giữ nguyên) ---
def log_message_to_db_sync(message):
    global conn, cursor
    # Thử kết nối lại nếu bị mất (logic đơn giản)
    if conn is None or conn.closed != 0:
        print("Mất kết nối DB, đang thử kết nối lại để ghi log...")
        if not asyncio.run(setup_database()):
             print("Không thể kết nối lại DB để ghi log.")
             return


    if not conn or not cursor or conn.closed != 0:
         print("CẢNH BÁO: Vẫn mất kết nối DB, bỏ qua ghi log tin nhắn.")
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

    except Exception as e:
        print(f"LỖI không xác định khi ghi log DB: {e}")


# --- Hàm Phân tích AI Gemini (Cập nhật Prompt) ---
async def check_message_relevance(message_content: str) -> bool:
    """Kiểm tra xem tin nhắn có đề cập hoặc liên quan tiêu cực đến các tên mục tiêu không."""
    global last_ai_call_time, ai_model
    current_time = time.time()

    if not ai_model: return False
    if current_time - last_ai_call_time < AI_CALL_COOLDOWN: return False
    last_ai_call_time = current_time

    target_names_str = ", ".join([f"'{name}'" for name in TARGET_USERNAMES])


    prompt = f"""
    Phân tích tin nhắn sau. Tin nhắn này có vẻ đang nói xấu, chỉ trích, phàn nàn, hoặc thể hiện thái độ tiêu cực một cách rõ ràng về người dùng có tên nằm trong danh sách [{target_names_str}] không?
    Chỉ cần trả lời bằng một từ duy nhất: "YES" nếu có vẻ liên quan tiêu cực, và "NO" nếu không hoặc không liên quan.

    Tin nhắn: "{message_content}"

    Câu trả lời (YES hoặc NO):
    """

    try:
        response = await ai_model.generate_content_async(
             contents=[prompt],
             generation_config=genai.types.GenerationConfig(temperature=0.2) 
        )
        analysis_result = response.text.strip().upper()
        return "YES" in analysis_result

    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}")
        # traceback.print_exc()
        return False

# --- Sự kiện Bot Discord ---
@client.event
async def on_ready():
    """Sự kiện khi bot kết nối thành công."""
    print(f'Đã đăng nhập với tư cách {client.user.name} (ID: {client.user.id})')
    print('------')
    if not await setup_database():
        print("CẢNH BÁO: Không thể thiết lập database. Log tin nhắn sẽ không hoạt động.")

    # Thiết lập AI Client
    global ai_model
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            ai_model = genai.GenerativeModel(AI_MODEL_NAME)
            await ai_model.generate_content_async("Hello") # Test API key
            print(f"Đã cấu hình Google Generative AI với model: {AI_MODEL_NAME}")
        except Exception as e:
            print(f"LỖI: Không thể cấu hình Google AI: {e}")
            ai_model = None
    else:
        print("CẢNH BÁO: GEMINI_API_KEY chưa được đặt. Tính năng AI sẽ bị vô hiệu hóa.")
        ai_model = None

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
    # Sử dụng create_task để không đợi log xong mới xử lý AI
    asyncio.create_task(client.loop.run_in_executor(None, log_message_to_db_sync, message))

    # --- BƯỚC 2: Phân tích AI và Gửi DM cho Admin ---
    if ai_model and ADMIN_USER_ID: 
        try:
            # Kiểm tra xem tin nhắn có vẻ tiêu cực về target không
            is_relevant_negative = await check_message_relevance(message.content)

            if is_relevant_negative:
                print(f"Phát hiện tin nhắn có thể liên quan tiêu cực đến {TARGET_USERNAMES} từ {message.author}.")

                # Lấy đối tượng User của Admin
                admin_user = client.get_user(ADMIN_USER_ID)
                if not admin_user:
                    try:
                        admin_user = await client.fetch_user(ADMIN_USER_ID)
                    except discord.NotFound:
                        print(f"LỖI: Không tìm thấy Admin với ID {ADMIN_USER_ID}.")
                        return # Không thể gửi DM nếu không tìm thấy admin
                    except discord.HTTPException:
                         print(f"LỖI: Lỗi mạng khi fetch Admin ID {ADMIN_USER_ID}.")
                         return

                # Tạo nội dung DM
                dm_content = (
                    f"**⚠️ Tin nhắn đáng chú ý về {', '.join(TARGET_USERNAMES)}:**\n"
                    f"👤 **Người gửi:** {message.author.mention} (`{message.author}`)\n"
                    f"📌 **Kênh:** {message.channel.mention} (`#{message.channel.name}`)\n"
                    f"🔗 **Link:** {message.jump_url}\n"
                    f"💬 **Nội dung:**\n```\n{message.content}\n```"
                )

                # Gửi DM cho Admin
                try:
                    await admin_user.send(dm_content)
                    print(f"Đã gửi DM thông báo cho Admin (ID: {ADMIN_USER_ID}).")
                except discord.Forbidden:
                    print(f"LỖI: Không thể gửi DM cho Admin (ID: {ADMIN_USER_ID}). Có thể Admin đã chặn bot hoặc tắt DM từ người lạ/server.")
                except discord.HTTPException as e:
                     print(f"LỖI: Lỗi mạng khi gửi DM cho Admin: {e}")
                except Exception as e:
                    print(f"Lỗi không xác định khi gửi DM: {e}")

        except Exception as e:
            print(f"Lỗi trong quá trình xử lý AI/DM cho tin nhắn {message.id}: {e}")



# --- Hàm Chính để Chạy Bot ---
async def main():
    if not TOKEN: print("LỖI: DISCORD_TOKEN chưa được đặt."); return
    if not ADMIN_USER_ID: print("CẢNH BÁO: ADMIN_USER_ID chưa được đặt, không thể gửi DM."); # Vẫn chạy

    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure: print("LỖI: Token Discord không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired: print("LỖI: Bot yêu cầu Privileged Gateway Intents (Message Content).")
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