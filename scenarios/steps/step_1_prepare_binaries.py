import logging
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import List, cast

from arrows.stress.contracts import config
from arrows.stress.contracts.contract import Contract
from arrows.stress.contracts.contracts_registry import ContractsRegistry
from erdpy import utils


def main(cli_args: List[str]):
    logging.basicConfig(level=logging.WARN)

    parser = ArgumentParser()
    parser.add_argument("--workspace", default=config.DEFAULT_WORKSPACE)
    args = parser.parse_args(cli_args)

    workspace = Path(args.workspace)
    prototypes_folder = workspace / "prototypes"
    src_folder = workspace / "src"
    bin_folder = workspace / "bin"
    registry = ContractsRegistry()
    contracts: List[Contract] = registry.get_all()

    utils.ensure_folder(args.workspace)
    utils.remove_folder(prototypes_folder)
    utils.ensure_folder(prototypes_folder)
    utils.remove_folder(src_folder)
    utils.ensure_folder(src_folder)
    utils.remove_folder(bin_folder)
    utils.ensure_folder(bin_folder)

    create_source_prototypes(prototypes_folder, contracts)
    create_instances_from_source(prototypes_folder, src_folder, contracts)
    build(src_folder, bin_folder, contracts)
    create_additional_instances_from_bin(bin_folder, contracts)

    print("*" * 80)
    print("Done, built contracts.")
    print("Folder SRC:")
    print(src_folder)
    print("Folder BIN (WASM):")
    print(bin_folder)


def create_source_prototypes(prototypes_folder: Path, contracts: List[Contract]):
    for contract in contracts:
        if contract.is_pre_deployed():
            continue
        if contract.is_pre_built():
            continue
        if contract.has_non_movable_source_code():
            continue
        contract.create_source_prototype(prototypes_folder)


def create_instances_from_source(prototypes_folder: Path, src_folder: Path, contracts: List[Contract]):
    for contract in contracts:
        name = contract.get_name()
        prototype_folder = prototypes_folder / name
        num_instances = contract.get_num_instances_from_source()

        for i in range(0, num_instances):
            clone_folder = src_folder / name / str(i)
            contract.create_instance_from_source(prototype_folder, clone_folder, i)


def build(src_folder: Path, bin_folder: Path, contracts: List[Contract]):
    for contract in contracts:
        name = contract.get_name()
        num_instances = contract.get_num_instances_from_source()

        if contract.is_pre_built():
            shutil.copyfile(contract.get_pre_built_wasm_file(), bin_folder / f"{name}_0.wasm")
            continue

        if contract.has_non_movable_source_code():
            folder = contract.get_non_movable_source_code()
            contract.build(folder, bin_folder / f"{name}_0.wasm")

        for i in range(0, num_instances):
            folder = src_folder / name / str(i)
            bin_file_to = bin_folder / f"{name}_{i}.wasm"
            contract.build(folder, bin_file_to)


def create_additional_instances_from_bin(bin_folder: Path, contracts: List[Contract]):
    for contract in contracts:
        name = contract.get_name()
        num_instances = contract.get_num_additional_instances_from_bin()
        if not num_instances:
            continue

        existing_bin_file = bin_folder / f"{name}_0.wasm"
        existing_bytecode = cast(bytes, utils.read_file(existing_bin_file, binary=True))

        for i in range(0, num_instances):
            new_byte_code = bytearray(len(existing_bytecode))
            new_byte_code[:] = existing_bytecode
            new_bin_file = bin_folder / f"{name}_{i}.wasm"
            contract.mutate_additional_instance_from_bin(new_byte_code, i)

            with open(new_bin_file, "wb") as f:
                f.write(new_byte_code)


if __name__ == "__main__":
    main(sys.argv[1:])
