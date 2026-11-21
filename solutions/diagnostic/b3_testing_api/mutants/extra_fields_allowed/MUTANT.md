Correct field constraints, but unknown fields are silently ignored (pydantic's default). A client that misspells `avg_session_min` gets a prediction computed without it and no error.
