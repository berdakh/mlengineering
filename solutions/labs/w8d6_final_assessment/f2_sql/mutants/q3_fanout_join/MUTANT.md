q3 joins both child tables before aggregating. COUNT(DISTINCT) rescues the complaint count, but the fee sum is multiplied by the number of complaints (fan-out).
