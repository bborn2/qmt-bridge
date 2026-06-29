"""Bark 推送通知后端。

通过 Bark 服务将交易事件推送到 iPhone 设备。Bark 使用简单的 GET 接口，
本后端会把事件转换为标题和正文，并通过配置的 Bark 服务地址发送。
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote

from .base import NotifierBackend

logger = logging.getLogger("qmt_bridge.notify.bark")


class BarkBackend(NotifierBackend):
    """Bark 通知后端。"""

    def __init__(
        self,
        url: str,
        *,
        sound: str = "birdsong",
        group: str = "",
        icon: str = "",
    ) -> None:
        self._url = url.rstrip("/")
        self._sound = sound
        self._group = group
        self._icon = icon
        self._client = None  # type: ignore[assignment]

    def name(self) -> str:
        return "bark"

    async def start(self) -> None:
        import httpx

        self._client = httpx.AsyncClient(timeout=10.0)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _event_title(event: dict[str, Any]) -> str:
        etype = str(event.get("type", "notify"))
        mapping = {
            "trade": "成交通知",
            "order": "委托更新",
            "order_error": "委托错误",
            "cancel_error": "撤单失败",
            "connected": "交易连接",
            "disconnected": "连接断开",
            "asset": "资产变动",
            "position": "持仓变动",
            "account_status": "账户状态",
            "test": "测试通知",
        }
        return mapping.get(etype, f"通知:{etype}")

    @staticmethod
    def _event_body(event: dict[str, Any]) -> str:
        data = event.get("data", {})
        if isinstance(data, dict):
            try:
                return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            except TypeError:
                return str(data)
        return str(data)

    async def send(self, event: dict) -> None:
        if self._client is None:
            logger.warning("Bark client not started, dropping event")
            return

        title = self._event_title(event)
        body = self._event_body(event)
        encoded_title = quote(title, safe="")
        encoded_body = quote(body, safe="")
        url = f"{self._url}/{encoded_title}/{encoded_body}"

        params: dict[str, str] = {"sound": self._sound}
        if self._group:
            params["group"] = self._group
        if self._icon:
            params["icon"] = self._icon

        resp = await self._client.get(url, params=params)
        if resp.status_code >= 400:
            logger.warning(
                "Bark push failed with %s: %s", resp.status_code, resp.text[:200]
            )
