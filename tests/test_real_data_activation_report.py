import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data_quality.real_data_activation_report import (
    build_real_data_activation_report,
)
from src.db.base import Base
from src.db.models import Competition, Match, Team, TeamAlias


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_team(session, name, code):
    team = Team(
        name=name,
        official_name=name,
        short_name=code,
        country_code=code,
        fifa_code=code,
        confederation="TEST",
    )
    session.add(team)
    session.flush()
    session.add(
        TeamAlias(
            team_id=team.id,
            source_id=None,
            alias=name,
            normalized_alias=name.lower(),
            confidence=1.0,
            is_approved=True,
        )
    )
    session.flush()
    return team


def test_empty_db_generates_not_ready_report(tmp_path):
    session = _session()

    report = build_real_data_activation_report(
        session,
        output_dir=tmp_path / "real_data_reports",
        min_finished_matches=20,
    )

    assert report["teams_count"] == 0
    assert report["matches_count"] == 0
    assert report["readiness"]["ready_for_training"] is False
    assert "too few finished matches" in report["warnings"][0]
    assert (
        tmp_path / "real_data_reports" / "real_data_activation_report.json"
    ).is_file()
    assert (
        tmp_path / "real_data_reports" / "real_data_activation_report.md"
    ).is_file()


def test_finished_matches_above_threshold_sets_ready_true(tmp_path):
    session = _session()
    team_a = _seed_team(session, "Spain", "ESP")
    team_b = _seed_team(session, "Italy", "ITA")
    competition = Competition(
        name="FIFA World Cup",
        official_name="FIFA World Cup",
        competition_type="world_cup",
        confederation=None,
        is_fifa_official=True,
        is_major_tournament=True,
    )
    session.add(competition)
    session.flush()

    for offset in range(3):
        session.add(
            Match(
                competition_id=competition.id,
                stage="Friendly",
                date=date(2024, 1, offset + 1),
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                neutral_site=True,
                status="finished",
                team_a_goals=offset + 1,
                team_b_goals=0,
            )
        )
    session.commit()

    report = build_real_data_activation_report(
        session,
        output_dir=tmp_path / "real_data_reports",
        min_finished_matches=2,
    )

    assert report["finished_matches_count"] == 3
    assert report["readiness"]["ready_for_training"] is True
    assert report["competitions_top"][0]["competition"] == "FIFA World Cup"


def test_report_contains_counts_readiness_and_warnings(tmp_path):
    session = _session()
    team_a = _seed_team(session, "United States", "USA")
    team_b = _seed_team(session, "Mexico", "MEX")
    competition = Competition(
        name="Friendly Cup",
        official_name="Friendly Cup",
        competition_type="friendly",
        confederation=None,
        is_fifa_official=False,
        is_major_tournament=False,
    )
    session.add(competition)
    session.flush()
    session.add(
        Match(
            competition_id=competition.id,
            stage="Friendly",
            date=date(2025, 1, 1),
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            neutral_site=True,
            status="scheduled",
        )
    )
    session.commit()

    report = build_real_data_activation_report(
        session,
        output_dir=tmp_path / "real_data_reports",
        min_finished_matches=5,
    )
    report_json = json.loads(
        (
            tmp_path / "real_data_reports" / "real_data_activation_report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["teams_count"] == 2
    assert report["scheduled_matches_count"] == 1
    assert "ready_for_training" in report["readiness"]
    assert report_json["warnings"]
