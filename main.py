import uuid
from utils import *
from config import *
from time import time as tm
from pyrogram import idle
from pyromod import listen
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums
from shorterner import *
from asyncio import get_event_loop
from pymongo import MongoClient
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DOWNLOAD_PATH = "downloads/"
CHUNK_SIZE = 1024 * 1024 * 200
loop = get_event_loop()
THUMBNAIL_COUNT = 6
GRID_COLUMNS = 2  # Number of columns in the grid

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

MONGO_COLLECTION = "users"
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client[MONGO_DB_NAME]
mongo_collection = mongo_db[MONGO_COLLECTION]

user_data = {}
TOKEN_TIMEOUT = 7200

app = Client(
    "my_bot",
      api_id=API_ID,
      api_hash=API_HASH, 
      bot_token=BOT_TOKEN, 
      workers=1000, 
      parse_mode=enums.ParseMode.HTML,
      in_memory=True)

user = Client(
                "userbot",
                api_id=int(API_ID),
                api_hash=API_HASH,
                session_string=STRING_SESSION,
                no_updates = True
            )


async def main():
    async with app, user:
        await idle() 

with app:
    bot_username = (app.get_me()).username
    
# Send Single Command 
@app.on_message(filters.command("send") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        await message.reply_text("send post link")
        tg_link = (await app.listen(message.chat.id)).text

        msg_id = await extract_tg_link(tg_link)

        file_message = await app.get_messages(DB_CHANNEL_ID, int(msg_id))

        media = file_message.document or file_message.video or file_message.audio
        file_id = file_message.id

        if media:
            caption = file_message.caption if file_message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)

                # Generate file path
                logger.info(f"Downloading {file_id}...")

                file_path = await app.download_media(media.file_id)

                # Generate a thumbnail
                thumbnail_path = await generate_thumbnail(file_path)

                file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{file_id}</code>"

                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, has_spoiler=True)

                os.remove(thumbnail_path)
                os.remove(file_path)

                await asyncio.sleep(3)
            
        await message.reply_text("Messages send successfully!")
    except Exception as e:
        logger.error(f"{e}")

# Send Multiple Command
@app.on_message(filters.command("sendm") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        await message.reply_text("send post start link")
        start_msg = (await app.listen(message.chat.id)).text

        await message.reply_text("send post end link")
        end_msg = (await app.listen(message.chat.id)).text

        start_msg_id = int(await extract_tg_link(start_msg))
        end_msg_id = int(await extract_tg_link(end_msg))

        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            file_messages = await app.get_messages(DB_CHANNEL_ID, range(start, end + 1))

            for file_message in file_messages:

                media = file_message.document or file_message.video or file_message.audio

                if media:
                    file_id = file_message.id
                    caption = file_message.caption if file_message.caption else None

                    if caption:
                        new_caption = await remove_unwanted(caption)

                        # Generate file path
                        logger.info(f"Downloading {file_id}...")

                        file_path = await app.download_media(media.file_id)
                        # Generate a thumbnail
                        thumbnail_path = await generate_thumbnail(file_path)

                        file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{file_id}</code>"

                        await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, has_spoiler=True)

                        os.remove(thumbnail_path)
                        os.remove(file_path)

                        await asyncio.sleep(3)

        await message.reply_text("Messages send successfully!")

    except FloodWait as e:
        await asyncio.sleep(e.value)

    except Exception as e:
        logger.error(f'{e}')

@app.on_message(filters.command("download") & filters.user(OWNER_USERNAME))
async def download(client, message):
    
    await message.reply_text("send post start link")
    start_msg = (await app.listen(message.chat.id)).text

    await message.reply_text("send post end link")
    end_msg = (await app.listen(message.chat.id)).text

    channel_id = int(await extract_channel_id(start_msg))

    start_msg_id = int(await extract_tg_link(start_msg))
    end_msg_id = int(await extract_tg_link(end_msg))

    batch_size = 199
    for start in range(start_msg_id, end_msg_id + 1, batch_size):
        end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
        file_messages = await app.get_messages(channel_id, range(start, end + 1))

        for file_message in file_messages:
            media = file_message.document or file_message.video
            file_id = file_message.id
            file_name = file_message.caption
            if media:
                logger.info(f"Downloading {file_id}...")
                file_path = await app.download_media(media.file_id, progress=progress_callback, progress=progress)
                logger.info(f"Generating Thumbnail {file_id}...")
                thumbnail_path = await generate_thumbnail(file_path)
                logger.info(f"Uploading {file_id}...")
                upload = await app.send_video(DB_CHANNEL_ID, video=file_path, caption=file_name, thumb=thumbnail_path, progress=progress)
                new_caption = await remove_unwanted(caption)
                file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{upload.id}</code>"
                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, has_spoiler=True)
                os.remove(thumbnail_path)     
                os.remove(file_path) 
    await message.reply_text("Messages send successfully!")
    
async def progress(current, total):
    logger.info(f"{current * 100 / total:.1f}%")
                
# Delete Commmand
@app.on_message(filters.command("delete") & filters.user(OWNER_USERNAME))
async def get_command(client, message):
    try:
        await message.reply_text("Enter channel_id")
        channel_id = int((await app.listen(message.chat.id)).text)

        await message.reply_text("Enter count")
        limit = int((await app.listen(message.chat.id)).text)

        await app.send_message(channel_id, "Hi")

        try:
            async for message in user.get_chat_history(channel_id, limit):
                await message.delete()
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
        await user.send_message(channel_id, "done")
    except Exception as e:
        logger.error(f"Error : {e}")
      
if __name__ == "__main__":
    loop.run_until_complete(main())
