"""
tests/test_notifications.py — Mixtape

Tests for notification service logic.
"""

import pytest
from app import create_app, db
from models import User, Song
from services.notification_service import rate_song, get_notifications


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def test_data(app):
    with app.app_context():
        u1 = User(username="sharer", email="sharer@example.com")
        u2 = User(username="rater", email="rater@example.com")
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        song = Song(title="Test Song", artist="Test Artist", shared_by=u1.id)
        db.session.add(song)
        db.session.commit()

        yield u1.id, u2.id, song.id


def test_rate_song_creates_notification(app, test_data):
    """Rating a song should notify the original sharer."""
    sharer_id, rater_id, song_id = test_data

    with app.app_context():
        # Before rating, sharer has 0 notifications
        notifs = get_notifications(sharer_id)
        assert len(notifs) == 0

        # Rate the song
        rate_song(rater_id, song_id, 5)

        # Sharer should have 1 notification
        notifs = get_notifications(sharer_id)
        assert len(notifs) == 1
        assert notifs[0]["type"] == "song_rated"
        assert "rated your song" in notifs[0]["body"]
        
def test_rate_own_song_no_notification(app, test_data):
    """Rating your own song should not create a notification."""
    sharer_id, rater_id, song_id = test_data

    with app.app_context():
        # Rate own song
        rate_song(sharer_id, song_id, 4)

        # Sharer should have 0 notifications
        notifs = get_notifications(sharer_id)
        assert len(notifs) == 0
