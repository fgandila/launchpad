import sys
import traceback
from typing import Any

import config
from contracts.contract_identities import DEXContractInterface
from utils.logger import get_logger
from utils.utils_tx import prepare_contract_call_tx, send_contract_call_tx, NetworkProviders, ESDTToken, \
    multi_esdt_endpoint_call, deploy, endpoint_call
from events.price_discovery_events import (DepositPDLiquidityEvent,
                                           WithdrawPDLiquidityEvent, RedeemPDLPTokensEvent)
from utils.utils_chain import log_explorer_transaction
from utils.utils_generic import log_step_fail, log_step_pass, log_substep, log_warning
from utils.utils_chain import Account, WrapperAddress as Address
from multiversx_sdk import CodeMetadata, ProxyNetworkProvider
from multiversx_sdk import AccountNonceHolder, Address, ProxyNetworkProvider, SmartContractTransactionsFactory, TransactionComputer, \
                            TransactionsFactoryConfig, TransferTransactionsFactory, UserSigner, QueryRunnerAdapter, SmartContractQueriesController
from multiversx_sdk.abi.abi import Abi

logger = get_logger(__name__)
proxy = ProxyNetworkProvider(config.devnet)
abi = Abi.load(config.PRICE_DISCOVERY_ABI)
factory_config = TransactionsFactoryConfig(proxy.get_network_config().chain_id)
transactions_factory = SmartContractTransactionsFactory(factory_config, abi)
query_runner = QueryRunnerAdapter(ProxyNetworkProvider(config.devnet))
query_controller = SmartContractQueriesController(query_runner, abi)

