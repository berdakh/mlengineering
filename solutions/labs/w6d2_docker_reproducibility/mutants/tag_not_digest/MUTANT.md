# tag_not_digest
Plausible mistake: a careful multi-stage build whose base is still the moving tag python:3.12-slim. The next Debian or Python patch release changes the image without any change to the Dockerfile. Expected to fail: test_every_external_base_image_is_pinned_by_digest.
