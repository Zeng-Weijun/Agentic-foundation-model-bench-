Agent-not-converged proofs for the two special tasks (both adjudicated FALSE, counted in denom=89):
- mailman.*: agent left postfix/mailman3 non-functional (post-agent pane: ConnectionRefused [Errno 111] on SMTP :25);
  the task test hung and hit the 7200s test-timeout (tb-native is_resolved=null, failure_mode=test_timeout).
- tune-mjcf.*: agent stuck at 'Time pctg ~100%% (need 60.00%%)', Speedup 1.00x, never met the 60%% threshold;
  container was a live zombie (docker id 3bdb9767) killed at 2026-07-12T20:26Z so terminus could finalize
  (tb-native is_resolved=null, failure_mode=unknown_agent_error). container_inspect + live_probe captured before kill.
Serving was healthy throughout (terminal_bench.log: 0 RateLimit/429/5xx/connection errors).
