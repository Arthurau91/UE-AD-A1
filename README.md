# UE-AD-A1 – Cinema microservices (REST + GraphQL)

Four small Python/Flask services for a cinema application, built for the IMT Atlantique UE-AD course.

| Service  | Port | API     | Role                                              | API docs (OpenAPI) |
|----------|------|---------|---------------------------------------------------|------|
| Movie    | 3200 | GraphQL | Movie catalogue                                   | [movie/docs/movie.yaml](movie/docs/movie.yaml) |
| Booking  | 3201 | GraphQL | Users' bookings (JWT-protected)                   | [booking/docs/booking.yaml](booking/docs/booking.yaml) |
| Schedule | 3202 | REST    | Which movies are shown on which date              | [schedule/docs/schedule.yaml](schedule/docs/schedule.yaml) |
| User     | 3203 | REST    | Users (MongoDB) and JWT login                     | [user/docs/user.yaml](user/docs/user.yaml) |

Booking calls Schedule (REST) to validate a booking and Movie (GraphQL) to enrich booking details. It trusts the
JWT issued by User, so both share the same `JWT_SECRET`.

## Install and run with Docker (recommended)

Requirements: Docker with Compose.

```bash
cp .env.example .env        # then set JWT_SECRET to a long random string
docker compose up --build
```

The services are then on `localhost:3200`–`3203`. Docker Compose also starts MongoDB (27017) and
mongo-express (http://localhost:8081).

## Run locally (without Docker)

Requirements: Python 3.12+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Set `JWT_SECRET` in your environment, then start each service from its own folder (they read `./databases/...`):

```bash
cd movie    && python movie.py
cd schedule && python schedule.py
cd booking  && python booking.py   # SCHEDULE_URL / MOVIE_URL can override the defaults
```

The User service connects to the `mongo` host, so it only works through Docker Compose
(`docker compose up --build user mongo`).

## Try it

1. Log in: `curl -X POST localhost:3203/login -H "Content-Type: application/json" -d '{"id":"chris_rivers"}'`
2. Use the returned `auth_token` in Booking GraphQL operations (see [booking/docs/booking.yaml](booking/docs/booking.yaml)).

A demo front end that shows every request and response lives in the separate `UE-AD-A1-DEMO-FRONT` project
(`npm install && npm run dev`, proxies to ports 3200–3203).

## Project layout

```
movie/      GraphQL movie service (movie.graphql, movie.py, databases/, docs/)
booking/    GraphQL booking service
schedule/   REST schedule service
user/       REST user service + JWT login
docker-compose.yml, requirements.txt (shared), .env.example
```
