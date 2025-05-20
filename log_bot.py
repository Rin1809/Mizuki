# Mizuki/log_bot.py
import discord
import os
from dotenv import load_dotenv
import asyncio
import json
from datetime import datetime, timezone, timedelta
from aiohttp import web, ClientSession 
import hashlib 
import re 

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252')
MIZUKI_HTTP_PORT_STR = os.getenv('MIZUKI_HTTP_PORT', os.getenv('PORT', '8080'))
MIZUKI_EXPECTED_SECRET = os.getenv('MIZUKI_SHARED_SECRET', 'default_secret_key_for_mizuki')
RIN_PERSONAL_CARD_API_URL = os.getenv('RIN_PERSONAL_CARD_API_URL') # lay url api
if not RIN_PERSONAL_CARD_API_URL:
    print("[LOI CFG] RIN_PERSONAL_CARD_API_URL chưa được cấu hình trong .env của Mizuki.")


EXCLUDED_IPS_RAW = os.getenv('EXCLUDED_IPS', "")
EXCLUDED_IPS = [ip.strip() for ip in EXCLUDED_IPS_RAW.split(',') if ip.strip()]
if EXCLUDED_IPS:
    print(f"[CFG] IP Ngoai le (ko DM): {EXCLUDED_IPS}")


COMMAND_PREFIX = "!"
SHIROMI_COMMAND_PREFIX_REFERENCE = "Shi"

ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
        print(f"[CFG] ID Admin: {ADMIN_USER_ID}")
    except ValueError:
        print(f"[LOI] ADMIN_USER_ID '{ADMIN_USER_ID_STR}' ko phai so.")
        ADMIN_USER_ID = None
else:
    print("[LOI] ADMIN_USER_ID chua dc cfg.")

MIZUKI_HTTP_PORT = 8080
try:
    MIZUKI_HTTP_PORT = int(MIZUKI_HTTP_PORT_STR)
except ValueError:
    print(f"[LOI] MIZUKI_HTTP_PORT '{MIZUKI_HTTP_PORT_STR}' ko hop le. Dung port mac dinh: {MIZUKI_HTTP_PORT}")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.members = True

client = discord.Client(intents=intents)
http_runner = None

LOG_BUFFER_LIMIT = 30  
SESSION_TIMEOUT_SECONDS = 5 * 60 
FLUSH_INTERVAL_SECONDS = 30      
active_sessions = {}


async def send_dm_safe(user: discord.User | discord.DMChannel, content: str = None, embed: discord.Embed = None, embeds: list[discord.Embed] = None, context_log: str = "DM"):
    if not user:
        print(f"[DM][LOI] User ko hop le ({context_log}).")
        return
    target_channel : discord.abc.Messageable = None
    target_recipient_info = "Ko xd"
    try:
        if isinstance(user, discord.DMChannel):
            target_channel = user
            target_recipient_info = str(user.recipient) if user.recipient else "DM Kenh"
        elif isinstance(user, (discord.User, discord.Member)):
            target_recipient_info = str(user)
            if not user.dm_channel:
                target_channel = await user.create_dm()
            else:
                target_channel = user.dm_channel
        else:
            print(f"[DM][LOI] Loai user ko xd: {type(user)}")
            return

        if not target_channel:
            print(f"[DM][LOI] Ko tim thay kenh DM toi {target_recipient_info} ({context_log}).")
            return
        
        if embeds and len(embeds) > 0:
            for i, emb_item in enumerate(embeds): 
                await target_channel.send(embed=emb_item)
                if i < len(embeds) - 1:
                    await asyncio.sleep(0.3) 
            return
        
        if embed:
            await target_channel.send(embed=embed)
            return

        if content:
            if len(content) <= 2000:
                await target_channel.send(content)
            else: 
                chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
                for i, chunk in enumerate(chunks):
                    await target_channel.send(f"**(P.{i+1}/{len(chunks)})**\n{chunk}")
                    await asyncio.sleep(0.6) 
        else:
            print(f"[DM][LOI] Ko co content/embed de gui {context_log} toi {target_recipient_info}.")

    except discord.Forbidden:
        print(f"[DM][LOI] Ko co quyen gui {context_log} toi {target_recipient_info}.")
    except discord.HTTPException as e:
        print(f"[DM][LOI] HTTP {e.status} khi gui {context_log}: {e.text}")
    except Exception as e:
        print(f"[DM][LOI] Loi khac khi gui {context_log}: {e}")


