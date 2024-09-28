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
