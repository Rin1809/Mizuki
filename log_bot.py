import discord
import os
import datetime
import psycopg2 
from dotenv import load_dotenv
import asyncio
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Tải biến môi trường ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL') # Không bắt buộc
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# ID của Admin (Rin) - Nên đặt trong file .env hoặc biến môi trường Railway
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252')

# --- Cấu hình chính ---
ALERT_KEYWORDS = ["admin", "rin", "misuzu"] # Từ khóa cần theo dõi (chữ thường)
AI_MODEL_NAME = "gemini-2.0-flash"    # Model Gemini
CONTEXT_MESSAGE_LIMIT = 50                   # Số tin nhắn lấy trước/sau khi phát hiện từ khóa
DM_HISTORY_LIMIT = 10                        # Giới hạn lịch sử chat DM với Admin

# --- Chuyển đổi ID Admin ---
ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
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
intents.guilds = True            # Cần cho thông tin server/kênh
intents.dm_messages = True       # BẮT BUỘC để nhận tin nhắn DM
intents.members = True           # Cần để lấy thông tin người dùng (vd: khi gửi DM)

client = discord.Client(intents=intents)

# --- Hàm Kết nối Database (Tùy chọn) ---
async def setup_database():
    global conn, cursor
    if not DATABASE_URL:
        print("[THÔNG TIN] Không có DATABASE_URL, bỏ qua kết nối DB.")
        return False
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        # Kiểm tra/tạo bảng log (nếu dùng)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_logs (
                message_id BIGINT PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL,
                server_id BIGINT, server_name TEXT, channel_id BIGINT, channel_name TEXT,
                author_id BIGINT, author_name TEXT, content TEXT, attachment_urls TEXT
            )""")
        print("[DB] Kết nối PostgreSQL và kiểm tra bảng thành công.")
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
    if conn is None or conn.closed != 0: return
    if not cursor or cursor.closed:
         try: cursor = conn.cursor()
         except Exception: return
    try:
        data = (
            message.id, message.created_at,
            message.guild.id if message.guild else None,
            message.guild.name if message.guild else 'Direct Message',
            message.channel.id,
            message.channel.name if hasattr(message.channel, 'name') else f'DM with {message.author}',
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
        print("[CẢNH BÁO] GEMINI_API_KEY chưa được đặt. AI vô hiệu hóa.")
        ai_model = None
        return False

# --- Hàm Lấy Ngữ Cảnh Tin Nhắn ---
async def fetch_context_messages(message: discord.Message, limit_each_side: int) -> list[discord.Message]:
    context = []
    try:
        history = [msg async for msg in message.channel.history(limit=limit_each_side * 2 + 1, around=message)]
        context = sorted(history, key=lambda m: m.created_at)
    except Exception as e:
        print(f"[LỖI] Lấy lịch sử kênh {message.channel.mention}: {e}")
    return context

# --- Hàm Tóm Tắt Hội Thoại bằng AI ---
async def summarize_conversation_with_ai(messages: list[discord.Message], trigger_keyword: str, trigger_message: discord.Message) -> str | None:
    if not ai_model or not messages: return None

    formatted_conversation = f"**Ngữ cảnh từ kênh #{trigger_message.channel.name} server '{trigger_message.guild.name}'**\n"
    formatted_conversation += f"**Tin nhắn gốc (ID: {trigger_message.id}) chứa '{trigger_keyword}':**\n"
    formatted_conversation += f"[{trigger_message.created_at.strftime('%H:%M')}] {trigger_message.author}: {trigger_message.content}\n"
    formatted_conversation += "\n**Hội thoại xung quanh:**\n"
    for msg in messages:
        formatted_conversation += f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}\n"

    prompt = f"""Bạn là trợ lý AI, đọc đoạn hội thoại Discord sau. Tin nhắn gốc chứa từ khóa '{trigger_keyword}'.
