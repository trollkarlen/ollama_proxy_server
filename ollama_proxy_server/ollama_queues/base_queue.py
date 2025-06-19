"""
Base class for different queue implementation's
"""

from ollama_proxy_server.ollama_logger import get_logger


class BaseQueue:
    """
    The base class
    """

    _name = __name__

    def __init__(self, servers, max_queue_size=1):
        """
        Init for base class
        """
        self._queues = {}
        self._servers = servers
        self._servers_dict = {}
        self._max_queue_size = max_queue_size
        self._log = get_logger(self._name, "INFO")

        for server in self._servers:
            self._servers_dict[server[0]] = server

    def add_server(self, server):
        """
        add server to be scheduled
        """
        # make sure we dont update
        self._servers[server[0]] = server

    def delete_server(self, server_name):
        """
        remove server from scheduling
        """
        del self._servers[server_name]

    def enqueue(self, filter_=None, timeout=0):
        """
        blocks until the server with the shortest queue can handle the request

        filter:     a dict that can include
            model:  the model requested
            user:   the user doing the request
        timeout:    timeout float in seconds to block until giving up, raises TimeoutError

        returns
            server  the server that can handle the request

        """
        raise NotImplementedError("Function not implemented")

    def get_length(self, server_name):
        """
        Gets the queue length of server

            server_name:    the server name to get length from
        """
        raise NotImplementedError("Function not implemented")

    def dequeue(self, server_name, ok=False):
        """
        removes us from the queue

            server_name:    the server name to dequeue
            ok:             if the request was a succcess or not

        """
        raise NotImplementedError("Function not implemented")
