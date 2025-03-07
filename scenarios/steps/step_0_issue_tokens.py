import logging
import sys
from argparse import ArgumentParser
from typing import List

from arrows.stress.launchpad import config
from arrows.stress.esdtnft.shared import (build_token_name, build_token_ticker,
                                          load_contracts, make_call_arg_ascii,
                                          make_call_arg_pubkey)
from arrows.stress.shared import BunchOfAccounts, broadcast_transactions
from erdpy.contracts import SmartContract
from erdpy.proxy.core import ElrondProxy
from erdpy.transactions import Transaction


def main(cli_args: List[str]):
    logging.basicConfig(level=logging.ERROR)

    parser = ArgumentParser()
    parser.add_argument("--proxy", default=config.DEFAULT_PROXY)
    parser.add_argument("--accounts", default=config.DEFAULT_ACCOUNTS)
    parser.add_argument("--contracts", default=config.get_default_contracts_file())
    parser.add_argument("--sleep-between-chunks", type=int, default=5)
    parser.add_argument("--chunk-size", type=int, default=400)
    parser.add_argument("--from-shard")
    parser.add_argument("--via-shard")
    parser.add_argument("--base-gas-limit", type=int, default=config.DEFAULT_GAS_BASE_LIMIT_ISSUE)
    parser.add_argument("--gas-limit", type=int, default=0)
    parser.add_argument("--num-tokens", type=int, default=1)
    parser.add_argument("--num-decimals", type=int, default=0)
    parser.add_argument("--supply-exp", type=int, default=7)
    parser.add_argument("--tokens-prefix", default=config.DEFAULT_TOKEN_PREFIX)
    parser.add_argument("--value", default=str(config.DEFAULT_ISSUE_TOKEN_PRICE))
    parser.add_argument("--yes", action="store_true", default=False)
    parser.add_argument("--mode", choices=["direct", "via"], default="direct")

    args = parser.parse_args(cli_args)

    proxy = ElrondProxy(args.proxy)
    network = proxy.get_network_config()

    bunch_of_accounts = BunchOfAccounts.load_accounts_from_files([args.accounts])
    # bunch_of_accounts.sync_nonces(proxy)
    accounts = bunch_of_accounts.get_all() if args.from_shard is None else bunch_of_accounts.get_in_shard(int(args.from_shard))
    account = accounts[0]  # issue tokens only for SC owner account to improve times on large number of accounts
    account.sync_nonce(proxy)

    tokens_system_contract = SmartContract(address=config.TOKENS_CONTRACT_ADDRESS)

    supply = pow(10, args.supply_exp)
    num_decimals = args.num_decimals
    prefix = args.tokens_prefix
    print("Supply: ", supply, "Decimals: ", num_decimals, "Prefix: ", prefix)
    print("Number of tokens: ", args.num_tokens)

    def issue_token():
        for i in range(0, args.num_tokens):
            account = accounts[i]
            _, token_name = build_token_name(account.address, prefix)
            _, token_ticker = build_token_ticker(account.address, prefix)
            sc_args = [token_name, token_ticker, supply, num_decimals]
            tx_data = tokens_system_contract.prepare_execute_transaction_data("issue", sc_args)

            gas_limit = args.gas_limit or args.base_gas_limit + 50000 + 1500 * len(tx_data)
            value = args.value

            tx = Transaction()
            tx.nonce = account.nonce
            tx.value = value
            tx.sender = account.address.bech32()
            tx.receiver = tokens_system_contract.address.bech32()
            tx.gasPrice = network.min_gas_price
            tx.gasLimit = gas_limit
            tx.data = tx_data
            tx.chainID = str(network.chain_id)
            tx.version = network.min_transaction_version
            tx.sign(account)

            print("Holder account: ", account.address)
            print("Token name: ", token_name)
            print("Token ticker: ", token_ticker)

            transactions.append(tx)
            account.nonce += 1

    transactions: List[Transaction] = []

    issue_token()

    broadcast_transactions(transactions, proxy, args.chunk_size, sleep=args.sleep_between_chunks, confirm_yes=args.yes)


if __name__ == "__main__":
    main(sys.argv[1:])
