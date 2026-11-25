# This module implements a booking service that allows users to create,
# retrieve, and delete bookings for movies on specific dates.

import re
from json import load, dump
from os import environ

import requests
from ariadne import QueryType, MutationType, make_executable_schema, graphql_sync, load_schema_from_path
from flask import Flask, jsonify, request
from graphql import GraphQLError

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'
DB_PATH = "./databases/bookings.json"
# URLS for the schedule and movie services, can be overridden by environment variables
SCHEDULE_URL = environ.get("SCHEDULE_URL", "http://localhost:3202")
MOVIE_URL = environ.get("MOVIE_URL", "http://localhost:3200")
TIMEOUT = 5
DATE_PATTERN = re.compile(r"^\d{8}$")

with open(DB_PATH, 'r') as jsf:
    bookings = load(jsf)["bookings"]


def write(bookings):
    with open(DB_PATH, 'w') as f:
        dump({"bookings": bookings}, f)


def find_user(userid):
    return next((b for b in bookings if str(b["userid"]) == str(userid)), None)


def find_date(entry, date):
    return next((d for d in entry["dates"] if str(d["date"]) == str(date)), None)


# Raise if the date is not scheduled or a movie is not shown on that date
def check_schedule(date, movies):
    try:
        r = requests.get(f"{SCHEDULE_URL}/schedule/{date}", timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GraphQLError("Schedule service is unavailable") from exc

    if r.status_code == 404:
        raise GraphQLError("Date is not scheduled")
    if r.status_code != 200:
        raise GraphQLError("Schedule service is unavailable")

    scheduled = r.json().get("movies", [])
    for movie in movies:
        if movie not in scheduled:
            raise GraphQLError(f"Movie {movie} is not scheduled on {date}")


# Fetch a movie from the GraphQL Movie service; returns None if it does not exist
def fetch_movie(movieid: str):
    query = """
    query($id: String!) {
        movie_with_id(id: $id) { id title rating director }
    }
    """
    try:
        r = requests.post(
            f"{MOVIE_URL}/graphql",
            json={"query": query, "variables": {"id": movieid}},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise GraphQLError("Movie service is unavailable") from exc

    if body.get("errors"):
        raise GraphQLError("Movie service is unavailable")
    return (body.get("data") or {}).get("movie_with_id")


query = QueryType()
mutation = MutationType()


@query.field("user_bookings")
def resolve_user_bookings(_, info, userid):
    return find_user(userid)


@query.field("booking_details")
def resolve_booking_details(_, info, userid, date):
    entry = find_user(userid)
    booking = find_date(entry, date) if entry else None
    if booking is None:
        return None
    movies = [fetch_movie(mid) or {"id": mid} for mid in booking["movies"]]
    return {"userid": userid, "date": date, "movies": movies}


@mutation.field("add_booking")
def resolve_add_booking(_, info, userid, date, movies):
    if not DATE_PATTERN.match(date):
        raise GraphQLError("date must be formatted as YYYYMMDD")
    if not movies:
        raise GraphQLError("at least one movie is required")

    check_schedule(date, movies)

    entry = find_user(userid)
    if entry is not None and find_date(entry, date) is not None:
        raise GraphQLError("Booking already exists for this date")
    if entry is None:
        entry = {"userid": userid, "dates": []}
        bookings.append(entry)

    entry["dates"].append({"date": date, "movies": movies})
    write(bookings)
    return entry


@mutation.field("delete_booking")
def resolve_delete_booking(_, info, userid, date):
    entry = find_user(userid)
    if entry is None:
        raise GraphQLError("Booking does not exist")
    if find_date(entry, date) is None:
        raise GraphQLError("No booking for this date")
    entry["dates"] = [d for d in entry["dates"] if str(d["date"]) != str(date)]
    write(bookings)
    return entry


schema = make_executable_schema(load_schema_from_path("booking.graphql"), query, mutation)


@app.route("/graphql", methods=["POST"])
def graphql_server():
    success, result = graphql_sync(schema, request.get_json(), context_value=request, debug=app.debug)
    return jsonify(result), 200 if success else 400


if __name__ == "__main__":
    print("Server running in port %s"%(PORT))
    app.run(host=HOST, port=PORT)
