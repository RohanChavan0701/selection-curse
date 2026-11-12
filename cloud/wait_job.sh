#!/usr/bin/env bash
# Wait on the local machine until a remote run finishes, then print its final state.
#
#   bash cloud/wait_job.sh IP RUN_DIR TMUX_SESSION [INTERVAL_S] [MAX_SSH_FAILURES]
#   e.g. bash cloud/wait_job.sh 1.2.3.4 runs_v9 run9
#
# Polls every INTERVAL_S seconds (default 300) for RUN_DIR/DONE or for the tmux session to be
# gone. An SSH failure is retried, not treated as the end of the job: the waiter gives up only
# after MAX_SSH_FAILURES failures in a row (default 24, two hours at the default interval).
# Run 9's waiter had no retry, died on one SSH error, and the finished job sat for 3.3 hours.
#
# Exit codes: 0 job wrote DONE; 3 tmux session gone without DONE; 4 instance unreachable.
set -u
IP=$1; RUN_DIR=$2; SESSION=$3; INTERVAL=${4:-300}; MAX_FAIL=${5:-24}
SSH="ssh -o ConnectTimeout=20 -o ServerAliveInterval=15 -o BatchMode=yes ubuntu@$IP"
fails=0
while true; do
  S=$($SSH "cd ~/selection-curse; if [ -f $RUN_DIR/DONE ]; then echo DONE; \
      elif ! tmux has-session -t $SESSION 2>/dev/null; then echo GONE; else echo RUN; fi" 2>/dev/null)
  case "$S" in
    DONE|GONE) break ;;
    RUN) fails=0 ;;
    *) fails=$((fails + 1))
       echo "$(date -u +%FT%TZ) ssh failed ($fails of $MAX_FAIL)" >&2
       if [ "$fails" -ge "$MAX_FAIL" ]; then echo "state UNREACHABLE"; exit 4; fi ;;
  esac
  sleep "$INTERVAL"
done
echo "state $S"
$SSH "cd ~/selection-curse; date -u; cat $RUN_DIR/progress.log; cat $RUN_DIR/final.json 2>/dev/null" || true
[ "$S" = DONE ] && exit 0 || exit 3