async def find_target_channel(specifier: str) -> discord.TextChannel | None:
    target_channel = None
    try:
        channel_id = int(specifier)
        fetched_channel = client.get_channel(channel_id)
        if not fetched_channel: 
            fetched_channel = await client.fetch_channel(channel_id)
        if isinstance(fetched_channel, discord.TextChannel):
            target_channel = fetched_channel
        else: 
            target_channel = None
    except ValueError: 
        found = False
        for guild in client.guilds:
            for channel_in_guild in guild.text_channels:
                if channel_in_guild.name.lower() == specifier.lower():
                    target_channel = channel_in_guild
                    found = True; break
            if found: break
        if not found: target_channel = None
    except discord.NotFound: target_channel = None
    except discord.Forbidden: target_channel = None
    except Exception: target_channel = None 
    return target_channel

def format_timestamp_hcm(timestamp_iso_utc_str: str) -> str:
    try:
        dt_object_utc = datetime.fromisoformat(timestamp_iso_utc_str.replace('Z', '+00:00'))
    except ValueError: 
        dt_object_utc = datetime.now(timezone.utc)
    hcm_tz = timezone(timedelta(hours=7))
    dt_object_hcm = dt_object_utc.astimezone(hcm_tz)
    return dt_object_hcm.strftime('%H:%M:%S %d/%m/%Y (GMT+7)')

def get_session_key(ip: str, user_agent: str | None) -> str: 
    if not user_agent: user_agent = "unknown_ua_mizuki" 
    ua_hash = hashlib.md5(user_agent.encode('utf-8')).hexdigest()[:8] 
    return f"{ip}_{ua_hash}"

async def flush_session_logs(session_key: str):
    if session_key not in active_sessions:
        return

    session_data = active_sessions.pop(session_key, None) 
    if not session_data or not session_data.get('logs'): 
        return

    user_info = session_data['user_info']
    logs = session_data['logs']

    admin_user = await client.fetch_user(ADMIN_USER_ID)
    if not admin_user:
        print(f"[FLUSH][LOI] Ko tim thay Admin: {ADMIN_USER_ID}")
        return

    embed = discord.Embed(
        title="🖱️ Log Tương Tác Tổng Hợp",
        color=discord.Color.from_rgb(100, 180, 220), 
        timestamp=datetime.fromisoformat(user_info['first_server_timestamp'].replace('Z', '+00:00'))
    )
    embed.add_field(name="👤 IP", value=f"`{user_info['ip']}`", inline=True)
    embed.add_field(name="⏰ Bắt đầu (VN)", value=user_info['first_client_time_hcm'], inline=True)
    embed.add_field(name="📍 Vị trí", value=user_info['location'], inline=False)
    
    action_details = ""
    for log_entry in logs:
        action_details += f"[`{log_entry['time']}`] {log_entry['action_text']}\n"
    
    MAX_FIELD_VALUE_LENGTH = 1020 
    action_chunks = [action_details[i:i + MAX_FIELD_VALUE_LENGTH] for i in range(0, len(action_details), MAX_FIELD_VALUE_LENGTH)]
    
    for i, chunk in enumerate(action_chunks):
        embed.add_field(
            name=f"🔎 Hành động {f'(Phần {i+1})' if len(action_chunks) > 1 else ''}", 
            value=chunk if chunk.strip() else "Không có hành động.", 
            inline=False
        )
    
    embed.add_field(name="🖥️ Thiết bị", value=f"```{user_info['userAgent']}```", inline=False)
    embed.set_footer(text="rin-personal-card | batched interaction log")

    await send_dm_safe(admin_user, embed=embed, context_log="Batched Interaction Log")
    

async def periodic_log_flusher():
    await client.wait_until_ready() 
    while not client.is_closed():
        await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
        now_utc = datetime.now(timezone.utc)
        expired_sessions_keys = []
        try: 
            current_session_keys = list(active_sessions.keys()) 
            for session_key in current_session_keys:
                if session_key in active_sessions: 
                    data = active_sessions[session_key]
                    if (now_utc - data['last_activity']).total_seconds() > SESSION_TIMEOUT_SECONDS:
                        expired_sessions_keys.append(session_key)
            
            for session_key in expired_sessions_keys:
                await flush_session_logs(session_key)
        except Exception as e:
            print(f"[FLUSHER][LOI] Loi trong periodic_log_flusher: {e}")


