#!/usr/bin/env bash
# Run 9 on a fresh Lambda A10 (CLOUD_RUN.md, RUN9_DESIGN.md). Run on the instance inside tmux:
#   bash ~/selection-curse/cloud/run9_remote.sh LOOP_DEADLINE_EPOCH [WORKERS]
# after the laptop has unpacked the working tree to ~/selection-curse.
# A round of the loops that cannot finish by LOOP_DEADLINE is not started, and the loops then
# stop there for every arm at once. Final scoring always runs, so LOOP_DEADLINE must leave
# room for it (about 5 hours on an A10) before the ledger's cap.
# Idempotent: proposals, episodes, grades and loop states are cached, so a rerun resumes.
#
# Two Ollama servers share the GPU and the model store, as in run 8: the main one (student
# and judge, W slots) and a one-slot server for the 32B proposer, which runs only while the
# main server's models are unloaded.
set -euo pipefail
LOOP_DEADLINE=$1; W=${2:-8}
OLLAMA_VERSION=0.40.13          # same as runs 4 to 8
PORT=11435; PPORT=11436         # frozen_v9.yaml points at these ports
STUDENT=qwen2.5:7b-instruct; JUDGE=llama3.1:8b; PROPOSER=qwen2.5:32b-instruct
TRAIN_URL=https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/train.json
cd ~/selection-curse
OUT=runs_v9; mkdir -p $OUT/logs data/finqa; L=$OUT/logs
export OLLAMA_MODELS=$HOME/ollama_v9/models

[ -f data/finqa/train.json ] || curl -fsSL -o data/finqa/train.json $TRAIN_URL   # run9 checks its sha256
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
  $PY -m rsi.run9 propose --round $1 > $L/propose_r$1.log 2>&1
  on $PPORT ps | tee $L/proposer_ps_r$1.txt      # must show 100% GPU
  on $PPORT stop $PROPOSER || true
  wait_gpu_free
  ls $OUT/prop_*_r$1.json >/dev/null 2>&1 && sha256sum $OUT/prop_*_r$1.json >> $OUT/progress.log
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
$PY -m pytest -q tests/test_run6.py tests/test_run7.py tests/test_run8.py tests/test_run9.py | tee $L/pytest.log
echo "setup done $(date -u +%FT%TZ)" | tee $OUT/progress.log

$PY -m rsi.run9 baseline --workers $W > $L/baseline.log 2>&1
echo "baseline done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
ROUNDS=$($PY -c "import yaml; print(yaml.safe_load(open('frozen_v9.yaml'))['loop']['rounds'])")
for R in $(seq $ROUNDS); do
  [ -f $OUT/rounds_cut.json ] && break
  propose $R
  $PY -m rsi.run9 build --round $R --workers $W --deadline $LOOP_DEADLINE > $L/build_r$R.log 2>&1
  echo "build $R done $(date -u +%FT%TZ) $(cat $OUT/timing.json | tr -d '\n ')" | tee -a $OUT/progress.log
done
on $PORT ps | tee $L/ollama_ps.txt
$PY -m rsi.run9 final --workers $W > $L/final.log 2>&1
echo "final done $(date -u +%FT%TZ)" | tee -a $OUT/progress.log
echo "run9 done $(date -u +%FT%TZ)" | tee $OUT/DONE
