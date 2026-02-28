# Command Handling

## Supported Commands

The command supported for starting a new collaborative adventure is:

`!start [theme]`

## Available Themes
- fantasy
- medieval
- scifi (also sci-fi or science fiction)
- horror
- dark_fantasy
- urban_fantasy
- steampunk
- dieselpunk
- cyberpunk
- post_apocalypse
- dystopian
- space_opera
- cosmic_horror
- occult
- ancient
- renaissance
- victorian
- wild_west
- comedy
- noir
- mystery
- romance
- slice_of_life
- grimdark
- wholesome
- high_school
- college
- corporate
- pirate
- expedition
- anime
- superhero
- fairy_tale
- mythology

**Note:** When referencing themes in commands, use underscores (e.g., `dark_fantasy`) rather than spaces.

## Note

Support for the `!adv` command has been completely removed to simplify the command interface. All user-facing help texts and documentation have been updated accordingly. Users should now use `!start [theme]` exclusively to begin new adventures.

## Admin Commands

Some commands are restricted to admins to prevent griefing in collaborative mode:

- `!quit` or `!end` - **[ADMIN ONLY]** Immediately ends the adventure for all users on the channel

If no admin users are configured, all users can use these commands (backward-compatible behaviour).

## Voting System

Non-admin users can vote to end an adventure:

- `!vote` - Cast a vote to end the current adventure. When 3 or more users vote, the adventure ends automatically.

Vote counts are shown after each vote (e.g., `🗳️ Voted to end adventure (2/3 votes needed)`). Votes are cleared when the adventure ends or a new one begins.