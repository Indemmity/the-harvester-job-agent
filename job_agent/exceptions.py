class JobAgentError(Exception):
    """Base exception for the job agent."""


class ConfigurationError(JobAgentError):
    """Raised when the runtime configuration is invalid."""


class PipelineError(JobAgentError):
    """Raised when the orchestration pipeline cannot finish."""


class SourceAdapterError(JobAgentError):
    """Raised when a source adapter fails to collect or parse jobs."""

