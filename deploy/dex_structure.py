import time
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Type, Dict, Optional

import config
from contracts.fees_collector_contract import FeesCollectorContract

from contracts.unstaker_contract import UnstakerContract
from deploy import sync_tokens, issue_tokens
from deploy.tokens_tracks import BunchOfTracks
from utils.contract_data_fetchers import PriceDiscoveryContractDataFetcher, \
    LockedAssetContractDataFetcher, FarmContractDataFetcher, StakingContractDataFetcher, \
    ProxyContractDataFetcher
from contracts.builtin_contracts import ESDTContract
from contracts.farm_contract import FarmContract
from contracts.router_contract import RouterContract
from contracts.contract_identities import FarmContractVersion, DEXContractInterface, \
    RouterContractVersion, PairContractVersion, ProxyContractVersion, StakingContractVersion, MetaStakingContractVersion
from contracts.staking_contract import StakingContract
from utils.utils_tx import NetworkProviders
from utils.utils_chain import hex_to_string
from utils.utils_chain import Account, WrapperAddress as Address
from utils.utils_generic import write_json_file, read_json_file, log_step_fail, log_step_pass, \
    log_warning, get_continue_confirmation
from deploy import populate_deploy_lists


class ContractStructure:
    def __init__(self, label: str, contract_class: Type[DEXContractInterface], bytecode_path: str, deploy_function,
                 deploy_clean: bool = True):
        self.label = label
        self.contract_class = contract_class
        self.deploy_structure_list = populate_deploy_lists.populate_list(config.DEPLOY_STRUCTURE_JSON, label)
        self.deployed_contracts: List[contract_class] = []
        self.deploy_clean = deploy_clean
        self.deploy_function = deploy_function
        self.bytecode = bytecode_path

    def save_deployed_contracts(self):
        if self.deployed_contracts:
            dump = []
            for contract in self.deployed_contracts:
                dump.append(contract.get_config_dict())

            filepath = config.DEFAULT_CONFIG_SAVE_PATH / f"deployed_{self.label}.json"
            Path(config.DEFAULT_CONFIG_SAVE_PATH).mkdir(parents=True, exist_ok=True)

            write_json_file(filepath, dump)
            log_step_pass(f"Saved deployed {self.label} contracts.")

    def get_saved_deployed_contracts(self) -> list:
        contracts_list = []
        filepath = config.DEFAULT_CONFIG_SAVE_PATH / f"deployed_{self.label}.json"
        if not Path(filepath).is_file():    # no config available
            return []

        retrieved_contract_configs = read_json_file(filepath)

        for contract_config in retrieved_contract_configs:
            contract = self.contract_class.load_config_dict(contract_config)
            contracts_list.append(contract)

        return contracts_list

    def load_deployed_contracts(self):
        contracts_list = self.get_saved_deployed_contracts()
        if len(self.deploy_structure_list) == len(contracts_list):
            self.deployed_contracts = contracts_list
            log_step_pass(f"Loaded {len(contracts_list)} {self.label}.")
            return

        log_step_fail(f"No contracts fetched for: {self.label}; "
                             f"Either no save available or mismatch between deploy structure and loaded contracts.")

    def print_deployed_contracts(self):
        log_step_pass(f"{self.label}:")
        for contract in self.deployed_contracts:
            contract.print_contract_info()


