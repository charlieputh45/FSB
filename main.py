import os 
import sys
import time
from utils import *
from config import *
from html import escape
from pyrogram import idle
from pyromod import listen
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asyncio import get_event_loop

DOWNLOAD_PATH = "downloads/"
loop = get_event_loop()
THUMBNAIL_COUNT = 9
GRID_COLUMNS = 3 # Number of columns in the grid

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

user_data = {}
TOKEN_TIMEOUT = 7200

app = Client(
    "my_bot",
      api_id=API_ID,
      api_hash=API_HASH, 
      bot_token=BOT_TOKEN, 
      workers=1000, 
      parse_mode=enums.ParseMode.HTML)

async def main():
    async with app:
        await idle()

with app:
    bot_username = (app.get_me()).username

# Initialize global variables to track time and data
start_time = None
previous_time = None
previous_bytes = 0
total_bytes = 0

async def progress(current, total):
    global start_time, previous_time, previous_bytes, total_bytes

    # Initialize timers and bytes on the first call
    if start_time is None:
        start_time = time.time()
        previous_time = start_time

    # Calculate percentage
    percentage = current * 100 / total

    # Update total bytes downloaded
    total_bytes = current

    # Get current time
    current_time = time.time()

    # Calculate elapsed time
    elapsed_time = current_time - start_time

    # Calculate speed
    if elapsed_time > 0:
        speed = (current - previous_bytes) / (current_time - previous_time)  # bytes per second
        previous_time = current_time
        previous_bytes = current

        # Convert speed to MB/s
        speed_mbps = speed / (1024 * 1024)  # Convert to MB/s

        # Update progress in the same line
        sys.stdout.write(f"\rProgress: {percentage:.1f}% | Speed: {speed_mbps:.2f} MB/s")
    else:
        # Update percentage only initially
        sys.stdout.write(f"\rProgress: {percentage:.1f}%")
    
    sys.stdout.flush()  # Ensure the output is written immediately

    # Return None, so the download can continue
    return None

async def finish_download():
    global start_time, total_bytes

    # Calculate average speed after the download is complete
    elapsed_time = time.time() - start_time  # Total elapsed time
    if elapsed_time > 0:
        average_speed_mbps = total_bytes / elapsed_time / (1024 * 1024)  # Convert to MB/s
        print(f"\nDownload completed! Average Speed: {average_speed_mbps:.2f} MB/s")
    else:
        print("\nDownload completed! Unable to calculate average speed.")

# Reset variables when starting a new download
def reset_progress():
    global start_time, previous_time, previous_bytes
    start_time = None
    previous_time = None
    previous_bytes = 0

@app.on_message(filters.private & (filters.document | filters.video) & filters.user(OWNER_USERNAME))
async def forward_message_to_new_channel(client, message):
    try:
        media = message.document or message.video
        file_id = message.id
        file_size = media.file_size


        if media:
            caption = message.caption if message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)
                file_info = f"🗂️ <b>{escape(new_caption)}</b>\n\n💾 <b>{humanbytes(file_size)}</b>"

                # Generate file path
                logger.info(f"Downloading initial part of {file_id}...")
                
                dwnld_msg = await message.reply_text("📥 Downloading")
                start_time = time.time()  # Initialize start time
                previous_time = start_time
                previous_bytes = 0
                
                file_path = await app.download_media(message, file_name=f"{message.id}", progress=progress)
                                    
                print("Generating Thumbnail")
                # Generate a thumbnail
                thumbnail_path, duration = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

                if thumbnail_path:
                    print(f"Thumbnail generated: {thumbnail_path}")
                else:
                    print("Failed to generate thumbnail")   


                upld_msg = await dwnld_msg.edit_text("⏫ Uploading")
                send_msg = await app.send_video(DB_CHANNEL_ID, 
                                                video=file_path, 
                                                caption=f"<code>{escape(caption)}</code>",
                                                duration=duration, 
                                                width=480, 
                                                height=320, 
                                                thumb=thumbnail_path
                                               )
                
                await upld_msg.edit_text("Uploaded ✅")

                file_link  = f"https://thetgflix.sshemw.workers.dev/bot2/{send_msg.id}"
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])
                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, reply_markup=keyboard)

                os.remove(thumbnail_path)
                os.remove(file_path)

                await asyncio.sleep(3)

    except Exception as e:
        logger.error(f'{e}') 
        file_link  = f"https://thetgflix.sshemw.workers.dev/bot2/{send_msg.id}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])

        await app.send_photo(CAPTION_CHANNEL_ID, photo='photo.jpg', caption=file_info, reply_markup=keyboard)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        
        
