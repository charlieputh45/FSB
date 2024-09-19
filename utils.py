import re
import random
import subprocess
import asyncio
from PIL import Image
from config import *

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
        

async def download_initial_part(client, media, file_path, chunk_size):
    # Open the file for writing in binary mode
    with open(file_path, 'wb') as f:
        async for chunk in client.stream_media(media):
            f.write(chunk)
            if f.tell() >= chunk_size:
                break


async def handle_partial_download_and_thumbnail(client, media, file_path, chunk_size, num_thumbnails, grid_columns):
    # Step 1: Download the initial part of the file
    await download_initial_part(client, media, file_path, chunk_size)

    # Step 2: Estimate the duration of the downloaded portion (optional)
    try:
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        duration = float(subprocess.check_output(duration_cmd).strip())
    except Exception as e:
        print(f"Error estimating duration: {e}")
        # If ffprobe fails, assume a default duration
        duration = 30.0  # Adjust based on your requirements

    # Step 3: Generate the combined thumbnail
    thumbnail_path = await generate_partial_thumbnail(file_path, num_thumbnails, grid_columns, duration)

    return thumbnail_path

async def generate_partial_thumbnail(file_path: str, num_thumbnails: int, grid_columns: int, max_duration: float) -> str:
    try:
        # List to store individual thumbnails
        thumbnails = []

        # Set the duration to the max_duration of the partial file
        duration = max_duration

        # Generate random intervals within the available duration
        intervals = [random.uniform(0, duration) for _ in range(num_thumbnails)]

        # Create thumbnails at specified intervals
        for i, interval in enumerate(intervals):
            thumbnail_path = f"{file_path}_thumb_{i}.jpg"
            thumbnail_cmd = [
                'ffmpeg', '-ss', str(interval), '-i', file_path, 
                '-frames:v', '1', thumbnail_path, '-y'
            ]
            result = subprocess.run(thumbnail_cmd, capture_output=True)
            if result.returncode == 0:
                thumbnails.append(thumbnail_path)
            else:
                print(f"Failed to generate thumbnail at interval {interval}. Skipping.")

        # Open all successfully generated thumbnails and combine them into a grid
        if thumbnails:
            images = [Image.open(thumb) for thumb in thumbnails]
            widths, heights = zip(*(img.size for img in images))

            max_width = max(widths)
            max_height = max(heights)

            # Calculate grid dimensions
            grid_rows = (len(images) + grid_columns - 1) // grid_columns
            grid_width = grid_columns * max_width
            grid_height = grid_rows * max_height

            combined_image = Image.new('RGB', (grid_width, grid_height))

            for index, img in enumerate(images):
                x = (index % grid_columns) * max_width
                y = (index // grid_columns) * max_height
                combined_image.paste(img, (x, y))

            combined_thumbnail_path = f"{file_path}_combined.jpg"
            combined_image.save(combined_thumbnail_path)

            # Clean up individual thumbnails
            for thumb in thumbnails:
                os.remove(thumb)

            return combined_thumbnail_path
        else:
            print("No thumbnails generated.")
            return None

    except Exception as e:
        print(f"Error generating combined thumbnail: {e}")
        return None


async def generate_combined_thumbnail(file_path: str, num_thumbnails: int, grid_columns: int) -> str:
    try:
        # List to store individual thumbnails
        thumbnails = []

        # Use ffprobe to get video duration
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        duration = float(subprocess.check_output(duration_cmd).strip())

        # Generate random intervals
        intervals = [random.uniform(0, duration) for _ in range(num_thumbnails)]

        # Create thumbnails at specified intervals
        for i, interval in enumerate(intervals):
            thumbnail_path = f"{file_path}_thumb_{i}.jpg"
            thumbnail_cmd = [
                'ffmpeg', '-ss', str(interval), '-i', file_path, 
                '-frames:v', '1', thumbnail_path, '-y'
            ]
            subprocess.run(thumbnail_cmd, capture_output=True, check=True)
            thumbnails.append(thumbnail_path)

        # Open all thumbnails and combine them into a grid
        images = [Image.open(thumb) for thumb in thumbnails]
        widths, heights = zip(*(img.size for img in images))

        max_width = max(widths)
        max_height = max(heights)

        # Calculate grid dimensions
        grid_rows = (len(images) + grid_columns - 1) // grid_columns
        grid_width = grid_columns * max_width
        grid_height = grid_rows * max_height

        combined_image = Image.new('RGB', (grid_width, grid_height))

        for index, img in enumerate(images):
            x = (index % grid_columns) * max_width
            y = (index // grid_columns) * max_height
            combined_image.paste(img, (x, y))

        combined_thumbnail_path = f"{file_path}_combined.jpg"
        combined_image.save(combined_thumbnail_path)

        # Clean up individual thumbnails
        for thumb in thumbnails:
            os.remove(thumb)

        return combined_thumbnail_path, duration
    except Exception as e:
        print(f"Error generating combined thumbnail: {e}")
        return None
    

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
