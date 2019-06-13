# Global Ban COG

This cog allows users to easily ban and unban people from selected servers all at once. It is designed to reduce the time it takes to manually ban a user from more than one server... especially when dealing with 10-50 servers.

This cog also makes sure that a user meant to be banned, stays banned, until unbanned. On larger servers, making sure that everyone banned stays banned is quite difficult. This makes it easy for staff to unban someone without the admins noticing. However, with this cog, the bot would automatically re-sync all the global bans every day, week, or month and 12 PM.
## Installation

[Git](https://git-scm.com/downloads) is required to install the cog files.

```python
1. cd .../Red-DiscordBot/cogs/CogManager/cogs/ # Go to the directory that has Redbot installed.

2. git install https://github.com/dajkatal/globalban.git

3. Start Redbot

4. [p]load globalban

5. Done
```

## Commands

```python
- [p]globalban <name> or <name+discrim> or <mention> or <ID> # Bans a user from all connected servers.

- [p]globalunban <ID> # Unbans a user from all connected servers.

- [p]globalbans # Gives all the people who are banned.

- [p]bansync # Syncs all global bans across all servers.

- [p]syncedservers # Shows all the synced servers.

- [p]sync # Adds a server to the synced list if it is not already there and re-syncs all the global bans.

- [p]delsync # Removes a server from the synced server list.
```

## Installing Redbot
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install Redbot.

```bash
pip install Red-DiscordBot
```

## Difficulties
```
+ Missing some of the possible edge cases.
+ Finding the most optimal way of storing the data collected.
```

## What I learnt
```
+ How to work with discord.py rewrite and redbot.
+ How to find the possible edge cases given a situation.
+ How to optimize and reformat code to make it faster and more efficient.
``` 

## License
[MIT](https://choosealicense.com/licenses/mit/)