Hãy tóm tắt ngắn gọn (3-5 câu) nội dung liên quan đến '{trigger_keyword}' hoặc các chủ đề được bàn cùng nó để Admin nắm thông tin.

Đoạn hội thoại:
---
{formatted_conversation}
---
Bản tóm tắt:"""

    try:
        response = await ai_model.generate_content_async(
            contents=[prompt],
            generation_config=genai.types.GenerationConfig(temperature=0.5),
            safety_settings={ # Chặn nội dung không phù hợp
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            })
        return response.text.strip()
    except Exception as e:
        print(f"[LỖI AI] Tóm tắt: {e}")
        return f"(Lỗi khi tóm tắt bằng AI: {e})"

# --- Hàm Tạo Phản Hồi DM bằng AI ---
async def generate_dm_response_with_ai(user_message: str, user_id: int) -> str | None:
    global dm_conversation_history
    if not ai_model: return "Xin lỗi, chức năng AI của mình chưa sẵn sàng."

    history = dm_conversation_history.get(user_id, [])
    history.append({"role": "user", "parts": [user_message]})

    # Giới hạn lịch sử
    if len(history) > DM_HISTORY_LIMIT * 2:
        history = history[-(DM_HISTORY_LIMIT * 2):]

    # Context ban đầu cho AI biết vai trò
    initial_context = [
        {"role": "user", "parts": ["Bạn là Mizuki, trợ lý AI thân thiện trong Discord, đang nói chuyện riêng với Admin (Rin). Hãy trả lời tự nhiên và hữu ích."]},
        {"role": "model", "parts": ["Dạ Rin! Mizuki nghe đây ạ. Rin cần mình hỗ trợ gì không?"]},
    ]
    gemini_context = initial_context + history # Kết hợp context và lịch sử

    try:
        # Bắt đầu phiên chat với lịch sử (trừ tin nhắn cuối của user)
        chat_session = ai_model.start_chat(history=gemini_context[:-1])
        response = await chat_session.send_message_async(
             content = user_message, # Gửi tin nhắn cuối cùng
             generation_config=genai.types.GenerationConfig(temperature=0.8), # Sáng tạo hơn cho chat
             safety_settings={ # Cài đặt an toàn
                 HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
             })
        bot_response = response.text.strip()

        # Lưu phản hồi vào lịch sử
        history.append({"role": "model", "parts": [bot_response]})
        dm_conversation_history[user_id] = history

        return bot_response
    except Exception as e:
        print(f"[LỖI AI] Chat DM: {e}")
        # Xóa lịch sử nếu lỗi để tránh lặp lại
        if user_id in dm_conversation_history: del dm_conversation_history[user_id]
        return f"(Mình đang gặp chút trục trặc khi trả lời: {e})"

# --- Hàm Gửi DM An Toàn (Chia nhỏ nếu cần) ---
async def send_dm_safe(user: discord.User | discord.DMChannel, content: str):
    if not user: return
    target_channel = user if isinstance(user, discord.DMChannel) else user # Nếu là user thì gửi DM, nếu là kênh thì gửi vào kênh
    try:
        if len(content) <= 2000:
            await target_channel.send(content)
        else:
            chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
            for i, chunk in enumerate(chunks):
                await target_channel.send(f"**(Phần {i+1}/{len(chunks)})**\n{chunk}")
                await asyncio.sleep(0.5)
        print(f"[DM] Đã gửi tới {target_channel}.")
    except Exception as e:
        print(f"[LỖI DM] Gửi tới {target_channel}: {e}")

# --- Sự kiện Bot ---
@client.event
async def on_ready():
    print(f'>>> Đã đăng nhập: {client.user.name} <<<')
    await setup_database()
    configure_ai()
    print(f"--- Theo dõi từ khóa: {ALERT_KEYWORDS} ---")
    if not ADMIN_USER_ID: print(">>> LỖI: ADMIN_USER_ID KHÔNG HỢP LỆ! <<<")
    if not ai_model: print(">>> CẢNH BÁO: AI CHƯA SẴN SÀNG! <<<")
    print(">>> Bot đã sẵn sàng hoạt động! <<<")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot: return # Bỏ qua bot

    # --- Xử lý tin nhắn Server ---
    if message.guild:
        # Ghi log (nếu bật DB)
        if conn: asyncio.create_task(client.loop.run_in_executor(None, log_message_to_db_sync, message))

        # Kiểm tra từ khóa (chỉ khi AI và Admin ID OK)
        if ai_model and ADMIN_USER_ID:
            content_lower = message.content.lower()
            found_keyword = None
            for keyword in ALERT_KEYWORDS:
                if keyword in content_lower:
                    found_keyword = keyword
                    break

            if found_keyword:
                print(f"[PHÁT HIỆN] Từ khóa '{found_keyword}' tại kênh #{message.channel.name} bởi {message.author}.")

                admin_user = client.get_user(ADMIN_USER_ID)
                if not admin_user:
                    try: admin_user = await client.fetch_user(ADMIN_USER_ID)
                    except Exception as e: print(f"[LỖI] Fetch Admin User: {e}"); return

                context_messages = await fetch_context_messages(message, CONTEXT_MESSAGE_LIMIT)

                if context_messages:
                    summary = await summarize_conversation_with_ai(context_messages, found_keyword, message)
                    if summary:
                        dm_content = (
                            f"**🚨 Tóm tắt hội thoại liên quan đến '{found_keyword}'**\n"
                            f"*- Server:* `{message.guild.name}`\n"
                            f"*- Kênh:* {message.channel.mention}\n"
                            f"*- Tin gốc:* {message.jump_url}\n"
                            f"---\n{summary}\n---" )
                        await send_dm_safe(admin_user, dm_content)
                    else: # Lỗi tóm tắt
                        error_dm = f"⚠️ Không thể tóm tắt hội thoại '{found_keyword}' kênh {message.channel.mention}. Link gốc: {message.jump_url}"
                        await send_dm_safe(admin_user, error_dm)
                else: # Không lấy được context
                    no_context_dm = f"⚠️ Không lấy được ngữ cảnh '{found_keyword}' kênh {message.channel.mention}. Link gốc: {message.jump_url}"
                    await send_dm_safe(admin_user, no_context_dm)

    # --- Xử lý tin nhắn DM từ Admin ---
    elif isinstance(message.channel, discord.DMChannel) and message.author.id == ADMIN_USER_ID:
        print(f"[DM NHẬN] Từ Admin: {message.content[:50]}...")
        if ai_model:
            async with message.channel.typing():
                bot_response = await generate_dm_response_with_ai(message.content, ADMIN_USER_ID)
                if bot_response:
                    await send_dm_safe(message.channel, bot_response)
                else:
                    await message.channel.send("Xin lỗi Rin, mình đang không nghĩ được gì cả...")
        else: # AI không hoạt động
             await message.channel.send("Xin lỗi Rin, bộ não AI của mình đang tạm nghỉ...")

# --- Hàm chạy chính ---
async def main():
    if not TOKEN or not ADMIN_USER_ID:
        print("[LỖI] Thiếu TOKEN hoặc ADMIN_USER_ID.")
        return

    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure: print("[LỖI] Token Discord không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired: print("[LỖI] Thiếu quyền Privileged Intents.")
        except Exception as e: print(f"[LỖI NGHIÊM TRỌNG] Chạy bot: {e}")
        finally: await close_database()

if __name__ == "__main__":
    print("--- Khởi động Bot Discord (AI Tóm tắt & Chat DM) ---")
    try:
        asyncio.run(main())
    except KeyboardInterrupt: print("\n--- Nhận tín hiệu dừng (Ctrl+C) ---")
    finally: print("--- Bot đã tắt ---")