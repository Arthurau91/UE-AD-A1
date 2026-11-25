from json import load, dump
from uuid import uuid4

from ariadne import QueryType, MutationType, make_executable_schema, graphql_sync, load_schema_from_path
from flask import Flask
from graphql import GraphQLError

app = Flask(__name__)

PORT = 3200
HOST = '0.0.0.0'
DB_PATH = "./databases/movies.json"

with open(DB_PATH, 'r') as jsf:
    movies = load(jsf)["movies"]


def write(movies):
    with open(DB_PATH, 'w') as f:
        dump({"movies": movies}, f)


def validate(title=None, rating=None, director=None):
    if title is not None and len(title) > 100:
        raise GraphQLError("title must be at most 100 characters")
    if director is not None and len(director) > 100:
        raise GraphQLError("director must be at most 100 characters")
    if rating is not None and not 0 <= rating <= 10:
        raise GraphQLError("rating must be between 0 and 10")


def find_movie(id):
    return next((m for m in movies if str(m["id"]) == str(id)), None)


query = QueryType()
mutation = MutationType()


@query.field("movies")
def resolve_movies(_, info):
    return movies


@query.field("movie_with_id")
def resolve_movie_with_id(_, info, id):
    return find_movie(id)


@query.field("movie_with_title")
def resolve_movie_with_title(_, info, title):
    return next((m for m in movies if m["title"] == title), None)


@mutation.field("add_movie")
def resolve_add_movie(_, info, title, rating, director):
    validate(title, rating, director)
    movie = {"id": str(uuid4()), "title": title, "rating": rating, "director": director}
    movies.append(movie)
    write(movies)
    return movie


@mutation.field("update_movie")
def resolve_update_movie(_, info, id, **fields):
    validate(**fields)
    movie = find_movie(id)
    if movie is None:
        raise GraphQLError("Movie does not exist")
    movie.update({k: v for k, v in fields.items() if v is not None})
    write(movies)
    return movie


@mutation.field("delete_movie")
def resolve_delete_movie(_, info, id):
    movie = find_movie(id)
    if movie is None:
        raise GraphQLError("Movie does not exist")
    movies.remove(movie)
    write(movies)
    return movie


schema = make_executable_schema(load_schema_from_path("movie.graphql"), query, mutation)


@app.route("/graphql", methods=["POST"])
def graphql_server():
    success, result = graphql_sync(schema, request.get_json(), context_value=request, debug=app.debug)
    return jsonify(result), 200 if success else 400
    

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
