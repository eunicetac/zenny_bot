import os
import sys
import requests
from datetime import datetime, timedelta, timezone
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

# Map group names to their actual PAYG API keys
API_KEYS = {
    "key1": {"name": "Group 1", "key": os.environ.get("ZENMUX_KEY_1")},
    "key2": {"name": "Group 2", "key": os.environ.get("ZENMUX_KEY_2")},
    "key3": {"name": "Group 3", "key": os.environ.get("ZENMUX_KEY_3")},
    "key4": {"name": "Group 4", "key": os.environ.get("ZENMUX_KEY_4")},
}

def get_balance():
    resp = requests.get(
        "https://zenmux.ai/api/v1/management/payg/balance",
        headers={"Authorization": f"Bearer {ZENMUX_MANAGEMENT_API_KEY}"},
    )
    resp.raise_for_status()
    return resp.json()["data"]

def get_key_usage(api_key: str, days: int = 30):
    """Fetch logs for a specific API key and sum up the cost."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    page = 1

    while True:
        resp = requests.get(
            "https://zenmux.ai/api/v1/management/logs",
            headers={"Authorization": f"Bearer {ZENMUX_MANAGEMENT_API_KEY}"},
            params={
                "api_key": api_key,
                "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_time": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "page": page,
                "page_size": 100,
            }
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("data", {}).get("items", [])
        if not items:
            break

        for item in items:
            total_cost += item.get("cost", 0) or 0
            total_input_tokens += item.get("input_tokens", 0) or 0
            total_output_tokens += item.get("output_tokens", 0) or 0

        # Stop if we've reached the last page
        total_pages = data.get("data", {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return {
        "cost": total_cost,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
    }

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 *ZenMux Balance Bot*\n\nCommands:\n"
        "/balance — check total account balance\n"
        "/usage — check spending per group\n"
        "/usage\\_all — check spending for all groups",
        parse_mode="Markdown"
    )

async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        data = get_balance()
        msg = (
            "💳 *ZenMux PAYG Balance*\n\n"
            f"• Total credits: `${data['total_credits']:.2f}`\n"
            f"• Top-up credits: `${data['top_up_credits']:.2f}`\n"
            f"• Bonus credits: `${data['bonus_credits']:.2f}`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def usage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(info["name"], callback_data=key_id)]
        for key_id, info in API_KEYS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a group to check spending (last 30 days):",
        reply_markup=reply_markup
    )

async def usage_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching usage for all groups...")
    msg = "📊 *Spending — All Groups (last 30 days)*\n\n"
    grand_total = 0.0

    for key_id, info in API_KEYS.items():
        if not info["key"]:
            msg += f"*{info['name']}*: ❌ Not configured\n\n"
            continue
        try:
            data = get_key_usage(info["key"])
            grand_total += data["cost"]
            msg += (
                f"*{info['name']}*\n"
                f"• Cost: `${data['cost']:.4f}`\n"
                f"• Input tokens: `{data['input_tokens']:,}`\n"
                f"• Output tokens: `{data['output_tokens']:,}`\n\n"
            )
        except Exception as e:
            msg += f"*{info['name']}*: ❌ Error: {e}\n\n"

    msg += f"💰 *Grand Total: `${grand_total:.4f}`*"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key_id = query.data
    selected = API_KEYS.get(key_id)

    if not selected or not selected["key"]:
        await query.edit_message_text(f"❌ API key not configured for {key_id}")
        return

    await query.edit_message_text(f"⏳ Fetching usage for {selected['name']}...")

    try:
        data = get_key_usage(selected["key"])
        msg = (
            f"📊 *{selected['name']} — Last 30 Days*\n\n"
            f"• Cost: `${data['cost']:.4f}`\n"
            f"• Input tokens: `{data['input_tokens']:,}`\n"
            f"• Output tokens: `{data['output_tokens']:,}`"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {e}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("usage", usage))
app.add_handler(CommandHandler("usage_all", usage_all))
app.add_handler(CallbackQueryHandler(button_handler))

print("Bot running...")
app.run_polling()