import uuid
import time
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

async def progress(current, total, message, start_time, last_edit_time):
    percentage = current * 100 / total
    bar_length = 20  # Length of the progress bar
    dots = int(bar_length * (current / total))
    bar = '●' * dots + '○' * (bar_length - dots)
    
    # Calculate the download speed in MB/s
    elapsed_time = time.time() - start_time
    speed = (current / 1024 / 1024) / elapsed_time  # MB per second

    # Only edit the message if at least 3 seconds have passed since the last edit
    if time.time() - last_edit_time[0] >= 3:
        progress_message = (
            f"[{bar}] {percentage:.1f}%\n"
            f"Speed: {speed:.2f} MB/s"
        )
        
        # Edit the message with the new progress and speed
        await message.edit_text(progress_message)
        
        # Update the last edit time
        last_edit_time[0] = time.time()

    
@app.on_message((filters.document | filters.video))
async def pyro_task(client, message):
    custom_thumb = f"downloads/photo.jpg"
    # Send an initial message to display the progress
    progress_msg = await message.reply_text("Starting download...")

    # Record the start time and initialize the last edit time
    start_time = time.time()
    last_edit_time = [start_time]  # Store as list to pass by reference   

    logger.info(f"Downloading {message.caption}...")
    # Download the media and update the progress
    file_path = await app.download_media(message, 
                                         progress=progress, 
                                         progress_args=(progress_msg, start_time, last_edit_time)
                                         )
    duration = await get_duration(file_path)
    logger.info(f"Uploading {message.caption}...")

    await app.send_video(chat_id=message.chat.id, 
                         video=file_path, 
                         caption=f"<code>{message.caption}</code>", 
                         duration=duration, 
                         width=480, 
                         height=320, 
                         thumb=custom_thumb, 
                         progress=progress, 
                         progress_args=(progress_msg, start_time, last_edit_time))
    
    os.remove(custom_thumb) 
    # Edit the message to indicate the download is complete
    await progress_msg.delete() 
                
@app.on_message(filters.photo)
async def get_photo(client, message):
    await app.download_media(message, file_name='photo.jpg')
    await message.delete()


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
