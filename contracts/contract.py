import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

import config
from contracts.launchpad_guaranteed_contract import PreparedQuery
from contracts.tracks import TrackOfContract
import utils
from utils.utils_chain import Account, Address
from multiversx_sdk.network_providers.network_config import NetworkConfig
from multiversx_sdk.core import Transaction
from multiversx_sdk import CodeMetadata, SmartContractTransactionsFactory, Transaction, Address, \
                            TransactionComputer, TransactionsFactoryConfig, AddressComputer, UserSigner
from multiversx_sdk.abi import Abi
from multiversx_sdk import UserSigner
from multiversx_sdk_cli import projects
from multiversx_sdk_cli.projects.core import load_project
from utils.utils_generic import read_file

class FlowConfig:
    def __init__(self, mode: str, hint_volume: int, hint_gas: float):
        self.mode = mode
        self.hint_volume = hint_volume
        self.hint_gas = hint_gas


class Contract:
    def __init__(self):
        pass

    def get_name(self) -> str:
        raise Exception("not implemented")

    def get_config(self) -> Any:
        contract_config = config.CONTRACTS.get(self.get_name(), None)
        if contract_config is None:
            raise Exception(f"Contract isn't configured: {self.get_name()}")

        return contract_config

    def get_num_instances_from_source(self) -> int:
        return self.get_config().get("num-instances-from-source", 1)

    def get_num_additional_instances_from_bin(self) -> int:
        return self.get_config().get("num-additional-instances-from-bin", 0)

    def create_source_prototype(self, prototypes_folder: Path):
        template = self.get_config().get("prototype-template", None)
        src = self.get_config().get("prototype-src", None)

        if template:
            self._create_prototype_from_template(template, prototypes_folder)
            return

        if src:
            self._create_prototype_from_folder(src, prototypes_folder)
            return

        raise Exception("Cannot create prototype. Bad config?")

    def _create_prototype_from_template(self, template: str, prototypes_folder: Path):
        name = self.get_name()
        projects.create_from_template(name, template, prototypes_folder)

    def _create_prototype_from_folder(self, folder: Path, prototypes_folder: Path):
        shutil.copytree(folder, prototypes_folder / self.get_name())

    def create_instance_from_source(self, prototype_folder: Path, instance_folder: Path, instance_index: int):
        shutil.copytree(prototype_folder, instance_folder)

        simple_src_mutation = self.get_config().get("simple-src-mutation", None)
        if simple_src_mutation is None:
            return

        src_file_relative, change_from, change_to = simple_src_mutation
        src_file = instance_folder / src_file_relative
        src = str(utils.read_file(src_file))
        src = src.replace(change_from, change_to.format(instance_index=instance_index))
        utils.write_file(src_file, src)

    def is_pre_built(self):
        return self.get_pre_built_wasm_file() is not None

    def get_pre_built_wasm_file(self):
        return self.get_config().get("pre-built-wasm", None)

    def has_non_movable_source_code(self):
        return self.get_non_movable_source_code() is not None

    def get_non_movable_source_code(self):
        return self.get_config().get("non-movable-src", None)

    def build(self, source_folder: Path, destination_file: Path):
        print(f"Building {source_folder} to {destination_file}.")

        project = load_project(source_folder)
        project.build(self.get_build_options())
        bin_file_from = project.get_file_wasm()
        shutil.copyfile(bin_file_from, destination_file)

    def get_build_options(self) -> Dict[str, Any]:
        return {"debug": False, "optimized": False, "verbose": False, "cargo_target_dir": config.get_cargo_target_dir()}

    def mutate_additional_instance_from_bin(self, new_bytecode: bytearray, instance_index: int):
        skip_bin_mutation = self.get_config().get("skip-bin-mutation", False)
        if skip_bin_mutation is True:
            return

        simple_bin_mutation = self.get_config().get("simple-bin-mutation", None)
        if simple_bin_mutation is None:
            raise Exception(f"Cannot create instance from bin (wasm). Bad config of {self.get_name()}?")

        mutation_offset, = simple_bin_mutation
        mutation_bytes = (instance_index + int(time.time())).to_bytes(4, "big")
        new_bytecode[mutation_offset:mutation_offset + len(mutation_bytes)] = mutation_bytes

    def get_deploy_transaction(self, bytecode: str, deployer: Account, network_config: NetworkConfig) -> Tuple[Transaction, Address]:
        if self.is_pre_deployed():
            raise Exception(f"{self.get_name()} is already deployed!")

        contract_config = self.get_config()
        gas_limit = contract_config.get("deploy-gas-limit")
        value = contract_config.get("deploy-value", 0)
        metadata = contract_config.get("deploy-metadata", CodeMetadata(upgradeable=True, payable=True))
        arguments = contract_config.get("deploy-arguments", [])

        if gas_limit is None:
            raise Exception(f"Please configure deploy-gas-limit for {self.get_name()}!")

        contract = SmartContract(bytecode=bytecode, metadata=metadata)
        tx = contract.deploy(deployer, arguments, config.DEFAULT_GAS_PRICE, gas_limit, value, network_config.chain_id, network_config.min_tx_version)
        address = contract.address
        return tx, address

    def get_deploy_transaction_new(self, bytecode: str, deployer: Account, network_config: NetworkConfig, abi: Abi, args: List) -> Tuple[Transaction, Address]:
        if self.is_pre_deployed():
            raise Exception(f"{self.get_name()} is already deployed!")

        contract_config = self.get_config()
        gas_limit = contract_config.get("deploy-gas-limit")
        # arguments = contract_config.get("deploy-arguments", [])

        if gas_limit is None:
            raise Exception(f"Please configure deploy-gas-limit for {self.get_name()}!")
        
        factory_config = TransactionsFactoryConfig(config.CHAIN_ID)
        transactions_factory = SmartContractTransactionsFactory(factory_config, abi)
        sender = Address.new_from_bech32(deployer.address.bech32())
            
        # contract = SmartContract(bytecode=bytecode, metadata=metadata)
        tx_new = transactions_factory.create_transaction_for_deploy(
            sender, 
            bytecode, 
            gas_limit, 
            args,
            is_upgradeable=True,
            is_readable=True,
            is_payable=True,
            is_payable_by_sc=True
            )
        # tx = contract.deploy(deployer, arguments, config.DEFAULT_GAS_PRICE, gas_limit, value, network_config.chain_id, network_config.min_tx_version)
        transaction_computer = TransactionComputer()
        tx_new.nonce = deployer.nonce
        users = UserSigner.from_pem_file_all(config.DEFAULT_ACCOUNTS)
        signer = users[0]
        tx_new.signature = signer.sign(transaction_computer.compute_bytes_for_signing(tx_new))

        address_computer = AddressComputer()
        contract_address = address_computer.compute_contract_address(
        deployer=Address.new_from_bech32(deployer.address.bech32()),
        deployment_nonce=tx_new.nonce
        )
        
        return tx_new, contract_address

    def get_pre_deployed_at_addresses(self) -> List[Address]:
        return self.get_config().get("pre-deployed-at", [])

    def is_pre_deployed(self):
        return len(self.get_pre_deployed_at_addresses()) > 0

    def setup_flow(self, all_callers: List[Account], all_tracks: List[TrackOfContract]):
        pass

    def run_flow(self, caller: Account, track: TrackOfContract, network_config: NetworkConfig, flow_config: FlowConfig) -> List[Transaction]:
        return []

    def aquire_query_data(self, data_folder: Path):
        pass

    def load_query_data(self, data_folder: Path) -> Any:
        return dict()

    def prepare_queries(self, track: TrackOfContract, accounts: List[Account], input_data: Any) -> List[PreparedQuery]:
        return []


def load_code_as_hex(file: Path):
    return cast(bytes, read_file(file, binary=True)).hex()


def make_call_arg_ascii(arg: str, prefix: bool = True):
    hex = arg.encode("ascii").hex()
    return f"0x{hex}" if prefix else hex


def make_call_arg_number(arg: int) -> str:
    return contracts._prepare_argument(arg)


def make_call_arg_pubkey(address: Address):
    return f"0x{address.hex()}"
