# content of conftest.py
import pytest
import datetime

from ollama_proxy_server import ollama_queues
from ollama_proxy_server.main import get_config

test_config = """
[DefaultServer00]
url = http://localhost:11434
model_black_list = ["llama3.2", "llama3.2:1b"]

[LocalServer01]
url = http://localhost:11435
model_black_list = ["llama3.2"]
model_white_list = ["llama3.2", "llama3.2:1b"]

[LocalServer02]
url = http://localhost:11436
model_white_list = []
model_black_list = ["llama3.2:1b"]

# Add more servers as you need.
"""

test_config_all_black = """
[DefaultServer00]
url = http://localhost:11434
model_black_list = ["llama3.2"]

[LocalServer01]
url = http://localhost:11435
model_black_list = ["llama3.2"]
model_white_list = ["llama3.2:1b"]

[LocalServer02]
url = http://localhost:11436
model_white_list = []
model_black_list = ["llama3.2"]

# Add more servers as you need.
"""


@pytest.fixture
def simple_queue():
    servers = get_config(test_config, "read_string")
    mq = ollama_queues.SimpleQueue(servers)
    return servers, mq


@pytest.fixture
def simple_queue_empty_config():
    servers = get_config(test_config)
    mq = ollama_queues.SimpleQueue(servers)
    return servers, mq


@pytest.fixture
def model_queue():
    servers = get_config(test_config, "read_string")
    mq = ollama_queues.ModelLoadedQueue(servers)
    return servers, mq


@pytest.fixture
def model_queue_bl():
    servers = get_config(test_config_all_black, "read_string")
    mq = ollama_queues.ModelLoadedQueue(servers)
    return servers, mq


@pytest.fixture
def model_queue_empty_config():
    servers = get_config(test_config)
    mq = ollama_queues.ModelLoadedQueue(servers)
    return servers, mq


class TestSimpleQueue:
    def test_simple_queue_empty(self, simple_queue_empty_config):
        """
        No servers should return None
        """
        servers, mq = simple_queue_empty_config
        assert isinstance(mq, ollama_queues.SimpleQueue)

        ms = mq.enqueue()
        assert ms is None

    def test_simple_queue_basic(self, simple_queue):
        """
        Should return first server
        """
        servers, mq = simple_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0])

    def test_simple_queue_dequeue(self, simple_queue):
        """
        Should return first server
        """
        servers, mq = simple_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0], ok=True)

        ls = servers[0][1]["last_seen"]
        assert ls <= datetime.datetime.now() - datetime.timedelta(microseconds=2)

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0], ok=False)

        assert servers[0][1]["last_seen"] == ls

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0], ok=1)

        assert servers[0][1]["last_seen"] <= datetime.datetime.now() - datetime.timedelta(microseconds=2)

    def test_simple_queue_dequeue_exception(self, simple_queue):
        """
        Should return first server
        """
        servers, mq = simple_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        with pytest.raises(KeyError):
            mq.dequeue(servers[0][0])

    def test_simple_queue_order_and_dequeue(self, simple_queue):
        """
        Should return servers in order from config
        """
        servers, mq = simple_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        for i in range(len(servers)):
            ms = mq.enqueue()
            assert ms[0] == servers[i][0]
            assert mq.get_length(servers[i][0]) == 1

        for i in range(len(servers)):
            mq.dequeue(servers[i][0])

        # check order again
        for i in range(len(servers)):
            ms = mq.enqueue()
            assert ms[0] == servers[i][0]
            assert mq.get_length(servers[i][0]) == 1

        for i in range(len(servers)):
            mq.dequeue(servers[i][0])

    def test_simple_queue_blocking(self, simple_queue):
        """
        Should return block when all is full
        """
        servers, mq = simple_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        for i in range(len(servers)):
            ms = mq.enqueue()
            assert ms[0] == servers[i][0]

        with pytest.raises(TimeoutError):
            ms = mq.enqueue(timeout=0.2)

    def test_simple_queue_nofilter(self, simple_queue):
        """
        Should return first server, will ignore filter
        """
        servers, mq = simple_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        sf = {"model": "llama3.2"}
        ms = mq.enqueue(filter_=sf)
        assert ms[0] == servers[0][0]


class TestModelQueue:
    def test_model_queue_empty(self, model_queue_empty_config):
        """
        No servers should return None
        """
        servers, mq = model_queue_empty_config
        assert isinstance(mq, ollama_queues.SimpleQueue)

        ms = mq.enqueue()
        assert ms is None

    def test_model_queue_basic(self, model_queue):
        """
        Should return first server
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0])

    def test_model_queue_dequeue(self, model_queue):
        """
        Should return first server
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0], ok=True)

        ls = servers[0][1]["last_seen"]
        assert ls <= datetime.datetime.now() - datetime.timedelta(microseconds=2)

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0], ok=False)

        assert servers[0][1]["last_seen"] == ls

        ms = mq.enqueue()
        assert ms[0] == servers[0][0]
        mq.dequeue(servers[0][0], ok=1)

        assert servers[0][1]["last_seen"] <= datetime.datetime.now() - datetime.timedelta(microseconds=2)

    def test_model_queue_dequeue_exception(self, model_queue):
        """
        Should return first server
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        with pytest.raises(KeyError):
            mq.dequeue(servers[0][0])

    def test_model_queue_order_and_dequeue(self, model_queue):
        """
        Should return servers in order from config
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        for i in range(len(servers)):
            ms = mq.enqueue()
            assert ms[0] == servers[i][0]
            assert mq.get_length(servers[i][0]) == 1

        for i in range(len(servers)):
            mq.dequeue(servers[i][0])

        # check order again
        for i in range(len(servers)):
            ms = mq.enqueue()
            assert ms[0] == servers[i][0]
            assert mq.get_length(servers[i][0]) == 1

        for i in range(len(servers)):
            mq.dequeue(servers[i][0])

    def test_model_queue_blocking(self, model_queue):
        """
        Should return block when all is full
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        for i in range(len(servers)):
            ms = mq.enqueue()
            assert ms[0] == servers[i][0]

        with pytest.raises(TimeoutError):
            ms = mq.enqueue(timeout=0.2)

    def test_model_queue_filter_basic(self, model_queue):
        """
        Should return second server
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        sf = {"model": "llama3.2"}
        ms = mq.enqueue(filter_=sf)
        assert ms[0] == servers[1][0]

    def test_model_queue_filter_bl(self, model_queue):
        """
        Should return second server
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        sf = {"model": "llama3.2:1b"}
        ms = mq.enqueue(filter_=sf)
        assert ms[0] == servers[1][0]

    def test_model_queue_filter_bl_notarget(self, model_queue):
        """
        Should return second server
        """
        servers, mq = model_queue
        assert isinstance(mq, ollama_queues.SimpleQueue)

        sf = {"model": "llama3.2:1b"}
        ms = mq.enqueue(filter_=sf)
        assert ms[0] == servers[1][0]

        with pytest.raises(TimeoutError):
            ms = mq.enqueue(filter_=sf, timeout=0.2)

        mq.dequeue(servers[1][0])

        with pytest.raises(KeyError):
            mq.dequeue(servers[2][0])

    def test_model_queue_filter_no_target(self, model_queue_bl):
        """
        Should return no server, None
        """
        servers, mq = model_queue_bl
        assert isinstance(mq, ollama_queues.SimpleQueue)

        sf = {"model": "llama3.2"}
        ms = mq.enqueue(filter_=sf)
        assert ms is None
