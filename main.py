import json
import os
import asyncio
import time
import re
import pathlib
import unicodedata

# ─────────────────────────────────────────────
#  TgCrypto — speeds up MTProto encryption
# ─────────────────────────────────────────────
try:
    import tgcrypto  # noqa: F401
    print("[CRYPTO] ✅ TgCrypto is active — encryption accelerated")
except ImportError:
    print("[CRYPTO] ⚠️  TgCrypto not found. Run: pip install tgcrypto")

from telethon import TelegramClient, events, Button
from telethon.tl import functions, types
from telethon.errors import MessageNotModifiedError
from telethon.utils import get_peer_id

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────
API_ID          = 30322662
API_HASH        = '820261ca851804a5c11b91cad4afc12f'
BOT_TOKEN       = '8870533936:AAFdjf7PNrhY1bu4Cd-dSeaStyIGk04B1pc'
HELPER_USERNAME = '@Tkdara_bot'

CATCHER_BOT_ID  = 6157455819

CHEAT_BOTS = {
    "zs": "zswaifu_cheat_bot",
    "sik": "Sik_waifu_bot",
}

# ─────────────────────────────────────────────
#  Invisible character cleaner
# ─────────────────────────────────────────────
INVISIBLE_CHARS = re.compile(
    r'[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064'
    r'\ufeff\u00ad\u180e\u00a0\u202f\u205f\u3000]'
)

def clean_text(text: str) -> str:
    cleaned = INVISIBLE_CHARS.sub('', text)
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) not in ('Cc', 'Cf'))
    return cleaned

def clean_character_name(text: str) -> str:
    cleaned = clean_text(text)
    cleaned = cleaned.replace('`', '').replace('"', '').replace("'", '').strip()
    return re.sub(r'\s+', ' ', cleaned).lower()

# ─────────────────────────────────────────────
#  Spawn trigger phrases
# ─────────────────────────────────────────────
SPAWN_TEXTS = [
    "ʜᴀs sᴘᴀᴡɴᴇᴅ ɪɴ ᴛʜᴇ ᴄʜᴀᴛ",
    "ꜱᴘᴀᴡɴᴇᴅ",
    "spawned in the chat",
    "A wild character appeared",
    "یه کاراکتر جدید ظاهر شد",
]

# ─────────────────────────────────────────────
#  Database helpers
# ─────────────────────────────────────────────
DB_DIR  = pathlib.Path(__file__).parent / 'data'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = str(DB_DIR / 'db.json')

DEFAULT_DB = {
    "is_active": False,
    "anti_spam": False,
    "delay": 5,
    "groups": {},
    "pending_action": None,
    "auto_react": False,
    "fake_online": False,
    "total_catches": 0,
    "antispam_count": 0,
    "selected_cheat_bot": "zs",
    "catch_mode": "dot",
    "rarity_catcher": {
        "🔵": True, "🟣": True, "🟠": True, "🟡": True,
        "💮": True, "⚜️": True, "⚡": True, "🪞": True, "✨": True, "❓": True
    },
}

def save_db(data: dict):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

_db_cache: dict = {}
_db_mtime: float = 0.0

def load_db() -> dict:
    global _db_cache, _db_mtime
    try:
        mtime = os.path.getmtime(DB_FILE)
        if mtime != _db_mtime:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in DEFAULT_DB.items():
                if k not in data:
                    data[k] = v
            if "rarity_catcher" in data:
                for rk, rv in DEFAULT_DB["rarity_catcher"].items():
                    if rk not in data["rarity_catcher"]:
                        data["rarity_catcher"][rk] = rv
            _db_cache = data
            _db_mtime = mtime
        return dict(_db_cache)
    except Exception:
        return dict(DEFAULT_DB)

def init_db():
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        save_db(dict(DEFAULT_DB))

init_db()

