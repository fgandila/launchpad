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

class LaunchpadContractDataFetcher(DataFetcher):
    def __init__(self, contract_address: Address, proxy_url: str):
        super().__init__(contract_address, proxy_url)
        self.view_handler_map = {
            "getNumberOfConfirmedTicketsForAddress": self._get_int_view,      
            "getTotalNumberOfTicketsForAddress": self._get_int_view,            
            "getTotalNumberOfTickets": self._get_int_view,
            "getTicketRangeForAddress": self._get_hex_view,
            "getNumberOfWinningTickets": self._get_int_view,
            "getTicketPrice": self._get_hex_view,
            "getConfiguration": self._get_hex_view,
            "getLaunchpadTokenId": self._get_hex_view,
            "getLaunchStageFlags": self._get_hex_view,
            "getUserTicketsStatus": self._get_hex_view,
            "getUnlockSchedule": self._get_hex_view,
            "getUserClaimedBalance": self._get_int_view,
            "getUserTotalClaimableBalance": self._get_int_view,
            "getClaimableTokens": self._get_int_view,
            "hasUserClaimedTokens": self._get_hex_view,
        }

    def get_token_reserve(self, token_ticker: str) -> int:
        data = self.proxy.get_fungible_token_of_account(self.contract_address, token_ticker)
        return data.balance