"""
for adding users to authorized_users.txt
"""

import sys
import uuid
import argparse
import datetime

import jwt

from envdefault import EnvDefault


def encode_user_jwt(jwt_key, user, email=None):
    """Stupid test function"""
    user_uuid = uuid.uuid4()
    dtnow = datetime.datetime.now(tz=datetime.timezone.utc)
    user_dict = {
        "user": user,
        "email": email,
        "user_uuid": str(user_uuid),
        # here we can have models and more
        "aud": ["urn:ollama_proxy"],
        "iat": int(dtnow.strftime("%s")),
        "exp": int((dtnow + datetime.timedelta(weeks=52 * 5)).strftime("%s")),
    }
    print(user_dict)
    encoded = jwt.encode(user_dict, jwt_key, algorithm="HS256")
    return user_dict, encoded


def main():
    """
    main entry
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-k",
        "--jwt-key",
        action=EnvDefault,
        envvar="JWT_KEY",
        help="Specify the JWT_KEY to use when creating users, needs to be the same as the proxy server(can also be specified using JWT_KEY environment variable)",
    )
    parser.add_argument(
        "-e",
        "--email",
        required=False,
        default=None,
        action=EnvDefault,
        envvar="USER_EMAIL",
        help="Specify the email to use when creating user(can also be specified using USER_MAIL environment variable)",
    )
    parser.add_argument("user")
    args = parser.parse_args()

    user_dict, encoded = encode_user_jwt(args.jwt_key, args.user, args.email)

    print(user_dict, file=sys.stderr)
    print(encoded)


if __name__ == "__main__":
    main()