# ─────────────────────────────────────────────
#  Clients
# ─────────────────────────────────────────────
user_client = TelegramClient(
    'siki', API_ID, API_HASH,
    connection_retries=5,
    retry_delay=1,
    flood_sleep_threshold=60,
)
bot_client = TelegramClient(
    'helper_tkdara_session', API_ID, API_HASH,
    connection_retries=5,
    retry_delay=1,
    flood_sleep_threshold=60,
)

# ─────────────────────────────────────────────
#  Runtime state
# ─────────────────────────────────────────────
ADMIN_ID: int | None = None
temp_rarity: dict = {}
latest_spawn_chat_id: int | None = None
catch_timestamps: list[float] = []
cooldown_until: float = 0.0

# ─────────────────────────────────────────────
#  Menu builders
# ─────────────────────────────────────────────
def build_main_menu():
    data = load_db()
    status_emoji   = "Active" if data["is_active"] else "Off"
    antispam_emoji = "Active" if data["anti_spam"] else "Off"
    groups_list    = "\n".join(f"  • {lnk}" for lnk in data["groups"].values()) or "  (none)"

    active_bot_name = "ZS Cheat" if data.get("selected_cheat_bot") == "zs" else "Sik Waifu"
    modes_display = {
        "full": "/catch@Character_Catcher_Bot",
        "slash": "/catch",
        "dot": ".catch"
    }
    active_mode_str = modes_display.get(data.get("catch_mode", "dot"), ".catch")

    text = (
        "⠀⠀⠀⠀🌸 AutoCatch 🌸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n\n"
        f"❖ Status        ›  {status_emoji}\n"
        f"❖ Anti-Spam    ›  {antispam_emoji}\n"
        f"❖ Cheat Bot    ›  {active_bot_name}\n"
        f"❖ Catch Mode   ›  {active_mode_str}\n"
        f"❖ Auto React   ›  {'Active' if data['auto_react'] else 'Off'}\n"
        f"❖ Fake Online  ›  {'Active' if data['fake_online'] else 'Off'}\n"
        f"❖ Delay         ›  {data['delay']}s\n\n"
        f"🗂 Groups:\n{groups_list}\n"
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    )

    toggle_style = "success" if data["is_active"] else "danger"
    spam_style   = "success" if data["anti_spam"] else "danger"
    react_style  = "success" if data["auto_react"] else "danger"
    online_style = "success" if data["fake_online"] else "danger"

    keyboard = [
        [Button.inline(f"{'✅' if data['is_active'] else '❌'} AutoCatch: {'Active' if data['is_active'] else 'Off'}", data=b"toggle", style=toggle_style)],
        [Button.inline(f"{'✅' if data['anti_spam'] else '❌'} Anti-Spam: {'Active' if data['anti_spam'] else 'Off'}", data=b"toggle_antispam", style=spam_style)],
        [
            Button.inline(f"🤖 Bot: {active_bot_name}", data=b"menu_cheat_bot", style="primary"),
            Button.inline(f"🎮 Mode: {active_mode_str}", data=b"menu_catch_mode", style="primary"),
        ],
        [Button.inline(f"{'✅' if data['auto_react'] else '❌'} Auto React: {'Active' if data['auto_react'] else 'Off'}", data=b"toggle_react", style=react_style)],
        [Button.inline(f"{'✅' if data['fake_online'] else '❌'} Fake Type & Online: {'Active' if data['fake_online'] else 'Off'}", data=b"toggle_online", style=online_style)],
        [Button.inline("⚙️ Rarity Settings", data=b"rarity_catcher", style="primary")],
        [Button.inline("📊 Stats", data=b"show_stats", style="primary")],
        [Button.inline(f"⏱ Delay: {data['delay']}s", data=b"menu_delay", style="primary")],
        [
            Button.inline("➕ Add Group", data=b"add_group", style="primary"),
            Button.inline("➖ Remove Group", data=b"remove_group", style="primary"),
        ],
    ]
    return text, keyboard

