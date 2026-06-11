import pytest

pytestmark = [pytest.mark.agents, pytest.mark.integration]


class DummyMcpClient:
    """
    Simplified MCP-style client:
    - send a 'request' dict
    - receive a 'response' dict
    """

    def __init__(self):
        self._tools = {
            "echo": self._tool_echo,
            "add": self._tool_add,
            "concat": self._tool_concat,
        }

    def _tool_echo(self, payload):
        return {"ok": True, "echo": payload}

    def _tool_add(self, payload):
        if "a" not in payload or "b" not in payload:
            return {"ok": False, "error": "missing_parameters"}
        return {"ok": True, "result": payload["a"] + payload["b"]}

    def _tool_concat(self, payload):
        if "strings" not in payload:
            return {"ok": False, "error": "missing_strings"}
        return {"ok": True, "result": "".join(payload["strings"])}

    def call_tool(self, name: str, payload: dict) -> dict:
        if name not in self._tools:
            return {"ok": False, "error": "unknown_tool"}
        return self._tools[name](payload)

    def list_tools(self) -> list:
        return list(self._tools.keys())


def test_mcp_echo_tool_roundtrip():
    """Test MCP echo tool returns payload correctly."""
    client = DummyMcpClient()
    payload = {"message": "hello"}
    resp = client.call_tool("echo", payload)
    assert resp["ok"] is True
    assert resp["echo"] == payload


def test_mcp_unknown_tool_error():
    """Test MCP returns error for unknown tools."""
    client = DummyMcpClient()
    resp = client.call_tool("unknown", {})
    assert resp["ok"] is False
    assert resp["error"] == "unknown_tool"


def test_mcp_add_tool_computation():
    """Test MCP add tool performs computation."""
    client = DummyMcpClient()
    resp = client.call_tool("add", {"a": 5, "b": 3})
    assert resp["ok"] is True
    assert resp["result"] == 8


def test_mcp_add_tool_missing_parameters():
    """Test MCP add tool handles missing parameters."""
    client = DummyMcpClient()
    resp = client.call_tool("add", {"a": 5})
    assert resp["ok"] is False
    assert resp["error"] == "missing_parameters"


def test_mcp_concat_tool():
    """Test MCP concat tool joins strings."""
    client = DummyMcpClient()
    resp = client.call_tool("concat", {"strings": ["hello", " ", "world"]})
    assert resp["ok"] is True
    assert resp["result"] == "hello world"


def test_mcp_list_available_tools():
    """Test MCP can list available tools."""
    client = DummyMcpClient()
    tools = client.list_tools()
    assert "echo" in tools
    assert "add" in tools
    assert "concat" in tools
    assert len(tools) == 3


def test_mcp_multiple_calls_same_client():
    """Test multiple tool calls on same client instance."""
    client = DummyMcpClient()
    
    resp1 = client.call_tool("echo", {"msg": "first"})
    assert resp1["ok"] is True
    
    resp2 = client.call_tool("add", {"a": 10, "b": 20})
    assert resp2["ok"] is True
    assert resp2["result"] == 30
    
    resp3 = client.call_tool("concat", {"strings": ["a", "b", "c"]})
    assert resp3["ok"] is True
    assert resp3["result"] == "abc"
