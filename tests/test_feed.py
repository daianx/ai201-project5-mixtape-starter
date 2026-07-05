"""
tests/test_feed.py — Mixtape

Tests for feed service logic.
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent
from services.feed_service import get_friends_listening_now


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
        u1 = User(username="user1", email="u1@example.com")
        u2 = User(username="user2", email="u2@example.com")
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        
        u1.friends.append(u2)
        u2.friends.append(u1)
        
        song = Song(title="Test Song", artist="Test Artist", shared_by=u1.id)
        db.session.add(song)
        db.session.commit()
        
        yield u1.id, u2.id, song.id


def test_friends_listening_now_excludes_old_events(app, test_data):
    """
    Events older than the 1-hour threshold should be excluded from 'listening now'.
    """
    user1_id, user2_id, song_id = test_data
    
    with app.app_context():
        now = datetime.now(timezone.utc)
        
        # friend listened 30 minutes ago (within threshold)
        recent_event = ListeningEvent(user_id=user2_id, song_id=song_id, listened_at=now - timedelta(minutes=30))
        db.session.add(recent_event)
        db.session.commit()
        
        feed = get_friends_listening_now(user1_id)
        assert len(feed) == 1
        assert feed[0]["friend"]["username"] == "user2"
        
        # test the negative case: older than threshold
        recent_event.listened_at = now - timedelta(hours=2)
        db.session.commit()
        
        feed_empty = get_friends_listening_now(user1_id)
        assert len(feed_empty) == 0


def test_friends_listening_now_deduplicates(app, test_data):
    """
    If a friend listened to multiple songs, only the most recent one is returned.
    """
    user1_id, user2_id, song_id = test_data
    
    with app.app_context():
        now = datetime.now(timezone.utc)
        
        # older event (45 mins ago)
        event1 = ListeningEvent(user_id=user2_id, song_id=song_id, listened_at=now - timedelta(minutes=45))
        # newer event (15 mins ago)
        event2 = ListeningEvent(user_id=user2_id, song_id=song_id, listened_at=now - timedelta(minutes=15))
        
        db.session.add_all([event1, event2])
        db.session.commit()
        
        feed = get_friends_listening_now(user1_id)
        assert len(feed) == 1
        assert feed[0]["listened_at"] == event2.listened_at.isoformat()
