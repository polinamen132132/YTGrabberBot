from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackContext, ConversationHandler, CallbackQueryHandler
)
from pytube import YouTube
import boto3
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('API_KEY')

HANDLE_LINK = 1

# Initialize S3 client
s3_client = boto3.client('s3')
bucket_name = 'youtubebucketchipa'  # Replace with your bucket name

# Define async function to start the bot and display a welcome message
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Welcome to the YouTube Downloader Bot. Please send me a YouTube link."
    )
    return HANDLE_LINK

# Async function to handle received messages containing YouTube links
async def handle_link(update: Update, context: CallbackContext) -> int:
    link = update.message.text
    yt = YouTube(link)
    video = yt.streams.get_highest_resolution()
    video_file_path = f"{yt.title}.mp4"

    # Attempt to download video and upload to S3
    try:
        video.download(filename=video_file_path)
        response = s3_client.upload_file(video_file_path, bucket_name, video_file_path)

        # Generate download link
        url = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': bucket_name, 'Key': video_file_path},
                                               ExpiresIn=3600)
        
        # Create button for downloading the next video
        keyboard = [
            [InlineKeyboardButton("Download Next Video", callback_data='download_next')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f'Title: {yt.title}\nViews: {yt.views}\nVideo has been uploaded. Download here: {url}',
            reply_markup=reply_markup
        )
        return HANDLE_LINK
    except Exception as e:
        await update.message.reply_text(f'Failed to download or upload video. Error: {str(e)}')
        return HANDLE_LINK

async def button(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'download_next':
        await query.message.reply_text("Please send me the next YouTube link.")
        # Restart the conversation to handle the next link
        return handle_link

# Cancel handler to stop the conversation
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Operation canceled.')
    return ConversationHandler.END

# Main function to run the bot
def main() -> None:
    application = Application.builder().token(api_key).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HANDLE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True  # Allow reentry to handle multiple links
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button, pattern='^download_next$'))

    application.run_polling()

if __name__ == "__main__":
    main()
