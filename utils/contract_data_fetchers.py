import sys
import traceback

from multiversx_sdk import Address, ContractQueryBuilder, ProxyNetworkProvider

from utils.logger import get_logger
from utils.utils_chain import base64_to_hex
from typing import List, Any

logger = get_logger(__name__)


class DataFetcher:
    def __init__(self, contract_address: Address, proxy_url: str):
        self.proxy = ProxyNetworkProvider(proxy_url)
        self.contract_address = contract_address
        self.view_handler_map = {}

    def get_data(self, view_name: str, attrs: List[Any] = []) -> Any:
        if view_name in self.view_handler_map:
            return self.view_handler_map[view_name](view_name, attrs)
        else:
            logger.error(f"View name not registered in {type(self).__name__}")
            raise ValueError(f"View name not registered in {type(self).__name__}")

    def _query_contract(self, view_name: str, attrs: List[Any] = []):
        builder = ContractQueryBuilder(
            contract=self.contract_address,
            function=view_name,
            call_arguments=attrs
        )
        query = builder.build()
        return self.proxy.query_contract(query)

    def _get_int_view(self, view_name: str, attrs: List[Any]) -> int:
        result = None
        try:
            result = self._query_contract(view_name, attrs)
            if len(result.return_data) == 0 or result.return_data[0] == "":
                return 0
            return int(base64_to_hex(result.return_data[0]), base=16)
        except Exception as ex:
            logger.exception(f"Exception encountered on view name {view_name}: {ex}")
            if result:
                logger.debug(f"Response content: {result.to_dictionary()}")
        return -1

    def _get_int_list_view(self, view_name: str, attrs: List[Any]) -> List[int]:
        result = None
        try:
            result = self._query_contract(view_name, attrs)
            return [int(base64_to_hex(elem), base=16) for elem in result.return_data]
        except Exception as ex:
            logger.exception(f"Exception encountered on view name {view_name}: {ex}")
            if result:
                logger.debug(f"Response content: {result.to_dictionary()}")
        return []

    def _get_hex_view(self, view_name: str, attrs: List[Any]) -> str:
        result = None
        try:
            result = self._query_contract(view_name, attrs)
            if len(result.return_data) == 0 or result.return_data[0] == "":
                return ""
            return base64_to_hex(result.return_data[0])
        except Exception as ex:
            logger.exception(f"Exception encountered on view name {view_name}: {ex}")
            if result:
                logger.debug(f"Response content: {result.to_dictionary()}")
        return ""

    def _get_hex_list_view(self, view_name: str, attrs: List[Any]) -> List[str]:
        result = None
        try:
            result = self._query_contract(view_name, attrs)
            return [base64_to_hex(elem) for elem in result.return_data]
        except Exception as ex:
            logger.exception(f"Exception encountered on view name {view_name}: {ex}")
            if result:
                logger.debug(f"Response content: {result.to_dictionary()}")
        return []


class LockedAssetContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getLockedAssetTokenId": self._get_hex_view,
            "getAssetTokenId": self._get_hex_view,
        }


class ProxyContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getWrappedLpTokenId": self._get_hex_view,
            "getWrappedFarmTokenId": self._get_hex_view,
            "getAssetTokenId": self._get_hex_view,
            "getLockedTokenIds": self._get_hex_list_view,
        }


class RouterContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getAllPairsManagedAddresses": self._get_hex_list_view,
            "getPairTemplateAddress": self._get_hex_view
        }


class PriceDiscoveryContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "totalLpTokensReceived": self._get_int_view,
            "getAcceptedTokenFinalAmount": self._get_int_view,
            "getLaunchedTokenFinalAmount": self._get_int_view,
            "getStartEpoch": self._get_int_view,
            "getEndEpoch": self._get_int_view,
            "getRedeemTokenId": self._get_hex_view,
        }

    def get_token_reserve(self, token_ticker: str) -> int:
        data = self.proxy.get_fungible_token_of_account(self.contract_address, token_ticker)
        return data.balance


class FarmContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getFarmTokenSupply": self._get_int_view,
            "getFarmingTokenReserve": self._get_int_view,
            "getLastRewardBlockNonce": self._get_int_view,
            "getPerBlockRewardAmount": self._get_int_view,
            "getRewardPerShare": self._get_int_view,
            "getRewardReserve": self._get_int_view,
            "getUndistributedFees": self._get_int_view,
            "getCurrentBlockFee": self._get_int_view,
            "getDivisionSafetyConstant": self._get_int_view,
            "getFarmTokenId": self._get_hex_view,
            "getFarmingTokenId": self._get_hex_view,
            "getRewardTokenId": self._get_hex_view,
            "getState": self._get_int_view,
            "getPairContractManagedAddress": self._get_hex_view,
            "getUserTotalFarmPosition": self._get_hex_view,
            "getCurrentWeek": self._get_int_view,            
            "getFirstWeekStartEpoch": self._get_int_view,
            "getLastGlobalUpdateWeek": self._get_int_view,
            "getUserEnergyForWeek": self._get_hex_view,
            "getLastActiveWeekForUser": self._get_int_view,
            "getCurrentClaimProgress": self._get_hex_view,
            "getFarmSupplyForWeek": self._get_int_view,
            "getTotalLockedTokensForWeek": self._get_int_view,
            "getTotalEnergyForWeek": self._get_int_view,
            "getTotalRewardsForWeek": self._get_int_view,
            "getRemainingBoostedRewardsToDistribute": self._get_int_view,
            "getUndistributedBoostedRewards": self._get_int_view,
            "getPermissions": self._get_int_view,
        }


class StakingContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getFarmTokenSupply": self._get_int_view,
            "getLastRewardBlockNonce": self._get_int_view,
            "getPerBlockRewardAmount": self._get_int_view,
            "getAnnualPercentageRewards": self._get_int_view,
            "getRewardCapacity": self._get_int_view,
            "getRewardReserve": self._get_int_view,
            "getAccumulatedRewards": self._get_int_view,
            "getRewardPerShare": self._get_int_view,
            "getMinUnbondEpochs": self._get_int_view,
            "getDivisionSafetyConstant": self._get_int_view,
            "getFarmTokenId": self._get_hex_view,
            "getFarmingTokenId": self._get_hex_view,
            "getState": self._get_int_view,
            "getUserTotalFarmPosition": self._get_hex_view,
            "getCurrentWeek": self._get_int_view,            
            "getFirstWeekStartEpoch": self._get_int_view,
            "getLastGlobalUpdateWeek": self._get_int_view,
            "getUserEnergyForWeek": self._get_hex_view,
            "getLastActiveWeekForUser": self._get_int_view,
            "getCurrentClaimProgress": self._get_hex_view,
            "getFarmSupplyForWeek": self._get_int_view,
            "getTotalLockedTokensForWeek": self._get_int_view,
            "getTotalEnergyForWeek": self._get_int_view,
            "getTotalRewardsForWeek": self._get_int_view,
            "getRemainingBoostedRewardsToDistribute": self._get_int_view,
            "getUndistributedBoostedRewards": self._get_int_view,
            "getPermissions": self._get_int_view,
        }


class LiquidLockingContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "lockedTokenAmounts": self._get_hex_view,
            "unlockedTokenAmounts": self._get_hex_view,
            "lockedTokens": self._get_hex_list_view,
            "unlockedTokens": self._get_hex_list_view,
            "whitelistedTokens": self._get_hex_list_view,
            "unbondPeriod": self._get_int_view
        }


class BaseFarmContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getFarmTokenSupply": self._get_int_view,
            "getLastRewardBlockNonce": self._get_int_view,
            "getPerBlockRewardAmount": self._get_int_view,
            "getRewardReserve": self._get_int_view,
            "getRewardPerShare": self._get_int_view,
            "getDivisionSafetyConstant": self._get_int_view,
            "getFarmTokenId": self._get_hex_view,
            "getFarmingTokenId": self._get_hex_view,
            "getState": self._get_int_view
        }


class BaseBoostedContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getCurrentWeek": self._get_int_view,            
            "getFirstWeekStartEpoch": self._get_int_view,
            "getLastGlobalUpdateWeek": self._get_int_view,
            "getUserTotalFarmPosition": self._get_hex_view,
            "getUserEnergyForWeek": self._get_hex_view,
            "getLastActiveWeekForUser": self._get_int_view,
            "getCurrentClaimProgress": self._get_hex_view,
            "getFarmSupplyForWeek": self._get_int_view,
            "getTotalLockedTokensForWeek": self._get_int_view,
            "getTotalEnergyForWeek": self._get_int_view,
            "getTotalRewardsForWeek": self._get_int_view,
            "getRemainingBoostedRewardsToDistribute": self._get_int_view,
            "getUndistributedBoostedRewards": self._get_int_view,
        }

class GuildContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getUserStakedTokens": self._get_hex_view,      
            "getUnbondTokenId": self._get_hex_view,            
            "getPermissions": self._get_hex_view,
            "getDivisionSafetyConstant": self._get_int_view,
            "get LastRewardBlockNonce": self._get_int_view,
            "getRewardTokenId": self._get_hex_view,
            "getPerBlockRewardAmount": self._get_int_view,
            "getRewardTokenId": self._get_hex_view,
            "getFarmingTokenId": self._get_hex_view,
            "getRewardReserve": self._get_int_view,
            "getUserRewardPerShare": self._get_int_view,
            "getGuildMasterRewardPerShare": self._get_int_view,
            "getRewardsCapacity": self._get_int_view,
            "getAccumulatedRewards": self._get_int_view,
            "getState": self._get_int_view,
            "getFarmTokenId": self._get_hex_view,
            "getFarmTokenSupply": self._get_int_view,
        }
        
class GuildFactoryDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getAdmins": self._get_hex_view,      
            "getConfigAddress": self._get_hex_view,            
            "getRemainingRewards": self._get_int_view,
            "getAllGuilds": self._get_hex_view,
            "getGuildId": self._get_hex_view,
            "getClosedGuilds": self._get_hex_view,
        }

class GuildConfigDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getGuildMasterTiers": self._get_hex_view,      
            "getUserTiers": self._get_hex_view,            
            "getMaxStakedTokens": self._get_int_view,
            "getMinUnboundEpochsUser": self._get_int_view,
            "getMinUnboundEpochsGuildMaster": self._get_int_view,
            "getMinStakeUser": self._get_int_view,
            "getMinStakeGuildMaster": self._get_int_view,
            "getTotalStakingTokenMinted": self._get_int_view,
            "getTotalStakingTokenStaked": self._get_int_view,
            "getBaseFarmTokenId": self._get_hex_view,
            "getBaseUnbondTokenId": self._get_hex_view,
            "getBaseTokenDisplayName": self._get_hex_view,
            "getTokenDecimals": self._get_hex_view,
            "getSecondsPerBlock": self._get_hex_view,
            "getPerBlockRewardAmount": self._get_int_view,
        }

class ChainDataFetcher:
    def __init__(self, proxy_url: str):
        self.proxy = ProxyNetworkProvider(proxy_url)

    def get_tx_block_nonce(self, txhash: str) -> int:
        if txhash == "":
            print("No hash provided")
            return 0
        try:
            response = self.proxy.get_transaction(txhash)
            return response.block_nonce

        except Exception as ex:
            print("Exception encountered:", ex)
            traceback.print_exception(*sys.exc_info())
            return 0

    def get_current_block_nonce(self) -> int:
        try:
            response = self.proxy.get_network_status(1)
            return response.highest_final_nonce
        except Exception as ex:
            print("Exception encountered:", ex)
            traceback.print_exception(*sys.exc_info())
            return 0
