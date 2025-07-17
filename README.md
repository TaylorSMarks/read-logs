# read-logs

Requires python 3.9 or newer.

Install it like this:

    python3 -m pip install https://github.com/TaylorSMarks/read-logs/archive/main.zip

Run it like this:

    python3 -m readLogs

If you want to make it easier to invoke, add an `alias` to your `.zprofile` like this (later examples assume you have this):

    alias readLogs="python3 -m readLogs"

With the above `alias` setup you can now just run it with:

    readLogs

If you want to filter the logs that are showing up, use `grep --line-buffered`, ie,

    readLogs | grep --line-buffered cd26df97-90b4-49df-b16f-61c7f9543b94 | readLogs

> **NOTE** - `readLogs` actually does two things:
> 1. If it's at the start of the pipeline, it'll automatically select from your running `docker` containers and pick whichever one is outputting the most lines of json looking logs then pipe that to the next process, 
>
> 2. If it's at the end of the pipeline, it'll take what it receieves and parse it into the gui for presentation to you.
>
> If it's the only thing you're running, it'll do both.
>
> **NOTE** - It follows the docker container's logs. By default, `grep` will buffer what it receives and only send once every 4096 bytes or when the end of stream is reached. `readLogs` won't ever send an end of stream though, so if you don't use `grep` in `--line-buffered` mode, there's a chance you won't see all (or any) of the lines you expect.

Although it's intended mostly for use with following docker container logs, you can read from a file or something instead, ie:

    cat out.log | readLogs

    wget https://example.com/my-remote-logs.log | readLogs

    docker logs a03a343b2c6e --follow | readLogs
