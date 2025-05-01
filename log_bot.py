# -*- coding: utf-8 -*-
import discord
import os
import datetime
import psycopg2 # Cần thiết để đọc log
from dotenv import load_dotenv
import asyncio
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# import traceback # Bỏ comment nếu cần debug

# --- Tải biến môi trường ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL') # BẮT BUỘC cho chức năng đọc log DB
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252') # <<-- Đặt ID Admin ở đây hoặc trong .env

# --- Cấu hình chính ---
ALERT_KEYWORDS = ["admin", "rin", "misuzu"] # Từ khóa theo dõi (chữ thường)
AI_MODEL_NAME = "gemini-1.5-flash-latest"    # Model Gemini
DB_LOG_FETCH_LIMIT = 50                      # Số log cũ lấy từ DB cho DM #1
LIVE_CONTEXT_FETCH_LIMIT = 50                # Số tin nhắn lấy trước/sau từ Discord cho AI
ALERT_SUMMARY_DELAY = 10                     # Giây chờ trước khi gửi tóm tắt AI (DM #2)
DM_HISTORY_LIMIT = 15                        # Giới hạn lịch sử chat DM

# --- Chuyển đổi ID Admin ---
ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
        print(f"[CẤU HÌNH] ID Admin nhận thông báo/chat DM: {ADMIN_USER_ID}")
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
intents.members = True           # Cần để lấy thông tin người dùng (fetch_user)

client = discord.Client(intents=intents)

# --- Hàm Kết nối Database ---
async def setup_database():
    global conn, cursor
    if not DATABASE_URL:
        print("[LỖI] DATABASE_URL chưa được đặt. Chức năng đọc log DB sẽ không hoạt động.")
        return False
    try:
        print("[DB] Đang kết nối đến PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = True # Tự commit cho lệnh INSERT/UPDATE đơn giản
        cursor = conn.cursor()
        print("[DB] Tạo cursor thành công.")
        # Kiểm tra/tạo bảng log
        print("[DB] Đang kiểm tra/tạo bảng discord_logs...")
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
            )""")
        print("[DB] Kết nối PostgreSQL và kiểm tra bảng log thành công.")
        return True
    except Exception as e:
        print(f"[LỖI DB] Kết nối/Thiết lập: {e}")
        conn, cursor = None, None
        return False

async def close_database():
    global conn, cursor
    if cursor:
        try:
            cursor.close()
            print("[DB] Đã đóng cursor.")
        except Exception as e:
            print(f"[LỖI DB] Khi đóng cursor: {e}")
    if conn:
        try:
            conn.close()
            print("[DB] Đã đóng kết nối.")
        except Exception as e:
            print(f"[LỖI DB] Khi đóng kết nối: {e}")
    print("[DB] Đã xử lý đóng kết nối (nếu có).")

# --- Hàm Ghi Log vào Database (Phiên bản Đồng bộ) ---
def log_message_to_db_sync(message):
    global conn, cursor
    # Chỉ ghi log nếu có kết nối DB và tin nhắn từ server
    if conn is None or conn.closed != 0 or message.guild is None:
        return
    if not cursor or cursor.closed:
         try:
             cursor = conn.cursor()
         except Exception as e:
             print(f"[LỖI DB LOG] Tạo lại cursor thất bại: {e}")
             return
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
            ON CONFLICT (message_id) DO NOTHING;
        """
        cursor.execute(sql, data)
    except Exception as e:
        print(f"[LỖI DB LOG] Ghi log msg {message.id}: {e}")


