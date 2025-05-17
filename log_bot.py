# Mizuki/log_bot.py
import discord
import os
from dotenv import load_dotenv
import asyncio
import json
from datetime import datetime, timezone, timedelta 
from aiohttp import web

# --- Tải biến môi trường ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252')
MIZUKI_HTTP_PORT_STR = os.getenv('MIZUKI_HTTP_PORT', os.getenv('PORT', '8080')) # Ưu tiên PORT từ Railway
MIZUKI_EXPECTED_SECRET = os.getenv('MIZUKI_SHARED_SECRET', 'default_secret_key_for_mizuki')


# --- Cấu hình chính ---
COMMAND_PREFIX = "!"
SHIROMI_COMMAND_PREFIX_REFERENCE = "Shi"

# --- Chuyển đổi ID Admin & Port ---
ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
        print(f"[CFG] ID Admin: {ADMIN_USER_ID}")
    except ValueError:
        print(f"[LỖI] ADMIN_USER_ID '{ADMIN_USER_ID_STR}' ko phải số.")
        ADMIN_USER_ID = None
else:
    print("[LỖI] ADMIN_USER_ID chưa dc cfg.")

MIZUKI_HTTP_PORT = 8080 # Port mặc định
try:
    MIZUKI_HTTP_PORT = int(MIZUKI_HTTP_PORT_STR)
except ValueError:
    print(f"[LỖI] MIZUKI_HTTP_PORT '{MIZUKI_HTTP_PORT_STR}' ko hợp lệ. Dùng port mặc định: {MIZUKI_HTTP_PORT}")


# --- Khởi tạo Bot Discord ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.members = True

client = discord.Client(intents=intents)

# --- State cho AIOHTTP server ---
http_runner = None

# --- Hàm Gửi DM An Toàn ---
async def send_dm_safe(user: discord.User | discord.DMChannel, content: str = None, embed: discord.Embed = None, context_log: str = "DM"):
    if not user:
        print(f"[DM CHECK][LỖI] Người nhận ko hợp lệ ({context_log}).")
        return
    target_channel : discord.abc.Messageable = None
    target_recipient_info = "Ko xác định"
    try:
        if isinstance(user, discord.DMChannel):
            target_channel = user
            target_recipient_info = str(user.recipient) if user.recipient else "DM Kênh"
        elif isinstance(user, (discord.User, discord.Member)): 
            target_recipient_info = str(user)
            if not user.dm_channel:
                target_channel = await user.create_dm()
            else:
                target_channel = user.dm_channel
        else:
            print(f"[DM CHECK][LỖI] Loại người nhận ko xđ: {type(user)}")
            return

        if not target_channel:
            print(f"[DM CHECK][LỖI] Ko thể xđ kênh DM tới {target_recipient_info} ({context_log}).")
            return
        
        if embed:
            await target_channel.send(embed=embed)
            print(f"[DM CHECK] Gửi EMBED {context_log} tới {target_recipient_info} thành công.")
            return 

        if content:
            if len(content) <= 2000:
                await target_channel.send(content)
            else: 
                chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
                for i, chunk in enumerate(chunks):
                    await target_channel.send(f"**(Phần {i+1}/{len(chunks)})**\n{chunk}")
                    await asyncio.sleep(0.6)
            print(f"[DM CHECK] Gửi TEXT {context_log} tới {target_recipient_info} thành công.")
        else:
            print(f"[DM CHECK][LỖI] Ko có content hoặc embed để gửi {context_log} tới {target_recipient_info}.")

    except discord.Forbidden:
        print(f"[DM CHECK][LỖI] Ko có quyền gửi {context_log} tới {target_recipient_info}.")
    except discord.HTTPException as e:
        print(f"[DM CHECK][LỖI] Lỗi HTTP {e.status} khi gửi {context_log}: {e.text}")
    except Exception as e:
        print(f"[DM CHECK][LỖI] Gửi {context_log}: {e}")


# --- Hàm tìm kênh mục tiêu ---
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

