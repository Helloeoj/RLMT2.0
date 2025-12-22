class SchemaValidationError(ValueError):
    """Raised when an Event fails Phase 0 schema validation."""


class PipelineError(RuntimeError):
    """Generic pipeline error."""
