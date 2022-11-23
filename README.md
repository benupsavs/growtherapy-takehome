# Grow Therapy Take Home Project

## Quick Start

### Docker
The easiest way to be up and running is to use docker-compose. The API service is exposed on port `8080`.

```bash
$ docker-compose up --build
```

### Local
To run locally, you would first need to set up Redis, and then update config.yml to point to the correct Redis host. Run the following commands and the API should be up and running in debug mode on port 5000.

```bash
$ python -m venv venv
$ venv/bin/activate
$ pip install -r requirements.txt
$ python app.py
```

## Run Tests
```bash
$ py.test
```

## APIs
All APIs return JSON data.

### Top articles by month
`GET /top/month/<year>/<month>/<year>`
```bash
$ curl --request GET \
  --url http://localhost:5000/top/month/2022/10
```

### Top articles by week
`GET /top/week/<year>/<week>`
```
$ curl --request GET \
  --url http://localhost:5000/top/week/2022/47
```

### Day of month with highest view count for article
`GET /articles/top/day/<year>/<month>/<article name>`
```bash
$ curl --request GET \
  --url http://localhost:5000/articles/top/day/2022/09/Main_Page
```

### Note on dates
Because the number of weeks in a year are not cleanly divisible into the year, this API considers that a year has 52 weeks, and one partial week. If week 53 is chosen, all days that occur within the given year are considered part of the week, and therefore the week will be shorter than seven days.

## Architecture

### Components
#### Main
- Flask
- Flask-Restful
- Redis

#### Test
- PyTest
- PyTest-Mock

### Layers
- Resources:  Controller/Business Logic
- Repository: Access to stored data in Wikipedia and the cache

app.py is the main entrypoint, since this is a Flask service. app.py creates the wikipedia REST repository, wraps it in a caching repository, and sets up the rest resources that handle the incoming requests.

When a user requests top articles for a month, or the day with top views for a month, the cache is read-through by day for the entire month.
For any days that are missing from the cache, a redlock is obtained, preventing multiple threads from fetching the same day's cached data.
All readers will properly block until the wikipedia data has downloaded.

### Cache
- Top articles for day
- Top articles for month
- Top articles for week

The top articles for month and week are not technically required but they avoid doing aggregation and large cache fetches for the summary data.
The top day in month for article is not cached, and it uses aggregation to render, primarily because there are so many articles, combined with so many available months, and the usage pattern would likely leave a lot of stale data in the cache.

## Notes
I used Windows 11 to write this in, just for fun, since I normally use Linux. In case you are interested, the experience was as good as Linux. Aside from the line endings, there should be no noticable difference in the deliverable.

If I were to do this again, I would not use flask-restful. It doesn't have type stubs, and error handling is awkward.

There is some opportunity in the wikipedia repo to remove duplicated code, though it could complicate the codebase and create a *spaghetti code* situation.

There are missing tests in the repo and resource packages, but I ran short on time, unfortunately.

In production I would also add observability, and fire off some stats in the repo.

In practice, it's not the best idea to block on reading from a remote API. If latency on a request for uncached data is a concern, there are two available options. The first is understanding data access requirements and pre-caching required data. The second idea is to return a different response when the data is not all available, and instruct the client to retry after a certain time. Once the result is available, the client will retrieve the result. This wouldn't be very difficult to implement either, but would put some burden on the client to retry for cache miss scenarios.
