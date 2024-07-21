import uuid
import asyncio
import aiohttp
from config import *
from time import time as tm
from pyshorteners import Shortener
from utils import auto_delete_message, get_readable_time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

user_data = {}
TOKEN_TIMEOUT = 7200


async def tiny(long_url):
    # Shorten URL using pyshorteners library
    try:
        s = Shortener()
        return await asyncio.to_thread(s.tinyurl.short, long_url)
    except Exception as e:
        logger.error(f'Failed to shorten URL: {long_url}, Error: {e}')
        return long_url

async def shorten_url(url):
    try:
        api_url = "{SHORTERNER_URL}"
        params = {
            "api": URLSHORTX_API_TOKEN,
            "url": url,
            "format": "text"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                if response.status == 200:
                    return (await response.text()).strip()
                else:
                    logger.error(
                        f"URL shortening failed. Status code: {response.status}, Response: {await response.text()}"
                    )
                    return url
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
        return url
    

async def verify_token(user_id, input_token):
    current_time = tm()

    # Check if the user_id exists in user_data
    if user_id not in user_data:
        return 'Token Mismatched ❌' 
    
    stored_token = user_data[user_id]['token']
    if input_token == stored_token:
        token = str(uuid.uuid4())
        user_data[user_id] = {"token": token, "time": current_time, "status": "verified"}
        return f'Token Verified ✅'
    else:
        return f'Token Mismatched ❌'
    
async def check_access(client, message, user_id):

    if user_id in user_data:
        time = user_data[user_id]['time']
        status = user_data[user_id]['status']
        expiry = time + TOKEN_TIMEOUT
        current_time = tm()
        if current_time < expiry and status == "verified":
            return True
        else:
            button = await update_token(client, user_id)
            send_message = await client.send_message(user_id,f'<b>You need to collect your token first 🎟\n(Valid: {get_readable_time(TOKEN_TIMEOUT)})</b>', reply_markup=button)
            await auto_delete_message(message, send_message)
    else:
        button = await genrate_token(user_id)
        send_message = await client.send_message(user_id,f'<b>You need to collect your token first 🎟\n(Valid: {get_readable_time(TOKEN_TIMEOUT)})</b>', reply_markup=button)
        await auto_delete_message(message, send_message)

async def update_token(client, user_id):
    try:
        time = user_data[user_id]['time']
        expiry = time + TOKEN_TIMEOUT
        if time < expiry:
            token = user_data[user_id]['token']
        else:
            token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified"}
        urlshortx = await shorten_url(f'https://telegram.me/{(client.get_me()).username}?start={token}')
        tinyurl = await tiny(urlshortx)
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Collect Token", url=tinyurl)]])
        return button
    except Exception as e:
        logger.error(f"error in update_token: {e}")

async def genrate_token(client, user_id):
    try:
        token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified"}
        urlshortx = await shorten_url(f'https://telegram.me/{(client.get_me()).username}?start={token}')
        tinyurl = await tiny(urlshortx)
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Collect Token", url=tinyurl)]])
        return button
    except Exception as e:
        logger.error(f"error in genrate_token: {e}")





