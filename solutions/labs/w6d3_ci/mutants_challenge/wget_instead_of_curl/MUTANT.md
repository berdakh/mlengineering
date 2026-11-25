# Mutant: curl swapped for wget inside the container
python:3.12-slim has no wget either; the job fails with exit code 127 again.
Caught by: test_image_check_does_not_need_tools_the_image_lacks.
