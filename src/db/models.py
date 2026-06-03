"""Relational database models for the project."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.db.base import Base

JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CreatedAtMixin:
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ActiveMixin:
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(100), nullable=False)
    url = Column(String(500), nullable=True)
    license = Column(String(255), nullable=True)
    priority = Column(Integer, nullable=True)
    reliability_score = Column(Float, nullable=True)
    update_frequency = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)


class Team(TimestampMixin, ActiveMixin, Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=False)
    short_name = Column(String(100), nullable=False)
    country_code = Column(String(3), nullable=False)
    fifa_code = Column(String(10), unique=True, nullable=True)
    confederation = Column(String(50), nullable=False)

    aliases = relationship("TeamAlias", back_populates="team")


class TeamAlias(TimestampMixin, Base):
    __tablename__ = "team_aliases"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "normalized_alias",
            "source_id",
            name="uq_team_aliases_team_normalized_source",
        ),
    )

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    alias = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False)
    language = Column(String(32), nullable=True)
    confidence = Column(Float, nullable=False, default=1.0, server_default="1.0")
    is_approved = Column(Boolean, nullable=False, default=False, server_default="false")

    team = relationship("Team", back_populates="aliases")


class Club(TimestampMixin, ActiveMixin, Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    league = Column(String(150), nullable=True)


class ClubAlias(TimestampMixin, Base):
    __tablename__ = "club_aliases"

    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    alias = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0, server_default="1.0")
    is_approved = Column(Boolean, nullable=False, default=False, server_default="false")


class Competition(TimestampMixin, Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=True)
    competition_type = Column(String(100), nullable=False)
    confederation = Column(String(50), nullable=True)
    is_fifa_official = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_major_tournament = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class CompetitionAlias(TimestampMixin, Base):
    __tablename__ = "competition_aliases"

    id = Column(Integer, primary_key=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    alias = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0, server_default="1.0")
    is_approved = Column(Boolean, nullable=False, default=False, server_default="false")


class Venue(TimestampMixin, Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude_m = Column(Float, nullable=True)
    capacity = Column(Integer, nullable=True)
    timezone = Column(String(100), nullable=True)


class VenueAlias(TimestampMixin, Base):
    __tablename__ = "venue_aliases"

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    alias = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0, server_default="1.0")
    is_approved = Column(Boolean, nullable=False, default=False, server_default="false")


class Bookmaker(TimestampMixin, Base):
    __tablename__ = "bookmakers"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)
    url = Column(String(500), nullable=True)
    is_exchange = Column(Boolean, nullable=False, default=False, server_default="false")


class Player(TimestampMixin, ActiveMixin, Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    nationality_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    primary_position = Column(String(50), nullable=True)
    preferred_foot = Column(String(30), nullable=True)
    height_cm = Column(Integer, nullable=True)

    nationality_team = relationship("Team")


class PlayerAlias(TimestampMixin, Base):
    __tablename__ = "player_aliases"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    alias = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False)
    team_id_context = Column(Integer, ForeignKey("teams.id"), nullable=True)
    club_id_context = Column(Integer, ForeignKey("clubs.id"), nullable=True)
    date_context = Column(Date, nullable=True)
    confidence = Column(Float, nullable=False, default=1.0, server_default="1.0")
    is_approved = Column(Boolean, nullable=False, default=False, server_default="false")


class Match(TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("team_a_id <> team_b_id", name="ck_matches_distinct_teams"),
        CheckConstraint(
            "team_a_goals IS NULL OR team_a_goals >= 0",
            name="ck_matches_team_a_goals_non_negative",
        ),
        CheckConstraint(
            "team_b_goals IS NULL OR team_b_goals >= 0",
            name="ck_matches_team_b_goals_non_negative",
        ),
    )

    id = Column(Integer, primary_key=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=True)
    stage = Column(String(100), nullable=True)
    matchday = Column(Integer, nullable=True)
    date = Column(Date, nullable=True)
    kickoff_time = Column(Time, nullable=True)
    timezone = Column(String(100), nullable=True)
    team_a_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team_b_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)
    neutral_site = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    status = Column(String(50), nullable=False)
    team_a_goals = Column(Integer, nullable=True)
    team_b_goals = Column(Integer, nullable=True)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team_a = relationship("Team", foreign_keys=[team_a_id])
    team_b = relationship("Team", foreign_keys=[team_b_id])


class Batch(TimestampMixin, Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    stage = Column(String(100), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    first_match_start = Column(DateTime(timezone=True), nullable=True)
    cutoff_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)


class BatchMatch(Base):
    __tablename__ = "batch_matches"
    __table_args__ = (
        PrimaryKeyConstraint("batch_id", "match_id", name="pk_batch_matches"),
    )

    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    order_in_batch = Column(Integer, nullable=True)

    batch = relationship("Batch")
    match = relationship("Match")


class MatchTeamStat(TimestampMixin, Base):
    __tablename__ = "match_team_stats"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "team_id",
            "source_id",
            name="uq_match_team_stats_match_team_source",
        ),
        CheckConstraint(
            "goals IS NULL OR goals >= 0", name="ck_mts_goals_non_negative"
        ),
        CheckConstraint("xg IS NULL OR xg >= 0", name="ck_mts_xg_non_negative"),
        CheckConstraint(
            "shots IS NULL OR shots >= 0", name="ck_mts_shots_non_negative"
        ),
        CheckConstraint(
            "shots_on_target IS NULL OR shots_on_target >= 0",
            name="ck_mts_shots_on_target_non_negative",
        ),
        CheckConstraint(
            "big_chances IS NULL OR big_chances >= 0",
            name="ck_mts_big_chances_non_negative",
        ),
        CheckConstraint(
            "possession IS NULL OR (possession >= 0 AND possession <= 100)",
            name="ck_mts_possession_range",
        ),
        CheckConstraint(
            "corners IS NULL OR corners >= 0", name="ck_mts_corners_non_negative"
        ),
        CheckConstraint(
            "fouls IS NULL OR fouls >= 0", name="ck_mts_fouls_non_negative"
        ),
        CheckConstraint(
            "yellow_cards IS NULL OR yellow_cards >= 0",
            name="ck_mts_yellow_cards_non_negative",
        ),
        CheckConstraint(
            "red_cards IS NULL OR red_cards >= 0",
            name="ck_mts_red_cards_non_negative",
        ),
        CheckConstraint(
            "offsides IS NULL OR offsides >= 0", name="ck_mts_offsides_non_negative"
        ),
        CheckConstraint(
            "passes IS NULL OR passes >= 0", name="ck_mts_passes_non_negative"
        ),
        CheckConstraint(
            "pass_accuracy IS NULL OR (pass_accuracy >= 0 AND pass_accuracy <= 100)",
            name="ck_mts_pass_accuracy_range",
        ),
        CheckConstraint("ppda IS NULL OR ppda >= 0", name="ck_mts_ppda_non_negative"),
        CheckConstraint(
            "field_tilt IS NULL OR (field_tilt >= 0 AND field_tilt <= 100)",
            name="ck_mts_field_tilt_range",
        ),
    )

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    goals = Column(Integer, nullable=True)
    xg = Column(Float, nullable=True)
    shots = Column(Integer, nullable=True)
    shots_on_target = Column(Integer, nullable=True)
    big_chances = Column(Integer, nullable=True)
    possession = Column(Float, nullable=True)
    corners = Column(Integer, nullable=True)
    fouls = Column(Integer, nullable=True)
    yellow_cards = Column(Integer, nullable=True)
    red_cards = Column(Integer, nullable=True)
    offsides = Column(Integer, nullable=True)
    passes = Column(Integer, nullable=True)
    pass_accuracy = Column(Float, nullable=True)
    ppda = Column(Float, nullable=True)
    field_tilt = Column(Float, nullable=True)


class ExternalTeamRating(CreatedAtMixin, Base):
    __tablename__ = "external_team_ratings"
    __table_args__ = (
        Index("ix_external_team_ratings_team_rating_date", "team_id", "rating_date"),
    )

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    rating_date = Column(Date, nullable=False)
    rating_type = Column(String(100), nullable=False)
    rating_value = Column(Float, nullable=True)
    rank_value = Column(Integer, nullable=True)


class InternalTeamRating(CreatedAtMixin, Base):
    __tablename__ = "internal_team_ratings"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    model_version = Column(String(100), nullable=False)
    rating_date = Column(Date, nullable=False)
    attack_rating = Column(Float, nullable=True)
    defense_rating = Column(Float, nullable=True)
    form_rating = Column(Float, nullable=True)
    fatigue_rating = Column(Float, nullable=True)
    injury_impact = Column(Float, nullable=True)
    suspension_impact = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)


class PlayerSnapshot(CreatedAtMixin, Base):
    __tablename__ = "player_snapshots"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    snapshot_date = Column(Date, nullable=False)
    market_value = Column(Numeric(14, 2), nullable=True)
    minutes_last_30d = Column(Integer, nullable=True)
    minutes_last_90d = Column(Integer, nullable=True)
    injury_status = Column(String(100), nullable=True)
    suspension_status = Column(String(100), nullable=True)
    expected_starter_probability = Column(Float, nullable=True)
    importance_score = Column(Float, nullable=True)
    fitness_score = Column(Float, nullable=True)


class PlayerAvailabilityEvent(CreatedAtMixin, Base):
    __tablename__ = "player_availability_events"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    event_date = Column(Date, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    body_part = Column(String(100), nullable=True)
    severity = Column(String(100), nullable=True)
    status = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


class IngestionRun(CreatedAtMixin, Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)
    rows_read = Column(Integer, nullable=False, default=0, server_default="0")
    rows_valid = Column(Integer, nullable=False, default=0, server_default="0")
    rows_inserted = Column(Integer, nullable=False, default=0, server_default="0")
    rows_rejected = Column(Integer, nullable=False, default=0, server_default="0")
    checksum = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON_VARIANT, nullable=True)


class RawDataSnapshot(CreatedAtMixin, Base):
    __tablename__ = "raw_data_snapshots"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    ingestion_run_id = Column(Integer, ForeignKey("ingestion_runs.id"), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True)
    checksum = Column(String(255), nullable=True)


class MarketSnapshot(CreatedAtMixin, Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        CheckConstraint(
            "implied_probability IS NULL OR "
            "(implied_probability >= 0 AND implied_probability <= 1)",
            name="ck_market_snapshots_implied_probability_range",
        ),
        CheckConstraint(
            "margin IS NULL OR (margin >= 0 AND margin <= 1)",
            name="ck_market_snapshots_margin_range",
        ),
        CheckConstraint(
            "odds_decimal IS NULL OR odds_decimal > 1",
            name="ck_market_snapshots_odds_decimal_gt_one",
        ),
    )

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    bookmaker_id = Column(Integer, ForeignKey("bookmakers.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    market_type = Column(String(100), nullable=False)
    selection = Column(String(255), nullable=False)
    odds_decimal = Column(Float, nullable=True)
    implied_probability = Column(Float, nullable=True)
    margin = Column(Float, nullable=True)
    snapshot_time = Column(DateTime(timezone=True), nullable=False)


class NewsItem(CreatedAtMixin, Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    url = Column(String(500), nullable=True)
    title = Column(String(500), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False)
    language = Column(String(32), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    summary = Column(Text, nullable=True)
    raw_text_hash = Column(String(255), nullable=True)
    reliability_score = Column(Float, nullable=True)


class NewsSignal(CreatedAtMixin, ActiveMixin, Base):
    __tablename__ = "news_signals"

    id = Column(Integer, primary_key=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    signal_type = Column(String(100), nullable=False)
    severity = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    superseded_by_signal_id = Column(
        Integer, ForeignKey("news_signals.id"), nullable=True
    )
    weight = Column(Float, nullable=True)


class FeatureSet(CreatedAtMixin, Base):
    __tablename__ = "feature_sets"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    cutoff_time = Column(DateTime(timezone=True), nullable=True)
    feature_config_json = Column(JSON_VARIANT, nullable=True)
    rows_count = Column(Integer, nullable=True)
    data_coverage_json = Column(JSON_VARIANT, nullable=True)


class MatchFeature(CreatedAtMixin, Base):
    __tablename__ = "match_features"
    __table_args__ = (
        UniqueConstraint(
            "feature_set_id", "match_id", name="uq_match_features_feature_set_match"
        ),
    )

    id = Column(Integer, primary_key=True)
    feature_set_id = Column(Integer, ForeignKey("feature_sets.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_a_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team_b_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    features_json = Column(JSON_VARIANT, nullable=False)
    target_result = Column(String(50), nullable=True)


class ModelRun(CreatedAtMixin, Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True)
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(100), nullable=False)
    trained_at = Column(DateTime(timezone=True), nullable=False)
    training_start_date = Column(Date, nullable=True)
    training_end_date = Column(Date, nullable=True)
    feature_set_id = Column(Integer, ForeignKey("feature_sets.id"), nullable=True)
    features_used_json = Column(JSON_VARIANT, nullable=True)
    metrics_json = Column(JSON_VARIANT, nullable=True)
    artifact_path = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)


class Prediction(CreatedAtMixin, Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint(
            "predicted_score_a >= 0 AND predicted_score_b >= 0",
            name="ck_predictions_scores_non_negative",
        ),
        CheckConstraint(
            "p_team_a_win_90 >= 0 AND p_team_a_win_90 <= 1",
            name="ck_predictions_p_team_a_win_90_range",
        ),
        CheckConstraint(
            "p_draw_90 >= 0 AND p_draw_90 <= 1",
            name="ck_predictions_p_draw_90_range",
        ),
        CheckConstraint(
            "p_team_b_win_90 >= 0 AND p_team_b_win_90 <= 1",
            name="ck_predictions_p_team_b_win_90_range",
        ),
        CheckConstraint(
            "p_team_a_qualifies IS NULL OR "
            "(p_team_a_qualifies >= 0 AND p_team_a_qualifies <= 1)",
            name="ck_predictions_p_team_a_qualifies_range",
        ),
        CheckConstraint(
            "p_team_b_qualifies IS NULL OR "
            "(p_team_b_qualifies >= 0 AND p_team_b_qualifies <= 1)",
            name="ck_predictions_p_team_b_qualifies_range",
        ),
        Index(
            "ix_predictions_match_batch_official",
            "match_id",
            "batch_id",
            "is_official",
        ),
    )

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    model_run_id = Column(Integer, ForeignKey("model_runs.id"), nullable=True)
    feature_set_id = Column(Integer, ForeignKey("feature_sets.id"), nullable=True)
    predicted_at = Column(DateTime(timezone=True), nullable=False)
    prediction_deadline = Column(DateTime(timezone=True), nullable=True)
    is_official = Column(Boolean, nullable=False, default=False, server_default="false")
    is_frozen = Column(Boolean, nullable=False, default=False, server_default="false")
    predicted_score_a = Column(Integer, nullable=False)
    predicted_score_b = Column(Integer, nullable=False)
    predicted_outcome = Column(String(50), nullable=False)
    p_team_a_win_90 = Column(Float, nullable=False)
    p_draw_90 = Column(Float, nullable=False)
    p_team_b_win_90 = Column(Float, nullable=False)
    expected_goals_a = Column(Float, nullable=True)
    expected_goals_b = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    confidence_label = Column(String(50), nullable=True)
    score_distribution_json = Column(JSON_VARIANT, nullable=True)
    explanation_json = Column(JSON_VARIANT, nullable=True)
    data_coverage_json = Column(JSON_VARIANT, nullable=True)
    p_team_a_qualifies = Column(Float, nullable=True)
    p_team_b_qualifies = Column(Float, nullable=True)
    predicted_qualifier_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    predicted_resolution = Column(String(100), nullable=True)
    extra_time_json = Column(JSON_VARIANT, nullable=True)
    penalties_json = Column(JSON_VARIANT, nullable=True)


class PredictionSignalLink(CreatedAtMixin, Base):
    __tablename__ = "prediction_signal_links"

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    signal_type = Column(String(100), nullable=False)
    signal_id = Column(Integer, nullable=False)
    weight_used = Column(Float, nullable=True)


class SimulationRun(CreatedAtMixin, Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    model_run_id = Column(Integer, ForeignKey("model_runs.id"), nullable=True)
    feature_set_id = Column(Integer, ForeignKey("feature_sets.id"), nullable=True)
    simulated_at = Column(DateTime(timezone=True), nullable=False)
    num_simulations = Column(Integer, nullable=False)
    config_json = Column(JSON_VARIANT, nullable=True)
    random_seed = Column(Integer, nullable=True)


class SimulationTeamResult(CreatedAtMixin, Base):
    __tablename__ = "simulation_team_results"
    __table_args__ = (
        CheckConstraint(
            "prob_group_winner IS NULL OR "
            "(prob_group_winner >= 0 AND prob_group_winner <= 1)",
            name="ck_sim_team_results_prob_group_winner_range",
        ),
        CheckConstraint(
            "prob_qualify IS NULL OR (prob_qualify >= 0 AND prob_qualify <= 1)",
            name="ck_sim_team_results_prob_qualify_range",
        ),
        CheckConstraint(
            "prob_round_32 IS NULL OR (prob_round_32 >= 0 AND prob_round_32 <= 1)",
            name="ck_sim_team_results_prob_round_32_range",
        ),
        CheckConstraint(
            "prob_round_16 IS NULL OR (prob_round_16 >= 0 AND prob_round_16 <= 1)",
            name="ck_sim_team_results_prob_round_16_range",
        ),
        CheckConstraint(
            "prob_quarter IS NULL OR (prob_quarter >= 0 AND prob_quarter <= 1)",
            name="ck_sim_team_results_prob_quarter_range",
        ),
        CheckConstraint(
            "prob_semi IS NULL OR (prob_semi >= 0 AND prob_semi <= 1)",
            name="ck_sim_team_results_prob_semi_range",
        ),
        CheckConstraint(
            "prob_final IS NULL OR (prob_final >= 0 AND prob_final <= 1)",
            name="ck_sim_team_results_prob_final_range",
        ),
        CheckConstraint(
            "prob_champion IS NULL OR (prob_champion >= 0 AND prob_champion <= 1)",
            name="ck_sim_team_results_prob_champion_range",
        ),
    )

    id = Column(Integer, primary_key=True)
    simulation_run_id = Column(
        Integer, ForeignKey("simulation_runs.id"), nullable=False
    )
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    prob_group_winner = Column(Float, nullable=True)
    prob_qualify = Column(Float, nullable=True)
    prob_round_32 = Column(Float, nullable=True)
    prob_round_16 = Column(Float, nullable=True)
    prob_quarter = Column(Float, nullable=True)
    prob_semi = Column(Float, nullable=True)
    prob_final = Column(Float, nullable=True)
    prob_champion = Column(Float, nullable=True)


class EvaluationResult(CreatedAtMixin, Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=False)
    actual_score_a = Column(Integer, nullable=False)
    actual_score_b = Column(Integer, nullable=False)
    actual_outcome = Column(String(50), nullable=False)
    log_loss = Column(Float, nullable=True)
    brier_score = Column(Float, nullable=True)
    is_correct_outcome = Column(Boolean, nullable=True)
    is_correct_score = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
