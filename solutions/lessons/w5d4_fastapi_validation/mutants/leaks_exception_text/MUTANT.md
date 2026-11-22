# Mutant: leaks_exception_text

Puts `str(exc)` into the 500 response 'to help debugging'. Exception messages contain paths,
hostnames, SQL, sometimes credentials; the client cannot act on them, an attacker can.