def build_cheat_bot_menu():
    data = load_db()
    current = data.get("selected_cheat_bot", "zs")
    text = "⠀⠀⠀⠀🤖 Select Cheat Bot⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n\nانتخاب کن پیام‌های اسپاون به کدوم چیت‌بات ارسال بشن:"
    keyboard = [
        [Button.inline(f"{'✅' if current == 'zs' else '⚪'} @zswaifu_cheat_bot", data=b"set_bot_zs", style="success" if current == "zs" else "primary")],
        [Button.inline(f"{'✅' if current == 'sik' else '⚪'} @Sik_waifu_bot", data=b"set_bot_sik", style="success" if current == "sik" else "primary")],
        [Button.inline("⬅️ Back", data=b"back_to_main", style="danger")]
    ]
    return text, keyboard

def build_catch_mode_menu():
    data = load_db()
    current = data.get("catch_mode", "dot")
    text = "⠀⠀⠀⠀🎮 Select Catch Command Style⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n\nفرمت دستوری که به گروه ارسال میشه رو انتخاب کن:"
    keyboard = [
        [Button.inline(f"{'✅' if current == 'full' else '⚪'} /catch@Character_Catcher_Bot name", data=b"set_mode_full", style="success" if current == "full" else "primary")],
        [Button.inline(f"{'✅' if current == 'slash' else '⚪'} /catch name", data=b"set_mode_slash", style="success" if current == "slash" else "primary")],
        [Button.inline(f"{'✅' if current == 'dot' else '⚪'} .catch name", data=b"set_mode_dot", style="success" if current == "dot" else "primary")],
        [Button.inline("⬅️ Back", data=b"back_to_main", style="danger")]
    ]
    return text, keyboard

def build_delay_menu():
    data = load_db()
    text = (
        "⠀⠀⠀⠀⏱ Set Catch Delay⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
        f"⠀⠀⠀⠀Current delay: {data['delay']} seconds⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"
    )
    keyboard = [
        [Button.inline("1s", data=b"set_delay_1", style="primary"), Button.inline("2s", data=b"set_delay_2", style="primary")],
        [Button.inline("3s", data=b"set_delay_3", style="primary"), Button.inline("4s", data=b"set_delay_4", style="primary")],
        [Button.inline("5s", data=b"set_delay_5", style="primary"), Button.inline("6s", data=b"set_delay_6", style="primary")],
        [Button.inline("7s", data=b"set_delay_7", style="primary"), Button.inline("8s", data=b"set_delay_8", style="primary")],
        [Button.inline("⬅️ Back", data=b"back_to_main", style="danger")],
    ]
    return text, keyboard

CATCHER_RARITIES = [
    ("🔵", "Common"),
    ("🟣", "Uncommon"),
    ("🟠", "Rare"),
    ("🟡", "Legendary"),
    ("💮", "Mystical"),
    ("⚜️", "Divine"),
    ("⚡", "CrossVerse"),
    ("🪞", "Supreme"),
    ("✨", "Cataphract"),
    ("❓", "Unknown / Special"),
]

def build_rarity_menu(temp: dict):
    text = "⠀⠀⠀⠀⚙️ @Character_Catcher_Bot Rarity Settings\n"
    keyboard = []
    for emoji, name in CATCHER_RARITIES:
        is_on = temp.get(emoji, True)
        label = f"{emoji} {name}"
        style = "success" if is_on else "primary"
        cb    = f"rtoggle_{emoji}".encode()
        keyboard.append([Button.inline(label, data=cb, style=style)])
    keyboard.append([
        Button.inline("💾 Save",  data=b"rsave_catcher", style="success"),
        Button.inline("⬅️ Back", data=b"back_to_main",  style="danger"),
    ])
    return text, keyboard

