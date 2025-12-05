import os
from transformers import AutoTokenizer, AutoModelForQuestionAnswering


def main():
	model_name = os.getenv("BERT_MODEL_URL", "distilbert-base-uncased-distilled-squad")
	print(f"Downloading model: {model_name}")

	try:
		tokenizer = AutoTokenizer.from_pretrained(model_name)
		model = AutoModelForQuestionAnswering.from_pretrained(model_name)
	except Exception as e:
		print("Error downloading or loading the model:", e)
		print("Tips: 1) Ensure `BERT_MODEL_URL` points to a QA-finetuned HF model."
			  " 2) Use a model compatible with AutoModelForQuestionAnswering,"
			  " or set `BERT_MODEL_URL` to `distilbert-base-uncased-distilled-squad`.")
		raise

	out_dir = os.path.abspath("./bert_squad_model")
	print(f"Saving tokenizer and model to: {out_dir}")
	tokenizer.save_pretrained(out_dir)
	model.save_pretrained(out_dir)
	print("Save complete")


if __name__ == '__main__':
	main()