async def handle_notify_visit(request: web.Request):
    received_secret = request.headers.get("X-Mizuki-Secret")
    if MIZUKI_EXPECTED_SECRET and received_secret != MIZUKI_EXPECTED_SECRET:
        return web.Response(text="Forbidden: Invalid secret", status=403)
    try:
        data = await request.json()
        ip = data.get("ip", "N/A")

        if ip in EXCLUDED_IPS:
            return web.Response(text="Visit from excluded IP, notification skipped.", status=200)

        location = data.get("location", "Không rõ")
        country = data.get("country", "N/A")
        city = data.get("city", "N/A")
        region = data.get("region", "N/A")
        isp = data.get("isp", "N/A")
        user_agent = data.get("userAgent", "N/A")
        timestamp_iso_utc = data.get("timestamp", datetime.now(timezone.utc).isoformat())
        timestamp_formatted_hcm = format_timestamp_hcm(timestamp_iso_utc)
        
        admin_user = await client.fetch_user(ADMIN_USER_ID)
        if admin_user:
            embed = discord.Embed(
                title="🌐 Có lượt truy cập website!",
                color=discord.Color.from_rgb(137, 180, 250), 
                timestamp=datetime.fromisoformat(timestamp_iso_utc.replace('Z', '+00:00'))
            )
            embed.add_field(name="👤 IP", value=f"`{ip}`", inline=True)
            embed.add_field(name="⏰ Thời gian (VN)", value=timestamp_formatted_hcm, inline=True)
            embed.add_field(name="📍 Vị trí", value=location, inline=False)
            if country != "N/A": embed.add_field(name="🌍 Quốc gia", value=country, inline=True)
            if city != "N/A" or region != "N/A": embed.add_field(name="🏙️ TP/Vùng", value=f"{city} / {region}", inline=True)
            if isp != "N/A": embed.add_field(name="📡 ISP", value=isp, inline=True)
            embed.add_field(name="🖥️ Thiết bị", value=f"```{user_agent}```", inline=False)
            embed.set_footer(text="rin-personal-card | visit notification")

            await send_dm_safe(admin_user, embed=embed, context_log="Visit Notify")
        else:
            print(f"[VISIT][LOI] Ko tim thay Admin: {ADMIN_USER_ID}")
        return web.Response(text="Notification received by Mizuki.", status=200)
    except json.JSONDecodeError: 
        print("[VISIT][LOI] Data POST ko phai JSON.")
        return web.Response(text="Bad Request: Invalid JSON", status=400)
    except Exception as e:
        print(f"[VISIT][LOI] Xu ly: {e}")
        return web.Response(text=f"Internal Server Error: {e}", status=500)


