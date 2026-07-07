#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="auto"
ENV_NAME="${ENV_NAME:-vlm-semobs}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

usage() {
  cat <<EOF
Usage:
  bash scripts/setup_env.sh [options]

Options:
  --backend auto|conda|venv  Environment backend. Default: auto
  --name NAME                Conda environment name. Default: $ENV_NAME
  --python VERSION           Python version for new env. Default: $PYTHON_VERSION
  -h, --help                 Show this help

Examples:
  bash scripts/setup_env.sh
  bash scripts/setup_env.sh --backend conda --name vlm-semobs --python 3.10
  bash scripts/setup_env.sh --backend venv
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend)
      BACKEND="$2"
      shift 2
      ;;
    --name)
      ENV_NAME="$2"
      shift 2
      ;;
    --python)
      PYTHON_VERSION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

cd "$ROOT_DIR"

ensure_env_file() {
  if [[ ! -f ".env" && -f ".env.example" ]]; then
    cp .env.example .env
    echo "Created .env from .env.example. Please edit API_KEY, BASE_URL, and MODEL_NAME before running VLM calls."
  fi
}

setup_conda() {
  if ! command -v conda >/dev/null 2>&1; then
    echo "conda was not found. Install Miniforge first, or run with --backend venv."
    exit 1
  fi

  local conda_base
  conda_base="$(conda info --base)"
  # shellcheck source=/dev/null
  source "$conda_base/etc/profile.d/conda.sh"

  if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Conda environment '$ENV_NAME' already exists."
  else
    if command -v mamba >/dev/null 2>&1; then
      mamba create -y -n "$ENV_NAME" "python=$PYTHON_VERSION"
    else
      conda create -y -n "$ENV_NAME" "python=$PYTHON_VERSION"
    fi
  fi

  conda activate "$ENV_NAME"
  python -m pip install -r requirements.txt
  ensure_env_file

  echo
  echo "Environment is ready."
  echo "Next time, run:"
  echo "  conda activate $ENV_NAME"
  echo "  cd $ROOT_DIR"
}

setup_venv() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 was not found."
    exit 1
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR" || {
      echo
      echo "Failed to create venv. On Ubuntu/Debian, install python3-venv or use Miniforge/conda."
      exit 1
    }
  fi

  # shellcheck source=/dev/null
  source "$VENV_DIR/bin/activate"
  python -m pip install -r requirements.txt
  ensure_env_file

  echo
  echo "Environment is ready."
  echo "Next time, run:"
  echo "  cd $ROOT_DIR"
  echo "  source .venv/bin/activate"
}

case "$BACKEND" in
  auto)
    if command -v conda >/dev/null 2>&1; then
      setup_conda
    else
      setup_venv
    fi
    ;;
  conda)
    setup_conda
    ;;
  venv)
    setup_venv
    ;;
  *)
    echo "Invalid --backend value: $BACKEND"
    usage
    exit 1
    ;;
esac

echo
echo "After editing .env and adding images to data/images/, try:"
echo "  python scripts/run_vlm_api.py --area-hint 会议室"
