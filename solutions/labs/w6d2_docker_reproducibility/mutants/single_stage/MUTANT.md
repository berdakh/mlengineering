# single_stage
Plausible mistake: pinning the base by digest and installing the hashed lock, but in one stage. Reproducible, yet the dependency install happens where the server runs, and anything the build needs (pip, compilers, caches) stays in the runtime image. Expected to fail: test_there_is_a_builder_stage_and_a_runtime_stage.
