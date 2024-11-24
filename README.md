My bot for the [Software Challenge Germany](https://software-challenge.de/) 2024.

I placed second in the tournament with the code logic2.py (builded in the latest build slowspeed 2.0.0)
Additionally, I had a local webserver running, where the logic2.py connected via UDP and send calculated match data to.
It had a webinterface where I watched my selfmade game replays, which were packed with field and debug infos, with which the bot chose it's move.
I created that application because my own map data per turn was multiple kilobytes in size and not practical to read in terminal.
I'll publish that code soon in another repo, because it was only developed locally on the server.

Today (22.11.2024), around 5 months after the Finals I set this repo to public.

~ quack


build command:

python logic.py --build -d botname -a manylinux2014_x86_64