def build_stats_menu():
    data = load_db()
    text = "⠀⠀⠀⠀📊 Statistics\n"
    keyboard = [
        [
            Button.inline(f"🎯 Total Catches: {data.get('total_catches', 0)}", data=b"noop1", style="primary"),
            Button.inline(f"🛡 Anti-Spam: {data.get('antispam_count', 0)}", data=b"noop2", style="primary"),
        ],
        [Button.inline("⬅️ Back", data=b"back_to_main", style="danger")],
    ]
    return text, keyboard

# ─────────────────────────────────────────────
#  Bot Callbacks
# ─────────────────────────────────────────────
@bot_client.on(events.InlineQuery)
async def inline_handler(event):
    try:
        if event.text == "menu":
            text, keyboard = build_main_menu()
            await event.answer([
                event.builder.article("Menu", text=text, buttons=keyboard, link_preview=False)
            ])
    except Exception:
        pass

@bot_client.on(events.CallbackQuery)
async def callback_handler(event):
    global ADMIN_ID

    if event.sender_id != ADMIN_ID:
        return await event.answer("⛔ Unauthorized.", alert=True)

    data = load_db()
    cb   = event.data.decode()

    try:
        if cb == "toggle":
            data["is_active"] = not data["is_active"]
        elif cb == "toggle_antispam":
            data["anti_spam"] = not data["anti_spam"]
        elif cb == "toggle_react":
            data["auto_react"] = not data["auto_react"]
        elif cb == "toggle_online":
            data["fake_online"] = not data["fake_online"]
        elif cb.startswith("noop"):
            return await event.answer()
        elif cb == "show_stats":
            text, kb = build_stats_menu()
            save_db(data)
            return await event.edit(text, buttons=kb, link_preview=False)

        # انتخاب بات چیت
        elif cb == "menu_cheat_bot":
            text, kb = build_cheat_bot_menu()
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "set_bot_zs":
            data["selected_cheat_bot"] = "zs"
            save_db(data)
            text, kb = build_cheat_bot_menu()
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "set_bot_sik":
            data["selected_cheat_bot"] = "sik"
            save_db(data)
            text, kb = build_cheat_bot_menu()
            return await event.edit(text, buttons=kb, link_preview=False)

        # انتخاب استایل دستور
        elif cb == "menu_catch_mode":
            text, kb = build_catch_mode_menu()
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "set_mode_full":
            data["catch_mode"] = "full"
            save_db(data)
            text, kb = build_catch_mode_menu()
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "set_mode_slash":
            data["catch_mode"] = "slash"
            save_db(data)
            text, kb = build_catch_mode_menu()
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "set_mode_dot":
            data["catch_mode"] = "dot"
            save_db(data)
            text, kb = build_catch_mode_menu()
            return await event.edit(text, buttons=kb, link_preview=False)

        elif cb == "rarity_catcher":
            temp_rarity["catcher"] = dict(data.get("rarity_catcher", {}))
            text, kb = build_rarity_menu(temp_rarity["catcher"])
            save_db(data)
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb.startswith("rtoggle_"):
            emoji = cb.split("_", 1)[1]
            if "catcher" not in temp_rarity:
                temp_rarity["catcher"] = dict(data.get("rarity_catcher", {}))
            temp_rarity["catcher"][emoji] = not temp_rarity["catcher"].get(emoji, True)
            text, kb = build_rarity_menu(temp_rarity["catcher"])
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "rsave_catcher":
            if "catcher" in temp_rarity:
                data["rarity_catcher"] = temp_rarity.pop("catcher")
            save_db(data)
            text, kb = build_main_menu()
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "menu_delay":
            text, kb = build_delay_menu()
            save_db(data)
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb.startswith("set_delay_"):
            data["delay"] = max(1, int(cb.split("_")[-1]))
        elif cb == "back_to_main":
            text, kb = build_main_menu()
            save_db(data)
            return await event.edit(text, buttons=kb, link_preview=False)
        elif cb == "add_group":
            data["pending_action"] = "add"
            save_db(data)
            return await event.edit(
                "Send the group link or ID as a reply to this message, then tap Save.",
                buttons=[[Button.inline("💾 Save", data=b"save", style="success")]],
                link_preview=False,
            )
        elif cb == "remove_group":
            data["pending_action"] = "remove"
            save_db(data)
            return await event.edit(
                "Reply with the group link or ID you want to remove, then tap Save.",
                buttons=[[Button.inline("💾 Save", data=b"save", style="success")]],
                link_preview=False,
            )
        elif cb == "save":
            data["pending_action"] = None

        save_db(data)
        text, kb = build_main_menu()
        await event.edit(text, buttons=kb, link_preview=False)

    except MessageNotModifiedError:
        pass
    except Exception as e:
        print(f"[callback_handler] {e}")

