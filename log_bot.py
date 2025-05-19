# Mizuki/log_bot.py
import discord
import os
from dotenv import load_dotenv
import asyncio
import json
from datetime import datetime, timezone, timedelta
from aiohttp import web
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252')
MIZUKI_HTTP_PORT_STR = os.getenv('MIZUKI_HTTP_PORT', os.getenv('PORT', '8080')) 
MIZUKI_EXPECTED_SECRET = os.getenv('MIZUKI_SHARED_SECRET', 'default_secret_key_for_mizuki')

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

async def send_dm_safe(user: discord.User | discord.DMChannel, content: str = None, embed: discord.Embed = None, context_log: str = "DM"):
    if not user:
        # print(f"[DM CHECK][LOI] Nguoi nhan ko hop le ({context_log}).") # dev
        return
    target_channel : discord.abc.Messageable = None
    target_recipient_info = "Ko xac dinh"
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
            # print(f"[DM CHECK][LOI] Loai nguoi nhan ko xd: {type(user)}") # dev
            return

        if not target_channel:
            # print(f"[DM CHECK][LOI] Ko the xd kenh DM toi {target_recipient_info} ({context_log}).") # dev
            return
        
        if embed:
            await target_channel.send(embed=embed)
            return

        if content:
            if len(content) <= 2000:
                await target_channel.send(content)
            else: # chia tin nhan
                chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
                for i, chunk in enumerate(chunks):
                    await target_channel.send(f"**(Phan {i+1}/{len(chunks)})**\n{chunk}")
                    await asyncio.sleep(0.6) # tranh rate limit
        # else: print(f"[DM CHECK][LOI] Ko co content/embed de gui {context_log} toi {target_recipient_info}.") # dev

    except discord.Forbidden:
        print(f"[DM CHECK][LOI] Ko co quyen gui {context_log} toi {target_recipient_info}.")
    except discord.HTTPException as e:
        print(f"[DM CHECK][LOI] Loi HTTP {e.status} khi gui {context_log}: {e.text}")
    except Exception as e:
        print(f"[DM CHECK][LOI] Gui {context_log}: {e}")


async def find_target_channel(specifier: str) -> discord.TextChannel | None:
    target_channel = None
    try: # thu parse ID
        channel_id = int(specifier)
        fetched_channel = client.get_channel(channel_id)
        if not fetched_channel: # cache miss
            fetched_channel = await client.fetch_channel(channel_id)
        if isinstance(fetched_channel, discord.TextChannel):
            target_channel = fetched_channel
        else:
            target_channel = None 
    except ValueError: # ko phai ID so, tim theo ten
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

async def handle_notify_visit(request: web.Request):
    received_secret = request.headers.get("X-Mizuki-Secret")
    if MIZUKI_EXPECTED_SECRET and received_secret != MIZUKI_EXPECTED_SECRET:
        # print("[HTTP NOTIFY VISIT][LOI] Sai secret key. Bo qua.") # dev
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
            print(f"[HTTP NOTIFY VISIT][LOI] Ko tim thay Admin User ID: {ADMIN_USER_ID}")
        return web.Response(text="Notification received by Mizuki.", status=200)
    except json.JSONDecodeError: 
        print("[HTTP NOTIFY VISIT][LOI] Du lieu POST ko phai JSON.")
        return web.Response(text="Bad Request: Invalid JSON", status=400)
    except Exception as e:
        print(f"[HTTP NOTIFY VISIT][LOI] Xu ly tbao visit: {e}")
        return web.Response(text=f"Internal Server Error: {e}", status=500)

