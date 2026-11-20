from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined


def repo_file(*parts: str) -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pnpm-workspace.yaml").is_file():
            return parent.joinpath(*parts)
    raise FileNotFoundError("/".join(parts))


def render_template(name: str, **values: object) -> str:
    # Templates are plain-text prompts, not HTML pages.
    environment = Environment(autoescape=False, undefined=StrictUndefined, trim_blocks=True)  # noqa: S701
    template = environment.from_string(repo_file("prompts", name).read_text(encoding="utf-8"))
    return template.render(**values).strip()


def prompt_text(name: str) -> str:
    return repo_file("prompts", name).read_text(encoding="utf-8")


def load_sequences() -> list[dict[str, object]]:
    directory = repo_file("data", "sequences")
    loaded: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("code"), str):
            loaded.append(raw)
    return loaded