async def handle_log_interaction(request: web.Request):
    received_secret = request.headers.get("X-Mizuki-Secret")
    if MIZUKI_EXPECTED_SECRET and received_secret != MIZUKI_EXPECTED_SECRET:
        return web.Response(text="Forbidden: Invalid secret", status=403)

    try:
        data = await request.json()
        ip = data.get("ip", "N/A")
        user_agent = data.get("userAgent", "N/A")

        if ip in EXCLUDED_IPS:
            return web.Response(text="Interaction from excluded IP, DM skipped.", status=200)
            
        client_timestamp_iso_utc = data.get("clientTimestamp", datetime.now(timezone.utc).isoformat())
        server_timestamp_iso_utc = data.get("serverTimestamp", datetime.now(timezone.utc).isoformat())
        
        event_type = data.get("eventType", "unknown_interaction")
        event_data = data.get("eventData", {})

        client_time_hcm_full = format_timestamp_hcm(client_timestamp_iso_utc)
        client_time_hcm_short = client_time_hcm_full.split(" ")[0] 
        
        session_key = get_session_key(ip, user_agent)

        action_text = ""
        current_lang = event_data.get('language', 'N/A').upper()
        
        if event_type == 'language_selected':
            action_text = f"Chon NN: **{event_data.get('language', 'N/A').upper()}**"
        elif event_type == 'view_changed':
            prev = event_data.get('previousView', 'N/A')
            curr = event_data.get('currentView', 'N/A')
            action_text = f"Chuyen View: `{prev}` ➡️ `{curr}` (NN: {current_lang})"
        elif event_type == 'about_subsection_viewed':
            prev_sub = event_data.get('previousSubSection', 'N/A')
            curr_sub = event_data.get('currentSubSection', 'N/A')
            action_text = f"Xem About: `{prev_sub}` ➡️ `{curr_sub}` (NN: {current_lang})"
        elif event_type == 'gallery_image_viewed':
            idx = event_data.get('imageIndex', -1)
            total = event_data.get('totalImages', 0)
            action = event_data.get('action', 'nav') 
            action_text_map = {'open_lightbox': "mo lightbox", 'carousel_side_click': "click anh phu"}
            details = action_text_map.get(action, "nav")
            action_text = f"Xem Gallery: `Anh {idx + 1}/{total}` ({details}) (NN: {current_lang})"
        elif event_type == 'guestbook_entry_viewed':
            entry_id = event_data.get('entryId', 'N/A')
            message_snippet = event_data.get('messageSnippet', 'N/A')
            action_text = f"Xem Guestbook: \"{message_snippet}\" (ID: `{entry_id}`, NN: {current_lang})"
        elif event_type == 'guestbook_entry_submitted':
            name = event_data.get('name', 'An danh')
            snippet = event_data.get('messageSnippet', '')
            action_text = f"Gui Guestbook: `{name}`, Snippet: \"{snippet}\" (NN: {current_lang})"
        else:
            details_json_str = json.dumps(event_data, indent=2, ensure_ascii=False)
            if len(details_json_str) > 100 : 
                details_json_str = details_json_str[:100] + "..."
            action_text = f"Event: `{event_type}` Data: `{details_json_str}`"


        log_entry = {'time': client_time_hcm_short, 'action_text': action_text}

        if session_key not in active_sessions:
            location = data.get("location", "Không rõ") 
            active_sessions[session_key] = {
                'logs': [log_entry],
                'last_activity': datetime.now(timezone.utc),
                'user_info': {
                    'ip': ip,
                    'location': location,
                    'userAgent': user_agent,
                    'first_client_time_hcm': client_time_hcm_full,
                    'first_server_timestamp': server_timestamp_iso_utc
                }
            }
        else:
            active_sessions[session_key]['logs'].append(log_entry)
            active_sessions[session_key]['last_activity'] = datetime.now(timezone.utc)

        if len(active_sessions[session_key]['logs']) >= LOG_BUFFER_LIMIT:
            await flush_session_logs(session_key)

        return web.Response(text="Interaction event received.", status=200)
    except json.JSONDecodeError:
        print("[LOG][LOI] Data POST ko phai JSON.")
        return web.Response(text="Bad Request: Invalid JSON", status=400)
    except Exception as e:
        print(f"[LOG][LOI] Xu ly: {e}")
        return web.Response(text=f"Internal Server Error: {e}", status=500)

async def setup_http_server():
    global http_runner
    app = web.Application()
    app.router.add_post('/notify-visit', handle_notify_visit)
    app.router.add_post('/log-interaction', handle_log_interaction)
    
    http_runner = web.AppRunner(app)
    await http_runner.setup()
    
    effective_port = int(os.getenv('PORT', MIZUKI_HTTP_PORT_STR))
    
    site = web.TCPSite(http_runner, '0.0.0.0', effective_port)
    try:
        await site.start()
        print(f"🌍 Mizuki HTTP server dang lang nghe port {effective_port}...")
    except OSError as e:
         print(f"[HTTP][LOI] Ko start server port {effective_port}: {e}")
         print("[HTTP][WARN] Bot chay ko co HTTP server.")