# --- Hàm Đọc Log Cũ Từ Database (Thêm Log Check) ---
def fetch_previous_logs_from_db_sync(channel_id: int, before_message_id: int, limit: int) -> list[tuple[datetime.datetime, str, str]]:
    global conn, cursor
    print(f"[DB CHECK] Bắt đầu fetch_previous_logs_from_db_sync cho kênh {channel_id}, trước ID {before_message_id}, limit {limit}") # Log Check
    if conn is None or conn.closed != 0:
        print("[DB CHECK][LỖI] Không có kết nối DB.")
        return []

    current_cursor = None # Sử dụng cursor cục bộ, không dùng cursor global
    logs = []
    try:
        # Luôn tạo cursor mới cho mỗi lần đọc để đảm bảo thread-safety
        current_cursor = conn.cursor()
        print("[DB CHECK] Tạo cursor tạm thời thành công.")

        sql = """
            SELECT timestamp, author_name, content
            FROM discord_logs
            WHERE channel_id = %s AND message_id < %s
            ORDER BY message_id DESC
            LIMIT %s;
        """
        print(f"[DB CHECK] Đang thực thi SQL với params ({channel_id}, {before_message_id}, {limit})") # Log Check
        current_cursor.execute(sql, (channel_id, before_message_id, limit))
        logs = current_cursor.fetchall()
        logs.reverse() # Đảo ngược lại để đúng thứ tự thời gian
        print(f"[DB CHECK] Thực thi SQL thành công. Tìm thấy {len(logs)} logs cũ.") # Log Check
    except Exception as e:
        print(f"[DB CHECK][LỖI] Đọc log cũ: {e}")
        logs = [] # Trả về list rỗng nếu lỗi
    finally:
        if current_cursor:
            try:
                current_cursor.close()
                # print("[DB CHECK] Đã đóng cursor tạm thời.") # Giảm nhiễu log
            except Exception as e:
                print(f"[DB CHECK][LỖI] Đóng cursor tạm thời: {e}")
    return logs


# --- Hàm Cấu hình AI ---
def configure_ai():
    global ai_model
    if GEMINI_API_KEY:
        try:
            print(f"[AI] Đang cấu hình Gemini AI với model: {AI_MODEL_NAME}")
            genai.configure(api_key=GEMINI_API_KEY)
            ai_model = genai.GenerativeModel(AI_MODEL_NAME)
            print(f"[AI] Đã cấu hình Gemini AI thành công.")
            return True
        except Exception as e:
            print(f"[LỖI AI] Không thể cấu hình Gemini: {e}")
            ai_model = None
            return False
    else:
        print("[CẢNH BÁO] GEMINI_API_KEY chưa được đặt. AI vô hiệu hóa.")
        ai_model = None
        return False

# --- Hàm Lấy Ngữ Cảnh Trực Tiếp Từ Discord ---
async def fetch_context_messages(message: discord.Message, limit_each_side: int) -> list[discord.Message]:
    print(f"[DISCORD CHECK] Bắt đầu fetch_context_messages cho kênh {message.channel.id}, quanh msg {message.id}, limit mỗi bên {limit_each_side}") # Log Check
    context = []
    try:
        # Lấy tối đa limit*2 + 1 tin nhắn xung quanh tin nhắn gốc
        history = [msg async for msg in message.channel.history(limit=limit_each_side * 2 + 1, around=message)]
        context = sorted(history, key=lambda m: m.created_at)
        print(f"[DISCORD CHECK] Lấy thành công {len(context)} tin nhắn live từ Discord (bao gồm cả tin gốc).") # Log Check
    except discord.Forbidden:
        print(f"[DISCORD CHECK][LỖI] Không có quyền đọc lịch sử kênh {message.channel.mention}")
    except discord.HTTPException as e:
         print(f"[DISCORD CHECK][LỖI] Lỗi HTTP khi lấy lịch sử kênh {message.channel.mention}: {e}")
    except Exception as e:
        print(f"[DISCORD CHECK][LỖI] Lấy lịch sử kênh {message.channel.mention}: {e}")
    return context

