# -*- coding: utf-8 -*-
import discord
import os
import datetime
import psycopg2 # Tùy chọn, nếu muốn ghi log vào DB
from dotenv import load_dotenv
import asyncio
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# import traceback # Bỏ comment nếu cần debug

# --- Tải biến môi trường ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL') # Không bắt buộc, chỉ dùng để log
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# ID của Admin (Rin) - Người mà bot sẽ chat cùng qua DM
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252') # <<-- Đặt ID của bạn ở đây hoặc trong .env

# --- Cấu hình AI & Chat ---
AI_MODEL_NAME = "gemini-1.5-flash-latest" # Model Gemini cho chat
DM_HISTORY_LIMIT = 15 # Giới hạn số lượt trao đổi (user + bot) trong lịch sử DM

# --- Chuyển đổi ID Admin ---
ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
        print(f"[CẤU HÌNH] ID Admin để chat DM: {ADMIN_USER_ID}")
    except ValueError:
        print(f"[LỖI] ADMIN_USER_ID '{ADMIN_USER_ID_STR}' không phải là số.")
else:
    print("[LỖI] ADMIN_USER_ID chưa được cấu hình.")

# --- Biến toàn cục ---
conn = None
cursor = None
ai_model = None
dm_conversation_history = {} # Lưu lịch sử chat DM {user_id: [messages]}

# --- Khởi tạo Bot Discord ---
intents = discord.Intents.default()
intents.messages = True          # Cần để đọc tin nhắn
intents.message_content = True   # BẮT BUỘC để đọc nội dung tin nhắn
intents.guilds = True            # Cần cho thông tin server/kênh (để log)
intents.dm_messages = True       # BẮT BUỘC để nhận tin nhắn DM
# intents.members = True         # Có thể không cần thiết nữa, nhưng giữ lại cũng ổn

client = discord.Client(intents=intents)

