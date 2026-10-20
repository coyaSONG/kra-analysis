"""Regression contracts for the audited HTTP and JWT dependency fixes."""

import base64
import gc
import hashlib
import hmac
import json
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path

import jwt
import pytest
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived
from h2.exceptions import ProtocolError
from multidict import CIMultiDict, MultiDict
from packaging.version import Version

from dependencies import auth

pytestmark = pytest.mark.unit

HMAC_MATERIAL = "dependency-test-only-" * 3
BASE_HEADERS = [
    (":method", "GET"),
    (":scheme", "https"),
    (":authority", "fixture.example"),
    (":path", "/"),
]


@pytest.mark.parametrize(
    ("package", "minimum"),
    [("h2", "4.4.1"), ("multidict", "6.9.1"), ("pyjwt", "2.15.1")],
)
def test_locked_and_exported_versions_match_safe_runtime(package, minimum):
    root = Path(__file__).resolve().parents[4]
    lock = tomllib.loads((root / "uv.lock").read_text())
    locked = next(
        item["version"] for item in lock["package"] if item["name"] == package
    )
    requirements = (root / "apps/api/requirements.txt").read_text().splitlines()
    assert f"{package}=={locked}" in requirements
    assert Version(locked) >= Version(minimum)
    assert Version(version(package)) == Version(locked)


@pytest.mark.parametrize(
    "hosts",
    [
        ["fixture.example", "fixture.example"],
        ["fixture.example", "other.example"],
        ["other.example", "fixture.example"],
    ],
)
def test_http2_rejects_duplicate_host_headers(hosts):
    client = H2Connection(
        config=H2Configuration(client_side=True, validate_outbound_headers=False)
    )
    server = H2Connection(config=H2Configuration(client_side=False))
    client.initiate_connection()
    server.initiate_connection()
    client.send_headers(
        1, BASE_HEADERS + [("host", host) for host in hosts], end_stream=True
    )
    with pytest.raises(ProtocolError):
        server.receive_data(client.data_to_send())


def test_http2_accepts_a_single_matching_host():
    client = H2Connection(config=H2Configuration(client_side=True))
    server = H2Connection(
        config=H2Configuration(client_side=False, header_encoding="utf-8")
    )
    client.initiate_connection()
    server.initiate_connection()
    client.send_headers(
        1, BASE_HEADERS + [("host", "fixture.example")], end_stream=True
    )
    events = server.receive_data(client.data_to_send())
    request = next(event for event in events if isinstance(event, RequestReceived))
    assert request.headers == BASE_HEADERS + [("host", "fixture.example")]


@pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="The affected C-extension reference count is a CPython contract",
)
@pytest.mark.parametrize("mapping", [MultiDict, CIMultiDict])
@pytest.mark.parametrize("operation", ["reflected_union", "subtraction"])
def test_multidict_items_operations_release_operand_references(mapping, operation):
    headers = mapping({"seed": "value"})
    sentinel = object()
    operand = [(f"k{i}", sentinel) for i in range(3)]
    gc.collect()
    before = sys.getrefcount(sentinel)
    if operation == "reflected_union":
        result = operand | headers.items()
        assert result == set(operand) | {("seed", "value")}
    else:
        result = headers.items() - operand
        assert result == {("seed", "value")}
    del result
    gc.collect()
    assert sys.getrefcount(sentinel) == before


@pytest.mark.parametrize("decoder", [jwt.decode, jwt.decode_complete])
def test_jwt_options_are_not_mutated_and_claims_are_rechecked(decoder):
    token = jwt.encode(
        {"sub": "fixture-user", "exp": 1}, HMAC_MATERIAL, algorithm="HS256"
    )
    options = {"verify_signature": False}
    decoder(token, HMAC_MATERIAL, algorithms=["HS256"], options=options)
    assert options == {"verify_signature": False}
    options["verify_signature"] = True
    with pytest.raises(jwt.ExpiredSignatureError):
        decoder(token, HMAC_MATERIAL, algorithms=["HS256"], options=options)


@pytest.fixture
def jwt_settings(monkeypatch):
    monkeypatch.setattr(auth.settings, "secret_key", HMAC_MATERIAL)
    monkeypatch.setattr(auth.settings, "algorithm", "HS256")


def test_jwt_round_trip_preserves_registered_claim_validation(jwt_settings):
    token = auth.create_access_token({"sub": "fixture-user"})
    assert auth.verify_token(token)["sub"] == "fixture-user"
    expired = jwt.encode(
        {"sub": "fixture-user", "exp": 1}, HMAC_MATERIAL, algorithm="HS256"
    )
    assert auth.verify_token(expired) is None
    wrong_algorithm = jwt.encode(
        {"sub": "fixture-user"}, HMAC_MATERIAL, algorithm="HS384"
    )
    assert auth.verify_token(wrong_algorithm) is None


@pytest.mark.parametrize("claim", ["exp", "nbf", "iat"])
@pytest.mark.parametrize("value", [None, [], {}])
def test_malformed_numeric_claims_follow_the_auth_error_contract(
    jwt_settings, claim, value
):
    token = jwt.encode(
        {"sub": "fixture-user", claim: value}, HMAC_MATERIAL, algorithm="HS256"
    )
    assert auth.verify_token(token) is None


@pytest.mark.parametrize("segment", ["header", "payload"])
def test_json_recursion_errors_follow_the_auth_error_contract(
    jwt_settings, monkeypatch, segment
):
    nested = b'{"nested":' + b"[" * (sys.getrecursionlimit() + 100)
    nested += b"0" + b"]" * (sys.getrecursionlimit() + 100) + b"}"
    if segment == "payload":
        token = jwt.api_jws.encode(nested, HMAC_MATERIAL, algorithm="HS256")
    else:
        header = base64.urlsafe_b64encode(nested).rstrip(b"=").decode()
        token = f"{header}.e30.invalid"
    original_loads = json.loads

    def recursive_loads(value, *args, **kwargs):
        if value == nested:
            raise RecursionError("fixture parser recursion")
        return original_loads(value, *args, **kwargs)

    # CPython's C JSON parser has a separate, platform-dependent nesting limit.
    # Exercise the upstream error boundary deterministically for both segments.
    monkeypatch.setattr(json, "loads", recursive_loads)
    with pytest.raises(jwt.DecodeError) as error:
        jwt.decode(token, HMAC_MATERIAL, algorithms=["HS256"])
    assert isinstance(error.value.__cause__, RecursionError)
    assert auth.verify_token(token) is None


@pytest.mark.parametrize("malformation", ["junk", "noncanonical_pad_bits"])
def test_jwt_rejects_signature_encoding_aliases(jwt_settings, malformation):
    token = auth.create_access_token({"sub": "fixture-user"})
    header, payload, signature = token.split(".")
    if malformation == "junk":
        signature += "!!!!"
    else:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        signature = signature[:-1] + alphabet[alphabet.index(signature[-1]) + 1]
    assert auth.verify_token(f"{header}.{payload}.{signature}") is None


def test_jwt_accepts_canonical_base64url_padding(jwt_settings):
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "fixture-user"}, separators=(",", ":")).encode()
    )
    signing_input = header + b"." + payload
    digest = hmac.new(HMAC_MATERIAL.encode(), signing_input, hashlib.sha256).digest()
    token = signing_input + b"." + base64.urlsafe_b64encode(digest)
    assert auth.verify_token(token.decode())["sub"] == "fixture-user"
