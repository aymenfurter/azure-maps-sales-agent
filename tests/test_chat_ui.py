"""
Unit tests for chat_ui.py
"""
import pytest
from gradio import ChatMessage
from chat_ui import convert_dict_to_chatmessage, convert_chatmessage_to_dict, nullcontext, EventHandler


def test_nullcontext():
    """Test nullcontext context manager."""
    # Test with enter_result
    test_value = "test_value"
    ctx = nullcontext(enter_result=test_value)
    with ctx as result:
        assert result == test_value
    
    # Test without enter_result
    ctx2 = nullcontext()
    with ctx2 as result:
        assert result is None


def test_convert_dict_to_chatmessage():
    """Test converting dict to ChatMessage."""
    # Test with basic fields
    test_dict = {
        "role": "user",
        "content": "Hello, world!"
    }
    result = convert_dict_to_chatmessage(test_dict)
    assert isinstance(result, ChatMessage)
    assert result.role == "user"
    assert result.content == "Hello, world!"
    assert result.metadata is None
    
    # Test with metadata
    test_dict_with_metadata = {
        "role": "assistant",
        "content": "I can help you with that.",
        "metadata": {"source": "AI", "confidence": 0.95}
    }
    result = convert_dict_to_chatmessage(test_dict_with_metadata)
    assert isinstance(result, ChatMessage)
    assert result.role == "assistant"
    assert result.content == "I can help you with that."
    assert result.metadata == {"source": "AI", "confidence": 0.95}


def test_convert_chatmessage_to_dict():
    """Test converting ChatMessage to dict."""
    # Test with basic fields
    msg = ChatMessage(role="user", content="Hello, world!")
    result = convert_chatmessage_to_dict(msg)
    assert isinstance(result, dict)
    assert result["role"] == "user"
    assert result["content"] == "Hello, world!"
    assert result["metadata"] == {}
    
    # Test with metadata
    metadata = {"source": "User", "timestamp": "2023-07-15T12:00:00Z"}
    msg_with_metadata = ChatMessage(role="user", content="Testing", metadata=metadata)
    result = convert_chatmessage_to_dict(msg_with_metadata)
    assert result["role"] == "user"
    assert result["content"] == "Testing"
    assert result["metadata"] == metadata


def test_event_handler_initialization():
    """Test EventHandler initialization."""
    # Test without tracer
    handler = EventHandler()
    assert handler._current_message_id is None
    assert handler._accumulated_text == ""
    assert handler._current_tools == {}
    assert handler.conversation is None
    assert handler.create_tool_bubble_fn is None
    assert handler.tracer is None
    
    # Test with tracer
    mock_tracer = object()  # Simple mock object
    handler_with_tracer = EventHandler(tracer=mock_tracer)
    assert handler_with_tracer.tracer is mock_tracer