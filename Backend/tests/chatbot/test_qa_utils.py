import importlib
import sys
import types
from types import SimpleNamespace


def _import_qa_with_mocks(monkeypatch):
    # Create a fake transformers module
    fake_transformers = types.SimpleNamespace()

    class FakeTensor:
        def __init__(self, values):
            self.values = values
        def __iter__(self):
            return iter(self.values)
        def __getitem__(self, idx):
            return self.values[idx]

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, path):
            inst = cls()
            def encode_plus(question, context, return_tensors, truncation, max_length):
                # return a mapping where each value has a .to(device) method
                class T:
                    def __init__(self, data):
                        self._data = data
                    def to(self, device):
                        return self
                    def __getitem__(self, i):
                        return self._data[i]
                return {"input_ids": T([101, 102, 103, 104])}
            inst.encode_plus = encode_plus
            inst.convert_ids_to_tokens = lambda ids: ['[CLS]', 'The', 'answer', 'is']
            # Return the full token sequence joined (do not drop the first token)
            inst.convert_tokens_to_string = lambda tokens: ' '.join(tokens)
            return inst

    class FakeModel:
        @classmethod
        def from_pretrained(cls, path):
            # return an instance of FakeModel which is callable via its class __call__
            inst = cls()
            # Provide .to() and .eval() used at module import time
            inst.to = lambda device: inst
            inst.eval = lambda: None
            return inst

        def __call__(self, **inputs):
            # return an object with start_logits and end_logits that are iterable
            return SimpleNamespace(start_logits=[0, 0, 10, 0], end_logits=[0, 0, 0, 10])

    fake_transformers.BertTokenizer = FakeTokenizer
    fake_transformers.BertForQuestionAnswering = FakeModel

    monkeypatch.setitem(sys.modules, 'transformers', fake_transformers)

    # Create a fake torch module
    fake_torch = types.SimpleNamespace()

    def device(expr):
        return 'cpu'
    fake_torch.device = device

    # Provide a simple `cuda` namespace with `is_available()` to match calls
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)

    class NoGrad:
        def __enter__(self):
            return None
        def __exit__(self, exc_type, exc, tb):
            return False
    fake_torch.no_grad = lambda : NoGrad()

    def argmax(seq, dim=None):
        # seq is an iterable (list); return object that has .item()
        idx = list(seq).index(max(seq))
        return SimpleNamespace(item=lambda: idx)
    fake_torch.argmax = argmax

    monkeypatch.setitem(sys.modules, 'torch', fake_torch)

    # Now import (or reload) the target module which uses transformers and torch at import time
    if 'chatbot.qa_utils' in sys.modules:
        importlib.reload(sys.modules['chatbot.qa_utils'])
    else:
        importlib.import_module('chatbot.qa_utils')
    return importlib.import_module('chatbot.qa_utils')


def test_question_answer_returns_expected_answer(monkeypatch):
    qa = _import_qa_with_mocks(monkeypatch)

    answer = qa.question_answer('What is the answer?', 'The answer is 42')
    # our fake tokenizer converts tokens[1:] into the string 'The answer is'
    assert isinstance(answer, str)
    assert 'answer' in answer
