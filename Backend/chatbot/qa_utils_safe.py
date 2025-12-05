import os
import traceback
from typing import Optional

try:
    import torch
except Exception:
    torch = None

from transformers import AutoTokenizer, AutoModelForQuestionAnswering


# Configuration: local directory or HF name from env
LOCAL_MODEL_DIR = os.environ.get("LOCAL_BERT_MODEL_DIR", "./chatbot/bert_squad_model")
HF_MODEL_NAME = os.environ.get("BERT_MODEL_URL")

# Globals (initialized lazily)
tokenizer: Optional[object] = None
model = None
device = None
_model_loaded = False


def _load_model():
    global tokenizer, model, device, _model_loaded

    if _model_loaded:
        return

    # Determine candidate sources: local dir first, then HF name if provided, then a safe default
    candidates = [LOCAL_MODEL_DIR]
    if HF_MODEL_NAME:
        candidates.append(HF_MODEL_NAME)
    candidates.append("distilbert-base-uncased-distilled-squad")

    last_exc = None
    for candidate in candidates:
        try:
            print(f"qa_utils_safe: trying to load QA model from '{candidate}'")
            tokenizer = AutoTokenizer.from_pretrained(candidate)
            model = AutoModelForQuestionAnswering.from_pretrained(candidate)

            if torch is not None:
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                model = model.to(device)
            else:
                device = None

            model.eval()
            _model_loaded = True
            print(f"qa_utils_safe: loaded model from '{candidate}'")
            return
        except Exception as e:
            last_exc = e
            print(f"qa_utils_safe: failed to load '{candidate}': {e}")
            traceback.print_exc()

    # If we get here, all candidates failed
    _model_loaded = False
    print("qa_utils_safe: ERROR - could not load any QA model. See errors above.")
    if last_exc:
        raise last_exc


def question_answer(question: str, context: str) -> str:
    """Return an answer span for question/context. This will attempt to lazy-load the model
    on first call. If loading fails an informative exception is raised."""
    if not _model_loaded:
        _load_model()

    if not _model_loaded:
        raise RuntimeError("QA model not available")

    # Tokenize and move tensors to device if available
    inputs = tokenizer.encode_plus(question, context, return_tensors="pt", truncation=True, max_length=512)
    if device is not None and torch is not None:
        inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        start_scores = outputs.start_logits
        end_scores = outputs.end_logits

    import torch as _torch

    start_idx = int(_torch.argmax(start_scores, dim=1).item())
    end_idx = int(_torch.argmax(end_scores, dim=1).item())

    all_tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    answer_tokens = all_tokens[start_idx : end_idx + 1]
    answer = tokenizer.convert_tokens_to_string(answer_tokens)

    return answer
