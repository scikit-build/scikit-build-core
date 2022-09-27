import dataclasses


@dataclasses.dataclass
class CMakeSettings:
    min_version: str = "3.15"
