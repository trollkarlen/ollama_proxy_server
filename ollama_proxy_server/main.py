"""
project: ollama_proxy_server
file: main.py
author: ParisNeo
description: This is a proxy server that adds a security layer to one or multiple ollama servers
and routes the requests to the right server in order to minimize the charge of the server.
"""

import configparser
import argparse
import json
import datetime
import uuid

# import queue
import csv
import logging

from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

import jwt
import requests

# logging.basicConfig(
#        format='[%(asctime)s] %(levelname)s %(module)s.%(funcName)s %(filename)s:%(lineno)d - %(message)s',
##        format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
#        level=logging.INFO)

from ollama_proxy_server import ollama_queues
from ollama_proxy_server.ollama_logger import get_logger
from ollama_proxy_server.envdefault import EnvDefault

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(module)s.%(funcName)s %(filename)s:%(lineno)d - %(message)s",
    level=logging.DEBUG,
)

_LOG = None


def get_config(filename, readf="read"):
    """
    Read config from config file and parse it
    """
    config = configparser.ConfigParser({"model_white_list": "[]", "model_black_list": "[]"})
    getattr(config, readf)(filename)
    return [
        (
            name,
            {
                "url": config[name]["url"],
                # "queue": queue.Queue(maxsize=1),
                # "last_model": (None, datetime.datetime.now()),
                "model_wl": json.loads(config.get(name, "model_white_list")) or None,
                "model_bl": json.loads(config.get(name, "model_black_list")) or None,
                # add last seen so we pause servers that are offline
            },
        )
        for name in config.sections()
    ]


def jwt_decode(key, encoded):
    """decode jwt data with key"""
    return jwt.decode(encoded, key, audience="urn:ollama_proxy", algorithms="HS256")


# Read the authorized users and their keys from a file
def get_authorized_users(filename):
    """
    Read user and passwords from condig file
    """
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    authorized_users = {}
    for line in lines:
        if line == "":
            continue
        try:
            user, key = line.strip().split(":")
            authorized_users[user] = key
        except Exception:
            _LOG.exception("User entry broken: '%s'", line.strip())
    return authorized_users


