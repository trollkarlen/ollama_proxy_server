"""
simple queue
shedules the server with the shortest queue
"""

import time
import queue
import datetime

# from ollama_proxy_server.ollama_logger import get_logger
from .base_queue import BaseQueue

# _log = get_logger(__name__)


class SimpleQueue(BaseQueue):
    """
    class for simple queue
    """

    _name = __name__

    def enqueue(self, filter_=None, timeout=0):
        """gets the server that can serve the request"""
        return self._wait_for_server(self._servers, self._get_shortes_queue, timeout=timeout)

    def get_length(self, server_name):
        """retruns the length of the queue for a server"""
        return self._queues[server_name].qsize()

    def _wait_for_server(self, servers, func, timeout=0):
        """waits untill a server can handle the request sent"""
        old_server = None
        server = None
        start = time.time()

        while True:
            que, server = func(servers)
            # We have not servers to schedule on
            if server is None:
                # raise ValueError exception instead ?
                return None
            if server[0] != old_server:
                self._log.debug("changing server to %s", server[0])
            try:
                if timeout > 0:
                    put_timeout = min(0.5, max(0.0001, (time.time() - start) - timeout))
                else:
                    put_timeout = 0.5
                que.put(1, timeout=put_timeout)
                break
            except queue.Full as exc:
                if timeout > 0 and (time.time() - start - timeout) <= 0:  # pylint: disable=chained-comparison
                    raise TimeoutError("No avalibe server within {timeout}s") from exc
                self._log.debug("try to requeue")
                old_server = server

        return server

    def _get_shortes_queue(self, servers):
        """
        Get the shortest queue from all servers
        """

        if len(servers) == 0:
            return None, None

        min_queued_server = servers[0]
        if min_queued_server[0] not in self._queues:
            self._queues[min_queued_server[0]] = queue.Queue(maxsize=self._max_queue_size)

        que = self._queues[min_queued_server[0]]

        # TODO: speed this up  # pylint: disable=fixme
        for server in servers:
            sname = server[0]
            if sname not in self._queues:
                self._queues[sname] = queue.Queue(maxsize=self._max_queue_size)
            if self._queues[sname].qsize() < self._queues[min_queued_server[0]].qsize():
                min_queued_server = server
                que = self._queues[sname]
            # cant be less then zero so bail out here
            if que.qsize() == 0:
                return que, min_queued_server
        return que, min_queued_server

    def dequeue(self, server_name, ok=False):
        """removes a request from the servers queue"""
        if ok:
            self._servers_dict[server_name][1]["last_seen"] = datetime.datetime.now()
        self._queues[server_name].get_nowait()
