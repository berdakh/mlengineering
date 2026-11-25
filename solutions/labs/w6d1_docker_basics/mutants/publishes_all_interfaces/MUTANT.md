# publishes_all_interfaces
Plausible mistake: `-p 8000:8000` in the run script. Docker then listens on every host interface, and its own iptables rules bypass ufw (Docker's install documentation warns about this). Expected to fail: test_script_publishes_on_loopback_only.
