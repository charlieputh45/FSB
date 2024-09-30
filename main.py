import queue
import asyncio
import requests
from datetime import datetime, timezone
from config import *
from pymongo import MongoClient
from utils import *
from pyrogram import idle
from pyromod import listen
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from status import *
from asyncio import get_event_loop

# Initialize MongoDB client
MONGO_COLLECTION = "users"
mongo_client = MongoClient(MONGO_URI)  
db = mongo_client[MONGO_DB_NAME]
collection = db[COLLECTION_NAME]
mongo_collection = db[MONGO_COLLECTION]

loop = get_event_loop()
THUMBNAIL_COUNT = 9
GRID_COLUMNS = 3 # Number of columns in the grid

# Create a global task queue
task_queue = queue.Queue()
initial_messages = {}  # Store initial messages for progress updates

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=enums.ParseMode.HTML
)

async def worker():
    while True:
        message = await loop.run_in_executor(None, task_queue.get)
        if message is None:
            break  # Exit if a sentinel value is received
        
        await handle_media_message(app, message)
        task_queue.task_done()

async def main():
    # Start the worker
    loop.create_task(worker())

    async with app:
        await idle()


with app:
    bot_username = (app.get_me()).username

@app.on_message(filters.private & (filters.document | filters.video) & filters.user(OWNER_USERNAME))
async def enqueue_message(client, message):
    # Send an initial message when a new task is added to the queue
    initial_msg = await message.reply_text("📥 Preparing to download your file...")

    # Add the message and the initial message reference to the task queue
    task_queue.put((message, initial_msg))
    initial_messages[message.id] = initial_msg  # Store reference for later updates

async def handle_media_message(client, message_tuple):
    try:
        message, initial_msg = message_tuple  # Unpack the tuple
        media = message.document or message.video
        file_id = message.id
        file_size = media.file_size

        if media:
            caption = message.caption if message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)

                logger.info(f"Downloading initial part of {file_id}...")

                reset_progress()
                file_path = await app.download_media(message, file_name=f"{message.id}", 
                                                     progress=progress,
                                                     progress_args=("Download", initial_msg)
                                                     )

                # Generating Thumbnails
                screenshots, thumbnail, duration = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

                if screenshots:
                    logger.info(f"Thumbnail generated: {screenshots}")
                    cpy_msg = await message.copy(DB_CHANNEL_ID, caption=f"<code>{new_caption}</code>", parse_mode=enums.ParseMode.HTML)
                    # Prepare the file information to be stored
                    file_info = {
                        "file_id": cpy_msg.id,
                        "file_name": new_caption,
                        "file_size": humanbytes(file_size)
                    }
            
                    try:
                        # Upload the first image (thumbnail) to ImgBB
                        thumb_url = await upload_to_imgbb(thumbnail)
                        os.remove(thumbnail)  # Remove the local file
                        
                        # Upload the second image (screenshot) to ImgBB
                        screenshot_url = await upload_to_imgbb(screenshots)
                        os.remove(screenshots)  # Remove the local file
                        
                        # Create the document to store in MongoDB
                        document = {
                            "file_info": file_info,
                            "thumbnail_url": thumb_url,  
                            "screenshot_url": screenshot_url,  
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    
                        # Insert the document into MongoDB
                        try:
                            collection.insert_one(document)
                            await initial_msg.edit_text("Media information added successfully ✅")
                        except Exception as e:
                            logger.error(f"Error in handle_media_message: {e}")
                            await message.reply_text(f"An error occurred while adding the file information. Please try again.")
                    
                    except Exception as e:
                        await message.reply_text(f"Failed to upload the video thumbnail for {new_caption}. Please try again.")
                        logger.error(f"Error uploading video thumbnail: {e}")

                else:
                    logger.info("Failed to generate thumbnails")

                await asyncio.sleep(3)

    except Exception as e:
        logger.error(f'{e}') 
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)        
        if message.id in initial_messages:
            del initial_messages[message.id]  # Clean up the initial message reference


@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    reply = await message.reply_text(f"<b>💐Welcome to FileShare Bot")
    await auto_delete_message(message, reply)


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

async def upload_to_imgbb(image_path, expiration=None):
    url = "https://api.imgbb.com/1/upload"
    with open(image_path, "rb") as file:
        files = {
            "image": file,
        }
        payload = {
            "key": IMGBB_API_KEY,
        }

        # Add expiration if provided
        if expiration:
            payload["expiration"] = expiration
        
        response = requests.post(url, data=payload, files=files)
        
        # Check for successful response
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['data']['url']  # Return the direct image URL
            else:
                error_message = result.get('error', 'Unknown error')
                logger.error(f"ImgBB upload failed: {error_message}")
                return None
        else:
            logger.error(f"ImgBB API error: {response.status_code}")
            return None

@app.on_message(filters.command("copy") & filters.user(OWNER_USERNAME))
async def copy_msg(client, message):    
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
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
                if file_message and (file_message.document or file_message.video or file_message.audio or file_message.photo):
                    caption = file_message.caption
                    await file_message.copy(destination_id, caption=f"<b>{caption}</b>")
                    await asyncio.sleep(3)
                    
        await message.reply_text("Messages copied successfully!✅")
        
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f'{e}')

if __name__ == "__main__":
    logger.info("Bot is starting...")
    loop.run_until_complete(main())
    logger.info("Bot has stopped.")
