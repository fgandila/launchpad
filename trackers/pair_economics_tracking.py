from multiversx_sdk import Address
from utils.utils_tx import NetworkProviders
from trackers.abstract_observer import Subscriber
from trackers.concrete_observer import Observable
from utils.contract_data_fetchers import PairContractDataFetcher
from utils.utils_generic import log_step_fail, log_step_pass, log_substep



class PairEconomics(Subscriber):

    def __init__(self, contract_address: str, first_token: str, second_token: str, network_provider: NetworkProviders):
        self.contract_address = Address(contract_address, "erd")
        self.network_provider = network_provider
        self.pair_data_fetcher = PairContractDataFetcher(self.contract_address, self.network_provider.proxy.url)
        self._get_tokens_reserve_and_total_supply()
        self.fee = 0
        self.report_current_tracking_data()
        self.first_token = first_token
        self.second_token = second_token

    def _get_tokens_reserve_and_total_supply(self):
        reserves_and_total_supply = self.pair_data_fetcher.get_data("getReservesAndTotalSupply")
        if reserves_and_total_supply:
            self.first_token_reserve = reserves_and_total_supply[0]
            self.second_token_reserve = reserves_and_total_supply[1]
            self.total_supply = reserves_and_total_supply[2]
        else:
            self.first_token_reserve = 0
            self.second_token_reserve = 0
            self.total_supply = 0

    def report_current_tracking_data(self):
        print(f'Pair contract address: {self.contract_address.bech32()}')
        print(f'First token reserve: {self.first_token_reserve}')
        print(f'Second token reserve: {self.second_token_reserve}')
        print(f'Total supply: {self.total_supply}')

    def update(self, publisher: Observable):
        if publisher.contract is not None:
            if self.contract_address.bech32() == publisher.contract.address:
                if publisher.tx_hash:
                    self.network_provider.wait_for_tx_executed(publisher.tx_hash)
                    self._get_tokens_reserve_and_total_supply()
