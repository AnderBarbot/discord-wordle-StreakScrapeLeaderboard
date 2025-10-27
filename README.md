# Wordle Discord Bot
Gathers and displays statistics about Wordle games in a Discord channel or thread. 



## Features
tbd



## todo ideas
/scores to see your score.
stddev or confidence interval availability.
early poster stat (vv difficult to implement, but I would love to do it).
starter word scores
time spent pondering



## Setup
---dependencies. 
install them globally or in a venv.
the code below is intended for bash

-virtual environment steps,  skip to simplify and install deps globally.
    'python -m venv .venv'
    'source venv/Scripts/activate'
you are now using the venv
you should see a (venv) tag in your terminal
you can exit the venv via 'deactivate'

-dependency installation
    `pip install -r requirements.txt`



## Installation
[Create a bot account](https://discordpy.readthedocs.io/en/stable/discord.html)

Copy the bot token. Create a .env in the root directory and set the following variable. DISCORD_TOKEN=your_bot_token_here

set bot permissions
it needs permission to sense message content intent(read messages) and member intent (see member data, such as display name)
it also needs these permissions: send message, read message. use slash commands.

invite the bot.
I generated the invite link through the oauth2 tab becasuse i couldn't get the permissions to stick via the bot tab



## Deployment
add/invite the bot to your server, as described above. 

run it via 
    'python src/main.py'

then use the commands below to your heart's content.
/leaderboard (display basic leaderboard)
/catchup (scrape message history for new data)
/reset (reset the bot)