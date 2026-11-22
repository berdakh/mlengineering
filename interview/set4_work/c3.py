"""Interview set 4, prompt C3. Replace the bodies; keep the interface."""


class TimeWindowStats:
    def __init__(self, horizon_s: float):
        raise NotImplementedError

    def push(self, t: float, x: float) -> None:
        raise NotImplementedError

    def mean(self) -> float:
        raise NotImplementedError

    def std(self) -> float:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
