# syntax=docker/dockerfile:1
# flowguard prediction API - YOUR Dockerfile (w6d1 guided lab).
#
# Write the instructions below, in this order of concerns (the lesson, section 4, walks through it):
#   1. a base image with an explicit Python 3.12 tag (not "latest")
#   2. ENV settings: no .pyc files, unbuffered output, no pip cache
#   3. WORKDIR /app
#   4. dependencies FIRST: copy only requirements.txt, then pip install it (no cache)
#   5. code and model LAST: copy src/ and models/
#   6. an unprivileged user, and USER to switch to it
#   7. ENV for PYTHONPATH and FLOWGUARD_MODEL_DIR (where the model is inside the image)
#   8. EXPOSE 8000
#   9. HEALTHCHECK that asks /readyz (the slim image has no curl)
#  10. CMD in exec form: uvicorn with the app factory, listening on 0.0.0.0:8000
#
# Check your work:   python wb.py check w6d1
