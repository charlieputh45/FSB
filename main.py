import uuid
import gridfs
from time import time as tm
from datetime import datetime, timezone
from config import *
from pymongo import MongoClient
from utils import *
from pyromod import listen
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from shorterner import *
from pyrogram.types import User
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Initialize MongoDB client
MONGO_COLLECTION = "users"
mongo_client = MongoClient(MONGO_URI)  
db = mongo_client[MONGO_DB_NAME]
collection = db[COLLECTION_NAME]
mongo_collection = db[MONGO_COLLECTION]
fs = gridfs.GridFS(db)


THUMBNAIL_COUNT = 9
GRID_COLUMNS = 3 # Number of columns in the grid

user_data = {}
TOKEN_TIMEOUT = 28800

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=enums.ParseMode.HTML
)

with app:
    bot_username = (app.get_me()).username

@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user_link = await get_user_link(message.from_user)

    if len(message.command) > 1 and message.command[1] == "token":
        try:
            file_id = 1775
            get_msg = await app.get_messages(DB_CHANNEL_ID, int(file_id))
            cpy_msg = await get_msg.copy(chat_id=message.chat.id)
            await message.delete()
            await asyncio.sleep(300)
            await cpy_msg.delete()
            return
            
        except Exception as e:
            logger.error(f"{e}")
        return

    if len(message.command) > 1 and message.command[1].startswith("token_"):
        input_token = message.command[1][6:]
        token_msg = await verify_token(user_id, input_token)
        reply = await message.reply_text(token_msg)
        await app.send_message(LOG_CHANNEL_ID, f"User🕵️‍♂️{user_link} with 🆔 {user_id} @{bot_username} {token_msg}", parse_mode=enums.ParseMode.HTML)
        await auto_delete_message(message, reply)
        return

    file_id = message.command[1] if len(message.command) > 1 else None

    if file_id:
        if not await check_access(message, user_id):
            return
        try:
            file_message = await app.get_messages(DB_CHANNEL_ID, int(file_id))
            media = file_message.video or file_message.audio or file_message.document
            if media:
                caption = file_message.caption if file_message.caption else None
                if caption:
                    new_caption = await remove_extension(caption)
                    copy_message = await file_message.copy(chat_id=message.chat.id, caption=f"<b>{new_caption}</b>", parse_mode=enums.ParseMode.HTML)
                    user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1
                else:
                    copy_message = await file_message.copy(chat_id=message.chat.id)
                    user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1
                await auto_delete_message(message, copy_message)
                await asyncio.sleep(3)
            else:
                reply = await message.reply_text("File not found or inaccessible.")
                await auto_delete_message(message, reply)

        except ValueError:
            reply = await message.reply_text("Invalid File ID") 
            await auto_delete_message(message, reply)  

        except FloodWait as f:
            await asyncio.sleep(f.value)
            if caption:
                copy_message = await file_message.copy(chat_id=message.chat.id, caption=f"<b>{new_caption}</b>", parse_mode=enums.ParseMode.HTML)
                user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1
            else:
                copy_message = await file_message.copy(chat_id=message.chat.id)
                user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1

            await auto_delete_message(message, copy_message)
            await asyncio.sleep(3)

    else:
        await mongo_collection.update_one(
                {'user_id': user_id},
                {'$set': {'user_id': user_id}}, 
                upsert=True
            )                   
        reply = await message.reply_text(f"<b>💐Welcome to FileShare Bot")
        await auto_delete_message(message, reply)

