import time
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

    # Download the media and update the progress
    file_path = await app.download_media(
        message, 
        progress=progress,
        progress_args=(progress_msg, start_time, last_edit_time)  # Pass the message object, start time, and last edit time to the progress function
    )
    duration = await get_duration(file_path)
    await app.send_video(chat_id=message.chat.id, 
                                        video=file_path, 
                                        caption=f"<code>{message.caption}</code>", 
                                        duration=duration, 
                                        width=480, 
                                        height=320, 
                                        thumb=custom_thumb, 
                                        progress=progress, 
                                        progress_args=(progress_msg, start_time, last_edit_time))
    # Edit the message to indicate the download is complete
    await progress_msg.edit_text("Download complete!")

@app.on_message(filters.photo)
async def get_photo(client, message):
    await app.download_media(message, file_name='photo.jpg')
    await message.delete()

app.run()
