import asyncio

from qmt_bridge.server.notify.bark import BarkBackend


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def aclose(self) -> None:
        return None

    async def get(self, url: str, params: dict | None = None) -> _FakeResponse:
        self.calls.append((url, params or {}))
        return _FakeResponse()


def test_bark_backend_sends_event_to_bark_url(monkeypatch) -> None:
    fake_client = _FakeClient()

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self._client = fake_client

        async def __aenter__(self) -> _FakeClient:
            return fake_client

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def aclose(self) -> None:
            return None

        async def get(self, url: str, params: dict | None = None) -> _FakeResponse:
            return await self._client.get(url, params=params)

    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)

    async def run_test() -> None:
        backend = BarkBackend("https://api.day.app/abc123")
        await backend.start()
        await backend.send({"type": "trade", "data": {"stock_code": "000001", "price": 10.5}})
        await backend.stop()

        assert fake_client.calls
        url, params = fake_client.calls[0]
        assert url.startswith("https://api.day.app/abc123/")
        assert "%E6%88%90%E4%BA%A4%E9%80%9A%E7%9F%A5" in url
        assert params["sound"] == "birdsong"

    asyncio.run(run_test())
