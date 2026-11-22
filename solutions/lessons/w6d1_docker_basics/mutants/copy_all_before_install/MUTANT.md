# copy_all_before_install
Plausible mistake: `COPY . .` before `pip install`, the most common first Dockerfile. Any code edit invalidates the dependency layer (measured: 20-21 s rebuilds instead of ~2 s). Expected to fail: test_dependencies_are_installed_before_the_code_is_copied.
