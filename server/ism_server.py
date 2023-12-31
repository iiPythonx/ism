# Copyright 2023 iiPython

# Modules
import os
import secrets
import logging
from typing import Dict
from pathlib import Path
from hashlib import sha256
from json import dumps, loads

from blacksheep import (
    json, redirect, bad_request, unauthorized,
    Application, Request, Response
)
from blacksheep.server.templating import use_templates
from jinja2 import FileSystemLoader

# Initialization
base_dir = Path(__file__).parent
logging.basicConfig(
    format = "[%(levelname)s] %(message)s",
    level = logging.INFO
)

app = Application()
app.use_sessions(os.urandom(128))
app.serve_files(base_dir / "static", root_path = "static")

view = use_templates(app, loader = FileSystemLoader(base_dir / "templates"))

# Handle access token
access_token = os.environ.get("ACCESS_TOKEN", "").strip()
if not access_token:
    logging.warn("No access token present! It it highly recommended that you add one.")
    access_token = None

# Setup data recording
data_path = base_dir / "data"
tokens_file = data_path / "tokens.json"
os.makedirs(data_path, exist_ok = True)

def get_tokens() -> Dict[str, Dict[str, str]]:
    if not tokens_file.is_file():
        return {}

    with open(tokens_file, "r") as fh:
        return loads(fh.read())

def add_token(ip: str, hostname: str, token: str) -> None:
    tokens = get_tokens()
    tokens[ip] = {"hostname": hostname, "token": token}
    with open(tokens_file, "w+") as fh:
        fh.write(dumps(tokens))

@app.route("/api/upload", methods = ["POST"])
async def api_upload(request: Request) -> Response:
    data = await request.json()
    if data is None:
        return bad_request({"success": False, "error": "Missing payload."})

    try:
        data, auth = data["data"], data["auth"]
        correct_token = get_tokens()[request.client_ip]["token"]
        if correct_token != auth["token"]:
            return unauthorized({"success": False, "error": "Invalid client token."})

    except (IndexError, KeyError):
        return json({"success": False, "error": "Invalid request."})

    path, logs = data_path / (auth["hostname"] + ".json"), []
    if path.is_file():
        with open(path, "r") as fh:
            logs = loads(fh.read())

    logs.append(data)
    with open(path, "w+") as fh:
        fh.write(dumps(logs[-4320:]))

    return json({"success": True})

@app.route("/api/add", methods = ["POST"])
async def api_add(request: Request) -> Response:
    if "logged_in" not in request.session:
        return json({"success": False, "error": "You are not logged in."})

    data = await request.json()
    if data is None:
        return json({"success": False, "error": "Missing payload."})

    elif not all([data.get("hostname", "").strip(), data.get("ip", "").strip()]):
        return json({"success": False, "error": "Parameters cannot be empty."})

    token = secrets.token_hex(16)
    add_token(data["ip"], data["hostname"], token)
    return json({"success": True, "token": token})

@app.route("/api/logs", methods = ["GET"])
async def api_logs(request: Request) -> Response:
    if "logged_in" not in request.session:
        return json({"success": False, "error": "You are not logged in."})

    log_data = {}
    for file in os.listdir(data_path):
        if file == "tokens.json":
            continue

        with open(data_path / file, "r") as fh:
            log_data[file.removesuffix(".json")] = loads(fh.read())

    return json(log_data)

# Public routing
@app.route("/", methods = ["GET"])
async def route_index(request: Request) -> Response:
    if "logged_in" in request.session:
        return redirect("/dashboard")

    return redirect("/login")

@app.route("/logout", methods = ["GET"])
async def route_logout(request: Request) -> Response:
    if "logged_in" in request.session:
        del request.session["logged_in"]

    return redirect("/login")

@app.route("/login", methods = ["GET", "POST"])
async def route_login(request: Request) -> Response:
    if access_token is None:
        request.session["logged_in"] = True
        return redirect("/dashboard")

    elif "logged_in" in request.session:
        return redirect("/dashboard")

    # Handle posting
    elif request.method == "POST":
        data = await request.form()
        if "token" not in data:
            return bad_request("Missing token!")

        elif sha256(data["token"].encode()).hexdigest() != access_token:
            return unauthorized("Invalid token!")

        request.session["logged_in"] = True
        return redirect("/dashboard")

    return view("login", {})

@app.route("/dashboard", methods = ["GET"])
async def route_dashboard(request: Request) -> Response:
    if "logged_in" not in request.session:
        return redirect("/login")

    return view("dashboard", {})

