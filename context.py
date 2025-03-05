import random
from datetime import datetime

import config
from utils.utils_tx import NetworkProviders
from utils.utils_chain import Account, BunchOfAccounts, WrapperAddress as Address


class Context:
    def __init__(self):

        self.deployer_account = Account(pem_file=config.DEFAULT_OWNER)
        if config.DEX_OWNER_ADDRESS:    # manual override only for shadowforks
            self.deployer_account.address = Address(config.DEX_OWNER_ADDRESS)
        self.admin_account = Account(pem_file=config.DEFAULT_ADMIN)
        if config.DEX_ADMIN_ADDRESS:  # manual override only for shadowforks
            self.admin_account.address = Address(config.DEX_ADMIN_ADDRESS)
        self.accounts = BunchOfAccounts.load_accounts_from_files([config.DEFAULT_ACCOUNTS])
        self.nonces_file = config.DEFAULT_WORKSPACE / "_nonces.json"
        self.debug_level = 1

        self.network_provider = NetworkProviders(config.DEFAULT_API, config.DEFAULT_PROXY)

        # logger
        self.start_time = datetime.now()

        self.add_liquidity_max_amount = 0.1
        self.remove_liquidity_max_amount = 0.5
        self.numEvents = 100  # sys.maxsize
        self.pair_slippage = 0.05
        self.swap_min_tokens_to_spend = 0
        self.swap_max_tokens_to_spend = 0.8

        self.enter_farm_max_amount = 0.2
        self.exit_farm_max_amount = 0.5

        self.enter_metastake_max_amount = 0.1
        self.exit_metastake_max_amount = 0.3

        # BEGIN DEPLOY
        self.deployer_account.sync_nonce(self.network_provider.proxy)
        self.admin_account.sync_nonce(self.network_provider.proxy)

    def get_slippaged_below_value(self, value: int):
        return value - int(value * self.pair_slippage)

    def get_slippaged_above_value(self, value: int):
        return value + int(value * self.pair_slippage)

    def set_swap_spend_limits(self, swap_min_spend, swap_max_spend):
        self.swap_min_tokens_to_spend = swap_min_spend
        self.swap_max_tokens_to_spend = swap_max_spend

    def get_random_user_account(self):
        account_list = self.accounts.get_all()
        return random.choice(account_list)
