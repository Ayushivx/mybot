from pyrogram import Client, filters
import config

app = Client(
    "my_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Start command handler
@app.on_message(filters.command(["start"]))
def start_command(client, message):
    client.send_message(
        chat_id=message.chat.id,
        text="Welcome! Send me a message and I will echo it back."
    )

# Echo handler
@app.on_message(filters.text & ~filters.command)
def echo(client, message):
    client.send_message(
        chat_id=message.chat.id,
        text=message.text
    )

app.run()
