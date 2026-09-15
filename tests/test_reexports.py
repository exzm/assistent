from app import db_middleware, exceptions
from app.services import textutil


def test_reexports():
    assert textutil.clip_telegram("a") == "a"
    assert db_middleware.setup_logging is not None
    assert exceptions.HelperBotError is not None
