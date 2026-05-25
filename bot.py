import os
import sys
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ZENMUX_MANAGEMENT_API_KEY = os.environ.get("ZENMUX_MANAGEMENT_API_KEY")

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN is not set")
    sys.exit(1)

if not ZENMUX_MANAGEMENT_API_KEY:
    print("ERROR: ZENMUX_MANAGEMENT_API_KEY is not set")
    sys.exit(1)

# Define your 4 API keys here — update the names to match yours
API_KEYS = {
    "key1": {"name": "Group 1", "key": os.environ.get("ZENMUX_KEY_1")},
    "key2": {"name": "Group 2", "key": os.environ.get("ZENMUX_KEY_2")},
    "key3": {"name": "Group 3", "key": os.environ.get("ZENMUX_KEY_3")},
    "key4": {"name": "Group 4", "key": os.environ.get("ZENMUX_KEY_4")},
}

def get_balance(api_key: str):
    resp = requests.get(
        "https://zenmux.ai/api/v1/management/payg/balance",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()
    return resp.json()["data"]

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 *ZenMux Balance Bot*\n\nCommands:\n"
        "/balance — check your PAYG credits\n"
        "/balance\\_all — check all API keys at once",
        parse_mode="Markdown"
    )

async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(info["name"], callback_data=key_id)]
        for key_id, info in API_KEYS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select an API key to check:", reply_markup=reply_markup)

async def balance_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = "💳 *ZenMux PAYG Balance — All Keys*\n\n"
    for key_id, info in API_KEYS.items():
        if not info["key"]:
            msg += f"*{info['name']}*: ❌ Not configured\n\n"
            continue
        try:
            data = get_balance(info["key"])
            msg += (
                f"*{info['name']}*\n"
                f"• Total: `${data['total_credits']:.2f}`\n"
                f"• Top-up: `${data['top_up_credits']:.2f}`\n"
                f"• Bonus: `${data['bonus_credits']:.2f}`\n\n"
            )
        except Exception as e:
            msg += f"*{info['name']}*: ❌ Error: {e}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key_id = query.data
    selected = API_KEYS.get(key_id)

    if not selected or not selected["key"]:
        await query.edit_message_text(f"❌ API key not configured for {key_id}")
        return

    try:
        data = get_balance(selected["key"])
        msg = (
            f"💳 *{selected['name']} Balance*\n\n"
            f"• Total credits: `${data['total_credits']:.2f}`\n"
            f"• Top-up credits: `${data['top_up_credits']:.2f}`\n"
            f"• Bonus credits: `${data['bonus_credits']:.2f}`"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {e}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("balance_all", balance_all))
app.add_handler(CallbackQueryHandler(button_handler))

print("Bot running...")
app.run_polling()