import json

import pytest

from antenna_pattern_lab.collector import PskReporterCollector


def test_topic_for_own_ft8_spots():
    assert PskReporterCollector.topic("ok7ps", "20m", "ft8") == (
        "pskr/filter/v2/20m/FT8/OK7PS/#"
    )


@pytest.mark.parametrize("call", ["", "OK7PS/#", "+"])
def test_topic_rejects_unsafe_call(call):
    with pytest.raises(ValueError):
        PskReporterCollector.topic(call)


def test_connect_callback_reports_confirmed_subscription():
    states = []
    collector = PskReporterCollector(lambda _spot: None, on_connection=lambda *args: states.append(args))
    collector._topic = "pskr/filter/v2/20m/FT8/OK7PS/#"

    class Client:
        subscribed = None

        def subscribe(self, topic, qos):
            self.subscribed = (topic, qos)

    client = Client()
    collector._handle_connect(client, None, None, 0, None)
    assert client.subscribed == (collector._topic, 0)
    assert states == [("connected", collector._topic)]


def test_field_topic_is_routed_to_activity_not_own_spots():
    own, activity = [], []
    collector = PskReporterCollector(own.append, on_activity=activity.append)
    topic = "pskr/filter/v2_field/20m/FT8/+/JO"
    collector._activity_topics = {topic}

    class Message:
        payload = json.dumps(
            {
                "t": 1_700_000_000,
                "f": 14_074_000,
                "md": "FT8",
                "rp": -10,
                "sc": "OTHER",
                "sl": "JN79",
                "rc": "DL1RX",
                "rl": "JO62",
                "b": "20m",
            }
        ).encode()

    Message.topic = topic
    collector._handle_message(None, None, Message())
    assert own == []
    assert len(activity) == 1