# --- HTTP Handler cho thông báo truy cập ---
async def handle_notify_visit(request: web.Request):
    received_secret = request.headers.get("X-Mizuki-Secret")
    if MIZUKI_EXPECTED_SECRET and received_secret != MIZUKI_EXPECTED_SECRET:
        print("[HTTP NOTIFY][LỖI] Sai secret key. Bỏ qua.")
        return web.Response(text="Forbidden: Invalid secret", status=403)

    try:
        data = await request.json()
        ip = data.get("ip", "N/A")
        location = data.get("location", "Không rõ")
        country = data.get("country", "N/A")
        city = data.get("city", "N/A")
        region = data.get("region", "N/A")
        isp = data.get("isp", "N/A")
        user_agent = data.get("userAgent", "N/A")
        timestamp_iso_utc = data.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Chuyển ISO string (mặc định là UTC từ server) sang datetime object UTC
        try:
            dt_object_utc = datetime.fromisoformat(timestamp_iso_utc.replace('Z', '+00:00'))
        except ValueError: # Nếu parse lỗi, dùng tgian hiện tại UTC
            dt_object_utc = datetime.now(timezone.utc)
        
        # Tạo timezone cho UTC+7 (TP.HCM)
        hcm_tz = timezone(timedelta(hours=7))
        # Chuyển datetime object từ UTC sang UTC+7
        dt_object_hcm = dt_object_utc.astimezone(hcm_tz)
        
        # Format thời gian hiển thị theo múi giờ UTC+7
        timestamp_formatted_hcm = dt_object_hcm.strftime('%H:%M:%S %d/%m/%Y (GMT+7)')

        admin_user = await client.fetch_user(ADMIN_USER_ID)
        if admin_user:
            embed = discord.Embed(
                title="🌐 Có lượt truy cập website!",
                color=discord.Color.from_rgb(137, 180, 250), 
                # timestamp của embed vẫn nên là UTC, Discord client sẽ tự hiển thị theo local của người xem
                # Hoặc có thể đặt là dt_object_hcm nếu muốn timestamp của embed cố định là giờ HCM
                timestamp=dt_object_utc 
            )
            embed.add_field(name="👤 IP", value=f"`{ip}`", inline=True)
            # Hiển thị thời gian đã chuyển đổi sang UTC+7
            embed.add_field(name="⏰ Thời gian (VN)", value=timestamp_formatted_hcm, inline=True) 
            embed.add_field(name="📍 Vị trí ước tính", value=location, inline=False)
            embed.add_field(name="🌍 Quốc gia", value=country, inline=True)
            embed.add_field(name="🏙️ TP/Vùng", value=f"{city} / {region}", inline=True)
            embed.add_field(name="📡 ISP", value=isp, inline=True)
            embed.add_field(name="🖥️ Thiết bị", value=f"```{user_agent}```", inline=False)
            embed.set_footer(text="rin-personal-card | visit notification")

            await send_dm_safe(admin_user, embed=embed, context_log="Visit Notify")
            print(f"[HTTP NOTIFY] Đã gửi tbáo visit cho Admin: IP {ip}, Time (HCM): {timestamp_formatted_hcm}")
        else:
            print(f"[HTTP NOTIFY][LỖI] Ko tìm thấy Admin User ID: {ADMIN_USER_ID}")

        return web.Response(text="Notification received by Mizuki.", status=200)
    except json.JSONDecodeError:
        print("[HTTP NOTIFY][LỖI] Dữ liệu POST ko phải JSON.")
        return web.Response(text="Bad Request: Invalid JSON", status=400)
    except Exception as e:
        print(f"[HTTP NOTIFY][LỖI] Xử lý tbáo visit: {e}")
        return web.Response(text=f"Internal Server Error: {e}", status=500)

# --- Hàm khởi tạo HTTP server  ---
async def setup_http_server():
    global http_runner 
    app = web.Application()
    app.router.add_post('/notify-visit', handle_notify_visit) 

    http_runner = web.AppRunner(app)
    await http_runner.setup()
    
    effective_port = int(os.getenv('PORT', MIZUKI_HTTP_PORT_STR))
    
    site = web.TCPSite(http_runner, '0.0.0.0', effective_port)
    await site.start()
    print(f"🌍 Mizuki HTTP server đang lắng nghe trên port {effective_port}...")

# --- Sự kiện Bot  ---
@client.event
async def on_ready():
    print(f'>>> Đã đăng nhập: {client.user.name} ({client.user.id}) <<<')
    print("--- Mizuki đơn giản hóa ---")
    print(f"--- Prefix lệnh Mizuki: {COMMAND_PREFIX} ---")
    print(f"--- Prefix lệnh Shiromi (tham khảo): {SHIROMI_COMMAND_PREFIX_REFERENCE} ---")
    if not ADMIN_USER_ID:
        print(">>> LỖI NGHIÊM TRỌNG: ADMIN_USER_ID KO HỢP LỆ! Bot sẽ ko h.động. <<<")
    else:
        print(">>> Bot đã sẵn sàng nhận lệnh DM từ Admin! <<<")
        await setup_http_server()

