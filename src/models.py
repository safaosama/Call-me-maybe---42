from typing import Any

from pydantic import BaseModel


class ParameterDefinition(BaseModel):
    """Define the type of a function parameter."""
    type: str


class ReturnDefinition(BaseModel):
    """Define the return type of a function."""
    type: str


class FunctionDefinition(BaseModel):
    """Define a function and its parameters and return type."""
    name: str
    description: str
    parameters: dict[str, ParameterDefinition]
    returns: ReturnDefinition


class TestPrompt(BaseModel):
    """Store a user prompt for testing."""
    prompt: str


class FunctionCallResult(BaseModel):
    """Store the function call result for a prompt."""
    prompt: str
    name: str
    parameters: dict[str, Any]
