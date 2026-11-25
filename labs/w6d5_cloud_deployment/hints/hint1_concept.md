# w6d5 hint 1: the concept

* The deploy script is **a plan you can read**. Think of it as the experiment protocol you would get a
  colleague to check before an expensive session: every step written out, in order, with the actual
  values, before anything runs. `--live` then executes that same text, nothing else.
* Order follows dependencies **and cost**: confirm who you are, then put the budget in place, then
  create things that can bill. A service needs its task definition; the task definition needs the role
  and the log group; the image must be pushed before the service starts it.
* Teardown is the deploy in reverse dependency order, not in reverse line order: a cluster cannot be
  deleted while a service is in it; a role cannot be deleted while a policy is attached; a security
  group cannot be deleted while a task's network interface uses it.
* "Not public" is a property of the **security group**, not of the IP address: a task can have a public
  IP and still accept no connection at all.
* A gate that can be passed without reading anything is not a gate: the flag says "I mean it", the
  sign-off says "I read the briefing and accept the cost".