# --- Hàm Tóm Tắt Hội Thoại bằng AI ---
async def summarize_conversation_with_ai(messages: list[discord.Message], trigger_keyword: str, trigger_message: discord.Message) -> str | None:
    if not ai_model:
        print("[AI CHECK][LỖI] AI model không sẵn sàng để tóm tắt.")
        return None
    if not messages:
        print("[AI CHECK][CẢNH BÁO] Không có tin nhắn nào trong context để tóm tắt.")
        return "*Không có ngữ cảnh để tóm tắt.*"

    print(f"[AI CHECK] Bắt đầu summarize_conversation_with_ai với {len(messages)} tin nhắn.") # Log Check

    # Format hội thoại cho AI
    formatted_conversation = f"**Ngữ cảnh từ kênh #{trigger_message.channel.name} server '{trigger_message.guild.name}'**\n"
    formatted_conversation += f"**Tin nhắn gốc (ID: {trigger_message.id}) chứa từ khóa '{trigger_keyword}':**\n"
    formatted_conversation += f"[{trigger_message.created_at.strftime('%H:%M')}] {trigger_message.author}: {trigger_message.content}\n"
    formatted_conversation += "\n**Đoạn hội thoại xung quanh (lấy trực tiếp từ Discord):**\n"
    for msg in messages:
        # Không lặp lại tin nhắn gốc trong phần context
        if msg.id != trigger_message.id:
             formatted_conversation += f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}\n"

    # Giới hạn độ dài input cho AI nếu cần
    # max_len = 30000
    # if len(formatted_conversation) > max_len: formatted_conversation = formatted_conversation[:max_len] + "\n... (nội dung quá dài đã bị cắt)"

    prompt = f"""Bạn là một trợ lý Discord. Hãy đọc kỹ đoạn hội thoại sau từ server Discord.
Tin nhắn gốc có chứa từ khóa '{trigger_keyword}'.
Nhiệm vụ của bạn là tóm tắt ngắn gọn đoạn hội thoại này (khoảng 3-5 câu), tập trung vào những gì được nói liên quan đến từ khóa '{trigger_keyword}' hoặc những người/vấn đề được đề cập cùng với từ khóa đó. Mục tiêu là cung cấp thông tin nhanh cho Admin về nội dung đang được bàn luận.

Đoạn hội thoại:
---
{formatted_conversation}
---

Bản tóm tắt của bạn:"""

    try:
        print(f"[AI CHECK] Đang gửi yêu cầu tóm tắt tới Gemini...")
        response = await ai_model.generate_content_async(
            contents=[prompt],
            generation_config=genai.types.GenerationConfig(temperature=0.5),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            })

        # Xử lý response an toàn
        if response.parts:
             summary = "".join(part.text for part in response.parts).strip()
        else:
             if response.prompt_feedback.block_reason:
                 summary = f"*(Tóm tắt bị chặn bởi bộ lọc an toàn: {response.prompt_feedback.block_reason})*"
                 print(f"[AI CHECK][CẢNH BÁO] Tóm tắt bị chặn: {response.prompt_feedback.block_reason}")
             else:
                 summary = "*(AI không trả về nội dung tóm tắt.)*"
                 print("[AI CHECK][CẢNH BÁO] AI không trả về nội dung tóm tắt.")

        print(f"[AI CHECK] Nhận được tóm tắt từ Gemini: {summary[:100]}...") # Log Check
        return summary
    except Exception as e:
        print(f"[AI CHECK][LỖI] Tóm tắt: {e}")
        return f"(Lỗi khi tóm tắt bằng AI: {e})"


# --- Hàm Tạo Phản Hồi DM bằng AI ---
async def generate_dm_response_with_ai(user_message: str, user_id: int) -> str | None:
    global dm_conversation_history
    if not ai_model: return "Xin lỗi, chức năng AI của mình chưa sẵn sàng."

    print(f"[AI CHAT CHECK] Bắt đầu generate_dm_response cho user {user_id}")
    history = dm_conversation_history.get(user_id, [])
    history.append({"role": "user", "parts": [{"text": user_message}]})

    if len(history) > DM_HISTORY_LIMIT * 2:
        print(f"[AI CHAT CHECK] Lịch sử DM quá dài ({len(history)}), đang cắt bớt...")
        history = history[-(DM_HISTORY_LIMIT * 2):]

    try:
        print(f"[AI CHAT CHECK] Đang gửi yêu cầu chat tới Gemini với {len(history)} tin nhắn trong lịch sử...")
        chat_session = ai_model.start_chat(history=history[:-1]) # Bỏ tin nhắn cuối của user

        response = await chat_session.send_message_async(
             content = [{"text": user_message}], # Gửi tin nhắn cuối cùng dạng chuẩn
             generation_config=genai.types.GenerationConfig(temperature=0.8),
             safety_settings={
                 HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                 HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
             })

        if response.parts:
             bot_response = "".join(part.text for part in response.parts).strip()
        else:
             if response.prompt_feedback.block_reason:
                 bot_response = f"*(Tin nhắn của mình bị chặn bởi bộ lọc: {response.prompt_feedback.block_reason})*"
                 print(f"[AI CHAT CHECK][CẢNH BÁO] Phản hồi chat bị chặn: {response.prompt_feedback.block_reason}")
             else:
                 bot_response = "*(Mình không biết nói gì nữa...)*"
                 print("[AI CHAT CHECK][CẢNH BÁO] AI không trả về phản hồi chat.")

        print(f"[AI CHAT CHECK] Nhận được phản hồi từ Gemini: {bot_response[:100]}...")

        if bot_response and not bot_response.startswith("*("):
             history.append({"role": "model", "parts": [{"text": bot_response}]})
             dm_conversation_history[user_id] = history

        return bot_response
    except Exception as e:
        print(f"[AI CHAT CHECK][LỖI] Chat DM: {e}")
        if user_id in dm_conversation_history: del dm_conversation_history[user_id]
        return f"(Ái chà, mình đang bị lỗi chút xíu khi nghĩ câu trả lời: {e})"