# xu ly lenh blog
async def handle_blog_command(message: discord.Message, command_content: str):
    if message.author.id != ADMIN_USER_ID:
        await send_dm_safe(message.channel, "⚠️ Bạn không có quyền đăng blog.", context_log="BlogPermDenied")
        return

    title_match = re.match(r"^\s*(.+?)\s*(?:\(|$)".strip(), command_content)
    title = title_match.group(1).strip() if title_match else None

    if not title:
        await send_dm_safe(message.channel, "⚠️ Vui lòng nhập tiêu đề cho bài blog.\nCú pháp: `blog <Tiêu đề bài viết> (đính kèm ảnh nếu có)`", context_log="BlogNoTitle")
        return

    image_url = None
    if message.attachments and len(message.attachments) > 0:
        attachment = message.attachments[0] 
        if attachment.content_type and attachment.content_type.startswith('image/'):
            image_url = attachment.url
        else:
            await send_dm_safe(message.channel, "⚠️ File đính kèm không phải là hình ảnh hợp lệ.", context_log="BlogInvalidAttachment")
    
    blog_content = None # hien tai ko co content

    blog_post_data = {
        "title": title,
        "content": blog_content,
        "image_url": image_url,
        "discord_message_id": str(message.id),
        "discord_author_id": str(message.author.id)
    }

    if not RIN_PERSONAL_CARD_API_URL:
        await send_dm_safe(message.channel, "🙁 Lỗi cấu hình: URL của server blog chưa được thiết lập cho Mizuki.", context_log="BlogAPIMissing")
        return

    try:
        api_url = f"{RIN_PERSONAL_CARD_API_URL}/api/blog/posts"
        headers = {
            'Content-Type': 'application/json',
            'X-Mizuki-Secret': MIZUKI_EXPECTED_SECRET 
        }
        async with ClientSession() as session:
            async with session.post(api_url, json=blog_post_data, headers=headers) as response:
                if response.status == 201:
                    response_data = await response.json()
                    await send_dm_safe(message.channel, f"✅ Đã đăng blog: '{response_data.get('title', title)}'\nID bài viết: {response_data.get('id')}", context_log="BlogPostSuccess")
                elif response.status == 409:
                    await send_dm_safe(message.channel, "⚠️ Bài blog này (dựa trên ID tin nhắn Discord) đã được đăng trước đó.", context_log="BlogPostDuplicate")
                else:
                    error_text = await response.text()
                    await send_dm_safe(message.channel, f"❌ Lỗi khi đăng blog: Server phản hồi {response.status} - {error_text}", context_log="BlogPostAPIError")
    except Exception as e:
        print(f"[BLOG_CMD][LOI] Lỗi gửi API: {e}")
        await send_dm_safe(message.channel, f"🙁 Có lỗi xảy ra khi kết nối tới server blog: {e}", context_log="BlogPostNetworkError")


@client.event
async def on_ready():
    print(f'>>> Logged in: {client.user.name} ({client.user.id}) <<<')
    print("--- Mizuki (Simplified) ---")
    print(f"--- Mizuki CMD Prefix: {COMMAND_PREFIX} ---")
    if not ADMIN_USER_ID:
        print(">>> CRITICAL ERROR: ADMIN_USER_ID not valid! Bot may not function. <<<")
    else:
        print(">>> Bot san sang nhan DM tu Admin! <<<")
        try:
            await setup_http_server()
            client.loop.create_task(periodic_log_flusher())
            print("📝 Log flusher da khoi dong.")
        except Exception as e:
            print(f"[LOI] Ko khoi tao dc HTTP server / log flusher: {e}")