class DeployStructureArguments:
    @classmethod
    def add_parsed_arguments(cls, parser: ArgumentParser):
        parser.add_argument("--egld-wraps", action="store_true", help="Deploy clean EGLD wraps")
        parser.add_argument("--locked-assets", action="store_true", help="Deploy clean locked assets")
        parser.add_argument("--proxies", action="store_true", help="Deploy clean proxies")
        parser.add_argument("--fees-collectors", action="store_true", help="Deploy clean fees collectors")
        parser.add_argument("--unstakers", action="store_true", help="Deploy clean unstakers")
        parser.add_argument("--proxies-v2", action="store_true", help="Deploy clean proxies v2")
        parser.add_argument("--router", action="store_true", help="Deploy clean router")
        parser.add_argument("--router-v2", action="store_true", help="Deploy clean router v2")
        parser.add_argument("--pairs", action="store_true", help="Deploy clean pairs")
        parser.add_argument("--pairs-v2", action="store_true", help="Deploy clean pairs v2")
        parser.add_argument("--farms-community", action="store_true", help="Deploy clean farms community")
        parser.add_argument("--farms-unlocked", action="store_true", help="Deploy clean farms unlocked")
        parser.add_argument("--farms-locked", action="store_true", help="Deploy clean farms locked")
        parser.add_argument("--farms-v2", action="store_true", help="Deploy clean farms v2")
        parser.add_argument("--price-discoveries", action="store_true", help="Deploy clean price discoveries")
        parser.add_argument("--stakings", action="store_true", help="Deploy clean stakings")
        parser.add_argument("--stakings-v2", action="store_true", help="Deploy clean stakings v2")
        parser.add_argument("--stakings-boosted", action="store_true", help="Deploy clean stakings boosted")



