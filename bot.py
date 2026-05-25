import os
import sys
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ZENMUX_MANAGEMENT_API_KEY = os.environ.get("ZENMUX_MANAGEMENT_API_KEY")

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN is not set")
    sys.exit(1)

if not ZENMUX_MANAGEMENT_API_KEY:
    print("ERROR: ZENMUX_MANAGEMENT_API_KEY is not set")
    sys.exit(1)
    
def get_balance():
    resp = requests.get(
        "https://zenmux.ai/api/v1/management/payg/balance",
        headers={"Authorization": f"Bearer {ZENMUX_MGMT_KEY}"},
    )
    resp.raise_for_status()
    return resp.json()["data"]

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 *ZenMux Balance Bot*\n\nCommands:\n/balance — check your PAYG credits",
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

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))

print("Bot running...")
app.run_polling()
