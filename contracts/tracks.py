import json
from os import path
from pathlib import Path
from typing import Any, Dict, List, Union

from multiversx_sdk import Address

from utils.shared import get_shard_of_address


class TrackOfContract:
    def __init__(self, name: str, index: int, deployer: Address, address: Address, state: Union[Dict[str, Any], None], status: str = ""):
        self.name = name
        self.index = index
        self.deployer = deployer
        self.address = address
        self.state = state or dict()
        self.status = status or ""

        self.key = f"{name}_{index}_{address.bech32()}"

    def to_plain(self):
        plain = {
            "key": self.key,
            "name": self.name,
            "index": self.index,
            "deployer": self.deployer.bech32(),
            "address": self.address.bech32(),
            "state": self.state,
            "status": self.status
        }

        return plain

    def __repr__(self) -> str:
        return json.dumps(self.to_plain(), indent=4)

    def is_status_known(self):
        return len(self.status) > 0

    def is_status_unknown(self):
        return not self.is_status_known()

    def is_ok_or_unknown(self):
        return self.status == "deploy_ok" or self.is_status_unknown()

    def mark_as_ok(self):
        self.status = "deploy_ok"

    def mark_as_nok(self):
        self.status = "deploy_nok"


class TracksOfContracts:
    def __init__(self):
        self._tracks_by_key: Dict[str, TrackOfContract] = dict()

    @classmethod
    def load(cls, file: Path):
        instance = cls()
        if not path.isfile(file):
            raise Exception(f"{file} is not a file, thus tracks cannot be loaded.")

        with open(file) as f:
            data = json.load(f)

        for item in data:
            track = TrackOfContract(item["name"], item["index"], Address(item["deployer"]), Address(item["address"]), item["state"], item.get("status", None))
            instance.put_track(track)

        return instance

    @classmethod
    def load_many(cls, files: Union[List[str], List[Path]]):
        result = [cls.load(Path(file)) for file in files]
        return result

    @classmethod
    def load_many_as_union(cls, files: Union[List[str], List[Path]]):
        result: List[TrackOfContract] = []

        for tracks in cls.load_many(files):
            result.extend(tracks.get_all())

        return result

    def get_by_key(self, key: str) -> Union[TrackOfContract, None]:
        return self._tracks_by_key.get(key, None)

    def put_track(self, track: TrackOfContract):
        self._tracks_by_key[track.key] = track

    def __repr__(self) -> str:
        return json.dumps(self.to_plain(), indent=4)

    def to_plain(self):
        return [track.to_plain() for track in self._tracks_by_key.values() if track.is_ok_or_unknown()]

    def get_all(self) -> List[TrackOfContract]:
        return list(self._tracks_by_key.values())


def filter_bunch_of_tracks_by_shard(all: List[TrackOfContract], shard: str) -> List[TrackOfContract]:
    filtered = []
    if shard:
        filtered = [track for track in all if get_shard_of_address(track.address) == int(shard)]
    else:
        filtered = all

    print(f"Filtered tracks by shard = {shard}. Original = {len(all)}, filtered = {len(filtered)}.")
    return filtered


def filter_bunch_of_tracks_by_enabled_contracts(all: List[TrackOfContract], registry: Any):
    filtered = [track for track in all if registry.is_enabled_by_name(track.name)]
    print(f"Filtered tracks by (contract-is-enabled). Original = {len(all)}, filtered = {len(filtered)}.")
    return filtered
