# -*- coding: utf-8 -*-
import discord
import os
import datetime
import psycopg2
from dotenv import load_dotenv
import asyncio
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Tải và cấu hình cơ bản ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL') # Bắt buộc cho lấy log DB
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # Bắt buộc cho AI
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252') # ID Admin Rin

ALERT_KEYWORDS = ["admin", "rin", "misuzu"] # Từ khóa theo dõi
AI_MODEL_NAME = "gemini-1.5-flash-latest"    # Model Gemini
DB_LOG_FETCH_LIMIT = 50                      # Số log DB lấy cho DM 1
LIVE_CONTEXT_FETCH_LIMIT = 50                # Số tin nhắn live lấy cho DM 2
ALERT_SUMMARY_DELAY = 10                     # Giây chờ giữa DM 1 và DM 2
DM_HISTORY_LIMIT = 15                        # Giới hạn lịch sử chat DM

ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try: ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
    except ValueError: print(f"[LỖI] ADMIN_USER_ID '{ADMIN_USER_ID_STR}' không hợp lệ.")
else: print("[LỖI] ADMIN_USER_ID chưa được cấu hình.")

# --- Biến toàn cục ---
conn = None
cursor = None
ai_model = None
dm_conversation_history = {}

# --- Intents Bot ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.members = True

client = discord.Client(intents=intents)

