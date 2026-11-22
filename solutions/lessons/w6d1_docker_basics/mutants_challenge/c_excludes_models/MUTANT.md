# c_excludes_models
Plausible mistake: an allow-list that forgets the model directory. The context is tiny and the build succeeds, but the image has no model: /readyz answers 503 forever. Expected to fail: test_c_image_still_gets_what_it_needs.
