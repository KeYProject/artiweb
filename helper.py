from typing import Any


class ObjDict(object):
    def __init__(self, d) -> None:
        self._dict = d

    def __getattribute__(self, __name: str) -> Any:
        obj = self._dict[__name]
        if isinstance(obj, dict):
            return ObjDict(obj)
        return obj
