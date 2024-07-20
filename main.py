from utils import *
from config import *
from pyrogram import idle
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums

DOWNLOAD_PATH = "downloads/"
CHUNK_SIZE = 1024 * 1024 * 200

THUMBNAIL_INTERVALS = ['00:01:10', '00:2:00', '00:2:30', '00:03:00', '00:3:30']  # Intervals to take screenshots
GRID_COLUMNS = 2  # Number of columns in the grid


os.makedirs(DOWNLOAD_PATH, exist_ok=True)

app = Client(
    "my_bot",
      api_id=API_ID,
      api_hash=API_HASH, 
      bot_token=BOT_TOKEN, 
      workers=1000, 
      parse_mode=enums.ParseMode.HTML)

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


@app.on_message(filters.chat(DB_CHANNEL_ID) & (filters.document | filters.video))
async def forward_message_to_new_channel(client, message):
    try:
        media = message.document or message.video or message.audio
        file_id = message.id

        if media:
            caption = message.caption if message.caption else None

            if caption:
                new_caption = await remove_unwanted(caption)

                # Generate file path
                file_path = os.path.join(DOWNLOAD_PATH,  str(file_id))

                logger.info(f"Downloading initial part of {file_id}...")

                await download_initial_part(client, media, file_path, CHUNK_SIZE)

                # Generate a thumbnail
                thumbnail_path = await generate_combined_thumbnail(file_path)

                if thumbnail_path:
                    print(f"Thumbnail generated: {thumbnail_path}")
                else:
                    print("Failed to generate thumbnail")   

                file_info = f"<code>{new_caption}</code>\n\n<code>✅ {file_id}</code>"

                await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info)

                os.remove(thumbnail_path)
                os.remove(file_path)

                await asyncio.sleep(3)
            else:
                audio_path = await app.download_media(media.file_id)
                audio_thumb = await get_audio_thumbnail(audio_path)
                
                file_info = f"🎧 <b>{media.title}</b>\n🧑‍🎤 <b>{media.performer}</b>\n\n<code>🆔 {file_id}</code>"

                await app.send_photo(CAPTION_CHANNEL_ID, audio_thumb, caption=file_info)

                os.remove(audio_path)

                await asyncio.sleep(3)
            
            
    except Exception as e:
        logger.error(f'{e}')    

@app.on_message(filters.command("send") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    await message.reply_text("send post link")
    tg_link = (await app.listen(message.chat.id)).text

    msg_id = await extract_tg_link(tg_link)

    file_message = await app.get_messages(DB_CHANNEL_ID, int(msg_id))

    media = file_message.document or file_message.video or file_message.audio
    file_id = file_message.id

    if media:
        caption = file_message.caption if file_message.caption else None

        if caption:
            new_caption = await remove_unwanted(caption)

            # Generate file path
            file_path = os.path.join(DOWNLOAD_PATH, str(file_id))

            logger.info(f"Downloading initial part of {file_id}...")

            await download_initial_part(client, media, file_path, CHUNK_SIZE)

            # Generate a thumbnail
            thumbnail_path = await generate_combined_thumbnail(file_path, THUMBNAIL_INTERVALS, GRID_COLUMNS)

            if thumbnail_path:
                print(f"Thumbnail generated: {thumbnail_path}")
            else:
                print("Failed to generate thumbnail")   

            file_info = f"<code>{new_caption}</code>\n\n<code>✅ {file_id}</code>"

            await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info)

            os.remove(thumbnail_path)
            os.remove(file_path)

            await asyncio.sleep(3)

        else:
            audio_path = await app.download_media(media.file_id)
            audio_thumb = await get_audio_thumbnail(audio_path)
            
            file_info = f"🎧 <b>{media.title}</b>\n🧑‍🎤 <b>{media.performer}</b>\n\n<code>🆔 {file_id}</code>"

            await app.send_photo(CAPTION_CHANNEL_ID, audio_thumb, caption=file_info)

            os.remove(audio_path)

            await asyncio.sleep(3)
        
    await message.reply_text("Messages send successfully!")

@app.on_message(filters.command("sendm") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        await message.reply_text("send post start link")
        start_msg = (await app.listen(message.chat.id)).text

        await message.reply_text("send post end link")
        end_msg = (await app.listen(message.chat.id)).text

        start_msg_id = int(await extract_tg_link(start_msg))
        end_msg_id = int(await extract_tg_link(end_msg))

        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            file_messages = await app.get_messages(DB_CHANNEL_ID, range(start, end + 1))

            for file_message in file_messages:

                media = file_message.document or file_message.video or file_message.audio
                file_id = file_message.id

                if media:
                    caption = file_message.caption if file_message.caption else None

                    if caption:
                        new_caption = await remove_unwanted(caption)

                        # Generate file path
                        file_path = os.path.join(DOWNLOAD_PATH, str(file_id))
                        logger.info(f"Downloading initial part of {file_id}...")

                        await download_initial_part(client, media, file_path, CHUNK_SIZE)

                        # Generate a thumbnail
                        thumbnail_path = await generate_combined_thumbnail(file_path)

                        if thumbnail_path:
                            print(f"Thumbnail generated: {thumbnail_path}")
                        else:
                            print("Failed to generate thumbnail")  

                        file_info = f"<code>{new_caption}</code>\n\n<code>✅ {file_id}</code>"

                        await app.send_photo(CAPTION_CHANNEL_ID, thumbnail_path, caption=file_info)

                        os.remove(thumbnail_path)
                        os.remove(file_path)

                        await asyncio.sleep(3)

                    else:
                        audio_path = await app.download_media(media.file_id)
                        audio_thumb = await get_audio_thumbnail(audio_path)
                        
                        file_info = f"🎧 <code>{media.title}</code>\n🧑‍🎤 <code>{media.performer}</code>\n\n✅ <code>{file_id}</code>"

                        await app.send_photo(CAPTION_CHANNEL_ID, audio_thumb, caption=file_info)

                        os.remove(audio_path)

                        await asyncio.sleep(3)

            await message.reply_text("Messages send successfully!")

    except FloodWait as e:
        await asyncio.sleep(e.value)

    except Exception as e:
        logger.error(f'{e}')
      
if __name__ == "__main__":
    loop.run_until_complete(main())
