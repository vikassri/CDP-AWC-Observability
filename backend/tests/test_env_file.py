from pathlib import Path

from backend.app.services.env_file import read_env_map, write_env_updates


def test_write_env_updates_merge_and_remove(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FOO=1\nBAR=keep\n", encoding="utf-8")
    write_env_updates(env, {"FOO": "2", "BAZ": "new", "BAR": None})
    text = env.read_text(encoding="utf-8")
    assert "FOO=2" in text
    assert "BAZ=new" in text
    assert "BAR=" not in text
    assert read_env_map(env)["FOO"] == "2"
