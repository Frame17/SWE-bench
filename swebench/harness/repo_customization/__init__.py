import importlib


def _repo_to_module_name(repo: str) -> str:
    """Convert 'owner/repo-name' to 'owner__repo_name'."""
    return repo.replace("/", "__").replace("-", "_")


def get_customization_commands(repo: str) -> list[str]:
    """Return per-repo customization commands, or empty list if none exist."""
    module_name = _repo_to_module_name(repo)
    try:
        mod = importlib.import_module(f".{module_name}", package=__name__)
        return getattr(mod, "COMMANDS", [])
    except ModuleNotFoundError:
        return []
