from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_readme_documents_docker_persistence_contract():
    readme_path = get_project_root() / "README.md"

    content = readme_path.read_text(encoding="utf-8")
    assert "CWS_DATA_DIR=/data" in content, f"{readme_path} must mention CWS_DATA_DIR=/data"
    assert "./docker-data" in content, f"{readme_path} must mention ./docker-data mapping"
