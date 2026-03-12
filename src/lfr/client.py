from hishel.httpx import SyncCacheClient as Client

from lfr.settings import BASE_URL


def get_client() -> Client:
    return Client(
        base_url=BASE_URL,
    )
