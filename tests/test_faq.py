from src.assistant import ds
from random import choice, sample

ds_query = ds.query(kind="FAQ")
ALL_FAQS = list(ds_query.fetch())


def test_faq_start(make_request):
    fulfill = make_request("Community-FAQ")
    assert "select a category" in fulfill["text"]
    assert "faq-category-selection" in fulfill["contexts"]
    assert "listSelect" in fulfill["msgs"]
    assert "suggestions" in fulfill["msgs"]


def test_all_faq_questions(make_request):
    fulfill = make_request("Community-FAQ-All")
    assert "Select a question below" in fulfill["text"]
    assert "faq-selection" in fulfill["contexts"]
    assert "listSelect" in fulfill["msgs"]


def test_category_questions(make_request):
    for c in ["Building", "General", "Environment"]:
        fulfill = make_request("Community-FAQ-Category", {"faq_category": c})
        assert "Select a question below" in fulfill["text"]
        assert "faq-selection" in fulfill["contexts"]
        assert "listSelect" in fulfill["msgs"]


def test_faq_answer(make_request):
    sample_faqs = sample(ALL_FAQS, 10)

    for faq in sample_faqs:
        synonym = choice(faq["synonyms"])
        fulfill = make_request("FAQ", {"faq": synonym})
        assert faq["Speech"].replace("Plasir", "testing") == fulfill["text"].replace(
            "Plasir", "testing"
        )

        if faq.get("TextResponse") and faq.get("Web"):
            assert "basicCard" in fulfill["msgs"]
        if faq.get("Chips"):
            assert "suggestions" in fulfill["msgs"]


def test_faq_answer_no_faq(make_request):
    fulfill = make_request("FAQ", {"faq": ""})
    assert "rephras" in fulfill["text"]


def test_contact_followup(make_request):
    faqs_with_contact = []
    for f in ALL_FAQS:
        if f.get("Call") or f.get("Email") or f.get("Directions"):
            faqs_with_contact.append(f)
    sample_faqs = sample(faqs_with_contact, 10)

    for faq in sample_faqs:
        call, email, directions = (
            faq.get("Call"),
            faq.get("Email"),
            faq.get("Directions"),
        )

        contexts = {"voice-faq-contact": {"faq_data": faq}}
        fulfill = make_request("FAQ-Contact-Followup", contexts=contexts)

        if call:
            assert "To contact us about" in fulfill["text"]
            assert f"by phone at {faq['Call']}" in fulfill["text"]
        if email:
            assert "by email at" in fulfill["text"]
        if directions:
            assert f"in person by going to {directions}" in fulfill["text"]
