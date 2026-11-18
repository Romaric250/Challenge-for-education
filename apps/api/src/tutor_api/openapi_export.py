import json
from pathlib import Path

from tutor_api.main import app


def repository_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pnpm-workspace.yaml").is_file():
            return parent
    raise RuntimeError("Could not locate the repository root from the API package")


def export_openapi(destination: Path | None = None) -> Path:
    target = destination or repository_root() / "packages" / "api-client" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    return target


def main() -> None:
    export_openapi()


if __name__ == "__main__":
    main()
