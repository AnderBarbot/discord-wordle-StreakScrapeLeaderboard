# Wordle Discord Bot
Gathers and displays statistics about Wordle games in a Discord channel or thread. 
commands: /leaderboard (display basic leaderboard) /catchup (scrape message history for new data) /reset (reset the bot)
leaderboard details: displays all users in the database. displays user, avg score, adj avg score, total games played, losses, consistency (std dev), current streak, longest streak. sorted by bayesian average with a threshold of 10 (aka adj avg score). each user should have their own row, and their data should all be shown in that single row.
Guilds: currently,this app is only used in a single server and does not need guilds. this may change one day, so please leave stubs accordingly

## Features
message parsing
parses streak messages to scrape data. 
all game messages are known to come from this author, who is also a bot
author=1211781489931452447 
here are some message previews.
preview=**Your group is on a 5 day streak!** 🔥 Here are yesterday's results:\n👑 3/6: <@710479504900096090> <@703017808342024282> @Mason @Brenden\n4/6: <@275352516504453120> <@606265025509720066> <@336678214631948288> <@619363697269145600> <@1339421617167663136> <@598287781235785730>\n5/6: <@6511083717636915

preview=**Your group is on a 7 day streak!** 🔥 Here are yesterday's results:\n👑 4/6: <@598287781235785730> <@606265025509720066> <@961067371378921512> @Brenden\n5/6: <@651108371763691597> <@619363697269145600> <@703017808342024282>\n6/6: @Ethan @Mason

plaintext message:
**Your group is on a 6 day streak!** 🔥 Here are yesterday's results:
👑 4/6: <@598287781235785730> <@606265025509720066>
5/6: <@287842837603549187> <@275352516504453120> <@631913619264765963> <@336678214631948288> <@703017808342024282>
6/6: <@651108371763691597>
X/6: <@619363697269145600>

Parsing details: be very lenient/flexible in the parsing. Be aware that multiple users may have the same score. A score of "x/6", as shown in the last example, indicates failure to complete the puzzle. a failed game will simply result in a loss tally for that user, and should not affect avg score calculation

I can help you find user aliases if needed. 


## Planned features
- TBD - user specific information retrieval command
- SOON - Earliest posts
- SOON - time spent pondering
- TBD -starter word scores

## todo



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
it needs permission to sense message content intent(read messages) and member intent (see member data, such as display name)
it also needs these permissions: send message, read message. use slash commands.

invite the bot.
I generated the invite link through the oauth2 tab becasuse i couldn't get the permissions to stick via the bot tab



## Running
add it to your server. 

run it via python src/main.py

(commands?)


## deploy