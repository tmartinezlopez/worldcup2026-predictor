from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.batch_seed import seed_batches
from src.db.models import Batch


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_seed_batches_creates_batches():
    session = _session()

    result = seed_batches(session)
    batches = session.scalars(select(Batch).order_by(Batch.sequence_order)).all()

    assert result["created"] > 0
    assert batches


def test_seed_batches_does_not_duplicate():
    session = _session()

    first = seed_batches(session)
    second = seed_batches(session)

    assert first["created"] > 0
    assert second["created"] == 0
    assert second["skipped"] >= first["created"]