# --- Hàm Kết nối Database (Tùy chọn) ---
async def setup_database():
    global conn, cursor
    if not DATABASE_URL:
        print("[THÔNG TIN] Không có DATABASE_URL, chức năng ghi log DB bị bỏ qua.")
        return False
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        # Kiểm tra/tạo bảng log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_logs (
                message_id BIGINT PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL,
                server_id BIGINT, server_name TEXT, channel_id BIGINT, channel_name TEXT,
                author_id BIGINT, author_name TEXT, content TEXT, attachment_urls TEXT
            )""")
        print("[DB] Kết nối PostgreSQL và kiểm tra bảng log thành công.")
        return True
    except Exception as e:
        print(f"[LỖI DB] Không thể kết nối hoặc thiết lập: {e}")
        conn, cursor = None, None
        return False

async def close_database():
    global conn, cursor
    if cursor: cursor.close()
    if conn: conn.close()
    print("[DB] Đã đóng kết nối (nếu có).")

# --- Hàm Ghi Log vào Database (Tùy chọn, phiên bản đồng bộ) ---
def log_message_to_db_sync(message):
    global conn, cursor
    # Chỉ ghi log nếu có kết nối DB và tin nhắn từ server
    if conn is None or conn.closed != 0 or message.guild is None: return
    if not cursor or cursor.closed:
         try: cursor = conn.cursor()
         except Exception: return
    try:
        data = (
            message.id, message.created_at,
            message.guild.id, message.guild.name, message.channel.id, message.channel.name,
            message.author.id, str(message.author), message.content,
            ", ".join([att.url for att in message.attachments]) if message.attachments else None )
        sql = """
            INSERT INTO discord_logs (message_id, timestamp, server_id, server_name, channel_id,
            channel_name, author_id, author_name, content, attachment_urls)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING; """
        cursor.execute(sql, data)
    except Exception as e:
        print(f"[LỖI DB] Ghi log msg {message.id}: {e}")

# --- Hàm Cấu hình AI ---
def configure_ai():
    global ai_model
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            ai_model = genai.GenerativeModel(AI_MODEL_NAME)
            print(f"[AI] Đã cấu hình Gemini AI với model: {AI_MODEL_NAME}")
            return True
        except Exception as e:
            print(f"[LỖI AI] Không thể cấu hình Gemini: {e}")
            ai_model = None
            return False
    else:
        print("[CẢNH BÁO] GEMINI_API_KEY chưa được đặt. Chức năng chat AI bị vô hiệu hóa.")
        ai_model = None
        return False

# --- Hàm Tạo Phản Hồi DM bằng AI ---
async def generate_dm_response_with_ai(user_message: str, user_id: int) -> str | None:
    global dm_conversation_history
    if not ai_model: return "Xin lỗi, chức năng AI của mình chưa sẵn sàng."

    # Lấy hoặc tạo lịch sử chat
    history = dm_conversation_history.get(user_id, [])
    history.append({"role": "user", "parts": [user_message]})

    # Giới hạn lịch sử
    if len(history) > DM_HISTORY_LIMIT * 2: # *2 vì có user và model parts
        history = history[-(DM_HISTORY_LIMIT * 2):]

    # Context ban đầu cho AI biết vai trò
    initial_context = [
        {"role": "user", "parts": ["Bạn là Mizuki, một trợ lý AI thân thiện trong Discord. Bạn đang nói chuyện riêng với Admin (Rin) của server. Hãy trả lời một cách tự nhiên, gần gũi và hữu ích."]},
        {"role": "model", "parts": ["Dạ Rin! Mình Mizuki nè. Hôm nay Rin có chuyện gì muốn tâm sự hay cần mình giúp không ạ?"]},
    ]
    gemini_context = initial_context + history # Kết hợp context và lịch sử

    try:
        # Bắt đầu phiên chat với lịch sử (trừ tin nhắn cuối của user)
        chat_session = ai_model.start_chat(history=gemini_context[:-1])
        response = await chat_session.send_message_async(
             content=user_message, # Gửi tin nhắn cuối cùng
             generation_config=genai.types.GenerationConfig(temperature=0.8), # Sáng tạo cho chat
             safety_settings={ # Cài đặt an toàn
                 HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
             })
        bot_response = response.text.strip()

        # Lưu phản hồi vào lịch sử
        history.append({"role": "model", "parts": [bot_response]})
        dm_conversation_history[user_id] = history # Cập nhật lại

        return bot_response
    except Exception as e:
        print(f"[LỖI AI] Chat DM: {e}")
        # Xóa lịch sử nếu lỗi để tránh lặp lại
        if user_id in dm_conversation_history: del dm_conversation_history[user_id]
        return f"(Ái chà, mình đang bị lỗi chút xíu khi nghĩ câu trả lời: {e})"

# --- Hàm Gửi DM An Toàn (Chia nhỏ nếu cần) ---
async def send_dm_safe(target_channel: discord.DMChannel, content: str):
    if not target_channel: return
    try:
        if len(content) <= 2000:
            await target_channel.send(content)
        else: # Chia nhỏ tin nhắn nếu quá dài
            chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
            for i, chunk in enumerate(chunks):
                await target_channel.send(f"**(Phần {i+1}/{len(chunks)})**\n{chunk}")
                await asyncio.sleep(0.5) # Chờ chút giữa các phần
        # print(f"[DM] Đã gửi tới {target_channel.recipient}.") # Có thể bật nếu cần debug
    except Exception as e:
        print(f"[LỖI DM] Gửi tới {target_channel.recipient}: {e}")

# --- Sự kiện Bot ---
@client.event
async def on_ready():
    print(f'>>> Đã đăng nhập: {client.user.name} ({client.user.id}) <<<')
    await setup_database() # Thiết lập DB (nếu có)
    configure_ai() # Thiết lập AI
    if not ADMIN_USER_ID: print(">>> LỖI: ADMIN_USER_ID KHÔNG HỢP LỆ! Chức năng chat DM sẽ không hoạt động. <<<")
    if not ai_model: print(">>> CẢNH BÁO: AI CHƯA SẴN SÀNG! Chat DM sẽ không hoạt động. <<<")
    print(">>> Bot đã sẵn sàng! <<<")

@client.event
async def on_message(message: discord.Message):
    # Bỏ qua tin nhắn từ chính bot
    if message.author.bot:
        return

    # --- Xử lý tin nhắn trong SERVER (Chỉ để ghi log) ---
    if message.guild:
        # Ghi log vào DB (nếu bật DB)
        if conn:
            # Chạy ghi log trong nền để không làm chậm bot
            asyncio.create_task(client.loop.run_in_executor(None, log_message_to_db_sync, message))
        # Không làm gì khác với tin nhắn server

    # --- Xử lý tin nhắn TRỰC TIẾP (DM) từ ADMIN ---
    elif isinstance(message.channel, discord.DMChannel) and message.author.id == ADMIN_USER_ID:
        print(f"[DM NHẬN] Từ Admin ({ADMIN_USER_ID}): {message.content[:50]}...")
        if ai_model:
            # Hiển thị "Bot is typing..."
            async with message.channel.typing():
                # Gọi AI để tạo phản hồi
                bot_response = await generate_dm_response_with_ai(message.content, ADMIN_USER_ID)
                if bot_response:
                    # Gửi phản hồi lại cho Admin
                    await send_dm_safe(message.channel, bot_response)
                else: # Trường hợp generate_dm_response_with_ai trả về None hoặc lỗi
                    await message.channel.send("Xin lỗi Rin, mình không nghĩ ra câu trả lời được...")
        else:
            # Phản hồi nếu AI không được cấu hình
             await message.channel.send("Rin ơi, bộ não AI của mình đang tạm thời không hoạt động...")

# --- Hàm chạy chính ---
async def main():
    # Kiểm tra các biến môi trường bắt buộc
    if not TOKEN:
        print("[LỖI] Thiếu DISCORD_TOKEN. Không thể khởi động.")
        return
    if not ADMIN_USER_ID:
        print("[LỖI] Thiếu ADMIN_USER_ID. Chức năng chat DM sẽ không hoạt động.")
        # Có thể vẫn cho bot chạy để log DB nếu muốn
        # return
    if not GEMINI_API_KEY:
         print("[CẢNH BÁO] Thiếu GEMINI_API_KEY. Chức năng chat DM sẽ không hoạt động.")

    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure: print("[LỖI] Token Discord không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired: print("[LỖI] Thiếu quyền Privileged Intents (Message Content?).")
        except Exception as e: print(f"[LỖI NGHIÊM TRỌNG] Khi chạy bot: {e}")
        finally:
            await close_database() # Đảm bảo đóng DB khi dừng

if __name__ == "__main__":
    print("--- Khởi động Bot Discord (Log DB & Chat DM AI) ---")
    try:
        asyncio.run(main())
    except KeyboardInterrupt: print("\n--- Nhận tín hiệu dừng (Ctrl+C) ---")
    finally: print("--- Bot đã tắt ---")