# Handler moi cho session log
async def handle_log_session_interactions(request: web.Request):
    received_secret = request.headers.get("X-Mizuki-Secret")
    if MIZUKI_EXPECTED_SECRET and received_secret != MIZUKI_EXPECTED_SECRET:
        # print("[HTTP SESSION LOG][LOI] Sai secret key. Bo qua.") # dev
        return web.Response(text="Forbidden: Invalid secret", status=403)

    try:
        data = await request.json()
        ip = data.get("ip", "N/A")

        if ip in EXCLUDED_IPS: # ko log neu ip bi chan
            return web.Response(text="Session log from excluded IP, DM skipped.", status=200)
            
        location = data.get("location", "Không rõ")
        user_agent = data.get("userAgent", "N/A")
        session_start_time_iso = data.get("sessionStartTime", datetime.now(timezone.utc).isoformat())
        session_end_time_iso = data.get("sessionEndTime", datetime.now(timezone.utc).isoformat())
        interactions = data.get("interactions", [])

        session_start_hcm = format_timestamp_hcm(session_start_time_iso)
        session_end_hcm = format_timestamp_hcm(session_end_time_iso)
        
        admin_user = await client.fetch_user(ADMIN_USER_ID)
        if not admin_user:
            print(f"[HTTP SESSION LOG][LOI] Ko tim thay Admin User ID: {ADMIN_USER_ID}")
            return web.Response(text="Admin user not found", status=500)

        embed_color = discord.Color.from_rgb(100, 160, 220) 
        if not interactions: 
            embed_color = discord.Color.from_rgb(220, 220, 180) 

        embed = discord.Embed(
            title="📊 Log Phiên Tương Tác",
            color=embed_color,
            timestamp=datetime.fromisoformat(session_end_time_iso.replace('Z', '+00:00'))
        )
        embed.add_field(name="👤 IP", value=f"`{ip}`", inline=True)
        embed.add_field(name="📍 Vị trí", value=location, inline=True)
        embed.add_field(name="⏰ Bắt đầu (VN)", value=session_start_hcm, inline=True)
        embed.add_field(name="⏰ Kết thúc (VN)", value=session_end_hcm, inline=True)
        embed.add_field(name="🖥️ Thiết bị", value=f"```{user_agent}```", inline=False)

        actions_summary = ""
        if not interactions:
            actions_summary = "_Không có hành động nào được ghi lại trong phiên này._"
        else:
            interaction_lines = []
            for i_idx, interaction in enumerate(interactions):
                event_type = interaction.get("eventType", "unknown")
                event_data = interaction.get("eventData", {})
                client_timestamp_iso = interaction.get("clientTimestamp", session_start_time_iso)
                
                dt_object_client_utc = datetime.fromisoformat(client_timestamp_iso.replace('Z', '+00:00'))
                hcm_tz = timezone(timedelta(hours=7))
                client_time_hcm_short = dt_object_client_utc.astimezone(hcm_tz).strftime('%H:%M:%S')
                
                current_lang = event_data.get('language', 'N/A').upper()
                action_detail = ""

                # Format chi tiet tung hanh dong
                if event_type == 'language_selected':
                    action_detail = f"Chon NN: **{event_data.get('language', 'N/A').upper()}**"
                elif event_type == 'view_changed':
                    prev = event_data.get('previousView', 'N/A')
                    curr = event_data.get('currentView', 'N/A')
                    action_detail = f"View: `{prev}` ➡️ `{curr}` (NN: {current_lang})"
                elif event_type == 'about_subsection_viewed':
                    prev_sub = event_data.get('previousSubSection', 'N/A')
                    curr_sub = event_data.get('currentSubSection', 'N/A')
                    action_detail = f"About: `{prev_sub}` ➡️ `{curr_sub}` (NN: {current_lang})"
                elif event_type == 'gallery_image_viewed':
                    idx = event_data.get('imageIndex', -1)
                    total = event_data.get('totalImages', 0)
                    action = event_data.get('action', 'nav') 
                    action_text = "nav"
                    if action == 'open_lightbox': action_text = "mo lightbox"
                    elif action == 'carousel_side_click': action_text = "click anh phu"
                    action_detail = f"Gallery: `Ảnh {idx + 1}/{total}` ({action_text}) (NN: {current_lang})"
                elif event_type == 'guestbook_entry_viewed':
                    action_detail = f"Guestbook: xem ID `{event_data.get('entryId', 'N/A')}` (NN: {current_lang})"
                elif event_type == 'guestbook_entry_submitted':
                    name = event_data.get('name', 'An danh')
                    snippet = event_data.get('messageSnippet', '')
                    action_detail = f"Guestbook: gửi bởi `{name}` - \"{snippet}\" (NN: {current_lang})"
                else:
                    details_json_str = json.dumps(event_data, ensure_ascii=False)
                    if len(details_json_str) > 50: details_json_str = details_json_str[:50] + "..."
                    action_detail = f"Event: `{event_type}`, Data: `{details_json_str}` (NN: {current_lang})"
                
                interaction_lines.append(f"`{client_time_hcm_short}` {action_detail}")

            actions_summary = "\n".join(interaction_lines)
            if len(actions_summary) > 1020: # gioi han ky tu field discord
                actions_summary = actions_summary[:1020] + "\n... (và các hành động khác)"
        
        embed.add_field(name="📜 Hành động trong phiên", value=actions_summary if actions_summary else "Không có hành động.", inline=False)
        embed.set_footer(text="rin-personal-card | session interaction log")

        await send_dm_safe(admin_user, embed=embed, context_log="Session Log")

        return web.Response(text="Session interactions logged by Mizuki.", status=200)
    except json.JSONDecodeError:
        print("[HTTP SESSION LOG][LOI] Du lieu POST ko phai JSON.")
        return web.Response(text="Bad Request: Invalid JSON", status=400)
    except Exception as e:
        print(f"[HTTP SESSION LOG][LOI] Xu ly log: {e}")
        return web.Response(text=f"Internal Server Error: {e}", status=500)

