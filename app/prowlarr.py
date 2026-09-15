from dataclasses import dataclass

import httpx


@dataclass
class Indexer:
    id: int
    name: str
    enable: bool
    privacy: str
    tags: list[int]


@dataclass
class Tag:
    id: int
    label: str


class ProwlarrClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-Api-Key": api_key},
            transport=transport,
            timeout=15.0,
        )

    def get_indexers(self) -> list[Indexer]:
        response = self._client.get("/api/v1/indexer")
        response.raise_for_status()
        return [
            Indexer(
                id=item["id"],
                name=item["name"],
                enable=item["enable"],
                privacy=item["privacy"],
                tags=item.get("tags", []),
            )
            for item in response.json()
        ]

    def get_tags(self) -> list[Tag]:
        response = self._client.get("/api/v1/tag")
        response.raise_for_status()
        return [Tag(id=item["id"], label=item["label"]) for item in response.json()]

    def close(self) -> None:
        self._client.close()
