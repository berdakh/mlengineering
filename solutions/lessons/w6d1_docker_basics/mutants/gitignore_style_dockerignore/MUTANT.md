# gitignore_style_dockerignore
Plausible mistake: a .dockerignore written like a .gitignore. Patterns without **/ match only at the context root, so src/flowguard/__pycache__ and scripts/__pycache__ are still sent. Expected to fail: test_excluded for the nested __pycache__ paths.
