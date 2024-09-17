import os 
from utils import *
from config import *
from html import escape
from pyrogram import idle
from pyromod import listen
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums
from asyncio import get_event_loop

DOWNLOAD_PATH = "downloads/"
loop = get_event_loop()

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

@app.on_message(filters.private & (filters.document | filters.video))
async def forward_message_to_new_channel(client, message):
    try:
        media = message.document or message.video
        file_id = message.id
        file_size = media.file_size

        if media:
            caption = message.caption if message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)

                # Generate file path
                logger.info(f"Downloading initial part of {file_id}...")
                
                dwnld_msg = await message.reply_text("📥 Downloading")
                
                file_path = await app.download_media(message, file_name=f"{caption}")
                print("Generating Thumbnail")
                # Generate a thumbnail
                movie_name, release_year = await extract_movie_info(caption)
                thumbnail_path = await get_movie_poster(movie_name, release_year)
                duration = await generate_duration(file_path)

                if thumbnail_path:
                    print(f"Thumbnail generated: {thumbnail_path}")
                else:
                    print("Failed to generate thumbnail")   


                upld_msg = await dwnld_msg.edit_text("⏫ Uploading")
                send_msg = await app.send_video(DB_CHANNEL_ID, 
                                                video=file_path, 
                                                caption=f"<code>{escape(caption)}</code>",
                                                duration=duration, 
                                                width=480, 
                                                height=320, 
                                                thumb=thumbnail_path
                                               )
                
                await upld_msg.edit_text("Uploaded ✅")

                file_info = f"<b>🗂️ {escape(new_caption)}\n\n💾 {humanbytes(file_size)}   🆔 <code>{send_msg.id}</code></b>"

                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info)

                os.remove(thumbnail_path)
                os.remove(file_path)

                await asyncio.sleep(3)

    except Exception as e:
        logger.error(f'{e}') 
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        
@app.on_message(filters.command("set"))
async def forward_message_to_new_channel(client, message):
    try:
        media = message.document or message.video
        file_id = message.id
        file_size = media.file_size

        if media:
            caption = message.caption if message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)

                # Generate file path
                logger.info(f"Downloading initial part of {file_id}...")
                
                dwnld_msg = await message.reply_text("📥 Downloading")
                
                file_path = await app.download_media(message, file_name=f"{caption}")
                print("Generating Thumbnail")
                # Generate a thumbnail
                rply = await message.reply_text(f"Please send a photo")
                photo_msg = await app.listen(message.chat.id, filters=filters.photo)
                thumbnail_path = await app.download_media(photo_msg, file_name=f'photo_{message.id}.jpg')
                await rply.delete()
                await photo_msg.delete()
                
                duration = await generate_duration(file_path)

                if thumbnail_path:
                    print(f"Thumbnail generated: {thumbnail_path}")
                else:
                    print("Failed to generate thumbnail")   


                upld_msg = await dwnld_msg.edit_text("⏫ Uploading")
                send_msg = await app.send_video(DB_CHANNEL_ID, 
                                                video=file_path, 
                                                caption=f"<code>{escape(caption)}</code>",
                                                duration=duration, 
                                                width=480, 
                                                height=320, 
                                                thumb=thumbnail_path,
                                               )
                
                await upld_msg.edit_text("Uploaded ✅")

                file_info = f"<b>🗂️ {escape(new_caption)}\n\n💾 {humanbytes(file_size)}   🆔 <code>{send_msg.id}</code></b>"

                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info)

                os.remove(thumbnail_path)
                os.remove(file_path)

                await asyncio.sleep(3)

    except Exception as e:
        logger.error(f'{e}') 
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

@app.on_message(filters.command("start"))
async def get_command(client, message):
    reply = await message.reply_text(f"<b>💐Welcome this is TG⚡️Flix Bot")
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
    
      
if __name__ == "__main__":
    loop.run_until_complete(main())