# --- Hàm Gửi DM An Toàn ---
async def send_dm_safe(user: discord.User | discord.DMChannel, content: str, context_log: str = "DM"):
    if not user:
        print(f"[DM CHECK][LỖI] Người nhận không hợp lệ ({context_log}).")
        return

    target_channel : discord.abc.Messageable = None
    target_recipient_info = "Không xác định" # Để log lỗi

    try:
        if isinstance(user, discord.DMChannel):
            target_channel = user
            target_recipient_info = str(user.recipient)
        elif isinstance(user, discord.User):
            target_recipient_info = str(user)
            if not user.dm_channel:
                 print(f"[DM CHECK] Chưa có kênh DM cho {user}, đang tạo...")
                 target_channel = await user.create_dm()
                 print(f"[DM CHECK] Tạo kênh DM cho {user} thành công.")
            else:
                 target_channel = user.dm_channel
        else:
            print(f"[DM CHECK][LỖI] Loại người nhận không xác định: {type(user)}")
            return

        if not target_channel:
             print(f"[DM CHECK][LỖI] Không thể xác định kênh DM để gửi tới {target_recipient_info} ({context_log}).")
             return

        print(f"[DM CHECK] Chuẩn bị gửi {context_log} tới {target_recipient_info}...")
        if len(content) <= 2000:
            await target_channel.send(content)
        else: # Chia nhỏ
            print(f"[DM CHECK] Nội dung {context_log} quá dài ({len(content)}), đang chia nhỏ...")
            chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
            for i, chunk in enumerate(chunks):
                print(f"[DM CHECK] Đang gửi phần {i+1}/{len(chunks)} của {context_log} tới {target_recipient_info}...")
                await target_channel.send(f"**(Phần {i+1}/{len(chunks)})**\n{chunk}")
                await asyncio.sleep(0.6)
        print(f"[DM CHECK] Gửi {context_log} tới {target_recipient_info} thành công.")
    except discord.Forbidden:
         print(f"[DM CHECK][LỖI] Không có quyền gửi {context_log} tới {target_recipient_info}. Có thể do bị chặn hoặc cài đặt quyền riêng tư.")
    except discord.HTTPException as e:
         print(f"[DM CHECK][LỖI] Lỗi HTTP {e.status} khi gửi {context_log} tới {target_recipient_info}: {e.text}")
    except Exception as e:
        print(f"[DM CHECK][LỖI] Gửi {context_log} tới {target_recipient_info}: {e}")
        # traceback.print_exc()


