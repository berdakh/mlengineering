# Mutant: extra_fields_ignored

Pydantic's default is `extra="ignore"`: unknown fields are silently dropped. A client that
misspells `flow_rate` as `flowrate` gets a 422 for the missing field, but a client that sends an
extra field it believes is used (`rpm`) gets a 200 and wrong assumptions.
