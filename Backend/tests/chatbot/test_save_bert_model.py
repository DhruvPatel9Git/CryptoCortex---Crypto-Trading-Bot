import importlib
import sys
import types


def test_save_bert_model_invokes_save_pretrained(monkeypatch):
    fake_transformers = types.SimpleNamespace()
    fake_transformers.saved_paths = []

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, name):
            inst = cls()
            def save_pretrained(path):
                fake_transformers.saved_paths.append(('tokenizer', path))
            inst.save_pretrained = save_pretrained
            return inst

    class FakeModel:
        @classmethod
        def from_pretrained(cls, name):
            inst = cls()
            def save_pretrained(path):
                fake_transformers.saved_paths.append(('model', path))
            inst.save_pretrained = save_pretrained
            return inst

    fake_transformers.BertTokenizer = FakeTokenizer
    fake_transformers.BertForQuestionAnswering = FakeModel

    monkeypatch.setitem(sys.modules, 'transformers', fake_transformers)

    # Import the module under test (it will call save_pretrained at import time)
    if 'chatbot.save_bert_model' in sys.modules:
        importlib.reload(sys.modules['chatbot.save_bert_model'])
    else:
        importlib.import_module('chatbot.save_bert_model')

    # Assert that save_pretrained was called twice (tokenizer and model)
    assert ('tokenizer', './bert_squad_model') in fake_transformers.saved_paths
    assert ('model', './bert_squad_model') in fake_transformers.saved_paths