@client.event
async def on_message(message: discord.Message):
    if not isinstance(message.channel, discord.DMChannel) or message.author.id != ADMIN_USER_ID:
        return

    if message.content.startswith(f"{COMMAND_PREFIX}shiromi_cmd"):
        try:
            parts = message.content[len(COMMAND_PREFIX) + len("shiromi_cmd"):].strip().split(maxsplit=1)
            if len(parts) < 2:
                await send_dm_safe(message.channel,
                                   f"⚠️ Cu phap: `{COMMAND_PREFIX}shiromi_cmd <kenh_ID/ten> <lenh_cho_Shiromi>`\n"
                                   f"*Ko can prefix Shiromi (`{SHIROMI_COMMAND_PREFIX_REFERENCE}`).*\n"
                                   f"Vd: `{COMMAND_PREFIX}shiromi_cmd general romi`",
                                   context_log="DM Shiromi Cmd Usage")
                return

            target_channel_specifier = parts[0]
            shiromi_command_to_send = parts[1]
            target_channel = await find_target_channel(target_channel_specifier)

            if target_channel:
                try:
                    await target_channel.send(shiromi_command_to_send)
                    await send_dm_safe(message.channel,
                                       f"✅ Da gui `{shiromi_command_to_send}` toi `#{target_channel.name}` (`{target_channel.guild.name}`).",
                                       context_log="DM Shiromi Cmd Success")
                except discord.Forbidden:
                    await send_dm_safe(message.channel, f"❌ Mizuki ko co quyen gui vao `#{target_channel.name}`.", context_log="DM Shiromi Cmd Perm Err")
                except discord.HTTPException as e_http:
                    await send_dm_safe(message.channel, f"❌ Loi HTTP gui toi `#{target_channel.name}`: {e_http}", context_log="DM Shiromi Cmd HTTP Err")
            else:
                await send_dm_safe(message.channel, f"⚠️ Ko tim thay kenh `{target_channel_specifier}`.", context_log="DM Shiromi Chan Not Found")
        except Exception as e:
            print(f"[SHIROMI_CMD][LOI] Xu ly: {e}")
            await send_dm_safe(message.channel, f"🙁 Loi xu ly lenh Shiromi: {e}", context_log="DM Shiromi Cmd Unexpected Err")
    
    elif message.content.startswith(f"{COMMAND_PREFIX}blog"):
        command_content = message.content[len(COMMAND_PREFIX) + len("blog"):].strip()
        await handle_blog_command(message, command_content)

    elif message.content.startswith(COMMAND_PREFIX): 
        try:
            parts = message.content[len(COMMAND_PREFIX):].strip().split(maxsplit=1)
            if len(parts) < 2:
                await send_dm_safe(message.channel, f"⚠️ Cu phap: `{COMMAND_PREFIX}<kenh_ID/ten> <noi_dung>`\nVd: `{COMMAND_PREFIX}general Chao!`", context_log="DM Send Raw Usage")
                return

            target_channel_specifier = parts[0]
            content_to_send = parts[1]
            target_channel = await find_target_channel(target_channel_specifier)

            if target_channel:
                try:
                    await target_channel.send(content_to_send)
                    await send_dm_safe(message.channel, f"✅ Da gui toi `#{target_channel.name}` trong `{target_channel.guild.name}`.", context_log="DM Send Raw Success")
                except discord.Forbidden:
                    await send_dm_safe(message.channel, f"❌ Ko co quyen gui vao `#{target_channel.name}`.", context_log="DM Send Raw Perm Err")
                except discord.HTTPException as e:
                    await send_dm_safe(message.channel, f"❌ Loi HTTP gui toi `#{target_channel.name}`: {e}", context_log="DM Send Raw HTTP Err")
            else:
                await send_dm_safe(message.channel, f"⚠️ Ko tim thay kenh `{target_channel_specifier}`.", context_log="DM Send Raw Chan Not Found")
        except Exception as e:
            print(f"[SEND_RAW][LOI] Xu ly: {e}")
            await send_dm_safe(message.channel, f"🙁 Loi khi gui tin: {e}", context_log="DM Send Raw Unexpected Err")

async def main():
    if not TOKEN:
        print("[LOI] Thieu DISCORD_TOKEN.")
        return
    if not ADMIN_USER_ID:
        print("[LOI] ADMIN_USER_ID ko hop le. Bot ko the h.dong.")
        return

    discord_client_task = asyncio.create_task(client.start(TOKEN))
    
    try:
        await discord_client_task
    except discord.errors.LoginFailure: print("[LOI] Token Discord ko hop le.")
    except discord.errors.PrivilegedIntentsRequired: print("[LOI] Thieu quyen Privileged Intents.")
    except discord.errors.ConnectionClosed as e: print(f"[LOI] Ket noi Discord bi dong: Code {e.code}, Reason: {e.reason}")
    except Exception as e:
        print(f"[LOI MAIN] Khi chay bot: {type(e).__name__}: {e}")
    finally:
        print("[SYS] Bot dang tat...")
        active_session_keys_on_shutdown = list(active_sessions.keys()) 
        if active_session_keys_on_shutdown:
            print(f"[SHUTDOWN FLUSH] Gui log cho {len(active_session_keys_on_shutdown)} session con lai...")
            for session_key in active_session_keys_on_shutdown:
                await flush_session_logs(session_key) 
            print("[SHUTDOWN FLUSH] Da gui xong.")
        
        if http_runner: 
            await http_runner.cleanup()
            print("[HTTP] Server da tat.")
        if client and not client.is_closed(): 
            await client.close()
        print("[SYS] Bot da tat.")


if __name__ == "__main__":
    print("--- Khoi dong Bot Mizuki (Relay + Gui tho + HTTP Visit/Log Notify) ---")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- Nhan Ctrl+C, dang thoat ---")
    except Exception as e:
        print(f"\n[RUNTIME][LOI] Loi ko mong muon o top-level: {type(e).__name__}: {e}")
    finally:
        print("--- Chuong trinh ket thuc ---")