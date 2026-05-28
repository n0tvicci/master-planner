from backend.features.yt_shorts.models.topic import Topic


def test_topic_defaults_to_pending():
    topic = Topic(
        id="t1",
        title="Why snipers never aim for center mass",
        misconception="Movies always show chest shots",
        real_answer="Real snipers target the medulla oblongata for instant stop",
        us_curiosity_score=9,
    )
    assert topic.status == "pending"


def test_topic_serializes_correctly():
    topic = Topic(
        id="t1",
        title="Test title",
        misconception="Test misconception",
        real_answer="Test answer",
        us_curiosity_score=8,
    )
    data = topic.model_dump()
    assert data["id"] == "t1"
    assert data["status"] == "pending"
    assert data["us_curiosity_score"] == 8


def test_topic_approved_status():
    topic = Topic(
        id="t2",
        title="Test",
        misconception="X",
        real_answer="Y",
        us_curiosity_score=7,
        status="approved",
    )
    assert topic.status == "approved"
