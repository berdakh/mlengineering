# Mutant: public_by_default

Opens port 8000 to 0.0.0.0/0 when no CIDR is given ('so I can test it') and accepts any CIDR without
`allow_public`. An unauthenticated prediction API on the internet is found by scanners within hours.
