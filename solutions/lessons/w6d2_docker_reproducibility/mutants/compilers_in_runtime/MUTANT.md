# compilers_in_runtime
Plausible mistake: installing build-essential in the runtime stage "in case a package needs compiling". It adds hundreds of MB and a compiler to the attack surface of the serving image. Expected to fail: test_the_runtime_stage_does_not_resolve_or_compile_anything.
