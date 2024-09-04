import os
import time
import asyncio
from pyromod import listen
from pyrogram import Client, filters, enums, types
from config import *
from utils import *
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=enums.ParseMode.HTML,
    in_memory=True
)

# Dictionary to store the has_spoiler value per task/message ID
spoiler_settings = {}

async def progress(current, total, message, last_edit_time, last_data, status):
    percentage = current * 100 / total
    bar_length = 20  # Length of the progress bar
    dots = int(bar_length * (current / total))
    bar = '●' * dots + '○' * (bar_length - dots)
    
    elapsed_time = time.time() - last_edit_time[0]
    speed = ((current - last_data[0]) / 1024 / 1024) / elapsed_time  # MB per second

    if elapsed_time >= 3:
        progress_message = (
            f"Status: {status}\n"
            f"[{bar}] {percentage:.1f}%\n"
            f"Speed: {speed:.2f} MB/s"
        )
        await message.edit_text(progress_message)
        
        last_edit_time[0] = time.time()
        last_data[0] = current

@app.on_message(filters.private & (filters.document | filters.video | filters.photo))
async def pyro_task(client, message):
    start_time = time.time()
    last_edit_time = [start_time]  # Store as list to pass by reference
    last_data = [0]  # Track the last amount of data transferred
    caption = message.caption

    # Initialize the has_spoiler setting for this task/message
    spoiler_settings[message.id] = False

    rply = await message.reply_text(
        f"Please send a photo\nSelect the spoiler setting:",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [types.InlineKeyboardButton("True", callback_data=f"set_spoiler_true_{message.id}")],
                [types.InlineKeyboardButton("False", callback_data=f"set_spoiler_false_{message.id}")]
            ]
        )
    )
    
    photo_msg = await app.listen(message.chat.id, filters=filters.photo)
    
    thumb_path = await app.download_media(photo_msg, file_name=f'photo_{message.id}.jpg')
    await photo_msg.delete()
    
    progress_msg = await rply.edit_text("Starting download...")
    
    try:
        file_path = await app.download_media(message, file_name=f"{caption}", 
                                             progress=progress, progress_args=(progress_msg, last_edit_time, last_data, "Downloading"))
        
        duration = await get_duration(file_path)
        
        if not os.path.exists(thumb_path):
            await message.reply_text("Please set a custom thumbnail first.")
            return

        send_msg = await app.send_video(DB_CHANNEL_ID, 
                                        video=file_path, 
                                        caption=f"<code>{message.caption}</code>",
                                        has_spoiler=spoiler_settings[message.id],  # Use the stored spoiler setting
                                        duration=duration, 
                                        width=480, 
                                        height=320, 
                                        thumb=thumb_path, 
                                        progress=progress, 
                                        progress_args=(progress_msg, last_edit_time, last_data, "Uploading"))
        
        await progress_msg.edit_text("Uploaded ✅")

        new_caption = await remove_unwanted(caption)
        file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{send_msg.id}</code>"
        await app.send_photo(CAPTION_CHANNEL_ID, thumb_path, caption=file_info, has_spoiler=spoiler_settings[message.id])
        
    except Exception as e:
        logger.error(f'{e}')
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        # Clean up the spoiler setting for this message ID
        spoiler_settings.pop(message.id, None)

@app.on_callback_query(filters.regex(r"set_spoiler_(true|false)_\d+"))
async def spoiler_callback(client, callback_query):
    data_parts = callback_query.data.split('_')
    spoiler_value = data_parts[2] == "true"
    message_id = int(data_parts[3])
    
    # Update the dictionary with the new has_spoiler value for this task
    spoiler_settings[message_id] = spoiler_value
    await callback_query.answer(f"Set to {spoiler_value}")

app.run()
