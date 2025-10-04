
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import InviteToChannelRequest
import asyncio
import random
import os

api_id = 24063292
api_hash = '3aa5629f87c41581298ae8e84b5a2d2a'
session_name = 'InayatGaming'
source_group = 'https://t.me/stein_gc'
target_group = 'https://t.me/InayatGiveaways'
invite_link = 'https://t.me/+UInPOFQPDGU2OTk1'
min_delay = 4.0
max_delay = 10.0
pause_time = 600

sent_file = 'sent.txt'
invited_file = 'invited.txt'

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

async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print(f'Logged in as: {await client.get_me()}')

    while True:
        already_sent = load_set(sent_file)
        already_invited = load_set(invited_file)

        target_entity = await client.get_entity(target_group)
        participants = await client.get_participants(source_group)
        print(f'Total members in source group: {len(participants)}')

        for user in participants:
            uid = str(getattr(user, 'id', ''))
            if not uid or uid in already_invited or uid in already_sent or getattr(user, 'bot', False) or user.is_self:
                continue

            print(f"Processing: {uid} | {user.first_name} | @{getattr(user,'username','')}")

            invited_ok, info = await try_invite(client, target_entity, user)
            if invited_ok:
                print(f"[INVITED] {uid} ({info})")
                append_line(invited_file, uid)
                await asyncio.sleep(random.uniform(min_delay, max_delay))
                continue

            if info and info.startswith('floodwait'):
                print(f"FloodWait detected. Pausing {pause_time//60} minutes...")
                await asyncio.sleep(pause_time)
                continue
            if info == 'peerflood':
                print(f"PeerFlood detected. Pausing {pause_time//60} minutes...")
                await asyncio.sleep(pause_time)
                continue

            try:
                text = f"Hi {user.first_name or ''}! Join our group here: {invite_link}\nIf you'd rather not be messaged, sorry for the ping."
                await client.send_message(user.id, text)
                print(f"[MESSAGED] {uid}")
                append_line(sent_file, uid)
                await asyncio.sleep(random.uniform(min_delay, max_delay))
            except errors.UserPrivacyRestrictedError:
                print(f"Can't DM {uid}: privacy settings.")
            except errors.FloodWaitError as e:
                print(f"FloodWait during DM. Pausing {pause_time//60} minutes...")
                await asyncio.sleep(pause_time)
            except errors.PeerFloodError:
                print("PeerFlood detected on send. Pausing 10 minutes...")
                await asyncio.sleep(pause_time)
            except Exception as e:
                print(f"Failed to DM {uid}: {type(e).__name__} {e}")

        print("Batch finished. Restarting loop...")
        await asyncio.sleep(30)

if __name__ == '__main__':
    asyncio.run(main())
