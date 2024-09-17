import re
import aiohttp
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
        
'''
async def download_initial_part(client, media, file_path, chunk_size):
    # Open the file for writing in binary mode
    with open(file_path, 'wb') as f:
        async for chunk in client.stream_media(media):
            f.write(chunk)
            if f.tell() >= chunk_size:
                break
'''

async def extract_movie_info(caption):
    try:
        regex = re.compile(r'(.+?)(\d{4})')
        match = regex.search(caption)

        if match:
            # Replace '.' and remove '(' and ')' from movie_name
            movie_name = match.group(1).replace('.', ' ').replace('(', '').replace(')', '').strip()
            release_year = match.group(2)
            return movie_name, release_year
    except Exception as e:
        print(e)
    return None, None


async def generate_duration(file_path: str) -> str:
    try:

        # Use ffprobe to get video duration
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        duration = float(subprocess.check_output(duration_cmd).strip())

        return duration
    except Exception as e:
        logger.error(f"Error generating duration: {e}")
        return None
    
async def get_movie_poster(movie_name, release_year):
    tmdb_search_url = f'https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={movie_name}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tmdb_search_url) as search_response:
                search_data = await search_response.json()

                if search_data['results']:
                    # Filter results based on release year and first air date
                    matching_results = [
                        result for result in search_data['results']
                        if ('release_date' in result and result['release_date'][:4] == str(release_year)) or
                        ('first_air_date' in result and result['first_air_date'][:4] == str(release_year))
                    ]

                    if matching_results:
                        result = matching_results[0]

                        # Fetch additional details using movie ID
                        movie_id = result['id']
                        media_type = result['media_type']

                        tmdb_movie_image_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}/images?api_key={TMDB_API_KEY}&language=en-US&include_image_language=en,hi'

                        async with session.get(tmdb_movie_image_url) as movie_response:
                            movie_images = await movie_response.json()
 
                        # Use the backdrop_path or poster_path
                            poster_path = None
                            if 'backdrops' in movie_images and movie_images['backdrops']:
                                poster_path = movie_images['backdrops'][0]['file_path']
                                                         
                            elif 'posters' in movie_images and movie_images['posters']:
                                poster_path = movie_images['posters'][0]['file_path']

                            poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
                                   
                            return poster_url
    except Exception as e:               
        logger.error(f"Error fetching TMDB data: {e}")

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
