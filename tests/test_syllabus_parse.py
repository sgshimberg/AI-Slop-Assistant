"""Phase 3 automated test gate: parsing mechanics only — extension dispatch, short-text
error, and grouping/extraction logic against **mocked** Anthropic tool-use responses.
No network, no real syllabus content. The real Phase 3 gate is manual — see
docs/PHASE3.md and scripts/parse_courses.py.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.integrations import syllabus


def _tool_use_message(tool_name: str, tool_input: dict):
    block = SimpleNamespace(type="tool_use", name=tool_name, input=tool_input)
    return SimpleNamespace(content=[block])


# ---- extract_text ----


def test_extract_text_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    with pytest.raises(ValueError):
        syllabus.extract_text(path)


def test_extract_text_dispatches_pdf(tmp_path, monkeypatch):
    path = tmp_path / "syllabus.pdf"
    path.write_bytes(b"%PDF-fake")
    fake_page = SimpleNamespace(extract_text=lambda: "x" * 300)
    monkeypatch.setattr(syllabus, "PdfReader", lambda _path: SimpleNamespace(pages=[fake_page]))
    assert syllabus.extract_text(path) == "x" * 300


def test_extract_text_dispatches_docx(tmp_path, monkeypatch):
    path = tmp_path / "syllabus.docx"
    path.write_bytes(b"PK-fake")
    fake_paragraphs = [SimpleNamespace(text="y" * 300)]
    monkeypatch.setattr(syllabus, "Document", lambda _path: SimpleNamespace(paragraphs=fake_paragraphs))
    assert syllabus.extract_text(path) == "y" * 300


def test_extract_text_raises_on_suspiciously_short_pdf(tmp_path, monkeypatch):
    path = tmp_path / "scanned.pdf"
    path.write_bytes(b"%PDF-fake")
    fake_page = SimpleNamespace(extract_text=lambda: "short")
    monkeypatch.setattr(syllabus, "PdfReader", lambda _path: SimpleNamespace(pages=[fake_page]))
    with pytest.raises(RuntimeError):
        syllabus.extract_text(path)


# ---- identify_course ----


def test_identify_course_returns_tool_input(monkeypatch):
    message = _tool_use_message("record_course_code", {"code": "ECE 220"})
    mock_client = MagicMock()
    mock_client.messages.create.return_value = message
    monkeypatch.setattr(syllabus, "Anthropic", lambda api_key: mock_client)

    assert syllabus.identify_course("some syllabus text") == "ECE 220"
    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["tool_choice"] == {"type": "tool", "name": "record_course_code"}


# ---- group_by_course ----


def test_group_by_course_normalizes_and_groups(tmp_path, monkeypatch):
    (tmp_path / "a.pdf").write_bytes(b"fake")
    (tmp_path / "b.pdf").write_bytes(b"fake")
    (tmp_path / "c.txt").write_bytes(b"fake")  # unsupported extension, must be skipped

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    codes = {"a.pdf": "ECE220", "b.pdf": "ece 220"}
    monkeypatch.setattr(syllabus, "identify_course", lambda text: codes[text])

    groups = syllabus.group_by_course(tmp_path)

    assert set(groups) == {"ECE 220"}
    assert {p.name for p in groups["ECE 220"]} == {"a.pdf", "b.pdf"}


def test_group_by_course_keeps_unclassifiable_documents_separate(tmp_path, monkeypatch):
    (tmp_path / "a.pdf").write_bytes(b"fake")
    (tmp_path / "b.pdf").write_bytes(b"fake")

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    # One document classifies fine; the other comes back as an unresolvable/garbled
    # placeholder (mirrors a real observed model response, "&LT;UNKNOWN&GT;").
    codes = {"a.pdf": "ECE 211", "b.pdf": "&LT;UNKNOWN&GT;"}
    monkeypatch.setattr(syllabus, "identify_course", lambda text: codes[text])
    # No content-match found for the unclassifiable document either.
    monkeypatch.setattr(syllabus, "_match_unknown_to_candidate", lambda text, candidates: None)

    groups = syllabus.group_by_course(tmp_path)

    assert groups["ECE 211"] == [tmp_path / "a.pdf"]
    assert groups[f"{syllabus.UNKNOWN_COURSE}: b.pdf"] == [tmp_path / "b.pdf"]
    # Must never silently create a shared "UNKNOWN" bucket that could mix documents
    # from two different, genuinely unrelated courses.
    assert syllabus.UNKNOWN_COURSE not in groups


def test_group_by_course_reconciles_unknown_via_content_match(tmp_path, monkeypatch):
    (tmp_path / "syllabus.pdf").write_bytes(b"fake")
    (tmp_path / "schedule.pdf").write_bytes(b"fake")

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    codes = {"syllabus.pdf": "ECE 211", "schedule.pdf": "UNKNOWN"}
    monkeypatch.setattr(syllabus, "identify_course", lambda text: codes[text])
    monkeypatch.setattr(syllabus, "_match_unknown_to_candidate", lambda text, candidates: "ECE 211")

    groups = syllabus.group_by_course(tmp_path)

    assert set(groups) == {"ECE 211"}
    assert {p.name for p in groups["ECE 211"]} == {"syllabus.pdf", "schedule.pdf"}


def test_reconcile_unknowns_never_offers_other_unknowns_as_candidates(tmp_path, monkeypatch):
    (tmp_path / "known.pdf").write_bytes(b"fake")
    (tmp_path / "orphan1.pdf").write_bytes(b"fake")
    (tmp_path / "orphan2.pdf").write_bytes(b"fake")

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    codes = {"known.pdf": "ECE 211", "orphan1.pdf": "UNKNOWN", "orphan2.pdf": "UNKNOWN"}
    monkeypatch.setattr(syllabus, "identify_course", lambda text: codes[text])

    seen_candidate_keys = []

    def fake_match(text, candidates):
        seen_candidate_keys.append(set(candidates))
        return None

    monkeypatch.setattr(syllabus, "_match_unknown_to_candidate", fake_match)

    groups = syllabus.group_by_course(tmp_path)

    assert all(syllabus.UNKNOWN_COURSE not in keys and len(keys) <= 1 for keys in seen_candidate_keys)
    for keys in seen_candidate_keys:
        assert keys == {"ECE 211"}
    assert f"{syllabus.UNKNOWN_COURSE}: orphan1.pdf" in groups
    assert f"{syllabus.UNKNOWN_COURSE}: orphan2.pdf" in groups


def test_match_unknown_to_candidate_short_circuits_with_no_candidates(monkeypatch):
    def boom(api_key):
        raise AssertionError("Anthropic should never be called with no candidates")

    monkeypatch.setattr(syllabus, "Anthropic", boom)
    assert syllabus._match_unknown_to_candidate("some text", {}) is None


# ---- ask_human fallback ----


def test_group_by_course_asks_human_when_content_match_fails(tmp_path, monkeypatch):
    (tmp_path / "known.pdf").write_bytes(b"fake")
    (tmp_path / "mystery.pdf").write_bytes(b"fake")

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    codes = {"known.pdf": "ECE 211", "mystery.pdf": "UNKNOWN"}
    monkeypatch.setattr(syllabus, "identify_course", lambda text: codes[text])
    monkeypatch.setattr(syllabus, "_match_unknown_to_candidate", lambda text, candidates: None)

    calls = []

    def ask_human(path, text, known_courses):
        calls.append((path, text, known_courses))
        return "ECE 301"

    groups = syllabus.group_by_course(tmp_path, ask_human=ask_human)

    assert calls == [(tmp_path / "mystery.pdf", "mystery.pdf", ["ECE 211"])]
    assert set(groups) == {"ECE 211", "ECE 301"}
    assert groups["ECE 301"] == [tmp_path / "mystery.pdf"]


def test_group_by_course_does_not_ask_human_when_content_match_succeeds(tmp_path, monkeypatch):
    (tmp_path / "known.pdf").write_bytes(b"fake")
    (tmp_path / "mystery.pdf").write_bytes(b"fake")

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    codes = {"known.pdf": "ECE 211", "mystery.pdf": "UNKNOWN"}
    monkeypatch.setattr(syllabus, "identify_course", lambda text: codes[text])
    monkeypatch.setattr(syllabus, "_match_unknown_to_candidate", lambda text, candidates: "ECE 211")

    def ask_human(path, text, known_courses):
        raise AssertionError("should not ask a human once content-matching already resolved it")

    groups = syllabus.group_by_course(tmp_path, ask_human=ask_human)

    assert set(groups) == {"ECE 211"}


def test_group_by_course_stays_unresolved_when_human_doesnt_know_either(tmp_path, monkeypatch):
    (tmp_path / "mystery.pdf").write_bytes(b"fake")

    monkeypatch.setattr(syllabus, "extract_text", lambda path: path.name)
    monkeypatch.setattr(syllabus, "identify_course", lambda text: "UNKNOWN")
    monkeypatch.setattr(syllabus, "_match_unknown_to_candidate", lambda text, candidates: None)

    groups = syllabus.group_by_course(tmp_path, ask_human=lambda path, text, known_courses: "")

    assert groups[f"{syllabus.UNKNOWN_COURSE}: mystery.pdf"] == [tmp_path / "mystery.pdf"]
    assert syllabus.UNKNOWN_COURSE not in groups


# ---- parse_course_documents ----


def test_parse_course_documents_bundles_files_and_forces_tool(tmp_path, monkeypatch):
    path1 = tmp_path / "syllabus.pdf"
    path2 = tmp_path / "calendar.pdf"
    path1.write_bytes(b"fake")
    path2.write_bytes(b"fake")
    monkeypatch.setattr(syllabus, "extract_text", lambda path: f"TEXT:{path.name}")

    record = {
        "course": "ECE 220: Fields and Waves",
        "categories": [{"name": "Homework", "weight": 1.0}],
        "graded_items": [],
        "notes": None,
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _tool_use_message("record_course", record)
    monkeypatch.setattr(syllabus, "Anthropic", lambda api_key: mock_client)

    result = syllabus.parse_course_documents([path1, path2])

    assert result == record
    _, kwargs = mock_client.messages.create.call_args
    sent_text = kwargs["messages"][0]["content"]
    assert "=== syllabus.pdf ===" in sent_text
    assert "=== calendar.pdf ===" in sent_text
    assert kwargs["tool_choice"] == {"type": "tool", "name": "record_course"}


def test_parse_course_documents_defaults_missing_notes_to_none(tmp_path, monkeypatch):
    path = tmp_path / "syllabus.pdf"
    path.write_bytes(b"fake")
    monkeypatch.setattr(syllabus, "extract_text", lambda path: "text")

    record_without_notes = {"course": "ECE 211", "categories": [], "graded_items": []}
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _tool_use_message("record_course", record_without_notes)
    monkeypatch.setattr(syllabus, "Anthropic", lambda api_key: mock_client)

    result = syllabus.parse_course_documents([path])

    assert result["notes"] is None


def test_parse_course_documents_warns_when_weights_dont_sum_to_one(tmp_path, monkeypatch):
    path = tmp_path / "syllabus.pdf"
    path.write_bytes(b"fake")
    monkeypatch.setattr(syllabus, "extract_text", lambda path: "text")

    lopsided_record = {
        "course": "ECE 211",
        "categories": [{"name": "Homework", "weight": 0.2}],
        "graded_items": [],
        "notes": None,
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _tool_use_message("record_course", lopsided_record)
    monkeypatch.setattr(syllabus, "Anthropic", lambda api_key: mock_client)

    with pytest.warns(UserWarning, match="0.20"):
        syllabus.parse_course_documents([path])


# ---- parse_all_courses ----


def test_parse_all_courses_composes_group_and_parse(tmp_path, monkeypatch):
    monkeypatch.setattr(
        syllabus,
        "group_by_course",
        lambda dir_path, ask_human=None: {"ECE 220": [Path("a.pdf")], "ECE 301": [Path("b.pdf")]},
    )
    monkeypatch.setattr(syllabus, "parse_course_documents", lambda paths: {"course": paths[0].name})

    result = syllabus.parse_all_courses(tmp_path)

    assert result == {"ECE 220": {"course": "a.pdf"}, "ECE 301": {"course": "b.pdf"}}
