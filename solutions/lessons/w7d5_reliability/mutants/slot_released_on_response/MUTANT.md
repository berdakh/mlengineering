# Mutant: slot_released_on_response

The bulkhead slot is freed when the HTTP answer is sent, not when the model call ends. After a deadline answer the slow call is still running, so more calls run than `max_inflight` allows: the bulkhead leaks under exactly the slow-dependency failure it exists for. (This variant also forgets to release on errors.)
