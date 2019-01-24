from redis import Redis
from rq import Queue


class Storage:
    __instance = None

    def __init__(self):
        redis_conn = Redis()
        self.queue = Queue(connection=redis_conn)
        self.redis = Redis(host='localhost', port=6379, db=1)

    @staticmethod
    def instance():
        if not Storage.__instance:
            Storage.__instance = Storage()
        return Storage.__instance
