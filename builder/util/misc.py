from typing import Iterable, Union


def flatten(l: list) -> list:
    def _flatten(xs):
        for el in xs:
            if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
                yield from _flatten(el)
            else:
                yield el

    return list(_flatten(l))


def listify(d: dict[str, Union[str, list[str]]], k: str) -> list[str]:
    return flatten([d.get(k, [])])
