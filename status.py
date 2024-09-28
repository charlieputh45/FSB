import sys
import time
import asyncio

# Initialize global variables
start_time = None
previous_time = None
previous_bytes = 0

async def progress(current, total, status, message):
    global start_time, previous_time, previous_bytes

    # Initialize timers and bytes on the first call
    if start_time is None:
        start_time = time.time()
        previous_time = start_time
        previous_bytes = current  # Start with the initial current

    # Calculate percentage
    percentage = (current / total) * 100 if total > 0 else 0

    # Get current time
    current_time = time.time()

    # Calculate elapsed time
    elapsed_time = current_time - start_time

    # Check if enough time has passed to update the message
    if (current_time - previous_time) >= 3:  # 3-second interval
        # Calculate speed in bytes per second
        if previous_bytes < current:
            speed = (current - previous_bytes) / (current_time - previous_time)
        else:
            speed = 0  # Reset speed if no new data is received

        # Update previous time and bytes for the next calculation
        previous_time = current_time
        previous_bytes = current

        # Convert speed to MB/s
        speed_mbps = speed / (1024 * 1024)  # Convert to MB/s
        total_mb = total / (1024 * 1024)  # Convert total size to MB

        # Prepare the message content
        progress_message = (
            f"{status}: {percentage:.1f}%\n"
            f"Transferred: {current / (1024 * 1024):.2f} MB of {total_mb:.2f} MB\n"
            f"Speed: {speed_mbps:.2f} MB/s\n"
            f"Elapsed Time: {int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"
        )

        # Update the message in Telegram
        try:
            await message.edit_text(progress_message)
        except Exception as e:
            print(f"Error editing message: {e}")

        
async def finish_task(status):
    global start_time, total_bytes

    # Calculate average speed after the download is complete
    elapsed_time = time.time() - start_time  # Total elapsed time
    if elapsed_time > 0:
        average_speed_mbps = total_bytes / elapsed_time / (1024 * 1024)  # Convert to MB/s
        print(f"\{status} completed! Average Speed: {average_speed_mbps:.2f} MB/s")
    else:
        print(f"\{status} completed! Unable to calculate average speed.")

# Reset variables when starting a new download
def reset_progress():
    global start_time, previous_time, previous_bytes
    start_time = None
    previous_time = None
    previous_bytes = 0
