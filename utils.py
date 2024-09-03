import io
import re
import random
import subprocess
import asyncio
import aiohttp
from config import *
from pyrogram.types import User

async def auto_delete_message(user_message, bot_message):
    try:
        await user_message.delete()
        await asyncio.sleep(60)
        await bot_message.delete()
    except Exception as e:
        logger.error(f"{e}")
        
def get_readable_time(seconds: int) -> str:
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f" {minutes}m"
    seconds = int(seconds)
    result += f" {seconds}s"
    return result
    
async def remove_unwanted(caption):
    try:
        # Remove .mkv and .mp4 extensions if present
        cleaned_caption = re.sub(r'\.mkv|\.mp4|\.webm', '', caption)
        return cleaned_caption
    except Exception as e:
        logger.error(e)
        return None

def humanbytes(size):
    # Function to format file size in a human-readable format
    if not size:
        return "0 B"
    # Define byte sizes
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size >= 1024 and i < len(suffixes) - 1:
        size /= 1024
        i += 1
    f = ('%.2f' % size).rstrip('0').rstrip('.')
    return f"{f} {suffixes[i]}"

  
async def extract_tg_link(telegram_link):
    try:
        pattern = re.compile(r'https://t\.me/c/(-?\d+)/(\d+)')
        match = pattern.match(telegram_link)
        if match:
            message_id = match.group(2)
            return message_id
        else:
            return None, None
    except Exception as e:
        logger.error(e)

async def extract_channel_id(telegram_link):
    try:
        pattern = re.compile(r'https://t\.me/c/(-?\d+)/(\d+)')
        match = pattern.match(telegram_link)
        if match:
            channel_id = match.group(1)
            formatted_channel_id = f'-100{channel_id}'
            return formatted_channel_id
        else:
            return None
    except Exception as e:
        logger.error(e)
        
'''
async def download_initial_part(client, media, file_path, chunk_size):
    # Open the file for writing in binary mode
    with open(file_path, 'wb') as f:
        async for chunk in client.stream_media(media):
            f.write(chunk)
            if f.tell() >= chunk_size:
                break
'''

'''
async def get_duration(file_path: str) -> str:
    try:
        # Use ffprobe to get video duration
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        duration = float(subprocess.check_output(duration_cmd).strip())
        
        #random_interval = random.uniform(0, duration)

        # Adjust the duration to account for a 2% reduction
        #adjusted_duration = duration - (duration * 2 / 100)

        # Ensure at least some duration to work with
        #if adjusted_duration <= 0:
            #adjusted_duration = 3

        # Choose the midpoint of the adjusted duration for the thumbnail
        #midpoint = adjusted_duration / 2


        # Create a thumbnail at the random interval
        #thumbnail_path = f"{file_path}_thumb.jpg"
        #thumbnail_cmd = [
           # 'ffmpeg', '-ss', str(random_interval), '-i', file_path, 
           # '-frames:v', '1', thumbnail_path, '-y'
        #]
        #subprocess.run(thumbnail_cmd, capture_output=True, check=True)

        return duration
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None        
    
'''

'''
def generate_thumbnail(file_path: str) -> str:
    try:
        # Output thumbnail path
        thumbnail_path = f"{file_path}.jpg"

        # Use ffmpeg to generate a thumbnail
        (
            zender
            .input(file_path, ss='00:00:01')  # Seek to 1 second
            .output(thumbnail_path, vframes=1)
            .run(capture_stdout=True, capture_stderr=True)
        )
        return thumbnail_path
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None
'''

async def get_user_link(user: User) -> str:
    user_id = user.id
    first_name = user.first_name
    return f'<a href=tg://user?id={user_id}>{first_name}</a>'
