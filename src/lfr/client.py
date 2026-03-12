from hishel.httpx import SyncCacheClient as Client


def get_client() -> Client:
    return Client(
        base_url="https://linuxfr.org",
    )
