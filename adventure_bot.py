# Adventure Bot

"""This is the Adventure Bot for your themed adventures.

Commands:
- !start [theme]: Start an adventure with a specified theme. Valid themes are listed below.
"""

VALID_THEMES = [
    'fantasy', 'medieval', 'scifi', 'horror', 'dark_fantasy', 'urban_fantasy', 'steampunk',
    'dieselpunk', 'cyberpunk', 'post_apocalypse', 'dystopian', 'space_opera', 'cosmic_horror',
    'occult', 'ancient', 'renaissance', 'victorian', 'wild_west', 'comedy', 'noir',
    'mystery', 'romance', 'slice_of_life', 'grimdark', 'wholesome', 'high_school', 'college',
    'corporate', 'pirate', 'expedition', 'anime', 'superhero', 'fairy_tale', 'mythology'
]

# ... (other parts of the bot) ...

def handle_message(message):
    if message.content.startswith('!help'):
        return "Use !start [theme] to begin your adventure."
    elif message.content.startswith('!adv'):
        return "Deprecation warning: use !start [theme] instead."
    elif message.content.startswith('!start '):
        theme = message.content[7:]  # extract theme
        if theme in VALID_THEMES:
            return start_adventure(theme)
        else:
            return "Invalid theme."

# ... (additional methods) ...
