"""Centralized bot response messages for MCADV Adventure Bot."""

# Command responses
HELP_MESSAGE = (
    "MCADV Adventure Bot Commands:\n"
    "!adv [theme] - Start adventure (default: fantasy)\n"
    "!start [theme] - Start adventure\n"
    "1/2/3 - Make a choice\n"
    "!quit - End adventure\n"
    "!status - Check status\n"
    "Themes: {themes_list}"
)

# Story state messages
STORY_IN_PROGRESS = (
    "A story is already in progress! Continue the adventure by making choices (1/2/3), "
    "or wait for it to reach THE END."
)
STORY_ENDED = "Adventure ended. Type !adv to start a new one."
NO_ACTIVE_STORY = "No active adventure. Type !adv to start."

# Reset messages
AUTO_RESET_24H = "Resetting all adventures after 24 hours of runtime. A new tale may begin!"

# Story start
STORY_STARTING = "Starting {theme} adventure..."