@client.event
async def on_message(message: discord.Message):
    if not isinstance(message.channel, discord.DMChannel) or message.author.id != ADMIN_USER_ID:
        return 

    print(f"[DM NHẬN] Từ Admin ({ADMIN_USER_ID}): {message.content[:100]}...")

    if message.content.startswith(f"{COMMAND_PREFIX}shiromi_cmd"):
        print(f"[DM LỆNH SHIROMI] Admin {ADMIN_USER_ID} gửi: {message.content}")
        try:
            parts = message.content[len(COMMAND_PREFIX) + len("shiromi_cmd"):].strip().split(maxsplit=1)
            if len(parts) < 2:
                await send_dm_safe(message.channel,
                                   f"⚠️ Cú pháp: `{COMMAND_PREFIX}shiromi_cmd <kênh_ID/tên> <lệnh_cho_Shiromi>`\n"
                                   f"*Ko cần prefix Shiromi (`{SHIROMI_COMMAND_PREFIX_REFERENCE}`).*\n"
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
                                       f"✅ Đã gửi `{shiromi_command_to_send}` tới `#{target_channel.name}` (`{target_channel.guild.name}`).",
                                       context_log="DM Shiromi Cmd Success")
                except discord.Forbidden:
                    await send_dm_safe(message.channel, f"❌ Mizuki ko có quyền gửi vào `#{target_channel.name}`.", context_log="DM Shiromi Cmd Perm Err")
                except discord.HTTPException as e_http:
                    await send_dm_safe(message.channel, f"❌ Lỗi HTTP gửi tới `#{target_channel.name}`: {e_http}", context_log="DM Shiromi Cmd HTTP Err")
            else:
                await send_dm_safe(message.channel, f"⚠️ Ko tìm thấy kênh `{target_channel_specifier}`.", context_log="DM Shiromi Chan Not Found")
        except Exception as e:
            print(f"[LỖI DM LỆNH SHIROMI] Xử lý: {e}")
            await send_dm_safe(message.channel, f"🙁 Lỗi xử lý lệnh Shiromi: {e}", context_log="DM Shiromi Cmd Unexpected Err")

    elif message.content.startswith(COMMAND_PREFIX):
        print(f"[DM LỆNH GỬI THÔ] Admin {ADMIN_USER_ID} gửi: {message.content}")
        try:
            parts = message.content[len(COMMAND_PREFIX):].strip().split(maxsplit=1)
            if len(parts) < 2:
                await send_dm_safe(message.channel, f"⚠️ Cú pháp: `{COMMAND_PREFIX}<kênh_ID/tên> <nội_dung>`\nVd: `{COMMAND_PREFIX}general Chào!`", context_log="DM Send Raw Usage")
                return

            target_channel_specifier = parts[0]
            content_to_send = parts[1]

            target_channel = await find_target_channel(target_channel_specifier)

            if target_channel:
                try:
                    await target_channel.send(content_to_send)
                    await send_dm_safe(message.channel, f"✅ Đã gửi tới `#{target_channel.name}` trong `{target_channel.guild.name}`.", context_log="DM Send Raw Success")
                except discord.Forbidden:
                    await send_dm_safe(message.channel, f"❌ Ko có quyền gửi vào `#{target_channel.name}`.", context_log="DM Send Raw Perm Err")
                except discord.HTTPException as e:
                    await send_dm_safe(message.channel, f"❌ Lỗi HTTP gửi tới `#{target_channel.name}`: {e}", context_log="DM Send Raw HTTP Err")
            else:
                await send_dm_safe(message.channel, f"⚠️ Ko tìm thấy kênh `{target_channel_specifier}`.", context_log="DM Send Raw Chan Not Found")
        except Exception as e:
            print(f"[LỖI DM LỆNH GỬI THÔ] Xử lý: {e}")
            await send_dm_safe(message.channel, f"🙁 Lỗi khi gửi tin: {e}", context_log="DM Send Raw Unexpected Err")

# --- Hàm chạy chính ---
async def main():
    if not TOKEN:
        print("[LỖI] Thiếu DISCORD_TOKEN.")
        return
    if not ADMIN_USER_ID:
        print("[LỖI] ADMIN_USER_ID ko hợp lệ. Bot ko thể h.động.")
        return

    # Chạy client.start() như một task nền
    discord_client_task = asyncio.create_task(client.start(TOKEN))
    
    try:
        await discord_client_task 
    except discord.errors.LoginFailure: print("[LỖI] Token Discord ko hợp lệ.")
    except discord.errors.PrivilegedIntentsRequired: print("[LỖI] Thiếu quyền Privileged Intents.")
    except discord.errors.ConnectionClosed as e: print(f"[LỖI] Kết nối Discord bị đóng: Code {e.code}, Reason: {e.reason}")
    except Exception as e:
        print(f"[LỖI NGHIÊM TRỌNG] Khi chạy bot: {type(e).__name__}: {e}")
    finally:
        print("[H.THỐNG] Bot đang tắt...")
        if http_runner: 
            await http_runner.cleanup() 
            print("[HTTP] Server đã tắt.")
        if client and not client.is_closed(): 
            await client.close()
        print("[H.THỐNG] Bot đã tắt.")

if __name__ == "__main__":
    print("--- Khởi động Bot Mizuki (Relay + Gửi thô + HTTP Visit Notify) ---")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- Nhận tín hiệu dừng (Ctrl+C) ---")
    except Exception as e:
        print(f"\n[LỖI ASYNCIO/RUNTIME] Lỗi ko mong muốn ở cấp cao nhất: {type(e).__name__}: {e}")
    finally:
        print("--- Chương trình kết thúc ---")
