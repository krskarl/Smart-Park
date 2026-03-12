
try:
    from sense_hat import SenseHat
    sense = SenseHat()
    SIMULATION_MODE = False
except ImportError:
    SIMULATION_MODE = True

# Define pixel patterns for each status
STATUS_PATTERNS = {
    "Unlocked": [(1, 3), (2, 2), (3, 1), (4, 2), (5, 3)],
    "Rented": [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
    "Locked": [(2, 2), (2, 5), (5, 2), (5, 5)],
}

# Default off color (black)
OFF_COLOR = (0, 0, 0)

def display_status(status, color):
    """Displays a status pattern on the Sense HAT."""
    if SIMULATION_MODE:
        return

    pixels = [OFF_COLOR] * 64  # 8x8 grid

    if status in STATUS_PATTERNS:
        for x, y in STATUS_PATTERNS[status]:
            pixels[y * 8 + x] = color  # Convert (x, y) to 1D index

    sense.set_pixels(pixels)

def display_text(message, color="white"):
    if SIMULATION_MODE:
        return

    sense.show_message(message, text_colour=color)


def display_battery(percent):
    """Displays the battery level on the Sense HAT."""
    if SIMULATION_MODE:
        return

    pixels = [OFF_COLOR] * 64  # 8x8 grid

    if percent > 50:
        color = (0, 255, 0)  # Green
        num_lit_pixels = 3
    elif 30 <= percent <= 50:
        color = (255, 255, 0)  # Yellow
        num_lit_pixels = 2
    else:
        color = (255, 0, 0)  # Red
        num_lit_pixels = 1

    # Define the top-right corner positions
    top_right_positions = [(7, 0), (7, 1), (7, 2)]  # (x, y) coordinates

    # Light up the appropriate number of pixels
    for i in range(num_lit_pixels):
        x, y = top_right_positions[i]
        pixels[y * 8 + x] = color  # Convert (x, y) to 1D index

    sense.set_pixels(pixels)
