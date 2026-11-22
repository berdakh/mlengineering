# Mutant: settings_accept_unknown_vars

Ignores FLOWGUARD_* variables it does not know. A typo such as FLOWGUARD_MODEL_DlR is then silently
ignored and the default model directory is used: the service is ready and serves the wrong model.