def main():
    """
    Main function for proxy
    """
    global _LOG  # pylint: disable=global-statement
    _LOG = get_logger("ollama_proxy_server.main", "INFO")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-k",
        "--jwt-key",
        default=None,
        required=False,
        action=EnvDefault,
        envvar="JWT_KEY",
        help="Specify the JWT_KEY to use when creating users, needs to be the same as the proxy server(can also be specified using JWT_KEY environment variable)",
    )
    parser.add_argument("--config", default="config.ini", help="Path to the authorized users list")
    parser.add_argument("--log_path", default="access_log.txt", help="Path to the access log file")
    parser.add_argument("--users_list", default="authorized_users.txt", help="Path to the config file")
    parser.add_argument("--port", type=int, default=8000, help="Port number for the server")
    parser.add_argument("-d", "--deactivate_security", action="store_true", help="Deactivates security")
    args = parser.parse_args()
    _LOG.debug(args)
    servers = get_config(args.config)
    _LOG.debug(servers)

    server_queue = ollama_queues.ModelLoadedQueue(servers)

    authorized_users = get_authorized_users(args.users_list)
    deactivate_security = args.deactivate_security
    jwt_key = args.jwt_key
    _LOG.info("Ollama Proxy server")
    _LOG.info("Author: ParisNeo")

    class RequestHandler(BaseHTTPRequestHandler):
        """
        Request handler for the proxy server
        Will be one for each request
        """

        _response_sent = False
        _user = "unknown"
        _jwt_payload = None

        # def __init__(self, request, client_address, server):
        #     super().__init__(request, client_address, server)

        def add_access_log_entry(
            self,
            rid,
            event,
            ip_address,
            access,
            server,
            nb_queued_requests_on_server,
            error="",
        ):  # pylint: disable=too-many-positional-arguments
            """
            Logs acccess to file with extra info
            """
            log_file_path = Path(args.log_path)
            fieldnames = [
                "time_stamp",
                "request_id",
                "event",
                "user_name",
                "ip_address",
                "access",
                "server",
                "nb_queued_requests_on_server",
                "error",
            ]

            if not log_file_path.exists():
                with open(log_file_path, mode="w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

            with open(log_file_path, mode="a", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                row = {
                    "time_stamp": str(datetime.datetime.now()),
                    "request_id": rid,
                    "event": event,
                    "user_name": self._user,
                    "ip_address": ip_address,
                    "access": access,
                    "server": server,
                    "nb_queued_requests_on_server": nb_queued_requests_on_server,
                    "error": error,
                }
                writer.writerow(row)

        def _send_response(self, response):
            self.send_response(response.status_code)
            self._response_sent = True
            for key, value in response.headers.items():
                if key.lower() not in [
                    "content-length",
                    "transfer-encoding",
                    "content-encoding",
                ]:
                    self.send_header(key, value)
            # self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()

            try:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except BrokenPipeError:
                _LOG.exception("issue while writing response")

        def do_HEAD(self):  # pylint: disable=invalid-name
            """
            HEAD requests is callbacked here
            """
            self.log_request()
            self.proxy()

        def do_GET(self):  # pylint: disable=invalid-name
            """
            GET requests is callbacked here
            """
            self.log_request()
            self.proxy()

        def do_POST(self):  # pylint: disable=invalid-name
            """
            POST requests is callbacked here
            """
            self.log_request()
            self.proxy()

        def _validate_user_and_key(self):
            try:
                # Extract the bearer token from the headers
                auth_header = self.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return False
                token = auth_header.split(" ")[1]
                try:
                    user, key = token.split(":")
                except ValueError as e:
                    # try to jwt decode
                    if jwt_key:
                        self._jwt_payload = jwt_decode(jwt_key, token)
                        self._user = self._jwt_payload["user"]
                        return True
                    # raise or return False
                    raise e
                # Check if the user and key are in the list of authorized users
                if authorized_users.get(user) == key:
                    self._user = user
                    return True
                # is this needed ?
                # self._user = "unknown"
                return False
            except Exception:
                _LOG.exception("validate user exception")
                return False

        def proxy(self):
            """
            Main proxy function that handles all requests
            """
            rid = uuid.uuid4()
            client_ip, _ = self.client_address

            def log_access(event="rejected", access="Denied", server=None, error=""):
                self.add_access_log_entry(
                    rid=rid,
                    event=event,
                    ip_address=client_ip,
                    access=access,
                    server=server[0] if server else "None",
                    nb_queued_requests_on_server=server_queue.get_length(server[0]) if server else -1,
                    error=error,
                )

            # is this needed ?
            # self._user = "unknown"
            if not deactivate_security and not self._validate_user_and_key():
                _LOG.warning("User is not authorized")
                # Extract the bearer token from the headers
                auth_header = self.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    log_access(
                        error="Authentication failed",
                    )
                else:
                    log_access(
                        error="Authentication failed",
                    )
                self.send_response(403)
                self.end_headers()
                return
            url = urlparse(self.path)
            path = url.path
            get_params = parse_qs(url.query) or {}

            if self.command == "POST":
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                post_params = post_data  # parse_qs(post_data.decode('utf-8'))
            else:
                post_params = {}

            # Apply the queuing mechanism only for a specific endpoint.
            if path in ("/api/generate", "/api/chat", "/v1/chat/completions"):
                try:
                    post_data_dict = {}
                    if isinstance(post_data, bytes):
                        post_data_str = post_data.decode("utf-8")
                        post_data_dict = json.loads(post_data_str)

                        min_queued_server = server_queue.enqueue(post_data_dict)
                        _LOG.debug("sending request to server %s", min_queued_server[0] if min_queued_server else None)

                except (json.JSONDecodeError, json.decoder.JSONDecodeError) as ex:
                    _LOG.exception(rid)
                    log_access(
                        event="request_error",
                        access="Authorized",
                        error=ex,
                    )
                    self.send_error(400, "bad request could not decode")
                    return
                except Exception as ex:
                    _LOG.exception(rid)
                    log_access(
                        event="internal_error",
                        access="Authorized",
                        server=min_queued_server,
                        error=ex,
                    )
                    self.send_error(500, "internal error please contact proxy admin")
                    return

                log_access(
                    event="gen_request",
                    access="Authorized",
                    server=min_queued_server,
                )
                response = None
                try:
                    self._response_sent = False
                    # connect and request timeout
                    response = requests.request(
                        self.command,
                        min_queued_server[1]["url"] + path,
                        params=get_params,
                        data=post_params,
                        stream=post_data_dict.get("stream", False),
                        timeout=(5, 120),
                    )
                    # set last model used
                    #                    if response.ok:
                    #                        min_queued_server[1]["last_model"] = (
                    #                            model,
                    #                            datetime.datetime.now(),
                    #                        )
                    self._send_response(response)
                except requests.exceptions.Timeout as ex:
                    _LOG.exception(rid)
                    log_access(
                        event="gen_error",
                        access="Authorized",
                        server=min_queued_server,
                        error=ex,
                    )
                    if not self._response_sent:
                        self.send_error(408, "the remote server timeout please try again")
                except Exception as ex:
                    _LOG.exception(rid)
                    log_access(
                        event="gen_error",
                        access="Authorized",
                        server=min_queued_server,
                        error=ex,
                    )
                    if not self._response_sent:
                        self.send_error(
                            500,
                            "internal error during proxy please contact proxy admin",
                        )
                finally:
                    if min_queued_server:
                        server_queue.dequeue(min_queued_server[0], response and response.ok)
                    log_access(event="gen_done", access="Authorized", server=min_queued_server)
            else:
                # For other endpoints, just mirror the request.
                response = requests.request(
                    self.command,
                    min_queued_server[1]["url"] + path,
                    params=get_params,
                    data=post_params,
                    timeout=(5, 120),
                )
                self._send_response(response)

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """
        Threaded http server
        """

    _LOG.info("Starting server")
    server = ThreadedHTTPServer(("", args.port), RequestHandler)  # Set the entry port here.
    server.timeout = 300
    _LOG.info("Running server on port %s", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
