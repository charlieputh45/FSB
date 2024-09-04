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

# Dictionary to store the has_spoiler setting for each task
task_settings = {}

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

@app.on_message(filters.private & filters.command("setting"))
async def setting_handler(client, message):
    await message.reply_text(
        "Select the spoiler setting:",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [types.InlineKeyboardButton("True", callback_data=f"set_spoiler_true_{message.id}")],
                [types.InlineKeyboardButton("False", callback_data=f"set_spoiler_false_{message.id}")]
            ]
        )
    )

@app.on_callback_query(filters.regex(r"set_spoiler_(true|false)_\d+"))
async def spoiler_callback(client, callback_query):
    task_id = int(callback_query.data.split("_")[-1])
    task_settings[task_id] = callback_query.data == "set_spoiler_true"
    await callback_query.message.edit_text(
        f"Spoiler setting updated to: {task_settings[task_id]}"
    )
    await callback_query.answer(f"Set to {task_settings[task_id]}")

@app.on_message(filters.private & (filters.document | filters.video | filters.photo))
async def pyro_task(client, message):
    task_id = message.id
    task_settings[task_id] = False  # Default to False

    start_time = time.time()
    last_edit_time = [start_time]
    last_data = [0]
    caption = message.caption
    
    await asyncio.sleep(3)
    rply = await message.reply_text("Please send a photo")
    photo_msg = await app.listen(message.chat.id, filters=filters.photo)
    
    await asyncio.sleep(3)
    thumb_path = await app.download_media(photo_msg, file_name=f'photo_{task_id}.jpg')
    await photo_msg.delete()
    
    await asyncio.sleep(3)
    progress_msg = await rply.edit_text("Starting download...")
    
    try:
        await asyncio.sleep(3)
        file_path = await app.download_media(message, file_name=f"{caption}", 
                                             progress=progress, progress_args=(progress_msg, last_edit_time, last_data, "Downloading"))
        
        duration = await get_duration(file_path)
        
        if not os.path.exists(thumb_path):
            await asyncio.sleep(3)
            await message.reply_text("Please set a custom thumbnail first.")
            return
            
        await asyncio.sleep(3)
        send_msg = await app.send_video(DB_CHANNEL_ID, 
                                        video=file_path, 
                                        caption=f"<code>{message.caption}</code>",
                                        has_spoiler=task_settings[task_id],  # Use the task-specific spoiler setting
                                        duration=duration, 
                                        width=480, 
                                        height=320, 
                                        thumb=thumb_path, 
                                        progress=progress, 
                                        progress_args=(progress_msg, last_edit_time, last_data, "Uploading"))
        await asyncio.sleep(3)
        await progress_msg.edit_text("Uploaded ✅")

        new_caption = await remove_unwanted(caption)
        file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{send_msg.id}</code>"
        await asyncio.sleep(3)
        await app.send_photo(CAPTION_CHANNEL_ID, thumb_path, caption=file_info, has_spoiler=task_settings[task_id])
        
    except Exception as e:
        logger.error(f'{e}')
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

app.run()
