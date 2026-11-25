# 30-second version (reference)

I built flowguard, an educational fault detector for a water-pump testbed, as a service. The model is
deliberately simple: one sensor's distance from its own start-up level, chosen because nothing more
complex was shown to be better. Most of the work went into honest evaluation - by experiment, with
intervals, against a clock baseline that exposed the benchmark - and into the service around it:
parity-tested inference, an API, a container, monitoring and rollback.
