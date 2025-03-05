import logging
import sys
import time
from argparse import ArgumentParser
from itertools import cycle
from pathlib import Path
from typing import List

from arrows.stress.contracts import config
from arrows.stress.contracts.contract import FlowConfig
from arrows.stress.contracts.contracts_registry import ContractsRegistry
from arrows.stress.contracts.tracks import (
    TracksOfContracts, filter_bunch_of_tracks_by_enabled_contracts,
    filter_bunch_of_tracks_by_shard)
from arrows.stress.shared import (BunchOfAccounts, broadcast_transactions,
                                  filter_bunch_of_accounts_by_shard)
from arrows.stress.launchpad import flow_control
from erdpy import utils
from erdpy.proxy.core import ElrondProxy
from erdpy.transactions import Transaction


def main(cli_args: List[str]):
    logging.basicConfig(level=logging.ERROR)

    parser = ArgumentParser()
    parser.add_argument("--proxy", default=config.DEFAULT_PROXY)
    parser.add_argument("--workspace", default=config.DEFAULT_WORKSPACE)
    parser.add_argument("--accounts", default=config.DEFAULT_ACCOUNTS)
    parser.add_argument("--from-shard", type=str)
    parser.add_argument("--to-shard", type=str)
    parser.add_argument("--num-repeat", type=int, default=1)
    parser.add_argument("--num-repeat-over-tracks", type=int, default=1)
    parser.add_argument("--sleep-between-repetitions", type=int, default=0)
    parser.add_argument("--sleep-between-chunks", type=int, default=0)
    parser.add_argument("--chunk-size", type=int, default=10000)
    parser.add_argument("--tag", default=config.DEFAULT_SCENARIO_TAG, help="tag of the scenario")
    parser.add_argument("--mode", type=str, default=None)
    parser.add_argument("--hint-volume", type=int, default=1)
    parser.add_argument("--hint-gas", type=float, default=1.0)
    parser.add_argument("--yes", action="store_true", default=False)
    args = parser.parse_args(cli_args)

    proxy = ElrondProxy(args.proxy)
    network = proxy.get_network_config()
    workspace = Path(args.workspace)
    flow_config = FlowConfig(args.mode, args.hint_volume, args.hint_gas)

    number_of_used_accounts = args.num_repeat * args.num_repeat_over_tracks     # this calculates the quantity of accounts used in this flow run
    bunch_of_accounts = BunchOfAccounts.load_accounts_from_files([args.accounts])
    bunch_of_accounts = filter_bunch_of_accounts_by_shard(bunch_of_accounts, args.from_shard)
    if len(bunch_of_accounts) > number_of_used_accounts:
        print("Using", number_of_used_accounts, "accounts from imported bunch.")
        bunch_of_accounts = BunchOfAccounts(bunch_of_accounts.get_all()[:number_of_used_accounts])
    callers = bunch_of_accounts.get_all()
    callers_pool = cycle(callers)

    tracks_files = utils.list_files(workspace / "tracks")
    all_tracks = TracksOfContracts.load_many_as_union(tracks_files)
    registry = ContractsRegistry()
    registry.setup_flow(callers, all_tracks)

    for index in range(0, args.num_repeat):
        print("Repetition ...", index)

        config.DEFAULT_GAS_PRICE += 1

        if index > 0:
            print("Sleeping between repetitions ...")
            time.sleep(args.sleep_between_repetitions)

        bunch_of_accounts.sync_nonces(proxy)
        flow_control.sync_contract_owner_nonces(proxy)

        # The deploy step might have generated a large number of tracks files (depending on it's --num-repeat parameter).
        for tracks_file in tracks_files:
            # Workaround / hack. Skip track file.
            if args.tag not in tracks_file.name:
                continue

            bunch_of_tracks = TracksOfContracts.load(Path(tracks_file))
            tracks = bunch_of_tracks.get_all()
            tracks = filter_bunch_of_tracks_by_shard(tracks, args.to_shard)
            tracks = filter_bunch_of_tracks_by_enabled_contracts(tracks, registry)

            transactions: List[Transaction] = []
            expected_results: List[bool] = []

            for track in tracks * args.num_repeat_over_tracks:
                name = track.name
                contract = registry.get_by_name(name)
                owner = bunch_of_accounts.get_account(track.deployer)
                flow_control.set_contract_owner(track.address.bech32(), owner)
                caller = next(callers_pool)
                flow_transactions, flow_results = contract.run_flow(caller, track, network, flow_config)

                transactions.extend(flow_transactions)
                expected_results.extend(flow_results)

                if (len(transactions) % 1000 == 0):
                    print("... building transactions:", len(transactions))

            with open(tracks_file, "w") as f:
                utils.dump_out_json(bunch_of_tracks.to_plain(), f)

            hashes = broadcast_transactions(transactions, proxy, chunk_size=args.chunk_size, sleep=args.sleep_between_chunks, confirm_yes=args.yes)
            print(hashes)
            flow_control.add_txhash_expected_results(hashes, expected_results, transactions)


if __name__ == "__main__":
    main(sys.argv[1:])
