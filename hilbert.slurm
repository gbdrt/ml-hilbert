#!/bin/bash -l

#SBATCH --job-name=hilbert
#SBATCH --output slurm_Logs/%x_%j_hilbert.out
#SBATCH --error slurm_Logs/%x_%j_hilbert.err
#SBATCH -D ./

#SBATCH --nodes=1
#SBATCH --ntasks=1                   # 1 task par nodes
#SBATCH --ntasks-per-node=1           # Each task will see all GPUs of the node
#SBATCH --cpus-per-task=96
#SBATCH --gres=gpu:4
#SBATCH --time=02:00:00
#SBATCH --hint=nomultithread          # no hyperthreading
#SBATCH --constraint=h100             # h100 gpus
#SBATCH --account=mnn@h100            # account
#SBATCH --qos=qos_gpu_h100-dev

# Create logs directory if it doesn't exist
mkdir -p logs

# Load vLLM model 1: openai/gpt-oss-120b on port 8000
echo "Starting vLLM server for openai/gpt-oss-120b on port 8000..."
python -m vllm.entrypoints.openai.api_server \
    --model openai/gpt-oss-120b \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 2 \
    > logs/vllm_8000_${SLURM_JOB_ID}.log 2>&1 &
VLLM_PID_1=$!

# Load vLLM model 2: Goedel-LM/Goedel-Prover-V2-32B on port 10002
echo "Starting vLLM server for Goedel-LM/Goedel-Prover-V2-32B on port 10002..."
python -m vllm.entrypoints.openai.api_server \
    --model Goedel-LM/Goedel-Prover-V2-32B \
    --host 0.0.0.0 \
    --port 10002 \
    --tensor-parallel-size 2 \
    --max-model-len 16384 \
    > logs/vllm_10002_${SLURM_JOB_ID}.log 2>&1 &
VLLM_PID_2=$!

# Wait for both vLLM servers to be ready
echo "Waiting for vLLM servers to be ready..."
sleep 60

# Check if servers are responsive
until curl -s http://0.0.0.0:8000/v1/models > /dev/null; do
    echo "Waiting for vLLM server on port 8000..."
    sleep 10
done
echo "vLLM server on port 8000 is ready"

until curl -s http://0.0.0.0:10002/v1/models > /dev/null; do
    echo "Waiting for vLLM server on port 10002..."
    sleep 10
done
echo "vLLM server on port 10002 is ready"

# Run the main application
echo "Starting main application..."
OPENAI_API_KEY='empty' python -m src.run data=sample_dataset

# Cleanup: kill vLLM servers
echo "Cleaning up vLLM servers..."
kill $VLLM_PID_1 $VLLM_PID_2

echo "Job completed"
