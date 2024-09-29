import uuid
import queue
import asyncio
import requests
from time import time as tm
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
from pyrogram.enums import ParseMode

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
                    
                    # Prepare the file information to be stored
                    file_info = {
                        "file_id": message.id,
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

@app.on_message(filters.private & filters.command("upload") & filters.user(OWNER_USERNAME))
async def upload_video(client, message):
    if not message.reply_to_message or not (message.reply_to_message.document or message.reply_to_message.video):
        await message.reply_text("Please reply to a video or document message to upload it.")
        return

    reply_msg = message.reply_to_message
    media = reply_msg.document or reply_msg.video
    file_id = reply_msg.id
    file_size = media.file_size
    caption = reply_msg.caption if reply_msg.caption else None

    # Send an initial message for upload status
    initial_msg = await message.reply_text("📤 Preparing to upload your file...")

    try:
        if media:
            new_caption = await remove_unwanted(caption) if caption else None

            logger.info(f"Downloading initial part of {file_id}...")

            # Download the media file
            reset_progress()
            file_path = await app.download_media(reply_msg, file_name=f"{reply_msg.id}", 
                                                 progress=progress,
                                                 progress_args=("Download", initial_msg)
                                                 )

            # Generate thumbnails
            screenshots, thumbnail, duration = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

            if screenshots:
                logger.info(f"Thumbnail generated: {screenshots}")

                # Send the video to the designated channel
                uploaded_video = await app.send_video(
                    DB_CHANNEL_ID,
                    video=file_path,
                    caption=f"<code>{new_caption}</code>" if new_caption else None,
                    thumb=thumbnail,
                    duration=duration,
                    parse_mode=ParseMode.HTML
                )

                # Prepare file information
                file_info = {
                    "file_id": uploaded_video.id,
                    "file_name": new_caption,
                    "file_size": humanbytes(file_size)
                }

                try:
                    # Store the thumbnail in GridFS
                    with open(thumbnail, "rb") as f:
                        thumb_id = fs.put(f, filename=f"thumb_{file_id}.jpg")
                    os.remove(thumbnail)

                    # Store the screenshot in GridFS
                    with open(screenshots, "rb") as f:
                        screenshot_id = fs.put(f, filename=f"ss_{file_id}.jpg")
                    os.remove(screenshots)

                    # Create the MongoDB document
                    document = {
                        "file_info": file_info,
                        "thumbnail_id": thumb_id,
                        "screenshot_id": screenshot_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    # Insert the document into MongoDB
                    collection.insert_one(document)
                    await initial_msg.edit_text("Video uploaded successfully and information stored ✅")
                except Exception as e:
                    logger.error(f"Error while storing video information: {e}")
                    await initial_msg.edit_text("An error occurred while storing the video information. Please try again.")

            else:
                logger.info("Failed to generate thumbnails.")
                await initial_msg.edit_text("Failed to generate thumbnails. Upload aborted.")

            await asyncio.sleep(3)

    except Exception as e:
        logger.error(f"Error during video upload: {e}")
        await initial_msg.edit_text(f"An error occurred during the upload. Please try again.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(screenshots):
            os.remove(screenshots)
        if os.path.exists(thumbnail):
            os.remove(thumbnail)

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

if __name__ == "__main__":
    logger.info("Bot is starting...")
    loop.run_until_complete(main())
    logger.info("Bot has stopped.")
