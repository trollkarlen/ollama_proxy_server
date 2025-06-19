"""
model queue it sends request primary to nodes that already have the model loaded
"""

import datetime
# from ollama_proxy_server.ollama_logger import get_logger

from .simple_queue import SimpleQueue

# _log = get_logger(__name__)


class ModelLoadedQueue(SimpleQueue):
    """
    this queue prioritize servers with the model requested loaded to the gpus
    """

    _name = __name__

    def enqueue(self, filter_=None, timeout=0):
        """gets the server that can serve the request"""
        model = None
        if filter_ and "model" in filter_:
            model = filter_["model"]
        servers = self._get_servers_with_model(self._servers, model)
        servers = self._get_servers_with_loaded_model(servers, model)
        server = self._wait_for_server(servers, self._get_shortes_queue, timeout=timeout)
        self._log.debug("enqueue on server %s", server[0] if server else None)
        if server:
            server[1]["last_model"] = (model, server[1]["last_model"][1])
        return server

    def _get_servers_with_loaded_model(self, servers, model):
        """get all servers with the loaded model"""
        # TODO: implemet keep_alive like mentioned here  # pylint: disable=fixme
        # https://github.com/ollama/ollama/issues/1600
        lservers = []
        for server in servers:
            cs = server[1]
            if "last_model" not in cs:
                cs["last_model"] = (None, datetime.datetime.now() - datetime.timedelta(weeks=-(5 * 52)))
            lm = cs["last_model"]
            if model == lm[0] and datetime.datetime.now() > (lm[1] + datetime.timedelta(minutes=4, seconds=30)):
                lservers.append(server)

        # TODO: reove dupo and make this better
        # prio loaded models
        return lservers + servers

    def _get_servers_with_model(self, servers, model=None):
        """gets the servers that can handle a specific model"""
        if model:
            lservers = []
            for server in servers:
                cs = server[1]
                # white list trumph blacklist
                if cs["model_wl"] and model in cs["model_wl"]:
                    lservers.append(server)
                elif cs["model_bl"] is None or (cs["model_bl"] and model not in cs["model_bl"]):
                    lservers.append(server)
            return lservers
        return self._servers

    def dequeue(self, server_name, ok=False):
        """removed the server from queue"""
        if ok:
            self._servers_dict[server_name][1]["last_model"] = (
                self._servers_dict[server_name][1]["last_model"][0],
                datetime.datetime.now(),
            )
        super().dequeue(server_name, ok)
