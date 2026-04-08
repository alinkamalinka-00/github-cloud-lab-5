import sys
import os
import json

# Add webapp to path so we can import app.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "webapp"))


def create_app():
    """Create a test Flask app with Redis mocked out."""
    # Patch redis before importing app
    from unittest.mock import MagicMock, patch
    import importlib

    mock_redis = MagicMock()
    mock_redis.incr.return_value = 42
    mock_redis.ping.return_value = True

    with patch("redis.Redis", return_value=mock_redis):
        import app as flask_app
        importlib.reload(flask_app)
        flask_app.app.config["TESTING"] = True
        return flask_app.app.test_client(), mock_redis


def test_index_returns_200():
    client, _ = create_app()
    response = client.get("/")
    assert response.status_code == 200


def test_index_contains_visit_count():
    client, _ = create_app()
    response = client.get("/")
    assert b"42" in response.data


def test_info_returns_json():
    client, _ = create_app()
    response = client.get("/info")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "hostname" in data
    assert "environment" in data


def test_health_returns_ok():
    client, _ = create_app()
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert data["redis"] == "ok"


def test_health_redis_failure():
    """Health endpoint reports redis failure gracefully."""
    from unittest.mock import MagicMock, patch
    import importlib

    mock_redis = MagicMock()
    mock_redis.ping.side_effect = Exception("Connection refused")
    mock_redis.incr.return_value = 1

    with patch("redis.Redis", return_value=mock_redis):
        import app as flask_app
        importlib.reload(flask_app)
        flask_app.app.config["TESTING"] = True
        client = flask_app.app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert "Connection refused" in data["redis"]
