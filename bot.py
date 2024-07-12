from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaDocument, InputMediaPhoto
from pymongo import MongoClient
import config

app = Client("file_share_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)
client = MongoClient(config.MONGO_URI)
db = client["bot_db"]
users_collection = db["users"]

# Check if the user is the owner
def is_owner(user_id):
    return user_id == config.OWNER_ID

# Check if the user is subscribed to all channels
async def check_subscription(user_id):
    for channel in config.FORCE_SUB_CHANNELS:
        try:
            user = await app.get_chat_member(channel['username'], user_id)
            if user.status != "member":
                return False
        except UserNotParticipant:
            return False
    return True

# Ensure the bot only works in private chats
@app.on_message(filters.command(["upload", "batch", "caption", "help"]) & ~filters.private)
async def deny_group_access(client, message):
    await message.reply("This bot only works in private messages.")

# Help command for users
@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    if is_owner(message.from_user.id):
        await message.reply(
            "Owner Commands:\n"
            "/upload - Upload a file (reply to a document)\n"
            "/batch - Upload multiple files (reply to a media group)\n"
            "/caption - Set a custom caption (reply to a message)\n"
            "/help - Show this help message\n"
            "\nNote: Only you can upload and manage files."
        )
    else:
        await message.reply(
            "User Commands:\n"
            "/help - Show this help message\n"
            "To access files, you need to subscribe to our channels."
        )

# Owner-only file uploads
@app.on_message(filters.command("upload") & filters.private)
async def upload_file(client, message):
    if not is_owner(message.from_user.id):
        await message.reply("You are not authorized to upload files.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("Please reply to a document with /upload to upload it.")
        return

    file_id = message.reply_to_message.document.file_id
    file_caption = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else ""

    # Send the file to the log channel
    log_message = await app.send_document(config.LOG_CHANNEL, file_id, caption=file_caption)
    shareable_link = f"https://t.me/{config.LOG_CHANNEL}/{log_message.message_id}"
    
    await message.reply(f"File uploaded successfully! Shareable link: {shareable_link}")

# Owner-only batch uploads
@app.on_message(filters.command("batch") & filters.private)
async def batch_upload(client, message):
    if not is_owner(message.from_user.id):
        await message.reply("You are not authorized to upload files.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.media_group_id:
        await message.reply("Please reply to a media group with /batch to upload it.")
        return

    media_group_id = message.reply_to_message.media_group_id
    file_caption = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else ""
    
    messages = await app.get_media_group(message.chat.id, media_group_id)
    media = []

    for msg in messages:
        if msg.document:
            media.append(InputMediaDocument(msg.document.file_id, caption=file_caption))
        elif msg.photo:
            media.append(InputMediaPhoto(msg.photo.file_id, caption=file_caption))

    # Send the media group to the log channel
    log_messages = await app.send_media_group(config.LOG_CHANNEL, media)
    links = [f"https://t.me/{config.LOG_CHANNEL}/{msg.message_id}" for msg in log_messages]
    
    await message.reply(f"Files uploaded successfully! Shareable links: {', '.join(links)}")

# Custom captions
@app.on_message(filters.command("caption") & filters.private)
async def custom_caption(client, message):
    if not is_owner(message.from_user.id):
        await message.reply("You are not authorized to set custom captions.")
        return

    if not message.reply_to_message:
        await message.reply("Please reply to a message to set a custom caption.")
        return

    caption = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else ""
    await message.reply_to_message.edit_caption(caption)
    await message.reply("Caption updated successfully!")

# Restrict content saving and force subscription
@app.on_message(filters.private)
async def restrict_saving_and_force_subscribe(client, message):
    if not await check_subscription(message.from_user.id):
        subscribe_buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"Subscribe to Channel {i+1}", url=channel['invite_link'])] for i, channel in enumerate(config.FORCE_SUB_CHANNELS)]
        )
        await message.reply("You need to subscribe to our channels to use this bot.", reply_markup=subscribe_buttons)
        return

    if message.document or message.photo:
        await message.reply("You cannot save or forward this content.")
        return

# Auto-Approve Users in Private Channels
@app.on_message(filters.private)
async def auto_approve_users(client, message):
    if not await check_subscription(message.from_user.id):
        return

    for channel in config.FORCE_SUB_CHANNELS:
        try:
            await app.approve_chat_join_request(channel['username'], message.from_user.id)
        except:
            pass

# MongoDB integration: Save user data
@app.on_message(filters.private)
async def save_user_data(client, message):
    user_data = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "is_subscribed": await check_subscription(message.from_user.id)
    }
    users_collection.update_one({"user_id": message.from_user.id}, {"$set": user_data}, upsert=True)

app.run()
