from utils import *
from config import *
from pyrogram import idle
from pyromod import listen
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums
from asyncio import get_event_loop

DOWNLOAD_PATH = "downloads/"
loop = get_event_loop()
THUMBNAIL_COUNT = 6
GRID_COLUMNS = 3  # Number of columns in the grid

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

user_data = {}
TOKEN_TIMEOUT = 7200

app = Client(
    "my_bot",
      api_id=API_ID,
      api_hash=API_HASH, 
      bot_token=BOT_TOKEN, 
      workers=1000, 
      parse_mode=enums.ParseMode.HTML,
      in_memory=True)

user = Client(
                "userbot",
                api_id=int(API_ID),
                api_hash=API_HASH,
                session_string=STRING_SESSION,
                no_updates = True
            )

async def main():
    async with app, user:
        await idle()

with app:
    bot_username = (app.get_me()).username

@app.on_message(filters.chat(DB_CHANNEL_ID) & (filters.document | filters.video | filters.audio))
async def forward_message_to_new_channel(client, message):
    try:
        media = message.document or message.video or message.audio
        file_id = message.id

        if media:
            caption = message.caption if message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)

                # Generate file path
                logger.info(f"Downloading initial part of {file_id}...")

                file_path = await app.download_media(media.file_id)
                print("Generating Thumbnail")
                # Generate a thumbnail
                thumbnail_path = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

                if thumbnail_path:
                    print(f"Thumbnail generated: {thumbnail_path}")
                else:
                    print("Failed to generate thumbnail")   

                file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{file_id}</code>"
                
                file_link = f'https://telegram.me/@thetgflixxxbot?start={cpy_msg.id}'
                button = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])

                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, reply_markup=button)

                os.remove(thumbnail_path)
                os.remove(file_path)

                await asyncio.sleep(3)

    except Exception as e:
        logger.error(f'{e}') 
        
@app.on_message(filters.command("start"))
async def get_command(client, message):
    reply = await message.reply_text(f"<b>💐Welcome this is TG⚡️Flix Bot")
    await auto_delete_message(message, reply)

# Send Multiple Command
@app.on_message(filters.command("send") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        rply1 = await message.reply_text("send post start link")
        s_msg = await app.listen(message.chat.id)
        start_msg = s_msg.text 
        await rply1.delete()
        

        rply2 = await message.reply_text("send post end link")
        e_msg = await app.listen(message.chat.id)
        end_msg = e_msg.text
        await rply2.delete()

        start_msg_id = int(await extract_tg_link(start_msg))
        await s_msg.delete()
        await asyncio.sleep(3)
        end_msg_id = int(await extract_tg_link(end_msg))
        await e_msg.delete()
        
        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            file_messages = await app.get_messages(DB_CHANNEL_ID, range(start, end + 1))

            for file_message in file_messages:

                media = file_message.document or file_message.video or file_message.audio

                if media:
                    file_id = file_message.id
                    caption = file_message.caption if file_message.caption else None

                    if caption:
                        new_caption = await remove_unwanted(caption)

                        # Generate file path
                        logger.info(f"Downloading initial part of {file_id}...")

                        file_path = await app.download_media(media.file_id)
                        print("download complete")
                        # Generate a thumbnail
                        thumbnail_path = await generate_combined_thumbnail(file_path, THUMBNAIL_COUNT, GRID_COLUMNS)

                        if thumbnail_path:
                            print(f"Thumbnail generated: {thumbnail_path}")
                        else:
                            print("Failed to generate thumbnail")  

                        file_info = f"🎞️ <b>{new_caption}</b>\n\n🆔 <code>{file_id}</code>"
                        file_link = f'https://telegram.me/@thetgflixxxbot?start={cpy_msg.id}'
                        button = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])

                        await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info, reply_markup=button)

                        os.remove(thumbnail_path)
                        os.remove(file_path)

                        await asyncio.sleep(3)

        await message.reply_text("Messages send successfully!")

    except FloodWait as e:
        await asyncio.sleep(e.value)

    except Exception as e:
        logger.error(f'{e}')

# Delete Commmand
@app.on_message(filters.command("delete") & filters.user(OWNER_USERNAME))
async def get_command(client, message):
    try:
        await message.reply_text("Enter channel_id")
        channel_id = int((await app.listen(message.chat.id)).text)

        await message.reply_text("Enter count")
        limit = int((await app.listen(message.chat.id)).text)

        await app.send_message(channel_id, "Hi")

        try:
            async for message in user.get_chat_history(channel_id, limit):
                await message.delete()
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
        await user.send_message(channel_id, "done")
    except Exception as e:
        logger.error(f"Error : {e}")

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
    
      
if __name__ == "__main__":
    loop.run_until_complete(main())
