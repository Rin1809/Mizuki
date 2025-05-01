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

# --- Cấu hình AI ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TARGET_USERNAME = "Rin" 
AI_MODEL_NAME = "gemini-2.0-flash"
AI_CALL_COOLDOWN = 2 #

# Biến toàn cục cho kết nối DB và AI model
conn = None
cursor = None
ai_model = None
last_ai_call_time = 0

# --- Khởi tạo Bot Discord ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True 
intents.guilds = True
intents.members = True # BẮT BUỘC để thực hiện timeout/mute

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

        # Tạo bảng discord_logs (nếu chưa có)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_logs (
                message_id BIGINT PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL,
                server_id BIGINT, server_name TEXT, channel_id BIGINT, channel_name TEXT,
                author_id BIGINT, author_name TEXT, content TEXT, attachment_urls TEXT
            )
        """)

        # Tạo bảng user_warnings (nếu chưa có)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_warnings (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, guild_id BIGINT NOT NULL,
                warn_reason VARCHAR(100) NOT NULL, warn_count INTEGER NOT NULL DEFAULT 0,
                last_warned_at TIMESTAMPTZ, UNIQUE (user_id, guild_id, warn_reason)
            )
        """)
        conn.commit()
        print("Các bảng 'discord_logs' và 'user_warnings' đã được kiểm tra/tạo.")
        return True
    except psycopg2.Error as e:
        print(f"LỖI DB: Không thể kết nối hoặc thiết lập bảng: {e}")
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

# --- Hàm Ghi Log vào Database ---
def log_message_to_db(message):
    """Ghi thông tin tin nhắn vào bảng discord_logs."""
    global conn, cursor
    if not conn or not cursor or conn.closed != 0:
        print("CẢNH BÁO: Mất kết nối DB, không thể ghi log tin nhắn.")
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
        conn.commit()
    except psycopg2.Error as e:
        print(f"LỖI DB khi ghi log msg {message.id}: {e}")
        conn.rollback()
    except Exception as e:
        print(f"LỖI không xác định khi ghi log DB: {e}")
        conn.rollback()

# --- Hàm tương tác DB cho Warnings ---
def get_warning_count_sync(user_id: int, guild_id: int, reason: str) -> int:
    """Lấy số lần cảnh báo (phiên bản đồng bộ để chạy trong executor)."""
    global conn, cursor
    if not conn or not cursor or conn.closed != 0: return 0
    try:
        sql = "SELECT warn_count FROM user_warnings WHERE user_id = %s AND guild_id = %s AND warn_reason = %s;"
        cursor.execute(sql, (user_id, guild_id, reason))
        result = cursor.fetchone()
        return result[0] if result else 0
    except psycopg2.Error as e:
        print(f"Lỗi DB khi lấy warning count sync: {e}")
        conn.rollback()
        return 0

def increment_warning_count_sync(user_id: int, guild_id: int, reason: str):
    """Tăng số lần cảnh báo (phiên bản đồng bộ)."""
    global conn, cursor
    if not conn or not cursor or conn.closed != 0: return
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        sql = """
            INSERT INTO user_warnings (user_id, guild_id, warn_reason, warn_count, last_warned_at)
            VALUES (%s, %s, %s, 1, %s)
            ON CONFLICT (user_id, guild_id, warn_reason)
            DO UPDATE SET warn_count = user_warnings.warn_count + 1, last_warned_at = EXCLUDED.last_warned_at;
        """
        cursor.execute(sql, (user_id, guild_id, reason, now))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Lỗi DB khi tăng warning count sync: {e}")
        conn.rollback()

def reset_warning_count_sync(user_id: int, guild_id: int, reason: str):
    """Reset số lần cảnh báo về 0 (phiên bản đồng bộ)."""
    global conn, cursor
    if not conn or not cursor or conn.closed != 0: return
    try:
        sql = "UPDATE user_warnings SET warn_count = 0 WHERE user_id = %s AND guild_id = %s AND warn_reason = %s;"
        cursor.execute(sql, (user_id, guild_id, reason))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Lỗi DB khi reset warning count sync: {e}")
        conn.rollback()

# --- Hàm Phân tích AI Gemini ---
async def is_negative_towards_target(message_content: str) -> bool:
    """Kiểm tra tin nhắn có tiêu cực về TARGET_USERNAME không."""
    global last_ai_call_time, ai_model
    current_time = time.time()

    if not ai_model:
        return False

    # Cooldown API
    if current_time - last_ai_call_time < AI_CALL_COOLDOWN:
        return False
    last_ai_call_time = current_time

    # Prompt rõ ràng, yêu cầu YES/NO
    prompt = f"""
    Phân tích tin nhắn sau. Tin nhắn này có ý nói xấu, chỉ trích, lăng mạ, hoặc thể hiện thái độ tiêu cực dù là đùa giỡn, đối với người dùng tên '{TARGET_USERNAME}' không?
    Chỉ trả lời bằng một từ duy nhất: "YES" nếu có, và "NO" nếu không hoặc không liên quan.

    Tin nhắn: "{message_content}"

    Câu trả lời (YES hoặc NO):
    """

    try:
        response = await ai_model.generate_content_async(
             contents=[prompt],
             generation_config=genai.types.GenerationConfig(temperature=0.1)
        )
        analysis_result = response.text.strip().upper()
    

        return "YES" in analysis_result # Chỉ cần chứa "YES" là được

    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}")
        return False # Mặc định là không tiêu cực nếu lỗi

