# Wordle Discord Bot
Gathers and displays statistics about Wordle games in a Discord channel or thread.



## Features



## Planned features
- user specific info
- Earliest posts
- time spent pondering
- starter word scores

## todo
- do i need intent?
- do I need a db_close? or a bot shutdown?
- does load_all_users() need an arg?



## Setup
---dependencies. 
install then globally or in a venv.
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
it needs permission to sense message content intent. 
it also needs these permissions: send message, read message. use slash commands.

invite the bot.
I generated the invite link through the oauth2 tab becasuse i couldn't get the permissions to stick via the bot tab



## Running
add it to your server. 

run it via python src/main.py

(commands?)


## deploy