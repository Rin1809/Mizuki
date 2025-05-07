# -*- coding: utf-8 -*-
import discord
import os
from dotenv import load_dotenv
import asyncio
# import traceback # Bỏ comment nếu cần debug chi tiết lỗi

# --- Tải biến môi trường ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_USER_ID_STR = os.getenv('ADMIN_USER_ID', '873576591693873252') # ID Admin mặc định nếu không có trong .env

# --- Cấu hình chính ---
COMMAND_PREFIX = "!" # Prefix cho các lệnh của Mizuki (như !shiromi_cmd, !send)
# Prefix mà Shiromi sử dụng (tham khảo cho admin, không dùng trong code gửi)
SHIROMI_COMMAND_PREFIX_REFERENCE = "Shi" 

# --- Chuyển đổi ID Admin ---
ADMIN_USER_ID = None
if ADMIN_USER_ID_STR:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
        print(f"[CẤU HÌNH] ID Admin có quyền điều khiển: {ADMIN_USER_ID}")
    except ValueError:
        print(f"[LỖI] ADMIN_USER_ID '{ADMIN_USER_ID_STR}' không phải là số.")
        ADMIN_USER_ID = None # Đảm bảo là None nếu lỗi
else:
    print("[LỖI] ADMIN_USER_ID chưa được cấu hình trong .env hoặc code.")

# --- Khởi tạo Bot Discord ---
intents = discord.Intents.default()
# Vẫn cần intents này để đọc DM, tìm kênh/user
intents.messages = True
intents.message_content = True # Bắt buộc để đọc nội dung DM
intents.guilds = True          # Cần để tìm kênh trong server
intents.dm_messages = True     # Bắt buộc để nhận DM
intents.members = True         # Cần để fetch_user nếu admin không có trong cache

client = discord.Client(intents=intents)

# --- Hàm Gửi DM An Toàn (Giữ lại để gửi phản hồi cho Admin) ---
async def send_dm_safe(user: discord.User | discord.DMChannel, content: str, context_log: str = "DM"):
    if not user:
        print(f"[DM CHECK][LỖI] Người nhận không hợp lệ ({context_log}).")
        return

    target_channel : discord.abc.Messageable = None
    target_recipient_info = "Không xác định"

    try:
        if isinstance(user, discord.DMChannel):
            target_channel = user
            target_recipient_info = str(user.recipient) if user.recipient else "DM Kênh"
        elif isinstance(user, (discord.User, discord.Member)): # Chấp nhận cả Member
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

# --- Hàm tìm kênh mục tiêu ---
async def find_target_channel(specifier: str) -> discord.TextChannel | None:
    """Tìm kênh text dựa trên ID hoặc tên."""
    target_channel = None
    try: # Tìm bằng ID
        channel_id = int(specifier)
        fetched_channel = client.get_channel(channel_id)
        if not fetched_channel:
            print(f"[KÊNH] Kênh ID {channel_id} không có trong cache, đang fetch...")
            fetched_channel = await client.fetch_channel(channel_id)
        if isinstance(fetched_channel, discord.TextChannel):
            target_channel = fetched_channel
        else:
            print(f"[KÊNH][LỖI] Kênh ID {channel_id} không phải là TextChannel ({type(fetched_channel)}).")
            target_channel = None # Đảm bảo trả về None

    except ValueError: # Không phải ID, tìm bằng tên
        print(f"[KÊNH] Tìm kênh bằng tên: '{specifier}'")
        found = False
        for guild in client.guilds:
            for channel_in_guild in guild.text_channels:
                if channel_in_guild.name.lower() == specifier.lower(): # So sánh không phân biệt hoa thường
                    target_channel = channel_in_guild
                    print(f"[KÊNH] Tìm thấy kênh '{target_channel.name}' trong server '{guild.name}'")
                    found = True
                    break
            if found:
                break
        if not found:
             print(f"[KÊNH] Không tìm thấy kênh nào tên '{specifier}' trong các server bot tham gia.")
             target_channel = None

    except discord.NotFound:
        print(f"[KÊNH][LỖI] Không tìm thấy kênh ID: {specifier}")
        target_channel = None
    except discord.Forbidden:
        print(f"[KÊNH][LỖI] Không có quyền fetch kênh ID: {specifier}")
        target_channel = None
    except Exception as e:
        print(f"[KÊNH][LỖI] Lỗi không mong muốn khi tìm kênh '{specifier}': {e}")
        target_channel = None

    return target_channel # Trả về kênh tìm được hoặc None