@app.on_message(filters.command("start"))
async def get_command(client, message):
    reply = await message.reply_text(f"<b>💐Welcome this is TG⚡️Flix Bot")
    await auto_delete_message(message, reply)

# Send Multiple Command
@app.on_message(filters.command("send") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await link_msg.delete()
            await rply.delete()
            return link_msg.text
            
        start_msg_id = int(await extract_tg_link(await get_user_input("Send first post link")))
        end_msg_id = int(await extract_tg_link(await get_user_input("Send end post link")))
        
        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            file_messages = await app.get_messages(DB_CHANNEL_ID, range(start, end + 1))

            for file_message in file_messages:

                media = file_message.document or file_message.video or file_message.audio

                if media:
                    try:
                        file_id = file_message.id
                        caption = file_message.caption if file_message.caption else None
                        file_size = media.file_size

                        if caption:
                            new_caption = await remove_unwanted(caption)
                            file_info = f"🗂️ <b>{escape(new_caption)}</b>\n\n💾 <b>{humanbytes(file_size)}</b>"

                            # Generate file path
                            logger.info(f"Downloading {file_id} to {end_msg_id}")
                            reset_progress()
                            file_path = await app.download_media(file_message, file_name=f"{file_message.id}", progress=progress)
                            await finish_download()
                                                                                  
                            # Generate a thumbnail
                            thumbnail_path, duration = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

                            if thumbnail_path:
                                print(f"Thumbnail generated: {thumbnail_path}")
                            else:
                                print("Failed to generate thumbnail")
    
                            file_link  = f"https://thetgflix.sshemw.workers.dev/bot2/{file_message.id}"
                            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])
                            await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, reply_markup=keyboard)
        
                            os.remove(thumbnail_path)
                            os.remove(file_path)
    
                            await asyncio.sleep(3)
                            
                    except Exception as e:
                        file_link  = f"https://thetgflix.sshemw.workers.dev/bot2/{file_message.id}"
                        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])

                        await app.send_photo(CAPTION_CHANNEL_ID, photo='photo.jpg', caption=file_info, reply_markup=keyboard)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        if os.path.exists(thumbnail_path):
                            os.remove(thumbnail_path)
            
        await message.reply_text("Messages send successfully ✅")

    except FloodWait as e:
        await asyncio.sleep(e.value)

    except Exception as e:
        logger.error(f'{e}')

@app.on_message(filters.command("copy") & filters.user(OWNER_USERNAME))
async def copy_msg(client, message):    
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await link_msg.delete()
            await rply.delete()
            return link_msg.text
        
        # Collect input from the user
        start_msg_id = int(await extract_tg_link(await get_user_input("Send first post link")))
        end_msg_id = int(await extract_tg_link(await get_user_input("Send end post link")))
        db_channel_id = int(await extract_channel_id(await get_user_input("Send db_channel link")))
        destination_id = int(await extract_channel_id(await get_user_input("Send destination channel link")))

        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            # Get and copy messages
            file_messages = await app.get_messages(db_channel_id, range(start, end + 1))

            for file_message in file_messages:
                if file_message and (file_message.video):
                    caption = file_message.caption.html if file_message.caption else None
                    await file_message.copy(destination_id, caption=caption)
                    await asyncio.sleep(3)
                    
        await message.reply_text("Messages copied successfully!✅")
        
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f'{e}')

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

# Get Log Command
@app.on_message(filters.command("log") & filters.user(OWNER_USERNAME))
async def log_command(client, message):
    user_id = message.from_user.id

    # Send the log file
    try:
        reply = await app.send_document(user_id, document=LOG_FILE_NAME, caption="Bot Log File")
        await auto_delete_message(message, reply)
    except Exception as e:
        await app.send_message(user_id, f"Failed to send log file. Error: {str(e)}")
    
      
if __name__ == "__main__":
    logger.info("Bot is starting...")
    loop.run_until_complete(main())
    logger.info("Bot has stopped.")