# --- Hàm xử lý nền cho thông báo từ khóa ---
async def process_keyword_alert(message: discord.Message, found_keyword: str, admin_user: discord.User):
    task_id = message.id # Dùng ID tin nhắn làm ID task cho log
    task_start_time = time.time()
    print(f"[ALERT TASK {task_id}] Bắt đầu xử lý cho từ khóa '{found_keyword}'")

    # --- Gửi DM #1: Tin nhắn gốc + Log DB cũ ---
    print(f"[ALERT TASK {task_id}] Đang chuẩn bị DM #1 (Log DB)...")
    previous_logs_str = "*[DB] Không thể lấy log cũ hoặc không có kết nối DB.*"
    if conn:
        try:
            print(f"[ALERT TASK {task_id}] Gọi fetch_previous_logs_from_db_sync...")
            db_logs = await client.loop.run_in_executor(
                None, fetch_previous_logs_from_db_sync,
                message.channel.id, message.id, DB_LOG_FETCH_LIMIT
            )
            print(f"[ALERT TASK {task_id}] fetch_previous_logs_from_db_sync trả về {len(db_logs)} logs.")
            if db_logs:
                previous_logs_str = "```\n--- Log DB trước đó ---\n"
                for timestamp, author, content in db_logs:
                    log_time = timestamp.strftime('%H:%M:%S')
                    log_content_short = content[:150] + ('...' if len(content) > 150 else '')
                    previous_logs_str += f"[{log_time}] {author}: {log_content_short}\n"
                previous_logs_str += "```"
            else:
                previous_logs_str = "*[DB] Không tìm thấy log cũ phù hợp.*"
        except Exception as e:
            print(f"[ALERT TASK {task_id}][LỖI] Lấy log DB: {e}")
            previous_logs_str = f"*[LỖI] Lấy log DB: {e}*"

    dm1_content = (
        f"**🔔 Phát hiện từ khóa '{found_keyword}'!**\n\n"
        f"👤 **Người gửi:** {message.author.mention} (`{message.author}`)\n"
        f"📌 **Kênh:** {message.channel.mention} (`#{message.channel.name}`)\n"
        f"🔗 **Link:** {message.jump_url}\n\n"
        f"💬 **Nội dung gốc:**\n```\n{message.content}\n```\n"
        f"{previous_logs_str}" )
    print(f"[ALERT TASK {task_id}] Gọi send_dm_safe cho DM #1...")
    await send_dm_safe(admin_user, dm1_content, context_log="DM #1 (Log DB)")

    # --- Chờ đợi ---
    print(f"[ALERT TASK {task_id}] Chờ {ALERT_SUMMARY_DELAY} giây...")
    await asyncio.sleep(ALERT_SUMMARY_DELAY)

    # --- Gửi DM #2: Tóm tắt AI từ Context Live ---
    print(f"[ALERT TASK {task_id}] Đang chuẩn bị DM #2 (Tóm tắt AI)...")
    summary = "*[AI] Không thể tạo tóm tắt (AI chưa sẵn sàng hoặc lỗi).* "
    if ai_model:
        print(f"[ALERT TASK {task_id}] Gọi fetch_context_messages...")
        live_context_messages = await fetch_context_messages(message, LIVE_CONTEXT_FETCH_LIMIT)
        if live_context_messages:
            print(f"[ALERT TASK {task_id}] Gọi summarize_conversation_with_ai với {len(live_context_messages)} tin nhắn live...")
            summary_result = await summarize_conversation_with_ai(live_context_messages, found_keyword, message)
            if summary_result:
                 summary = summary_result
        else:
            summary = "*[Discord] Không lấy được ngữ cảnh live để tóm tắt.*"

    dm2_content = (
        f"**📊 Tóm tắt hội thoại (AI) gần đây:**\n\n"
        f"(Liên quan đến tin nhắn '{found_keyword}' tại {message.jump_url})\n"
        f"---\n{summary}\n---" )
    print(f"[ALERT TASK {task_id}] Gọi send_dm_safe cho DM #2...")
    await send_dm_safe(admin_user, dm2_content, context_log="DM #2 (AI Summary)")
    task_end_time = time.time()
    print(f"[ALERT TASK {task_id}] Đã hoàn thành xử lý (Tổng thời gian: {task_end_time - task_start_time:.2f}s).")


# --- Sự kiện Bot ---
@client.event
async def on_ready():
    print(f'>>> Đã đăng nhập: {client.user.name} ({client.user.id}) <<<')
    await setup_database()
    configure_ai()
    print(f"--- Theo dõi từ khóa: {ALERT_KEYWORDS} ---")
    if not ADMIN_USER_ID: print(">>> LỖI: ADMIN_USER_ID KHÔNG HỢP LỆ! <<<")
    if not ai_model and GEMINI_API_KEY : print(">>> CẢNH BÁO: Lỗi cấu hình AI dù có API Key! <<<")
    print(">>> Bot đã sẵn sàng! <<<")

