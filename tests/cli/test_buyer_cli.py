from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from troostwatch.interfaces.cli.buyer import buyer


def test_add_and_list_buyers(tmp_path: Path) -> None:
    db_file = tmp_path / "buyers.db"
    runner = CliRunner()

    add_result = runner.invoke(
        buyer, ["--db", str(db_file), "add", "B-1", "--name", "Example Buyer", "--notes", "VIP"]
    )

    assert add_result.exit_code == 0
    assert "Added buyer" in add_result.output

    list_result = runner.invoke(buyer, ["--db", str(db_file), "list"])

    assert list_result.exit_code == 0
    assert "B-1" in list_result.output
    assert "Example Buyer" in list_result.output
    assert "VIP" in list_result.output


def test_add_duplicate_buyer(tmp_path: Path) -> None:
    db_file = tmp_path / "buyers.db"
    runner = CliRunner()

    first_result = runner.invoke(buyer, ["--db", str(db_file), "add", "B-2"])
    duplicate_result = runner.invoke(buyer, ["--db", str(db_file), "add", "B-2"])

    assert first_result.exit_code == 0
    assert duplicate_result.exit_code == 1
    assert "already exists" in duplicate_result.output


def test_delete_buyer(tmp_path: Path) -> None:
    db_file = tmp_path / "buyers.db"
    runner = CliRunner()

    runner.invoke(buyer, ["--db", str(db_file), "add", "B-3"])

    delete_result = runner.invoke(buyer, ["--db", str(db_file), "delete", "B-3"])
    list_result = runner.invoke(buyer, ["--db", str(db_file), "list"])

    assert delete_result.exit_code == 0
    assert "Deleted buyer" in delete_result.output
    assert list_result.exit_code == 0
    assert "No buyers found" in list_result.output