# --- Sự kiện Bot ---
@client.event
async def on_ready():
    print(f'>>> Đã đăng nhập: {client.user.name} ({client.user.id}) <<<')
    print("--- Mizuki đơn giản hóa ---")
    print(f"--- Prefix lệnh Mizuki: {COMMAND_PREFIX} ---")
    print(f"--- Prefix lệnh Shiromi (tham khảo): {SHIROMI_COMMAND_PREFIX_REFERENCE} ---")
    if not ADMIN_USER_ID:
        print(">>> LỖI NGHIÊM TRỌNG: ADMIN_USER_ID KHÔNG HỢP LỆ HOẶC CHƯA ĐẶT! Bot sẽ không hoạt động. <<<")
    else:
        print(">>> Bot đã sẵn sàng nhận lệnh DM từ Admin! <<<")

@client.event
async def on_message(message: discord.Message):
    # Chỉ xử lý tin nhắn DM từ Admin đã cấu hình
    if not isinstance(message.channel, discord.DMChannel) or message.author.id != ADMIN_USER_ID:
        return

    print(f"[DM NHẬN] Từ Admin ({ADMIN_USER_ID}): {message.content[:100]}...")

    # --- Lệnh Relay cho Shiromi ---
    if message.content.startswith(f"{COMMAND_PREFIX}shiromi_cmd"):
        print(f"[DM LỆNH SHIROMI] Admin {ADMIN_USER_ID} gửi lệnh: {message.content}")
        try:
            # Tách lệnh: !shiromi_cmd <tên_kênh_hoặc_ID> <lệnh_cho_Shiromi_KHÔNG_CẦN_PREFIX>
            parts = message.content[len(COMMAND_PREFIX) + len("shiromi_cmd"):].strip().split(maxsplit=1)
            if len(parts) < 2:
                await send_dm_safe(message.channel,
                                   f"⚠️ Cú pháp: `{COMMAND_PREFIX}shiromi_cmd <tên_kênh_hoặc_ID> <lệnh_cho_Shiromi>`\n"
                                   f"*Lưu ý: KHÔNG cần gõ prefix của Shiromi (ví dụ: `{SHIROMI_COMMAND_PREFIX_REFERENCE}`) khi dùng lệnh này.*\n"
                                   f"Ví dụ 1 (lệnh romi): `{COMMAND_PREFIX}shiromi_cmd general romi`\n"
                                   f"Ví dụ 2 (lệnh shiromirun): `{COMMAND_PREFIX}shiromi_cmd general shiromirun export_csv=True`",
                                   context_log="DM Shiromi Command Usage")
                return

            target_channel_specifier = parts[0]
            shiromi_command_to_send = parts[1] # Đây là chuỗi lệnh Shiromi thực thi, vd "romi" hoặc "shiromirun ..."

            target_channel = await find_target_channel(target_channel_specifier)

            if target_channel:
                try:
                    # Mizuki gửi CHUỖI LỆNH ĐẦY ĐỦ mà Shiromi sẽ hiểu (đã bỏ prefix Shiromi)
                    await target_channel.send(shiromi_command_to_send)
                    await send_dm_safe(message.channel,
                                       f"✅ Đã gửi lệnh `{shiromi_command_to_send}` tới kênh `#{target_channel.name}` (Server: `{target_channel.guild.name}`). Shiromi sẽ xử lý nếu lệnh hợp lệ.",
                                       context_log="DM Shiromi Command Success")
                except discord.Forbidden:
                    await send_dm_safe(message.channel, f"❌ Mizuki không có quyền gửi tin vào kênh `#{target_channel.name}`.", context_log="DM Shiromi Command Perm Error")
                except discord.HTTPException as e_http:
                    await send_dm_safe(message.channel, f"❌ Lỗi HTTP khi Mizuki gửi lệnh tới `#{target_channel.name}`: {e_http}", context_log="DM Shiromi Command HTTP Error")
            else:
                await send_dm_safe(message.channel, f"⚠️ Không tìm thấy kênh văn bản `{target_channel_specifier}` hoặc Mizuki không có quyền truy cập.", context_log="DM Shiromi Channel Not Found")
        except Exception as e:
            print(f"[LỖI DM LỆNH SHIROMI] Xử lý: {e}")
            # traceback.print_exc()
            await send_dm_safe(message.channel, f"🙁 Lỗi khi xử lý lệnh Shiromi: {e}", context_log="DM Shiromi Command Unexpected Error")

    # --- Lệnh gửi tin nhắn thô ---
    # Sử dụng prefix !<tên kênh> hoặc !<ID kênh>
    elif message.content.startswith(COMMAND_PREFIX):
        print(f"[DM LỆNH GỬI THÔ] Admin {ADMIN_USER_ID} gửi lệnh: {message.content}")
        try:
            # Tách: !<tên_kênh_hoặc_ID> <nội_dung_còn_lại>
            parts = message.content[len(COMMAND_PREFIX):].strip().split(maxsplit=1)
            if len(parts) < 2:
                await send_dm_safe(message.channel, f"⚠️ Cú pháp sai. Dùng: `{COMMAND_PREFIX}<tên_kênh_hoặc_ID> <nội_dung_tin_nhắn>`\nVí dụ: `{COMMAND_PREFIX}general Xin chào mọi người!`", context_log="DM Send Raw Usage")
                return

            target_channel_specifier = parts[0]
            content_to_send = parts[1]

            target_channel = await find_target_channel(target_channel_specifier)

            if target_channel:
                try:
                    await target_channel.send(content_to_send)
                    await send_dm_safe(message.channel, f"✅ Đã gửi tin nhắn tới `#{target_channel.name}` trong server `{target_channel.guild.name}`.", context_log="DM Send Raw Success")
                except discord.Forbidden:
                    await send_dm_safe(message.channel, f"❌ Bot không có quyền gửi tin nhắn vào kênh `#{target_channel.name}`.", context_log="DM Send Raw Permission Error")
                except discord.HTTPException as e:
                    await send_dm_safe(message.channel, f"❌ Lỗi HTTP khi gửi tin nhắn tới `#{target_channel.name}`: {e}", context_log="DM Send Raw HTTP Error")
            else:
                await send_dm_safe(message.channel, f"⚠️ Không tìm thấy kênh văn bản nào tên là `{target_channel_specifier}` hoặc bot không có quyền truy cập.", context_log="DM Send Raw Channel Not Found")
        except Exception as e:
            print(f"[LỖI DM LỆNH GỬI THÔ] Xử lý: {e}")
            # traceback.print_exc()
            await send_dm_safe(message.channel, f"🙁 Đã có lỗi xảy ra khi xử lý lệnh gửi tin: {e}", context_log="DM Send Raw Unexpected Error")

    # Bỏ qua các tin nhắn DM khác nếu không muốn làm gì thêm

# --- Hàm chạy chính ---
async def main():
    if not TOKEN:
        print("[LỖI] Thiếu DISCORD_TOKEN.")
        return
    if not ADMIN_USER_ID:
        print("[LỖI] ADMIN_USER_ID không hợp lệ hoặc chưa được đặt. Bot không thể hoạt động.")
        return

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
            print("[SYSTEM] Bot đang tắt...")
            # Không cần close_database() nữa
            print("[SYSTEM] Bot đã tắt.")

if __name__ == "__main__":
    print("--- Khởi động Bot Mizuki (Phiên bản đơn giản hóa: Relay lệnh + Gửi tin thô) ---")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- Nhận tín hiệu dừng (Ctrl+C) ---")
    except Exception as e:
        print(f"\n[LỖI ASYNCIO/RUNTIME] Lỗi không mong muốn ở cấp cao nhất: {type(e).__name__}: {e}")
        # traceback.print_exc()
    finally:
        print("--- Chương trình kết thúc ---")