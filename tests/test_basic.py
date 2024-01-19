import json


def test_welcome(make_request):
    fulfill = make_request("Default Welcome Intent")
    assert "Welcome to the" in fulfill["text"]


def test_fallback(make_request, fallback_responses):
    fulfill = make_request("Default Fallback Intent")
    assert fulfill["text"] in fallback_responses


def test_prompt_end(make_request):
    fulfill = make_request("Prompt-End")
    assert "anything else" in fulfill["text"].lower()


def test_end_conv(make_request):
    contexts = {'"FAQ-Prompt-End-followup': {}}
    fulfill = make_request("Prompt-End-End")
    assert "Thanks for chatting" in fulfill["text"]