@client.event
async def on_message(message: discord.Message):
    # Bỏ qua tin nhắn từ chính bot hoặc webhook
    if message.author.bot or message.webhook_id is not None:
        return

    # --- Xử lý tin nhắn SERVER ---
    if message.guild:
        # Ghi log DB (nếu bật) - Chạy trong executor
        if conn:
            try:
                 client.loop.run_in_executor(None, log_message_to_db_sync, message)
            except Exception as e:
                 print(f"[LỖI EXECUTOR] Ghi log DB: {e}")


        # Kiểm tra từ khóa và chạy tác vụ nền
        if ADMIN_USER_ID:
            try:
                content_lower = message.content.lower()
                found_keyword = None
                for keyword in ALERT_KEYWORDS:
                    if keyword in content_lower:
                        found_keyword = keyword
                        break

                if found_keyword:
                    print(f"[==> PHÁT HIỆN <==] Từ khóa '{found_keyword}' trong tin nhắn ID {message.id} tại kênh #{message.channel.name} bởi {message.author}.")

                    admin_user_object = client.get_user(ADMIN_USER_ID)
                    if not admin_user_object:
                        print(f"[FETCH ADMIN CHECK] Admin {ADMIN_USER_ID} không có trong cache, đang fetch...")
                        try:
                            admin_user_object = await client.fetch_user(ADMIN_USER_ID)
                            print(f"[FETCH ADMIN CHECK] Fetch Admin {ADMIN_USER_ID} thành công: {admin_user_object}")
                        except discord.NotFound:
                             print(f"[FETCH ADMIN CHECK][LỖI] Không tìm thấy Admin ID {ADMIN_USER_ID}. Không thể gửi DM.")
                             return
                        except Exception as e:
                            print(f"[FETCH ADMIN CHECK][LỖI] Fetch Admin User: {e}")
                            return

                    if admin_user_object:
                         print(f"[TASK CREATE] Chuẩn bị tạo task process_keyword_alert cho msg {message.id}")
                         asyncio.create_task(process_keyword_alert(message, found_keyword, admin_user_object))
                    else:
                         print(f"[LỖI] Không thể lấy được đối tượng admin_user ({ADMIN_USER_ID}).")

            except Exception as e:
                print(f"[LỖI ON_MESSAGE SERVER] Xử lý tin nhắn {message.id}: {e}")
                # traceback.print_exc()


    # --- Xử lý tin nhắn DM từ ADMIN ---
    elif isinstance(message.channel, discord.DMChannel) and message.author.id == ADMIN_USER_ID:
        print(f"[DM NHẬN] Từ Admin ({ADMIN_USER_ID}): {message.content[:50]}...")
        if ai_model:
            try:
                async with message.channel.typing():
                    bot_response = await generate_dm_response_with_ai(message.content, ADMIN_USER_ID)
                    if bot_response:
                        await send_dm_safe(message.channel, bot_response, context_log="DM Chat Response")
                    else:
                        await message.channel.send("Xin lỗi Rin, mình gặp lỗi khi đang suy nghĩ câu trả lời...")
            except Exception as e:
                 print(f"[LỖI ON_MESSAGE DM] Xử lý chat: {e}")
                 await message.channel.send(":( Đã có lỗi xảy ra khi xử lý yêu cầu chat của bạn.")
        else:
             await message.channel.send("Rin ơi, bộ não AI của mình đang tạm thời không hoạt động...")


# --- Hàm chạy chính ---
async def main():
    # Kiểm tra các biến môi trường quan trọng
    if not TOKEN: print("[LỖI] Thiếu DISCORD_TOKEN."); return
    if not ADMIN_USER_ID: print("[CẢNH BÁO] Thiếu ADMIN_USER_ID, thông báo DM và chat DM sẽ không hoạt động."); return # Nên dừng nếu thiếu ID admin
    if not DATABASE_URL: print("[CẢNH BÁO] Thiếu DATABASE_URL, DM #1 sẽ không có log cũ.");
    if not GEMINI_API_KEY: print("[CẢNH BÁO] Thiếu GEMINI_API_KEY, chat và tóm tắt AI sẽ không hoạt động.");

    async with client:
        try:
            await client.start(TOKEN)
        except discord.errors.LoginFailure: print("[LỖI] Token Discord không hợp lệ.")
        except discord.errors.PrivilegedIntentsRequired: print("[LỖI] Thiếu quyền Privileged Intents (Message Content?).")
        except discord.errors.ConnectionClosed as e: print(f"[LỖI] Kết nối Discord bị đóng: Code {e.code}, Reason: {e.reason}")
        except Exception as e:
            print(f"[LỖI NGHIÊM TRỌNG] Khi chạy bot: {type(e).__name__}: {e}")
            # traceback.print_exc()
        finally:
            print("[SYSTEM] Bắt đầu quá trình tắt bot...")
            await close_database()
            print("[SYSTEM] Bot đã tắt hoàn toàn.")

if __name__ == "__main__":
    print("--- Khởi động Bot Discord (Log + Keyword Alert 2-Step + Chat DM AI) ---")
    # Chạy vòng lặp sự kiện asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- Nhận tín hiệu dừng (Ctrl+C) ---")
    # Bắt các lỗi runtime khác có thể xảy ra ngoài vòng lặp chính
    except Exception as e:
         print(f"\n[LỖI ASYNCIO/RUNTIME] Lỗi không mong muốn ở cấp cao nhất: {type(e).__name__}: {e}")
         # traceback.print_exc()
    finally:
        print("--- Chương trình kết thúc ---")