#!/usr/bin/env bash
set -euo pipefail

# Startup script for CryptoCortex Backend container
# - Optionally downloads the BERT model into ./chatbot/bert_squad_model when BERT_MODEL_URL is set
# - Then execs the Gunicorn server (or whatever CMD is specified)

MODEL_DIR="./chatbot/bert_squad_model"
# Default model id to download when BERT_MODEL_URL is not provided
DEFAULT_BERT_MODEL="bert-large-uncased-whole-word-masking-finetuned-squad"

if [ -z "${BERT_MODEL_URL-}" ]; then
  echo "BERT_MODEL_URL not set — defaulting to ${DEFAULT_BERT_MODEL}"
  BERT_MODEL_URL="${DEFAULT_BERT_MODEL}"
fi

echo "Ensuring BERT model is present in $MODEL_DIR (source: $BERT_MODEL_URL)"
if [ ! -d "$MODEL_DIR" ] || [ -z "$(ls -A "$MODEL_DIR")" ]; then
  echo "Model directory missing or empty — downloading model from $BERT_MODEL_URL"
  python ./scripts/download_bert_model.py "$BERT_MODEL_URL" "$MODEL_DIR"
else
  echo "Model already present — skipping download"
fi

# Exec the CMD provided to the container (e.g., gunicorn)
echo "Starting application..."
exec "$@"
