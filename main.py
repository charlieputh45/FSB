import os
import time
from pyromod import listen
from pyrogram import Client, filters, enums
from config import *
from utils import *


app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=enums.ParseMode.HTML,
    in_memory=True
)

async def progress(current, total, message, last_edit_time, last_data):
    percentage = current * 100 / total
    bar_length = 20  # Length of the progress bar
    dots = int(bar_length * (current / total))
    bar = '●' * dots + '○' * (bar_length - dots)
    
    # Calculate the download speed in MB/s since last update
    elapsed_time = time.time() - last_edit_time[0]
    speed = ((current - last_data[0]) / 1024 / 1024) / elapsed_time  # MB per second

    # Only edit the message if at least 3 seconds have passed since the last edit
    if elapsed_time >= 3:
        progress_message = (
            f"[{bar}] {percentage:.1f}%\n"
            f"Speed: {speed:.2f} MB/s"
        )
        
        # Edit the message with the new progress and speed
        await message.edit_text(progress_message)
        
        # Update the last edit time and data transferred
        last_edit_time[0] = time.time()
        last_data[0] = current

@app.on_message((filters.document | filters.video))
async def pyro_task(client, message):
    start_time = time.time()
    last_edit_time = [start_time]  # Store as list to pass by reference
    last_data = [0]  # Track the last amount of data transferred
    caption = message.caption
    
    rply = await message.reply_text("Please send a photo")
    # Listen for a photo message
    photo_msg = await app.listen(message.chat.id, filters=filters.photo)

    thumb_path = await app.download_media(photo_msg, file_name='photo_{message.id}.jpg')
    await photo_msg.delete()
    
    # Send an initial message to display the progress
    progress_msg = await rply.edit_text("Starting download...")
    try:
        # Download the media and update the progress
        file_path = await app.download_media(message, file_name=f"{caption}", 
                                             progress=progress, progress_args=(progress_msg, last_edit_time, last_data))
        
        duration = await get_duration(file_path)
        
        # Check if the custom thumbnail exists
        if not os.path.exists(thumb_path):
            await message.reply_text("Please set a custom thumbnail first.")
            return
            
        await app.send_video(chat_id=message.chat.id, 
                                            video=file_path, 
                                            caption=f"<code>{message.caption}</code>", 
                                            duration=duration, 
                                            width=480, 
                                            height=320, 
                                            thumb=thumb_path, 
                                            progress=progress, 
                                            progress_args=(progress_msg, last_edit_time, last_data))
        await progress_msg.edit_text("Upload complete!")
    except Exception as e:
        logger.error(f'{e}')
    finally:
        os.remove(file_path)
        os.remove(thumb_path)

app.run()
