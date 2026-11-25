"""User API"""

import json

from flask import Flask, jsonify, make_response, request
from pymongo import MongoClient
from bson.json_util import dumps

from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3203
HOST = '0.0.0.0'
client = MongoClient('mongodb://root:example@mongo:27017/')
db=client['user_database']
collection=db['users']


with open('{}/databases/users.json'.format("."), "r", encoding="utf-8") as jsf:
    users = json.load(jsf)["users"]

collection.insert_many(users)

@app.route("/", methods=['GET'])
def get_users():
    """get all users

    Returns:
        Json: A list of all users data
    """
    return make_response(dumps(collection.find()), 200)

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
    result = collection.update_one({"id": user_id}, {"$set": {"name": data["name"]}})
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
