# Mutant: any field change is breaking

Treats every added or removed field as breaking, in requests and responses alike. It catches all the
real breaks, but also flags new optional request fields and new response fields, which old clients
never notice. A checker that cries wolf on every additive change gets switched off, and then it
protects nobody. Requests and responses are asymmetric; the rules must be too.
