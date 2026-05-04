from app.ml.mock_llm_client import MockLLMClient, parse_with_repair

def test_repair():
    out = parse_with_repair('{bad json', MockLLMClient())
    assert out.summary
