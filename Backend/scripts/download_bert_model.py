import sys
from pathlib import Path

def download_model(src: str, dest: str):
    """
    Download a Hugging Face-style model using transformers and save it to dest.
    src can be a Hugging Face model id (e.g. 'bert-large-uncased-whole-word-masking-finetuned-squad')
    or a local/remote path supported by `from_pretrained`.
    """
    try:
        from transformers import BertTokenizer, BertForQuestionAnswering
    except Exception as e:
        print("transformers not available:", e)
        raise

    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading tokenizer from {src} to {dest}")
    tokenizer = BertTokenizer.from_pretrained(src)
    tokenizer.save_pretrained(dest)

    print(f"Downloading model from {src} to {dest}")
    model = BertForQuestionAnswering.from_pretrained(src)
    model.save_pretrained(dest)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: download_bert_model.py <model-id-or-path> <dest-dir>")
        sys.exit(2)
    src = sys.argv[1]
    dest = sys.argv[2]
    download_model(src, dest)
