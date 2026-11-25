# c_gitignore_style
Plausible mistake: a .gitignore-style file. Docker anchors patterns at the context root, so the nested experiments/*/sweep_*/runs/ checkpoints (about 200 MB), src/flowguard/__pycache__ and notebooks/.ipynb_checkpoints are still sent. Expected to fail: test_c_context_is_small and test_c_excludes for the nested paths.