async def setup_http_server():
    global http_runner
    app = web.Application()
    app.router.add_post('/notify-visit', handle_notify_visit)
    # Xoa/comment out route log cu
    # app.router.add_post('/log-interaction', handle_log_interaction) 
    app.router.add_post('/log-session-interactions', handle_log_session_interactions) # Them route moi
    
    http_runner = web.AppRunner(app)
    await http_runner.setup()
    
    effective_port = int(os.getenv('PORT', MIZUKI_HTTP_PORT_STR)) 
    
    site = web.TCPSite(http_runner, '0.0.0.0', effective_port) 
    try:
        await site.start()
        print(f"🌍 Mizuki HTTP server dang lang nghe tren port {effective_port}...")
    except OSError as e:
         print(f"[LOI HTTP SERVER] Khong the start server tren port {effective_port}: {e}")
         print("[LOI HTTP SERVER] Bot se tiep tuc chay ma khong co HTTP server.")


@client.event
async def on_ready():
    print(f'>>> Da dang nhap: {client.user.name} ({client.user.id}) <<<')
    print("--- Mizuki don gian hoa ---")
    print(f"--- Prefix lenh Mizuki: {COMMAND_PREFIX} ---")
    print(f"--- Prefix lenh Shiromi (tham khao): {SHIROMI_COMMAND_PREFIX_REFERENCE} ---")
    if not ADMIN_USER_ID:
        print(">>> LOI NGHIEM TRONG: ADMIN_USER_ID KO HOP LE! Bot se ko h.dong. <<<")
    else:
        print(">>> Bot da san sang nhan lenh DM tu Admin! <<<")
        try:
            await setup_http_server() 
        except Exception as e:
            print(f"[LOI] Khong the khoi tao HTTP server: {e}")


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
            print(f"[LOI DM LENH SHIROMI] Xu ly: {e}")
            await send_dm_safe(message.channel, f"🙁 Loi xu ly lenh Shiromi: {e}", context_log="DM Shiromi Cmd Unexpected Err")

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
            print(f"[LOI DM LENH GUI THO] Xu ly: {e}")
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
        print(f"[LOI NGHIEM TRONG] Khi chay bot: {type(e).__name__}: {e}")
    finally:
        print("[H.THONG] Bot dang tat...")
        if http_runner:
            await http_runner.cleanup()
            print("[HTTP] Server da tat.")
        if client and not client.is_closed():
            await client.close()
        print("[H.THONG] Bot da tat.")

if __name__ == "__main__":
    print("--- Khoi dong Bot Mizuki (Relay + Gui tho + HTTP Visit/Interaction Notify) ---")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- Nhan tin hieu dung (Ctrl+C) ---")
    except Exception as e:
        print(f"\n[LOI ASYNCIO/RUNTIME] Loi ko mong muon o cap cao nhat: {type(e).__name__}: {e}")
    finally:
        print("--- Chuong trinh ket thuc ---")