@app.on_message(filters.private & (filters.document | filters.video) & filters.user(OWNER_USERNAME))
async def handle_media_message(client, message):
    media = message.document or message.video

    if not media:
        await message.reply_text("The message does not contain a valid media file. Please provide a document or video.")
        return

    # Extract file information
    file_id = message.id
    file_size = media.file_size
    file_name = await remove_unwanted(message.caption)
    
    # Prepare the file information to be stored
    file_info = {
        "file_id": file_id,
        "file_name": file_name,
        "file_size": humanbytes(file_size)
    }

    # Initialize photo_id as None
    photo_id = None

    # If it's a video, download the thumbnail
    if message.video and message.video.thumbs:
        # Download the first available thumbnail (usually there is only one)
        thumbnail = message.video.thumbs[0]
        thumbnail_file = await app.download_media(thumbnail.file_id)

        # Store the thumbnail in GridFS
        try:
            with open(thumbnail_file, "rb") as f:
                photo_id = fs.put(f, filename="video_thumbnail.jpg")
            os.remove(thumbnail_file)  # Remove temporary thumbnail file
        except Exception as e:
            await message.reply_text("Failed to store the video thumbnail.")
            logger.error(f"Error storing video thumbnail: {e}")

    # Create the document to store in MongoDB
    document = {
        "file_info": file_info,
        "photo_id": photo_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Insert the document into MongoDB
    try:
        collection.insert_one(document)
        await message.reply_text("Media information added successfully.")
    except Exception as e:
        logger.error(f"Error in handle_media_message: {e}")
        await message.reply_text("An error occurred while adding the media information.")


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
                            file_name = await remove_unwanted(caption)

                            # Prepare the file information to be stored
                            file_info = {
                                "file_id": file_id,
                                "file_name": file_name,
                                "file_size": humanbytes(file_size)
                            }


                            # Generate file path
                            logger.info(f"Downloading {file_id} to {end_msg_id}")
                            file_path = await app.download_media(file_message, file_name=f"{file_message.id}")
                                                                                  
                            # Generate a thumbnail
                            thumbnail_path, duration = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

                            if thumbnail_path:
                                print(f"Thumbnail generated: {thumbnail_path}")
                                try:
                                    with open(thumbnail_path, "rb") as f:
                                        photo_id = fs.put(f, filename="video_thumbnail.jpg")
                                    os.remove(thumbnail_path)  # Remove temporary thumbnail 
                                    
                                        # Create the document to store in MongoDB
                                    document = {
                                        "file_info": file_info,
                                        "photo_id": photo_id,
                                        "timestamp": datetime.now(timezone.utc).isoformat()
                                    }

                                    # Insert the document into MongoDB
                                    collection.insert_one(document)
                                    await message.reply_text("Media information added successfully.")
                                except Exception as e:
                                    logger.error(f"Error in handle_media_message: {e}")
                                    await message.reply_text("An error occurred while adding the media information.")
                            else:
                                print("Failed to generate thumbnail")
                                                                            
                            os.remove(thumbnail_path)
                            os.remove(file_path)
    
                            await asyncio.sleep(3)
                            
                    except Exception as e:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        if os.path.exists(thumbnail_path):
                            os.remove(thumbnail_path)
            
        await message.reply_text("Messages send successfully ✅")

    except FloodWait as e:
        await asyncio.sleep(e.value)

    except Exception as e:
        logger.error(f'{e}')


# Get Total User Command
@app.on_message(filters.command("users") & filters.user(OWNER_USERNAME))
async def total_users_command(client, message):
    user_id = message.from_user.id

    total_users = mongo_collection.count_documents({})
    response_text = f"Total number of users in the database: {total_users}"
    reply = await app.send_message(user_id, response_text)
    await auto_delete_message(message, reply)
            
async def verify_token(user_id, input_token):
    current_time = tm()

    # Check if the user_id exists in user_data
    if user_id not in user_data:
        return 'Token Mismatched ❌' 
    
    stored_token = user_data[user_id]['token']
    if input_token == stored_token:
        token = str(uuid.uuid4())
        user_data[user_id] = {"token": token, "time": current_time, "status": "verified", "file_count": 0}
        return f'Token Verified ✅ (Validity: {get_readable_time(TOKEN_TIMEOUT)})'
    else:
        return f'Token Mismatched ❌'
    
async def check_access(message, user_id):

    if user_id in user_data:
        time = user_data[user_id]['time']
        status = user_data[user_id]['status']
        file_count = user_data[user_id].get('file_count', 0)
        expiry = time + TOKEN_TIMEOUT
        current_time = tm()
        if current_time < expiry and status == "verified":
            if file_count < 10:
                return True
            else:
                reply = await message.reply_text(f"You have reached the limit. Please wait until the token expires")
                await auto_delete_message(message, reply)
                return False
        else:
            button = await update_token(user_id)
            send_message = await app.send_message(user_id, f"<b>It looks like your token has expired. Get Free 💎 Limited Access again!</b>", reply_markup=button)
            await auto_delete_message(message, send_message)
            return False
    else:
        button = await genrate_token(user_id)
        send_message = await app.send_message(user_id, f"<b>It looks like you don't have a token. Get Free 💎 Limited Access now!</b>", reply_markup=button)
        await auto_delete_message(message, send_message)
        return False

async def update_token(user_id):
    try:
        time = user_data[user_id]['time']
        expiry = time + TOKEN_TIMEOUT
        if time < expiry:
            token = user_data[user_id]['token']
        else:
            token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified", "file_count": 0}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start=token_{token}')
        token_url = f'https://telegram.me/{bot_username}?start=token'
        button1 = InlineKeyboardButton("🎟️ Get Token", url=urlshortx)
        button2 = InlineKeyboardButton("👨‍🏫 How it Works", url=token_url)
        button = InlineKeyboardMarkup([[button1], [button2]]) 
        return button
    except Exception as e:
        logger.error(f"error in update_token: {e}")

async def genrate_token(user_id):
    try:
        token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified", "file_count": 0}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start=token_{token}')
        token_url = f'https://telegram.me/{bot_username}?start=token'
        button1 = InlineKeyboardButton("🎟️ Get Token", url=urlshortx)
        button2 = InlineKeyboardButton("👨‍🏫 How it Works", url=token_url)
        button = InlineKeyboardMarkup([[button1], [button2]]) 
        return button
    except Exception as e:
        logger.error(f"error in genrate_token: {e}")

async def get_user_link(user: User) -> str:
    user_id = user.id
    first_name = user.first_name
    return f'<a href=tg://user?id={user_id}>{first_name}</a>'


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

# Start the bot
print("starting bot")
app.run()
