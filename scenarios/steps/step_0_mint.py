import logging
import sys
from argparse import ArgumentParser
from typing import List

from arrows.stress.contracts import config
from arrows.stress.shared import BunchOfAccounts, broadcast_transactions
from erdpy.accounts import Account, Address
from erdpy.proxy.core import ElrondProxy
from erdpy.transactions import Transaction
from arrows.stress.launchpad import (sync_tokens, flow_control, config as lp_config)


def main(cli_args: List[str]):
    logging.basicConfig(level=logging.ERROR)

    parser = ArgumentParser()
    parser.add_argument("--proxy", default=config.DEFAULT_PROXY)
    parser.add_argument("--minter", default=config.DEFAULT_MINTER)
    parser.add_argument("--accounts", default=config.DEFAULT_ACCOUNTS)
    parser.add_argument("--value", default=str(config.DEFAULT_MINT_VALUE))
    parser.add_argument("--yes", action="store_true", default=False)
    args = parser.parse_args(cli_args)

    proxy = ElrondProxy(args.proxy)
    network = proxy.get_network_config()
    accounts = BunchOfAccounts.load_accounts_from_files([args.accounts])
    minter = Account(pem_file=str(args.minter))
    # a.address = Address.bech32("erd1rr5sx3rgpqcu2lq70n93y5k7q6jfh45gp6z44ke7y7mk4mhql9tsjttwtg")
    minter.sync_nonce(proxy)

    print("Minter", minter.address, "nonce", minter.nonce)

    transactions: List[Transaction] = []

    for account in accounts.get_all():
        transaction = Transaction()
        transaction.nonce = minter.nonce
        transaction.sender = minter.address.bech32()
        transaction.receiver = account.address.bech32()
        # transaction.receiver = "erd1tfq09ze5kz8xsp9ea4ujcua9kz3xm62g3udu9z3gfvr9c87uelesl7fu0e"
        transaction.value = str(args.value) # + "0" * 18
        transaction.gasPrice = config.DEFAULT_GAS_PRICE
        transaction.gasLimit = 50000
        transaction.chainID = str(network.chain_id)
        transaction.version = network.min_transaction_version
        transaction.sign(minter)
        minter.nonce += 1

        transactions.append(transaction)

    broadcast_transactions(transactions, proxy, 1000, confirm_yes=args.yes)


if __name__ == "__main__":
    main(sys.argv[1:])