# --- Database Functions ---
async def setup_database():
    global conn, cursor
    if not DATABASE_URL:
        print("[LỖI] DATABASE_URL chưa được đặt.")
        return False
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discord_logs (
                message_id BIGINT PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL,
                server_id BIGINT, server_name TEXT, channel_id BIGINT, channel_name TEXT,
                author_id BIGINT, author_name TEXT, content TEXT, attachment_urls TEXT
            )""")
        print("[DB] Kết nối PostgreSQL và kiểm tra bảng log thành công.")
        return True
    except Exception as e:
        print(f"[LỖI DB] Kết nối/Thiết lập: {e}")
        conn, cursor = None, None
        return False

async def close_database():
    global conn, cursor
    if cursor: cursor.close()
    if conn: conn.close()
    print("[DB] Đã đóng kết nối (nếu có).")

def log_message_to_db_sync(message):
    global conn, cursor
    if conn is None or conn.closed != 0 or message.guild is None: return
    if not cursor or cursor.closed:
         try: cursor = conn.cursor()
         except Exception: return
    try:
        data = ( message.id, message.created_at, message.guild.id, message.guild.name, message.channel.id, message.channel.name, message.author.id, str(message.author), message.content, ", ".join([att.url for att in message.attachments]) if message.attachments else None )
        sql = """ INSERT INTO discord_logs (message_id, timestamp, server_id, server_name, channel_id, channel_name, author_id, author_name, content, attachment_urls) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (message_id) DO NOTHING; """
        cursor.execute(sql, data)
    except Exception as e:
        print(f"[LỖI DB] Ghi log msg {message.id}: {e}")

def fetch_previous_logs_from_db_sync(channel_id: int, before_message_id: int, limit: int) -> list[tuple]:
    global conn, cursor
    if conn is None or conn.closed != 0: return []
    if not cursor or cursor.closed:
         try: cursor = conn.cursor()
         except Exception as e: print(f"[LỖI DB] Tạo lại cursor thất bại: {e}"); return []
    logs = []
    try:
        sql = """ SELECT timestamp, author_name, content FROM discord_logs WHERE channel_id = %s AND message_id < %s ORDER BY message_id DESC LIMIT %s; """
        cursor.execute(sql, (channel_id, before_message_id, limit))
        logs = cursor.fetchall()
        logs.reverse()
    except Exception as e:
        print(f"[LỖI DB] Đọc log cũ: {e}")
    return logs

# --- AI Functions ---
def configure_ai():
    global ai_model
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            ai_model = genai.GenerativeModel(AI_MODEL_NAME)
            print(f"[AI] Đã cấu hình Gemini AI: {AI_MODEL_NAME}")
            return True
        except Exception as e:
            print(f"[LỖI AI] Cấu hình: {e}")
            ai_model = None; return False
    else:
        print("[CẢNH BÁO] GEMINI_API_KEY chưa đặt. AI vô hiệu hóa."); ai_model = None; return False

async def fetch_context_messages(message: discord.Message, limit_each_side: int) -> list:
    context = []
    try:
        history = [msg async for msg in message.channel.history(limit=limit_each_side * 2 + 1, around=message)]
        context = sorted(history, key=lambda m: m.created_at)
    except Exception as e:
        print(f"[LỖI Discord] Lấy lịch sử kênh {message.channel.mention}: {e}")
    return context

async def summarize_conversation_with_ai(messages: list, trigger_keyword: str, trigger_message: discord.Message) -> str | None:
    if not ai_model or not messages: return None
    formatted_conversation = f"**Ngữ cảnh từ kênh #{trigger_message.channel.name} server '{trigger_message.guild.name}'**\n"
    formatted_conversation += f"**Tin nhắn gốc (ID: {trigger_message.id}) chứa '{trigger_keyword}':**\n"
    formatted_conversation += f"[{trigger_message.created_at.strftime('%H:%M')}] {trigger_message.author}: {trigger_message.content}\n"
    formatted_conversation += "\n**Hội thoại xung quanh (từ Discord):**\n"
    for msg in messages:
        formatted_conversation += f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}\n"
    prompt = f"""Bạn là trợ lý AI, đọc đoạn hội thoại Discord sau. Tin nhắn gốc chứa từ khóa '{trigger_keyword}'. Tóm tắt ngắn gọn (3-5 câu) nội dung liên quan đến '{trigger_keyword}' hoặc các chủ đề bàn cùng nó. Hội thoại:\n---\n{formatted_conversation}\n---\nBản tóm tắt:"""
    try:
        response = await ai_model.generate_content_async(
            contents=[prompt],
            generation_config=genai.types.GenerationConfig(temperature=0.5),
            safety_settings={ HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, }
        )
        return response.text.strip()
    except Exception as e:
        print(f"[LỖI AI] Tóm tắt: {e}")
        return f"(Lỗi khi tóm tắt: {e})"

async def generate_dm_response_with_ai(user_message: str, user_id: int) -> str | None:
    global dm_conversation_history
    if not ai_model: return "Chức năng AI chưa sẵn sàng."
    history = dm_conversation_history.get(user_id, [])
    history.append({"role": "user", "parts": [user_message]})
    if len(history) > DM_HISTORY_LIMIT * 2: history = history[-(DM_HISTORY_LIMIT * 2):]
    initial_context = [ {"role": "user", "parts": ["Bạn là Mizuki, trợ lý AI thân thiện trong Discord, đang nói chuyện riêng với Admin (Rin). Hãy trả lời tự nhiên và hữu ích."]}, {"role": "model", "parts": ["Dạ Rin! Mizuki nghe đây ạ."]}, ]
    gemini_context = initial_context + history
    try:
        chat_session = ai_model.start_chat(history=gemini_context[:-1])
        response = await chat_session.send_message_async( content=user_message, generation_config=genai.types.GenerationConfig(temperature=0.8), safety_settings={ HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE, } )
        bot_response = response.text.strip()
        history.append({"role": "model", "parts": [bot_response]})
        dm_conversation_history[user_id] = history
        return bot_response
    except Exception as e:
        print(f"[LỖI AI] Chat DM: {e}")
        if user_id in dm_conversation_history: del dm_conversation_history[user_id]
        return f"(Lỗi khi trả lời: {e})"

# --- Utility Functions ---
async def send_dm_safe(user: discord.User | discord.DMChannel, content: str):
    if not user: return
    target_channel = user if isinstance(user, discord.DMChannel) else user
    try:
        if len(content) <= 2000: await target_channel.send(content)
        else:
            chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
            for i, chunk in enumerate(chunks):
                await target_channel.send(f"**(Phần {i+1}/{len(chunks)})**\n{chunk}")
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"[LỖI DM] Gửi tới {getattr(target_channel, 'recipient', target_channel)}: {e}")

# --- Background Task for Alerts ---
async def process_keyword_alert(message: discord.Message, found_keyword: str, admin_user: discord.User):
    print(f"[ALERT TASK] Bắt đầu xử lý '{found_keyword}'")
    previous_logs_str = "*Không thể lấy log cũ từ DB.*"
    if conn:
        try:
            db_logs = await client.loop.run_in_executor( None, fetch_previous_logs_from_db_sync, message.channel.id, message.id, DB_LOG_FETCH_LIMIT )
            if db_logs:
                previous_logs_str = "```\n--- Log DB trước đó ---\n"
                for timestamp, author, content in db_logs: previous_logs_str += f"[{timestamp.strftime('%H:%M:%S')}] {author}: {content}\n"
                previous_logs_str += "```"
            else: previous_logs_str = "*Không tìm thấy log cũ phù hợp trong DB.*"
        except Exception as e: print(f"[LỖI TASK] Lấy log DB: {e}"); previous_logs_str = f"*Lỗi khi lấy log DB: {e}*"

    dm1_content = ( f"**🔔 Phát hiện '{found_keyword}'!**\n\n" f"👤 **Người gửi:** {message.author.mention} (`{message.author}`)\n" f"📌 **Kênh:** {message.channel.mention} (`#{message.channel.name}`)\n" f"🔗 **Link:** {message.jump_url}\n\n" f"💬 **Nội dung gốc:**\n```\n{message.content}\n```\n" f"{previous_logs_str}" )
    await send_dm_safe(admin_user, dm1_content)

    print(f"[ALERT TASK] Chờ {ALERT_SUMMARY_DELAY} giây...")
    await asyncio.sleep(ALERT_SUMMARY_DELAY)

    summary = "*Không thể tạo tóm tắt.*"
    if ai_model:
        live_context_messages = await fetch_context_messages(message, LIVE_CONTEXT_FETCH_LIMIT)
        if live_context_messages:
            summary = await summarize_conversation_with_ai(live_context_messages, found_keyword, message)
            if not summary: summary = "*AI không thể tạo tóm tắt hoặc đã gặp lỗi.*"
        else: summary = "*Không lấy được ngữ cảnh từ Discord để tóm tắt.*"

    dm2_content = ( f"**📊 Tóm tắt hội thoại (AI):**\n\n" f"(Liên quan đến tin nhắn '{found_keyword}' tại {message.jump_url})\n" f"---\n{summary}\n---" )
    await send_dm_safe(admin_user, dm2_content)
    print(f"[ALERT TASK] Hoàn thành xử lý '{found_keyword}'.")

# --- Discord Events ---
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
    if message.author.bot: return

    # Xử lý tin nhắn Server
    if message.guild:
        if conn: asyncio.create_task(client.loop.run_in_executor(None, log_message_to_db_sync, message))
        if ADMIN_USER_ID:
            content_lower = message.content.lower()
            found_keyword = None
            for keyword in ALERT_KEYWORDS:
                if keyword in content_lower: found_keyword = keyword; break
            if found_keyword:
                print(f"[PHÁT HIỆN] Từ khóa '{found_keyword}' tại #{message.channel.name}. Khởi chạy tác vụ nền...")
                admin_user = client.get_user(ADMIN_USER_ID)
                if not admin_user:
                    try: admin_user = await client.fetch_user(ADMIN_USER_ID)
                    except Exception as e: print(f"[LỖI] Fetch Admin User khi phát hiện từ khóa: {e}"); return
                # Chạy xử lý alert trong nền
                asyncio.create_task(process_keyword_alert(message, found_keyword, admin_user))

    # Xử lý tin nhắn DM từ Admin
    elif isinstance(message.channel, discord.DMChannel) and message.author.id == ADMIN_USER_ID:
        print(f"[DM NHẬN] Từ Admin ({ADMIN_USER_ID}): {message.content[:50]}...")
        if ai_model:
            async with message.channel.typing():
                bot_response = await generate_dm_response_with_ai(message.content, ADMIN_USER_ID)
                if bot_response: await send_dm_safe(message.channel, bot_response)
                else: await message.channel.send("Xin lỗi Rin, mình gặp lỗi khi đang suy nghĩ câu trả lời...")
        else: await message.channel.send("Rin ơi, bộ não AI của mình đang tạm thời không hoạt động...")

# --- Main Execution ---
async def main():
    if not TOKEN or not ADMIN_USER_ID: print("[LỖI] Thiếu TOKEN hoặc ADMIN_USER_ID."); return
    if not DATABASE_URL: print("[CẢNH BÁO] Thiếu DATABASE_URL, DM 1 sẽ không có log cũ.");
    if not GEMINI_API_KEY: print("[CẢNH BÁO] Thiếu GEMINI_API_KEY, chat DM và tóm tắt AI sẽ không hoạt động.");
    async with client:
        try: await client.start(TOKEN)
        except Exception as e: print(f"[LỖI NGHIÊM TRỌNG] Chạy bot: {e}")
        finally: await close_database()

if __name__ == "__main__":
    print("--- Khởi động Bot Discord (Log + Keyword Alert 2-Step + Chat DM AI) ---")
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\n--- Nhận tín hiệu dừng ---")
    finally: print("--- Bot đã tắt ---")