# ─────────────────────────────────────────────
#  User client handlers
# ─────────────────────────────────────────────
@user_client.on(events.NewMessage(outgoing=True, pattern=r'^/autocatch$'))
async def show_menu(event):
    await event.delete()
    results = await user_client.inline_query(HELPER_USERNAME, 'menu')
    if results:
        await results[0].click(event.chat_id)

@user_client.on(events.NewMessage(outgoing=True))
async def handle_group_replies(event):
    if not event.is_reply:
        return
    data = load_db()
    if data["pending_action"] not in ("add", "remove") or not event.text:
        return

    reply = await event.get_reply_message()
    if not reply or not reply.text:
        return
    if "group" not in reply.text.lower() and "section" not in reply.text.lower():
        return

    for line in event.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            chat = await user_client.get_entity(line)
            cid = str(get_peer_id(chat))
            if data["pending_action"] == "add":
                data["groups"][cid] = line
                print(f"[GROUP] Added: {line} (id: {cid})")
            else:
                data["groups"].pop(cid, None)
                print(f"[GROUP] Removed: {line}")
        except Exception as e:
            print(f"[GROUP] Could not resolve '{line}': {e}")

    data["pending_action"] = None
    save_db(data)
    await event.delete()

# ─────────────────────────────────────────────
#  Spawn detection
# ─────────────────────────────────────────────
@user_client.on(events.NewMessage(incoming=True))
async def spawn_detector(event):
    global latest_spawn_chat_id, cooldown_until

    if event.is_private or event.fwd_from is not None:
        return

    if event.sender_id != CATCHER_BOT_ID:
        return

    data = load_db()

    if not data["is_active"]:
        return

    if data["anti_spam"] and time.time() < cooldown_until:
        return

    cid = str(event.chat_id)
    if cid not in data["groups"]:
        return

    raw_text = event.message.message if event.message else ""
    if not raw_text:
        return

    text = clean_text(raw_text)

    rarity_cfg = data.get("rarity_catcher", {})
    found_emoji = None
    for emoji in rarity_cfg.keys():
        if emoji in text:
            found_emoji = emoji
            break

    for phrase in SPAWN_TEXTS:
        if phrase in text:
            if found_emoji and not rarity_cfg.get(found_emoji, True):
                print(f"[SPAWN] ⛔ Rarity {found_emoji} is disabled, skipping")
                return

            bot_key = data.get("selected_cheat_bot", "zs")
            target_cheat_bot = CHEAT_BOTS.get(bot_key, "zswaifu_cheat_bot")

            print(f"[SPAWN] ✅ Detected! Forwarding to @{target_cheat_bot}")
            latest_spawn_chat_id = event.chat_id

            if data["delay"] > 0:
                await asyncio.sleep(data["delay"])

            try:
                await user_client.forward_messages(target_cheat_bot, event.message)
                print(f"[SPAWN] ✅ Successfully forwarded to @{target_cheat_bot}")
            except Exception as e:
                print(f"[SPAWN] ❌ Forward failed: {e}")
            return

