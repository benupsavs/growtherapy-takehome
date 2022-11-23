from flask import Flask
from flask_restful import Api
import redis
import yaml

from repo.wikipedia import WikipediaCachingRepo, WikipediaRestRepo
from resource.article import TopDayForArticle, TopViewsForMonth, TopViewsForWeek

errors = {
    'ValueError': {
        'message': "The input was not valid.",
        'status': 400,
    },
    'WikipediaFetchException': {
        'message': "Error fetching from Wikipedia.",
        'status': 504,
    },
    'DataNotFoundException': {
        'message': "The requested data was not found.",
        'status': 404,
    },
}

app = Flask(__name__)
app.logger.setLevel('INFO')
api = Api(app, errors=errors)


with open('config.yml') as f:
    config = yaml.safe_load(f)

redis_pool = redis.Redis(host=config.get('redis_host'),
                         port=config.get('redis_port'))

wikipedia_repo = WikipediaCachingRepo(
    WikipediaRestRepo(
        max_concurrency=config["wikipedia_fetch_concurrency"], logger=app.logger),
    redis_pool,
    logger=app.logger,
)


api.add_resource(TopViewsForMonth,
                 '/top/month/<int:year>/<int:month>', resource_class_kwargs={"logger": app.logger, "wikipedia_repo": wikipedia_repo})
api.add_resource(TopViewsForWeek,
                 '/top/week/<int:year>/<int:week>', resource_class_kwargs={"logger": app.logger, "wikipedia_repo": wikipedia_repo})
api.add_resource(TopDayForArticle, '/articles/top/day/<int:year>/<int:month>/<article_name>',
                 resource_class_kwargs={"logger": app.logger, "wikipedia_repo": wikipedia_repo})

if __name__ == '__main__':
    app.logger.setLevel('DEBUG')
    app.run(debug=True)
