# Legacy script for interview set 1, prompt P2. It "works on my machine". Do not fix it in place:
# write your refactored version in interview/work/set1/p2.py.
import datetime
import json

f = open("/var/log/pipeline/events.log")
lines = f.readlines()

counts = {}
last_error = None
last_error_ts = None
now = datetime.datetime.now()
for l in lines:
    try:
        parts = l.strip().split(" ", 2)
        ts = datetime.datetime.fromisoformat(parts[0])
        level = parts[1]
        msg = parts[2]
    except Exception:
        continue
    if (now - ts).days < 1:
        if level not in counts:
            counts[level] = 0
        counts[level] = counts[level] + 1
        if level == "ERROR":
            if last_error_ts is None or ts > last_error_ts:
                last_error = msg
                last_error_ts = ts

print(json.dumps({"counts": counts, "last_error": last_error}))