# ─────────────────────────────────────────────
#  Receive answer from Cheat Bot
# ─────────────────────────────────────────────
@user_client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def cheat_bot_reply(event):
    global latest_spawn_chat_id, catch_timestamps, cooldown_until

    if not latest_spawn_chat_id or not event.raw_text:
        return

    data = load_db()
    current_key = data.get("selected_cheat_bot", "zs")
    expected_bot = CHEAT_BOTS.get(current_key, "zswaifu_cheat_bot").lower()

    chat = await event.get_chat()
    username = getattr(chat, 'username', '') or ''
    if username.lower() != expected_bot:
        return

    raw = clean_text(event.raw_text)

    # رد کردن پیام‌های خطا یا نشناختن کاراکتر
    if any(kw in raw for kw in ("❌", "Not Found", "Processing", "recognize", "I don't recognize")):
        print(f"[CHEAT] ⚠️ Character not recognized by @{username}. Skipping.")
        latest_spawn_chat_id = None
        return

    # استخراج نام کاراکتر از هر دو فرمت خروجی
    match = re.search(r'(?:▲:\s*)?/catch(?:@[a-zA-Z0-9_]+)?\s+([^\n\r]+)', raw)
    if not match:
        return

    char_name = clean_character_name(match.group(1))

    # قالب‌بندی طبق حالت انتخاب‌شده در پنل
    mode = data.get("catch_mode", "dot")
    if mode == "full":
        catch_cmd = f"/catch@Character_Catcher_Bot {char_name}"
    elif mode == "slash":
        catch_cmd = f"/catch {char_name}"
    else:  # "dot"
        catch_cmd = f".catch {char_name}"

    target_chat = latest_spawn_chat_id
    latest_spawn_chat_id = None

    data["total_catches"] = data.get("total_catches", 0) + 1
    save_db(data)
    print(f"[CATCH] Sending: {catch_cmd} → chat {target_chat}")

    if data.get("fake_online"):
        try:
            await user_client(functions.messages.SetTypingRequest(
                peer=target_chat,
                action=types.SendMessageTypingAction()
            ))
        except Exception:
            pass

    sent = await user_client.send_message(target_chat, catch_cmd)

    if data.get("auto_react"):
        async def delayed_reaction(peer, msg_id):
            await asyncio.sleep(6)
            try:
                await user_client(functions.messages.SendReactionRequest(
                    peer=peer,
                    msg_id=msg_id,
                    reaction=[types.ReactionEmoji(emoticon="🦄")]
                ))
                print(f"[REACT] 🦄 Reacted to message {msg_id}")
            except Exception as e:
                print(f"[REACT] Reaction failed: {e}")

        asyncio.create_task(delayed_reaction(target_chat, sent.id))

    if data["anti_spam"]:
        now = time.time()
        catch_timestamps = [t for t in catch_timestamps if now - t <= 300]
        catch_timestamps.append(now)
        if len(catch_timestamps) >= 3:
            cooldown_until = now + 180
            catch_timestamps.clear()
            data["antispam_count"] = data.get("antispam_count", 0) + 1
            save_db(data)
            print("[ANTI-SPAM] Cooldown active for 3 minutes.")

# ─────────────────────────────────────────────
#  Fake online loop
# ─────────────────────────────────────────────
async def fake_online_loop():
    while True:
        try:
            db = load_db()
            if db.get("fake_online"):
                await user_client(functions.account.UpdateStatusRequest(offline=False))
        except Exception:
            pass
        await asyncio.sleep(120)

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
async def main():
    global ADMIN_ID

    await user_client.start()
    await bot_client.start(bot_token=BOT_TOKEN)

    me = await user_client.get_me()
    ADMIN_ID = me.id
    print(f"[READY] Logged in as {me.first_name} (ID: {ADMIN_ID})")
    print("[READY] AutoCatch bot is running. Send /autocatch in any chat.")

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected(),
        fake_online_loop(),
    )

if __name__ == '__main__':
    asyncio.run(main())
