#!/usr/bin/env bash
# Run 8 on a fresh Lambda A10 (CLOUD_RUN.md, RUN8_DESIGN.md). Run on the instance inside tmux:
#   bash ~/selection-curse/cloud/run8_remote.sh BUILD_DEADLINE_EPOCH FINAL_DEADLINE_EPOCH [WORKERS]
# after the laptop has unpacked the working tree to ~/selection-curse (with data/finqa/dev.json).
# The bank starts no harness it cannot finish by BUILD_DEADLINE; the verdict regrade starts
# nothing it cannot finish by FINAL_DEADLINE. Set that well before the ledger's cap.
# Idempotent: proposals, episodes and grades are cached, so a rerun resumes.
#
# Two Ollama servers share the GPU and the model store. The main one (student and judge, W
# slots) is run 7's. The 32B proposer gets its own with one slot: with W slots its context
# would not fit on 24 GB. The proposer runs only while the main server's models are unloaded,
# and is unloaded before the student runs again, so the student is never partly on the CPU.
set -euo pipefail
BUILD_DEADLINE=$1; FINAL_DEADLINE=$2; W=${3:-8}
OLLAMA_VERSION=0.40.13          # same as runs 4 to 7
PORT=11435; PPORT=11436         # frozen_v8.yaml points at these ports
STUDENT=qwen2.5:7b-instruct; JUDGE=llama3.1:8b; PROPOSER=qwen2.5:32b-instruct
cd ~/selection-curse
OUT=runs_v8; mkdir -p $OUT/logs; L=$OUT/logs
export OLLAMA_MODELS=$HOME/ollama_v8/models

[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=$OLLAMA_VERSION sh
ollama --version | tee $L/ollama_version.txt

serve() {  # serve PORT SLOTS LOGFILE
  curl -fsS http://127.0.0.1:$1/api/version >/dev/null 2>&1 && return 0
  OLLAMA_HOST=127.0.0.1:$1 OLLAMA_NUM_PARALLEL=$2 OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_FLASH_ATTENTION=1 setsid nohup ollama serve > $3 2>&1 < /dev/null &
  for i in $(seq 30); do curl -fsS http://127.0.0.1:$1/api/version >/dev/null 2>&1 && return 0; sleep 2; done
  return 1
}
on() { OLLAMA_HOST=127.0.0.1:$1 ollama "${@:2}"; }
gpu_used() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
wait_gpu_free() {  # the next model must load onto an empty GPU
  for i in $(seq 60); do [ "$(gpu_used)" -lt 1500 ] && return 0; sleep 2; done
  echo "GPU not free: $(gpu_used) MiB" | tee -a $OUT/progress.log; return 1
}
propose() {  # propose ROUND: main models off the GPU, proposer on, then proposer off again
  on $PORT stop $STUDENT || true; on $PORT stop $JUDGE || true
  wait_gpu_free
  $PY -m rsi.run8 propose --round $1 > $L/propose$1.log 2>&1
  on $PPORT ps | tee $L/proposer_ps$1.txt       # must show 100% GPU
  on $PPORT stop $PROPOSER || true
  wait_gpu_free
  sha256sum $OUT/proposals_*.json | tee -a $OUT/progress.log
  echo "propose $1 done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
}

serve $PORT $W $L/ollama_serve.log
serve $PPORT 1 $L/ollama_serve_proposer.log
on $PORT pull $STUDENT > $L/pull_student.log 2>&1 &
PULL=$!
on $PORT pull $JUDGE > $L/pull_judge.log 2>&1
wait $PULL                               # only the pull: a bare wait would also wait on the servers
on $PORT pull $PROPOSER > $L/pull_proposer.log 2>&1
on $PORT list | tee $L/models.txt        # digests, for the write-up

PY=.venv/bin/python
$PY -m pytest -q tests/test_run6.py tests/test_run7.py tests/test_run8.py | tee $L/pytest.log
echo "setup done $(date -u +%FT%TZ)" | tee $OUT/progress.log

$PY -m rsi.run8 traces --workers $W > $L/traces.log 2>&1
echo "traces done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
propose 1
$PY -m rsi.run8 build --groups baseline,check,s4a --workers $W --deadline $BUILD_DEADLINE > $L/build_a.log 2>&1
echo "build a done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
propose 2
$PY -m rsi.run8 build --workers $W --deadline $BUILD_DEADLINE > $L/build.log 2>&1
echo "build done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
on $PORT ps | tee $L/ollama_ps.txt
$PY -m rsi.run8 verdict --workers $W --deadline $FINAL_DEADLINE > $L/verdict.log 2>&1
echo "verdict done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
echo "run8 done $(date -u +%FT%TZ)" | tee $OUT/DONE
