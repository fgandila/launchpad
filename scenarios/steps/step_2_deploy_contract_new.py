import logging
import sys
import time
from argparse import ArgumentParser
from itertools import cycle
from os import path
from pathlib import Path
from typing import List

from multiversx_sdk import ProxyNetworkProvider
from multiversx_sdk.core import Transaction as NewTransaction, SmartContractTransactionsFactory
from multiversx_sdk.abi import Abi
from multiversx_sdk.core.tokens import TokenIdentifierParts

from arrows.stress.contracts import config
from arrows.stress.contracts.contract import load_code_as_hex
from arrows.stress.contracts.contracts_registry import ContractsRegistry
from arrows.stress.contracts.tracks import TrackOfContract, TracksOfContracts
from arrows.stress.shared import (BunchOfAccounts, broadcast_transactions, broadcast_transactions_new,
                                  filter_bunch_of_accounts_by_shard, get_shard_of_address)
from arrows.stress.launchpad import (tokens_tracks, config as lp_config, flow_control)
from arrows.AutomaticTests.ProxyExtension import ProxyExtension
from erdpy import utils
from erdpy.accounts import Address
from erdpy.proxy.core import ElrondProxy
from erdpy.transactions import Transaction

def main(cli_args: List[str]):
    logging.basicConfig(level=logging.ERROR)

    parser = ArgumentParser()
    parser.add_argument("--proxy", default=config.DEFAULT_PROXY)
    parser.add_argument("--workspace", default=config.DEFAULT_WORKSPACE)
    parser.add_argument("--accounts", default=config.DEFAULT_ACCOUNTS)
    parser.add_argument("--tokens", default=lp_config.get_default_tokens_file())
    parser.add_argument("--from-shard", type=str)
    parser.add_argument("--num-repeat", type=int, default=1)
    parser.add_argument("--sleep-between-repetitions", type=int, default=0)
    parser.add_argument("--sleep-between-chunks", type=int, default=0)
    parser.add_argument("--chunk-size", type=int, default=300)
    parser.add_argument("--tag", default=config.DEFAULT_SCENARIO_TAG, help="tag of the scenario")
    parser.add_argument("--yes", action="store_true", default=False)
    args = parser.parse_args(cli_args)

    workspace = Path(args.workspace)
    bin_folder = workspace / "bin"

    utils.ensure_folder(workspace)
    utils.ensure_folder(path.join(workspace, "tracks"))

    proxy = ElrondProxy(args.proxy)
    proxy_new = ProxyNetworkProvider(args.proxy)
    proxy_ext = ProxyExtension(args.proxy)
    network = proxy.get_network_config()

    bunch_of_accounts = BunchOfAccounts.load_accounts_from_files([args.accounts])
    bunch_of_accounts = filter_bunch_of_accounts_by_shard(bunch_of_accounts, args.from_shard)
    deployers_pool = cycle(bunch_of_accounts.get_all()[:1])      # force deploy only from first account in the list
    bunch_of_tokens = tokens_tracks.BunchOfTracks.load(args.tokens)
    contracts = ContractsRegistry().get_all()

    for index in range(0, args.num_repeat):
        print("Repetition ...", index)

        if index > 0:
            print("Sleeping between repetitions ...")
            time.sleep(args.sleep_between_repetitions)

        # bunch_of_accounts.sync_nonces(proxy) - inefficient. will be done on account by account basis
        tracks_file = path.join(workspace, "tracks", f"{args.tag}_{index}.json")

        transactions: List[NewTransaction] = []
        tracks = TracksOfContracts()

        for contract in contracts:
            name = contract.get_name()

            # For pre-deployed contracts, simply add tracks and create no transaction.
            if contract.is_pre_deployed():
                for address in contract.get_pre_deployed_at_addresses():
                    tracks.put_track(TrackOfContract(name, index=0, deployer=Address.zero(), address=address, state=dict()))
                continue

            # Workaround (hack)
            num_instances = max(contract.get_num_instances_from_source(), contract.get_num_additional_instances_from_bin()) or 1

            for instance_index in range(0, num_instances):
                bin_file = bin_folder / f"{name}_{instance_index}.wasm"
                bytecode: bytes = bin_file.read_bytes()
                deployer = next(deployers_pool)
                deployer.sync_nonce(proxy)
                deployer_shard = get_shard_of_address(deployer.address)
                current_epoch = proxy_ext.get_network_status(deployer_shard).current_epoch
                current_block = proxy_ext.get_network_status(deployer_shard).current_nonce
                current_round = proxy_ext.get_network_status(deployer_shard).current_round

                # token_id = "0x" + bunch_of_tokens.get_tokens_by_holder(deployer.address)[0].encode("utf-8").hex()
                egld_id = "0x" + lp_config.DEFAULT_PAYMENT_TOKEN.encode("utf-8").hex()
                print(deployer.address.bech32())
                token_id = bunch_of_tokens.get_tokens_by_holder(deployer.address)[0]

                tokens_per_win_ticket = lp_config.TOKENS_PER_WINNING_TICKET
                ticket_price = lp_config.TICKET_PRICE
                winning_tickets = lp_config.NR_WINNING_TICKETS
                nft_payment_token_hex = "0x" + lp_config.NFT_PAYMENT_TOKEN.encode("utf-8").hex()
                nft_payment_token_nonce = lp_config.NFT_PAYMENT_TOKEN_NONCE
                nft_cost = lp_config.NFT_PRICE
                winning_nfts = lp_config.NR_WINNING_NFTS
                max_tier = max(lp_config.TICKET_TIERS)
                locked_tokens_percentage = lp_config.TOKENS_LOCKED_PERCENTAGE
                locked_tokens_unlock_epoch = current_epoch + lp_config.TOKENS_UNLOCK_EPOCH_OFFSET
                locking_address = lp_config.SIMPLE_LOCK_ADDRESS
                # if contract.get_name() == 'launchpad-v2' or contract.get_name() == 'launchpad':
                #     epoch_based_time = True
                # else:
                epoch_based_time = False

                # if contract.get_name() != "launchpad-v2" and contract.get_name() != "launchpad":
                current_time = current_round
                # else:
                #     current_time = current_epoch
                confirmation_time = current_time + lp_config.CONFIRMATION_PERIOD_OFFSET
                select_winners_time = confirmation_time + lp_config.SELECT_WINNERS_PERIOD_OFFSET
                claim_time = select_winners_time + lp_config.CLAIM_PERIOD_OFFSET

                arguments = [token_id, tokens_per_win_ticket, egld_id, ticket_price, winning_tickets,
                             confirmation_time, select_winners_time, claim_time]
                
                arguments_new = [token_id, tokens_per_win_ticket, "EGLD", ticket_price, winning_tickets, confirmation_time, select_winners_time, claim_time ]

                config.CONTRACTS[contract.get_name()]["deploy-arguments"] = arguments
                abi = Abi.load(lp_config.CONTRACT_ABI)

                deploy_transaction, contract_address = contract.get_deploy_transaction_new(bytecode, deployer, network, abi, arguments_new)
                transactions.append(deploy_transaction)
                deployer.nonce += 1

                tracks.put_track(TrackOfContract(name, instance_index, deployer.address, contract_address, dict()))
                print("Built deployment for: ", contract_address.bech32(), "from owner: ", deployer.address.bech32())
                print("Arguments: ", arguments)
                print("Current time:", current_time, "Confirm tickets time:", confirmation_time,
                      "Select winners time:", select_winners_time, "Claim time:", claim_time)
                
                vesting_claim_start = current_round + lp_config.VESTING_CLAIM_OFFSET
                vesting_initial_release = lp_config.VESTING_INITIAL_RELEASE
                vesting_times = lp_config.VESTING_TIMES
                vesting_percentage = lp_config.VESTING_PERCENTAGE
                vesting_period = lp_config.VESTING_PERIOD
                
                flow_control.add_period_tracker_for_address(contract_address.bech32(), confirmation_time,
                                                            select_winners_time, claim_time, args.proxy,
                                                            epoch_based_time,
                                                            vesting_claim_start, vesting_initial_release,
                                                            vesting_times, vesting_percentage, vesting_period
                                                            )

                if len(transactions) % 1000 == 0:
                    print("... building transactions:", len(transactions))

        with open(tracks_file, "w") as f:
            utils.dump_out_json(tracks.to_plain(), f)
        print(f"Tracks file has been saved: {tracks_file}")

        proxy_new.send_transaction(deploy_transaction)

if __name__ == "__main__":
    main(sys.argv[1:])
