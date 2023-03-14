import typing as t


class NoData:
    pass

NO_DATA = NoData()
EventCallback = t.Callable[[t.Any], t.Any]
CommandCallback = t.Callable