# wrong_model_dir
Plausible mistake: FLOWGUARD_MODEL_DIR points at the models root instead of the bundle directory. The image builds and the container starts, but the model never loads: /readyz is 503 forever (measured: "model not loaded: /app/models: checksums.json missing"). Expected to fail: test_the_image_layout_finds_the_app_and_the_model.