class DeployStructure:
    def __init__(self):
        self.token_prefix = populate_deploy_lists.get_token_prefix(config.DEPLOY_STRUCTURE_JSON)
        self.number_of_tokens = populate_deploy_lists.get_number_of_tokens(config.DEPLOY_STRUCTURE_JSON)
        self.tokens = []    # will be filled with tokens on network
        self.esdt_contract = ESDTContract(config.TOKENS_CONTRACT_ADDRESS)

        self.contracts: Dict[str, ContractStructure] = {     
            config.STAKINGS:
                ContractStructure(config.STAKINGS, StakingContract, config.STAKING_BYTECODE_PATH,
                                  self.staking_deploy, False),
            config.STAKINGS_V2:
                ContractStructure(config.STAKINGS_V2, StakingContract, config.STAKING_V2_BYTECODE_PATH,
                                  self.staking_deploy, False),
            config.STAKINGS_BOOSTED:
                ContractStructure(config.STAKINGS_BOOSTED, StakingContract, config.STAKING_V3_BYTECODE_PATH,
                                  self.staking_deploy, False),
        }

    # main entry method to deploy tokens (either deploy fresh ones or reuse existing ones)
    def deploy_tokens(self, deployer_account: Account, network_provider: NetworkProviders,
                      clean_deploy_override: bool):
        if not clean_deploy_override:
            if not self.load_deployed_tokens():
                return
        else:
            # get current tokens, see if they satisfy the request
            sync_tokens.main(["--tokens-prefix", self.token_prefix])
            tracks = BunchOfTracks(self.token_prefix).load(config.get_default_tokens_file())

            # issue tokens if necessary
            if len(tracks.accounts_by_token) < self.number_of_tokens:
                token_hashes = []
                for i in range(self.number_of_tokens - len(tracks.accounts_by_token)):
                    hashes = issue_tokens.main(["--tokens-prefix", self.token_prefix, "--yes"])
                    token_hashes.extend(hashes)

                for txhash in token_hashes:
                    network_provider.check_complex_tx_status(txhash)

                time.sleep(40)

                # get tokens, save them in offline json then load them here
                sync_tokens.main(["--tokens-prefix", self.token_prefix])
                tracks = tracks.load(config.get_default_tokens_file())

            # retrieve from list of tuples (holding address, token)
            self.load_tokens_from_individual_asset_tracks(tracks.get_all_individual_assets())
            self.save_deployed_tokens()

    def load_tokens_from_individual_asset_tracks(self, tracks):
        # individual_asset_tracks returns an array of tuples(Address, tokenID)
        # each array element contains a unique token
        # the second element in tuple stores the token ID
        for token in tracks:
            self.tokens.append(token[1])

    def save_deployed_tokens(self):
        if self.tokens:
            filepath = config.DEFAULT_CONFIG_SAVE_PATH / "deployed_tokens.json"
            write_json_file(filepath, self.tokens)
            log_step_pass("Saved deployed tokens.")
        else:
            log_step_fail("No tokens to save!")

    def get_saved_deployed_tokens(self) -> list:
        filepath = config.DEFAULT_CONFIG_SAVE_PATH / "deployed_tokens.json"
        retrieved_tokens = read_json_file(filepath)

        if retrieved_tokens and len(retrieved_tokens) == self.number_of_tokens:
            log_step_pass(f"Loaded {len(retrieved_tokens)} tokens.")
            return retrieved_tokens
        elif retrieved_tokens and len(retrieved_tokens) >= self.number_of_tokens:
            log_warning(f"Loaded {len(retrieved_tokens)} tokens instead of expected {self.number_of_tokens}.")
            return retrieved_tokens
        else:
            log_step_fail("No tokens loaded!")
            return []

    def load_deployed_tokens(self) -> bool:
        loaded_tokens = self.get_saved_deployed_tokens()
        if loaded_tokens and len(loaded_tokens) >= self.number_of_tokens:
            self.tokens = loaded_tokens
            return True
        else:
            return False

    def save_deployed_contracts(self):
        for contracts in self.contracts.values():
            contracts.save_deployed_contracts()

    def print_deployed_contracts(self):
        log_step_pass(f"Deployed contracts below:")
        for contracts in self.contracts.values():
            contracts.print_deployed_contracts()
            print("")

    # main entry method to deploy the DEX contract structure (either fresh deploy or loading existing ones)
    def deploy_structure(self, deployer_account: Account, network_provider: NetworkProviders,
                         clean_deploy_override: bool):
        deployer_account.sync_nonce(network_provider.proxy)
        for contract_label, contracts in self.contracts.items():
            if not clean_deploy_override and not contracts.deploy_clean:
                contracts.load_deployed_contracts()
            else:
                log_step_pass(f"Starting setup process for {contract_label}:")

                # if aborted deploy & setup, maybe attempt load instead
                if not get_continue_confirmation(config.FORCE_CONTINUE_PROMPT):
                    log_step_pass(f"Attempting load for {contract_label}:")
                    if not get_continue_confirmation(config.FORCE_CONTINUE_PROMPT):
                        return
                    contracts.load_deployed_contracts()
                    return

                contracts.deploy_function(contract_label, deployer_account, network_provider)
                if len(contracts.deployed_contracts) > 0:
                    contracts.print_deployed_contracts()
                    self.contracts[contract_label] = contracts
                    contracts.save_deployed_contracts()
                else:
                    log_warning(f"No contracts deployed for {contract_label}!")

    # should be run for fresh deployed contracts
    def start_deployed_contracts(self, deployer_account: Account, network_provider: NetworkProviders,
                                 clean_deploy_override: bool):
        deployer_account.sync_nonce(network_provider.proxy)
        for contracts in self.contracts.values():
            if contracts.deploy_clean or clean_deploy_override:
                for contract in contracts.deployed_contracts:
                    contract.contract_start(deployer_account, network_provider.proxy)

    def set_proxy_v2_in_pairs(self, deployer_account: Account, network_providers: NetworkProviders,
                              clean_deploy_override: bool):
        search_label = "proxy_v2"
        pair_contracts = self.contracts[config.PAIRS_V2]

        # execute only if proxy is clean or overriden
        if not self.contracts[config.PROXIES_V2].deploy_clean and not clean_deploy_override:
            return
        # execute only if pair contracts weren't cleanly deployed
        if pair_contracts.deploy_clean:
            return

    def get_deployed_contracts(self, label: str):
        return self.contracts[label].deployed_contracts

    # CONTRACT DEPLOYERS ------------------------------
    def staking_deploy(self, contracts_index: str, deployer_account: Account, network_providers: NetworkProviders):
        deployed_contracts = []
        contract_structure = self.contracts[contracts_index]
        for config_staking in contract_structure.deploy_structure_list:
            staking_token = self.tokens[config_staking['staking_token']]
            stake_token = config_staking['stake_token']
            stake_token_name = config_staking['stake_token_name']
            max_apr = config_staking['apr']
            rewards_per_block = config_staking['rpb']
            unbond_epochs = config_staking['unbond_epochs']
            topup_rewards = config_staking['rewards']

            if contracts_index == config.STAKINGS:
                version = StakingContractVersion.V1
            elif contracts_index == config.STAKINGS_V2:
                version = StakingContractVersion.V2
            elif contracts_index == config.STAKINGS_BOOSTED:
                version = StakingContractVersion.V3Boosted
            else:
                log_step_fail(f"FAIL: unknown staking contract version: {contracts_index}")
                return

            # deploy contract
            deployed_staking_contract = StakingContract(
                farming_token=staking_token,
                max_apr=max_apr,
                rewards_per_block=rewards_per_block,
                unbond_epochs=unbond_epochs,
                version=version
            )

            args = []
            if version != StakingContractVersion.V1:
                args.append(deployer_account.address.bech32())
                if 'admin' in config_staking:
                    args.append(config_staking['admin'])

            tx_hash, contract_address = deployed_staking_contract.contract_deploy(
                deployer_account, network_providers.proxy, contract_structure.bytecode, args)
            # check for deployment success and save the deployed address
            if not network_providers.check_deploy_tx_status(tx_hash, contract_address, "stake contract"): return
            deployed_staking_contract.address = contract_address
            log_step_pass(f"Stake contract address: {contract_address}")

            # register farm token and save it
            tx_hash = deployed_staking_contract.register_farm_token(deployer_account, network_providers.proxy,
                                                                    [stake_token_name, stake_token])
            if not network_providers.check_complex_tx_status(tx_hash, "register stake token"): return
            farm_token_hex = StakingContractDataFetcher(Address(deployed_staking_contract.address),
                                                        network_providers.proxy.url).get_data("getFarmTokenId")
            deployed_staking_contract.farm_token = hex_to_string(farm_token_hex)

            # set rewards per block
            tx_hash = deployed_staking_contract.set_rewards_per_block(deployer_account, network_providers.proxy,
                                                                      rewards_per_block)
            if not network_providers.check_simple_tx_status(tx_hash, "set rewards per block in stake contract"): return

            if version == StakingContractVersion.V3Boosted:
                # Set boosted yields rewards percentage
                if 'boosted_rewards' not in config_staking:
                    boosted_rewards = 6000
                    log_step_fail(f"Boosted yields rewards percentage not configured! "
                                  f"Setting default: {boosted_rewards}")
                else:
                    boosted_rewards = config_staking['boosted_rewards']
                tx_hash = deployed_staking_contract.set_boosted_yields_rewards_percentage(deployer_account,
                                                                                          network_providers.proxy,
                                                                                          boosted_rewards)
                if not network_providers.check_simple_tx_status(tx_hash, "set boosted yields rewards percentage in farm"):
                    return

                # Set boosted yields factors
                if "base_const" not in config_staking or \
                        "energy_const" not in config_staking or \
                        "farm_const" not in config_staking or \
                        "min_energy" not in config_staking or \
                        "min_farm" not in config_staking:
                    log_step_fail(f"Aborting deploy: Boosted yields factors not configured!")
                tx_hash = deployed_staking_contract.set_boosted_yields_factors(deployer_account,
                                                                               network_providers.proxy,
                                                                               [config_staking['base_const'],
                                                                                config_staking['energy_const'],
                                                                                config_staking['farm_const'],
                                                                                config_staking['min_energy'],
                                                                                config_staking['min_farm']])
                if not network_providers.check_simple_tx_status(tx_hash, "set boosted yields factors in farm"):
                    return

            # topup rewards
            if topup_rewards > 0:
                tx_hash = deployed_staking_contract.topup_rewards(deployer_account, network_providers.proxy, topup_rewards)
                _ = network_providers.check_simple_tx_status(tx_hash, "topup rewards in stake contract")

            deployed_contracts.append(deployed_staking_contract)
        self.contracts[contracts_index].deployed_contracts = deployed_contracts