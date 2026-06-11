import pytest

pytestmark = [pytest.mark.agents, pytest.mark.integration]


class DummyAgentClient:
    """
    Simple stub to represent an agent that would call OpenAI/Abacus/etc.
    """

    def __init__(self, provider: str):
        self.provider = provider

    def hello(self) -> str:
        return f"hello from {self.provider}"

    def invoke(self, prompt: str) -> dict:
        return {"provider": self.provider, "prompt": prompt, "response": "ok"}


@pytest.mark.parametrize(
    "provider",
    ["openai", "abacus", "redhat", "github_copilot", "codex_mcp"],
)
def test_agent_hello_world(provider):
    """Test basic agent initialization and hello message."""
    agent = DummyAgentClient(provider=provider)
    msg = agent.hello()
    assert provider in msg
    assert msg.startswith("hello from")


def test_agent_orchestrator_routes_to_correct_provider():
    """
    Minimal orchestrator that chooses provider based on 'target' field.
    """

    def orchestrate_call(target: str, prompt: str):
        if target == "fast-local":
            return {"provider": "local", "prompt": prompt, "response": "ok"}
        else:
            agent = DummyAgentClient(provider=target)
            return agent.invoke(prompt)

    result_local = orchestrate_call("fast-local", "ping")
    assert result_local["provider"] == "local"

    result_openai = orchestrate_call("openai", "ping")
    assert result_openai["provider"] == "openai"


def test_agent_invoke_returns_expected_structure():
    """Test agent invoke returns proper response structure."""
    agent = DummyAgentClient(provider="test-provider")
    result = agent.invoke("test prompt")
    
    assert "provider" in result
    assert "prompt" in result
    assert "response" in result
    assert result["provider"] == "test-provider"
    assert result["prompt"] == "test prompt"


def test_multiple_agents_can_coexist():
    """Test multiple agent instances can be created and used."""
    agent1 = DummyAgentClient(provider="openai")
    agent2 = DummyAgentClient(provider="abacus")
    agent3 = DummyAgentClient(provider="codex_mcp")
    
    assert agent1.hello() == "hello from openai"
    assert agent2.hello() == "hello from abacus"
    assert agent3.hello() == "hello from codex_mcp"


def test_agent_prompt_passthrough():
    """Test that prompts are correctly passed through to responses."""
    agent = DummyAgentClient(provider="test")
    prompts = ["analyze this", "generate code", "explain concept"]
    
    for prompt in prompts:
        result = agent.invoke(prompt)
        assert result["prompt"] == prompt