class PriceDiscoveryContract(DEXContractInterface):
    def __init__(self,
                 launched_token_id: str,
                 accepted_token_id: str,
                 redeem_token: str,
                 start_time: int,
                 user_deposit_withdraw_time: int,
                 owner_deposit_withdraw_time: int,
                 user_min_deposit: int,
                 admin: str,
                 ):
        self.launched_token_id = launched_token_id  # launched token
        self.accepted_token = accepted_token_id  # accepted token
        self.redeem_token = redeem_token
        self.start_time = start_time
        self.user_deposit_withdraw_time = user_deposit_withdraw_time
        self.owner_deposit_withdraw_time = owner_deposit_withdraw_time
        self.user_min_deposit = user_min_deposit
        self.admin = admin

    def get_config_dict(self) -> dict:
        output_dict = {
            "launched_token_id": self.launched_token_id,
            "accepted_token": self.accepted_token,
            "redeem_token": self.redeem_token,
            "address": self.address,
            "start_time": self.start_time,
            "user_deposit_withdraw_time": self.user_deposit_withdraw_time,
            "owner_deposit_withdraw_time": self.owner_deposit_withdraw_time,
            "user_min_deposit": self.user_min_deposit,
            "admin": self.admin,
        }
        return output_dict

    @classmethod
    def load_config_dict(cls, config_dict: dict):
        return PriceDiscoveryContract(launched_token_id=config_dict['launched_token_id'],  # launched token
                                      accepted_token_id=config_dict['accepted_token'],  # accepted token
                                      redeem_token=config_dict['redeem_token'],
                                      first_redeem_token_nonce=config_dict['first_redeem_token_nonce'],
                                      # launched token
                                      second_redeem_token_nonce=config_dict['second_redeem_token_nonce'],
                                      # accepted token
                                      address=config_dict['address'],
                                      locking_sc_address=config_dict['locking_sc_address'],
                                      start_block=config_dict['start_block'],
                                      no_limit_phase_duration_blocks=config_dict['no_limit_phase_duration_blocks'],
                                      linear_penalty_phase_duration_blocks=config_dict[
                                          'linear_penalty_phase_duration_blocks'],
                                      fixed_penalty_phase_duration_blocks=config_dict[
                                          'fixed_penalty_phase_duration_blocks'],
                                      unlock_epoch=config_dict['unlock_epoch'],
                                      min_launched_token_price=config_dict['min_launched_token_price'],
                                      min_penalty_percentage=config_dict['min_penalty_percentage'],
                                      max_penalty_percentage=config_dict['max_penalty_percentage'],
                                      fixed_penalty_percentage=config_dict['fixed_penalty_percentage'])
    
    def get_contract_tokens(self) -> list[str]:
        return [self.redeem_token]

    @classmethod
    def load_contract_by_address(cls, address: str):
        raise NotImplementedError

    def deposit_liquidity(self, proxy: ProxyNetworkProvider, user: Account, event: DepositPDLiquidityEvent) -> str:
        function_purpose = f"Deposit Price Discovery liquidity"
        logger.info(function_purpose)
        logger.debug(f"Account: {user.address}")
        logger.debug(f"Token: {event.deposit_token} Amount: {event.amount}")

        gas_limit = 10000000
        tokens = [ESDTToken(event.deposit_token, 0, event.amount)]
        sc_args = [tokens]
        return multi_esdt_endpoint_call(function_purpose, proxy, gas_limit, user,
                                        Address.from_bech32(self.address), "ownerDeposit", sc_args)

    def user_deposit(self, proxy: ProxyNetworkProvider, user: Account, event: DepositPDLiquidityEvent) -> str:
        function_purpose = f"Deposit accepted token"
        logger.info(function_purpose)
        logger.debug(f"Account: {user.address}")
        logger.debug(f"Token: {event.deposit_token} Amount: {event.amount}")

        gas_limit = 10000000
        tokens = [ESDTToken(event.deposit_token, 0, event.amount)]
        sc_args = [tokens]
        return multi_esdt_endpoint_call(function_purpose, proxy, gas_limit, user,
                                        Address.from_bech32(self.address), "userDeposit", sc_args)

    def withdraw_liquidity(self, proxy: ProxyNetworkProvider, user: Account, event: WithdrawPDLiquidityEvent) -> str:
        function_purpose = f"Withdraw Price Discovery liquidity"
        logger.info(function_purpose)
        logger.debug(f"Account: {user.address}")
        logger.debug(f"Token: {event.deposit_lp_token} Nonce: {event.nonce} Amount: {event.amount}")

        gas_limit = 10000000
        tokens = [ESDTToken(event.deposit_lp_token, event.nonce, event.amount)]
        sc_args = [tokens]
        return multi_esdt_endpoint_call(function_purpose, proxy, gas_limit, user,
                                        Address.from_bech32(self.address), "ownerWithdraw", sc_args)

    def user_withdraw(self,proxy: ProxyNetworkProvider, user: Account, event: WithdrawPDLiquidityEvent) -> str:
        function_purpose = f"Withdraw accepted token"
        logger.info(function_purpose)
        logger.debug(f"Account: {user.address}")
        logger.debug(f"Token: {event.deposit_lp_token} Nonce: {event.nonce} Amount: {event.amount}")

        gas_limit = 10000000
        tokens = [ESDTToken(event.deposit_lp_token, event.nonce, event.amount)]
        sc_args = [tokens]
        return multi_esdt_endpoint_call(function_purpose, proxy, gas_limit, user,
                                        Address.from_bech32(self.address), "userWithdraw", sc_args)

    def redeem_liquidity_position(self, proxy: ProxyNetworkProvider, user: Account, event: RedeemPDLPTokensEvent) -> str:
        function_purpose = f"Redeem Price Discovery liquidity"
        logger.info(function_purpose)
        logger.debug(f"Account: {user.address}")
        logger.debug(f"Token: {event.deposit_lp_token} Nonce: {event.nonce} Amount: {event.amount}")

        gas_limit = 10000000
        tokens = [ESDTToken(event.deposit_lp_token, event.nonce, event.amount)]
        sc_args = [tokens] #tokens
        return multi_esdt_endpoint_call(function_purpose, proxy, gas_limit, user,
                                        Address.from_bech32(self.address), "redeem", sc_args)
    
    def owner_redeem(self, proxy: ProxyNetworkProvider, user: Account, event: RedeemPDLPTokensEvent) -> str:
        function_purpose = f"Redeem Price Discovery liquidity"
        logger.info(function_purpose)
        logger.debug(f"Account: {user.address}")
        logger.debug(f"Token: {event.deposit_lp_token} Nonce: {event.nonce} Amount: {event.amount}")

        gas_limit = 10000000
        tokens = [ESDTToken(event.deposit_lp_token, event.nonce, event.amount)]
        sc_args = []

        return endpoint_call(proxy, gas_limit, user, Address.from_bech32(self.address), "redeem", sc_args)

    def add_user_to_whitelist(self, proxy: ProxyNetworkProvider, admin: Account, whitelisted_address: list):
        function_purpose = f"Add user to whitelist"
        logger.info(function_purpose)
        logger.debug(f"Account: {admin.address}")
        data: list[Any] = []
        for address in whitelisted_address:
            data.append([Address.new_from_bech32(address),0])

        sc_args = [
            data
        ]
    
        transaction = transactions_factory.create_transaction_for_execute(
                sender=Address.new_from_bech32(admin.address.to_bech32()),
                contract=Address.new_from_bech32(self.address),
                function="addUsersToWhitelist",
                gas_limit=50_000_000,
                arguments=sc_args
            )
        transaction.nonce = admin.nonce
        transaction.signature = admin.signer.sign(
                    TransactionComputer().compute_bytes_for_signing(transaction)
                    )
       
        result = proxy.send_transaction(transaction)
        transaction = proxy.get_transaction(result) 

        return transaction.get_status()
    
    def refund_users(self, proxy: ProxyNetworkProvider, admin: Account, users_to_refund: list):
        function_purpose = f"Refund users"
        logger.info(function_purpose)
        logger.debug(f"Account: {admin.address}")
        data: list[Any] = []
        for address in users_to_refund:
            data.append(Address.new_from_bech32(address))

        sc_args = [
            data
        ]
    
        transaction = transactions_factory.create_transaction_for_execute(
                sender=Address.new_from_bech32(admin.address.to_bech32()),
                contract=Address.new_from_bech32(self.address),
                function="refundUsers",
                gas_limit=50_000_000,
                arguments=sc_args
            )
        transaction.nonce = admin.nonce
        transaction.signature = admin.signer.sign(
                    TransactionComputer().compute_bytes_for_signing(transaction)
                    )
       
        result = proxy.send_transaction(transaction)
        transaction = proxy.get_transaction(result) 

        return transaction.get_status()
    
    def contract_deploy(self, deployer: Account, proxy: ProxyNetworkProvider, bytecode_path, args: list = []):
        function_purpose = f"Deploy price discovery contract"
        logger.info(function_purpose)

        metadata = CodeMetadata(upgradeable=True, payable_by_contract=True)
        gas_limit = 350000000

        arguments = [
            self.launched_token_id,  # launched token id
            self.accepted_token,  # accepted token id
            18,  # launched token decimals
            self.start_time,            
            self.user_deposit_withdraw_time,
            self.owner_deposit_withdraw_time,
            self.user_min_deposit,
            self.admin,
        ]

        tx_hash, address = deploy(type(self).__name__, proxy, gas_limit, deployer, bytecode_path, metadata, arguments)
        return tx_hash, address

    def issue_redeem_token(self, deployer: Account, proxy: ProxyNetworkProvider, redeem_token_ticker: str):
        """ Expected as args:
        type[str]: lp token name
        type[str]: lp token ticker
        """
        function_purpose = f"Issue price discovery redeem token"
        logger.info(function_purpose)

        gas_limit = 100000000
        sc_args = [
            redeem_token_ticker,
            redeem_token_ticker,
            18,
        ]
        return endpoint_call(proxy, gas_limit, deployer, Address.from_bech32(self.address), "issueRedeemToken", sc_args,
                             value=config.DEFAULT_ISSUE_TOKEN_PRICE)

    def contract_query(self, proxy: ProxyNetworkProvider, user: Account, function: str, args: list):

        builder = query_controller.create_query(
        contract=self.address,
        function=function,
        arguments=args,
        caller=user.address.to_bech32(),
        )

        query = query_controller.run_query(builder)

        data_parts = query_controller.parse_query_response(query)
        return data_parts

    def contract_start(self, deployer: Account, proxy: ProxyNetworkProvider, args: list = []):
        pass

    def print_contract_info(self):
        log_step_pass(f"Deployed price discovery contract: {self.address}")
        log_substep(f"Redeem token: {self.redeem_token}")
        log_substep(f"Start time: {self.start_time}")
