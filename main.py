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

# Initialize MongoDB client
MONGO_COLLECTION = "users"
mongo_client = MongoClient(MONGO_URI)  
db = mongo_client[MONGO_DB_NAME]
collection = db[COLLECTION_NAME]
mongo_collection = db[MONGO_COLLECTION]
fs = gridfs.GridFS(db)


THUMBNAIL_COUNT = 9
GRID_COLUMNS = 3 # Number of columns in the grid

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

    file_path = await app.download_media(message)

    thumbnail_path, duration = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

    # Store the thumbnail in GridFS
    try:
        with open(thumbnail_path, "rb") as f:
            photo_id = fs.put(f, filename="video_thumbnail.jpg")
        os.remove(thumbnail_path)
        os.remove(file_path)

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

    except Exception as e:
        await message.reply_text("Failed to store the video thumbnail.{file_name}")
        logger.error(f"Error storing video thumbnail: {e}")



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
                                    os.remove(thumbnail_path) 
                                    os.remove(file_path)                                    
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
                                    await message.reply_text("An error occurred while adding the media information. {file_name}")
                            else:
                                print("Failed to generate thumbnail {file_name}")
    
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
