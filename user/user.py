"""User API"""

import json
from datetime import datetime, timedelta, timezone
from os import environ
from pathlib import Path

import jwt
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request
from pymongo import MongoClient
from bson.json_util import dumps

from werkzeug.exceptions import NotFound

# Local runs: read the shared .env at the repo root (Docker injects it via env_file)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
JWT_SECRET = environ["JWT_SECRET"]

app = Flask(__name__)

PORT = 3203
HOST = '0.0.0.0'
client = MongoClient('mongodb://root:example@mongo:27017/')
db=client['user_database']
collection=db['users']


with open('{}/databases/users.json'.format("."), "r", encoding="utf-8") as jsf:
    users = json.load(jsf)["users"]

collection.insert_many(users)

ROLES = ("user", "admin")


def caller_from_token():
    """Decode the Bearer token and return its claims with the current role from the DB."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        claims = jwt.decode(header[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    user = collection.find_one({"id": claims["sub"]})
    if user is None:
        return None
    return {"sub": claims["sub"], "role": user.get("role", "user")}

@app.route("/", methods=['GET'])
def get_users():
    """get all users

    Returns:
        Json: A list of all users data
    """
    return make_response(dumps(collection.find()), 200)

@app.route("/login", methods=['POST'])
def login():
    """Issue a JWT for an existing user

    Returns:
        Json: The auth_token, or an error with its status code
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("id")
    if not user_id or not isinstance(user_id, str):
        return make_response(jsonify({"error": "id is required"}), 400)
    user = collection.find_one({"id": user_id})
    if user is None:
        return make_response(jsonify({"error": "Unknown user"}), 401)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user_id, "admin": user.get("role", "user") == "admin",
         "iat": now, "exp": now + timedelta(hours=1)},
        JWT_SECRET,
        algorithm="HS256",
    )
    return make_response(jsonify({"auth_token": token}), 200)

@app.route("/<user_id>", methods=['GET'])
def get_user(user_id):
    """get a single user by ID

    Args:
        user_id (string): The ID of the user to retrieve

    Raises:
        NotFound: If the user with the specified ID is not found

    Returns:
        dict: The user data if found
    """
    user = collection.find_one({"id": user_id})
    if user is None:
        raise NotFound(description="User not found")
    return make_response(dumps(user), 200)

@app.route("/", methods=['POST'])
def create_user():
    """Create a new user

    Returns:
        Json: Validation message and status code
    """
    data = request.get_json()
    if not data or "id" not in data or "name" not in data:
        return make_response(jsonify({"error": "Invalid user data"}), 400)
    data["role"] = "user"
    collection.insert_one(data)
    return make_response(jsonify({"message": "User created successfully"}), 201)

@app.route("/<user_id>", methods=['PUT'])
def update_user(user_id):
    """Update a user

    Args:
        user_id (string): The ID of the user to update

    Raises:
        NotFound: If the user with the specified ID is not found

    Returns:
        Json: Validation message and status code
    """
    data = request.get_json()
    if not data or "name" not in data:
        return make_response(jsonify({"error": "Invalid user data"}), 400)
    changes = {"name": data["name"]}
    if "role" in data:
        if data["role"] not in ROLES:
            return make_response(jsonify({"error": "Invalid role"}), 400)
        caller = caller_from_token()
        if caller is None or caller.get("role") != "admin":
            return make_response(jsonify({"error": "Admin token required to change role"}), 403)
        if caller["sub"] == user_id:
            return make_response(jsonify({"error": "You cannot change your own role"}), 403)
        changes["role"] = data["role"]
    result = collection.update_one({"id": user_id}, {"$set": changes})
    if result.matched_count == 0:
        raise NotFound(description="User not found")
    return make_response(jsonify({"message": "User updated successfully"}), 200)

@app.route("/<user_id>", methods=['DELETE'])
def delete_user(user_id):
    """User deletion

    Args:
        user_id (string): The ID of the user to delete

    Raises:
        NotFound: If the user with the specified ID is not found

    Returns:
        Json: Validation message and status code
    """
    result = collection.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise NotFound(description="User not found")
    return make_response(jsonify({"message": "User deleted successfully"}), 200)

if __name__ == "__main__":
    print("Server running in port %s"%(PORT))
    app.run(host=HOST, port=PORT)