# --- Sự kiện Bot Discord ---
@client.event
async def on_ready():
    """Sự kiện khi bot kết nối thành công."""
    print(f'Đã đăng nhập với tư cách {client.user.name} (ID: {client.user.id})')
    print('------')
    # Thiết lập Database
    if not await setup_database():
        print("LỖI NGHIÊM TRỌNG: Không thể thiết lập database.")


    # Thiết lập AI Client
    global ai_model
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            ai_model = genai.GenerativeModel(AI_MODEL_NAME)
            # Thử gọi API nhỏ để kiểm tra key và model
            await ai_model.generate_content_async("Hello")
            print(f"Đã cấu hình và kiểm tra Google Generative AI với model: {AI_MODEL_NAME}")
        except Exception as e:
            print(f"LỖI: Không thể cấu hình hoặc kiểm tra Google AI: {e}")
            ai_model = None # Vô hiệu hóa AI nếu lỗi
    else:
        print("CẢNH BÁO: GEMINI_API_KEY chưa được đặt. Tính năng AI sẽ bị vô hiệu hóa.")
        ai_model = None

    print("Bot đã sẵn sàng!")


@client.event
async def on_message(message: discord.Message):

    # Bỏ qua tin nhắn từ chính bot hoặc DM
    if message.author.bot or message.guild is None:
        return

    # ---- BƯỚC 1: Ghi log gốc vào DB ----
    # Chạy DB log trong executor để không block event loop lâu
    await client.loop.run_in_executor(None, log_message_to_db, message)

    # ---- BƯỚC 2: Phân tích AI và Xử lý Cảnh báo/Mute ----
    if ai_model: # Chỉ chạy nếu AI được cấu hình
        try:
            is_negative = await is_negative_towards_target(message.content)

            if is_negative:
                print(f"Phát hiện nội dung tiêu cực về '{TARGET_USERNAME}' từ {message.author}: {message.content[:100]}...")
                guild_id = message.guild.id
                user_id = message.author.id
                # Lý do nhất quán để truy vấn DB
                warn_reason = f'negative_{TARGET_USERNAME.lower()}'

                # Lấy số lần cảnh báo hiện tại (chạy DB trong executor)
                current_warnings = await client.loop.run_in_executor(
                    None, get_warning_count_sync, user_id, guild_id, warn_reason
                )

                # --- Xử lý dựa trên số lần cảnh báo ---
                if current_warnings == 0:
                    # Lần 1: Cảnh báo + Tăng count
                    warning_msg = f"Ê {message.author.mention}, đừng nói xấu {TARGET_USERNAME} nha! Lần đầu tui nhắc đó. 😉"
                    try:
                        await message.channel.send(warning_msg)
                        await client.loop.run_in_executor(
                            None, increment_warning_count_sync, user_id, guild_id, warn_reason
                        )
                        print(f"Đã cảnh báo lần 1 cho {message.author} về {warn_reason}.")
                    except discord.Forbidden:
                        print(f"Lỗi quyền: Không thể gửi tin nhắn vào kênh {message.channel.name}")
                    except Exception as e:
                        print(f"Lỗi khi gửi cảnh báo lần 1: {e}")

                elif current_warnings == 1:
                    # Lần 2: Mute + Reset count
                    mute_minutes = 1
                    mute_duration = datetime.timedelta(minutes=mute_minutes)
                    mute_msg = f"Đã bảo là đừng nói xấu {TARGET_USERNAME} rồi mà {message.author.mention}! Tui mute {mute_minutes} phút để bình tĩnh lại nha. 😠"
                    try:
                        await message.channel.send(mute_msg) # Thông báo trước khi mute
                        await message.author.timeout(mute_duration, reason=f"Nói xấu {TARGET_USERNAME} lần 2")
                        print(f"Đã mute {message.author} trong {mute_minutes} phút.")
                        # Reset cảnh báo sau khi mute thành công
                        await client.loop.run_in_executor(
                            None, reset_warning_count_sync, user_id, guild_id, warn_reason
                        )
                        print(f"Đã reset cảnh báo cho {message.author} về {warn_reason}.")
                    except discord.Forbidden:
                        print(f"Lỗi quyền: Không thể Timeout/Mute {message.author}. Kiểm tra quyền 'Timeout Members' và vị trí role.")
                        await message.channel.send(f" Định mute {message.author.mention} mà tui không có quyền 'Timeout Members' mất rồi... 😢")
                    except discord.HTTPException as e:
                        print(f"Lỗi HTTP khi mute {message.author}: {e}")
                        await message.channel.send(f"Gặp lỗi khi mute {message.author.mention}, báo admin giùm tui nha.")
                    except Exception as e:
                        print(f"Lỗi không xác định khi xử lý mute lần 2: {e}")


        except Exception as e:
            print(f"Lỗi trong quá trình xử lý AI/cảnh báo cho tin nhắn {message.id}: {e}")


# --- Hàm Chính để Chạy Bot ---
async def main():
    if not TOKEN:
        print("LỖI: DISCORD_TOKEN chưa được đặt trong biến môi trường.")
        return
    if not DATABASE_URL:
        print("LỖI: DATABASE_URL chưa được đặt. Bot sẽ chạy nhưng không ghi log DB.")


    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure:
            print("LỖI: Token Discord không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired:
             print("LỖI: Bot yêu cầu Privileged Gateway Intents (Message Content, Server Members). Vui lòng bật trong Discord Developer Portal.")
        except Exception as e:
            print(f"Lỗi nghiêm trọng khi chạy bot: {e}")

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