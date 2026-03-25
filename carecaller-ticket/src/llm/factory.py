from .base import LLMProvider

_REGISTRY: dict[str, type[LLMProvider]] = {}


def register(name: str):
    def decorator(cls: type[LLMProvider]):
        _REGISTRY[name] = cls
        return cls
    return decorator


def get_provider(name: str = "groq", model: str | None = None) -> LLMProvider:
    """Factory to get an LLM provider by name."""
    # lazy-register built-in providers
    if not _REGISTRY:
        from .groq_provider import GroqProvider
        _REGISTRY["groq"] = GroqProvider

    if name not in _REGISTRY:
        raise ValueError(f"Unknown LLM provider: {name!r}. Available: {list(_REGISTRY.keys())}")

    return _REGISTRY[name](model=model)
