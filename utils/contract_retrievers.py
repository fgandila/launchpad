from typing import Optional

from contracts.contract_identities import PairContractVersion, RouterContractVersion, \
    FarmContractVersion, StakingContractVersion, ProxyContractVersion, MetaStakingContractVersion
from contracts.farm_contract import FarmContract
from contracts.fees_collector_contract import FeesCollectorContract
from contracts.guild_contract import GuildContract
import config
from contracts.router_contract import RouterContract
from contracts.staking_contract import StakingContract
from contracts.unstaker_contract import UnstakerContract
from utils.contract_data_fetchers import GuildContractDataFetcher, \
    FarmContractDataFetcher, StakingContractDataFetcher, \
    ProxyContractDataFetcher, LockedAssetContractDataFetcher
from utils.utils_chain import hex_to_string, WrapperAddress as Address


def retrieve_farm_by_address(address: str) -> Optional[FarmContract]:
    data_fetcher = FarmContractDataFetcher(Address(address), config.DEFAULT_PROXY)
    farming_token = hex_to_string(data_fetcher.get_data("getFarmingTokenId"))
    farm_token = hex_to_string(data_fetcher.get_data("getFarmTokenId"))
    farmed_token = hex_to_string(data_fetcher.get_data("getRewardTokenId"))
    version = FarmContractVersion.V2Boosted    # TODO: find a way to determine this automatically

    if not farming_token or not farmed_token:
        return None

    contract = FarmContract(farming_token, farm_token, farmed_token, address, version)
    return contract

def retrieve_guild_by_address(address: str) -> Optional[GuildContract]:
    data_fetcher = GuildContractDataFetcher(Address(address), config.DEFAULT_PROXY)
    farming_token = hex_to_string(data_fetcher.get_data("getFarmingTokenId"))
    farm_token = hex_to_string(data_fetcher.get_data("getFarmTokenId"))
    farmed_token = hex_to_string(data_fetcher.get_data("getRewardTokenId"))
    version = FarmContractVersion.V2Boosted
    contract = GuildContract(farming_token, farm_token, farmed_token, address, version)
    return contract

def retrieve_router_by_address(address: str) -> Optional[RouterContract]:
    version = RouterContractVersion.V1  # TODO: find a way to determine this automatically

    contract = RouterContract(version, address)
    return contract

def retrieve_unstaker_by_address(address: str) -> Optional[UnstakerContract]:
    contract = UnstakerContract(address)
    return contract


def retrieve_fees_collector_by_address(address: str) -> Optional[FeesCollectorContract]:
    contract = FeesCollectorContract(address)
    return contract


def retrieve_staking_by_address(address: str, version: StakingContractVersion) -> Optional[StakingContract]:
    data_fetcher = StakingContractDataFetcher(Address(address), config.DEFAULT_PROXY)
    farming_token = hex_to_string(data_fetcher.get_data("getFarmingTokenId"))
    farm_token = hex_to_string(data_fetcher.get_data("getFarmTokenId"))
    max_apr = data_fetcher.get_data("getAnnualPercentageRewards")
    unbond_epochs = data_fetcher.get_data("getMinUnbondEpochs")
    rewards_per_block = data_fetcher.get_data("getPerBlockRewardAmount")

    contract = StakingContract(farming_token, max_apr, rewards_per_block, unbond_epochs, version,
                               farm_token, address)
    return contract




def retrieve_contract_by_address(address: str, contract_type: type):
    if contract_type == RouterContract:
        return retrieve_router_by_address(address)

    if contract_type == FarmContract:
        return retrieve_farm_by_address(address)

    if contract_type == UnstakerContract:
        return retrieve_unstaker_by_address(address)

    if contract_type == FeesCollectorContract:
        return retrieve_fees_collector_by_address(address)
