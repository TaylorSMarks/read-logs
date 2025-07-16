# read-logs

Requires python 3.9 or newer.

Install it like this:

    python3 -m pip install https://github.com/TaylorSMarks/read-logs/archive/main.zip

Run it like this:

    docker logs a03a343b2c6e --follow | python3 -m readLogs

If you want to filter the logs that are showing up, use grep, ie,

    docker logs a03a343b2c6e --follow | grep cd26df97-90b4-49df-b16f-61c7f9543b94 | python3 -m readLogs
