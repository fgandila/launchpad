from abc import abstractmethod, ABC
from enum import Enum

from utils.utils_chain import Account
from multiversx_sdk import ProxyNetworkProvider


class DEXContractIdentityInterface(ABC):

    address: str = NotImplemented


class DEXContractInterface(ABC):

    address: str = NotImplemented

    @abstractmethod
    def get_config_dict(self) -> dict:
        pass

    @classmethod
    @abstractmethod
    def load_config_dict(cls, config_dict: dict):
        pass

    @classmethod
    @abstractmethod
    def load_contract_by_address(cls, address: str):
        pass

    @abstractmethod
    def contract_deploy(self, deployer: Account, proxy: ProxyNetworkProvider, bytecode_path, args: list):
        pass

    @abstractmethod
    def contract_start(self, deployer: Account, proxy: ProxyNetworkProvider, args: list = None):
        pass

    @abstractmethod
    def print_contract_info(self):
        pass


class PriceDiscoveryContractIdentity(DEXContractIdentityInterface):
    launched_token_id: str
    accepted_token: str
    redeem_token: str
    first_redeem_token_nonce: int
    second_redeem_token_nonce: int
    address: str
    locking_sc_address: str
    min_launched_token_price: int
    start_block: int
    no_limit_phase_duration_blocks: int
    linear_penalty_phase_duration_blocks: int
    fixed_penalty_phase_duration_blocks: int
    unlock_epoch: int
    min_penalty_percentage: int
    max_penalty_percentage: int
    fixed_penalty_percentage: int


class ProxyContractVersion(Enum):
    V1 = 1
    V2 = 2

class RouterContractVersion(Enum):
    V1 = 1
    V2 = 2