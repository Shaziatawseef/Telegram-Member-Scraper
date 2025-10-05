from telethon import TelegramClient, errors
from telethon.tl.functions.channels import InviteToChannelRequest
import asyncio
import random
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Telegram Bot Token
BOT_TOKEN = '7713181989:AAGLUmTc_ZC_3hixTdrMiouCpokw0_L8-hk'

# Global variables to store user inputs
user_data = {}

# Files
sent_file = 'sent.txt'
invited_file = 'invited.txt'

# Delay settings
min_delay = 4.0
max_delay = 10.0
pause_time = 600

# Helper functions
def load_set(filename):
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def append_line(filename, line):
    with open(filename, 'a') as f:
        f.write(f"{line}\n")

async def try_invite(client, target_entity, user):
    try:
        await client(InviteToChannelRequest(channel=target_entity, users=[user]))
        return True, None
    except errors.UserAlreadyParticipantError:
        return True, 'already_participant'
    except errors.UserPrivacyRestrictedError:
        return False, 'privacy'
    except errors.FloodWaitError as e:
        return False, f'floodwait:{e.seconds}'
    except errors.PeerFloodError:
        return False, 'peerflood'
    except Exception as e:
        return False, f'error:{type(e).__name__}'

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Please send your API ID."
    )

async def receive_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['api_id'] = int(update.message.text)
    await update.message.reply_text("API ID received. Now send your API Hash:")

async def receive_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['api_hash'] = update.message.text
    await update.message.reply_text("API Hash received. Now send your session name:")

async def receive_session_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['session_name'] = update.message.text
    await update.message.reply_text("Session name received. Now send your source group link:")

async def receive_source_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['source_group'] = update.message.text
    await update.message.reply_text("Source group received. Now send your target group link:")

async def receive_target_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['target_group'] = update.message.text
    await update.message.reply_text("Target group received. Now send your invite link:")
    
async def receive_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['invite_link'] = update.message.text
    await update.message.reply_text("Invite link received. Starting automation...")
    asyncio.create_task(main(update))

# Main automation function
async def main(update: Update):
    api_id = user_data['api_id']
    api_hash = user_data['api_hash']
    session_name = user_data['session_name']
    source_group = user_data['source_group']
    target_group = user_data['target_group']
    invite_link = user_data['invite_link']

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    await update.message.reply_text(f'Logged in as: {await client.get_me()}')

    while True:
        already_sent = load_set(sent_file)
        already_invited = load_set(invited_file)

        target_entity = await client.get_entity(target_group)
        participants = await client.get_participants(source_group)
        await update.message.reply_text(f'Total members in source group: {len(participants)}')

        for user in participants:
            uid = str(getattr(user, 'id', ''))
            if not uid or uid in already_invited or uid in already_sent or getattr(user, 'bot', False) or user.is_self:
                continue

            await update.message.reply_text(f"Processing: {uid} | {user.first_name} | @{getattr(user,'username','')}")

            invited_ok, info = await try_invite(client, target_entity, user)
            if invited_ok:
                await update.message.reply_text(f"[INVITED] {uid} ({info})")
                append_line(invited_file, uid)
                await asyncio.sleep(random.uniform(min_delay, max_delay))
                continue

            if info and info.startswith('floodwait'):
                await update.message.reply_text(f"FloodWait detected. Pausing {pause_time//60} minutes...")
                await asyncio.sleep(pause_time)
                continue
            if info == 'peerflood':
                await update.message.reply_text(f"PeerFlood detected. Pausing {pause_time//60} minutes...")
                await asyncio.sleep(pause_time)
                continue

            try:
                text = f"Hi {user.first_name or ''}! Join our group here: {invite_link}\nIf you'd rather not be messaged, sorry for the ping."
                await client.send_message(user.id, text)
                await update.message.reply_text(f"[MESSAGED] {uid}")
                append_line(sent_file, uid)
                await asyncio.sleep(random.uniform(min_delay, max_delay))
            except errors.UserPrivacyRestrictedError:
                await update.message.reply_text(f"Can't DM {uid}: privacy settings.")
            except errors.FloodWaitError as e:
                await update.message.reply_text(f"FloodWait during DM. Pausing {pause_time//60} minutes...")
                await asyncio.sleep(pause_time)
            except errors.PeerFloodError:
                await update.message.reply_text("PeerFlood detected on send. Pausing 10 minutes...")
                await asyncio.sleep(pause_time)
            except Exception as e:
                await update.message.reply_text(f"Failed to DM {uid}: {type(e).__name__} {e}")

        await update.message.reply_text("Batch finished. Restarting loop...")
        await asyncio.sleep(30)

# Telegram bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_id))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_hash))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_session_name))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_source_group))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_group))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invite_link))

if __name__ == "__main__":
    app.run_polling()
