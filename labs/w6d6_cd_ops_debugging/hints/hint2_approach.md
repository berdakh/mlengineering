# w6d6 hint 2: the approach

**`load_settings(env)`**
1. `unknown = sorted(k for k in env if k.startswith(PREFIX) and k not in KNOWN)`; raise if any.
2. A helper `_required(env, name)` that strips the value and raises `SettingsError(f"{name} is required ...")`.
3. Check each required value: environment in `ENVIRONMENTS`; model dir starts with `/`; release matches
   `^[0-9a-f]{7,40}$`.
4. Optional values with defaults: log level (`.upper()`, must be in `LOG_LEVELS`), port (`int(...)` inside
   `try`, then range 1-65535). Every message starts with the variable's name.

**`select_rollback_target(history, env)`**
1. Filter to the environment, sort by `deployed_at`. Empty: raise `RollbackError`.
2. `current = entries[-1]`.
3. Walk the earlier entries from newest to oldest; return the first with status `good` and a digest
   different from `current["digest"]`.
4. None found: raise `RollbackError` with a message that suggests checking the configuration.

**`image_reference(entry)`**: check `entry["digest"].startswith("sha256:")`, return `f"{image}@{digest}"`.

**The incidents.** For each: run `status` and `history production` first and write down what changed and
when. Then read the production log without access lines. Then, if the container is not running,
`docker inspect` its state. Then decide: if the current deployment's digest differs from the last good
one, the image changed; if the digest is the same, something outside the image changed (`git diff -- ops/env`).
