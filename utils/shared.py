import os
import shutil
import time
from multiprocessing.dummy import Pool
from os import path
from pathlib import Path
from typing import Any, List, Set
from venv import logger

from multiversx_sdk import Address, Transaction
from multiversx_sdk import (AccountNonceHolder, Address as NewAddress, ProxyNetworkProvider, SmartContractTransactionsFactory, TransactionComputer,
                            TransactionsFactoryConfig, UserSigner)
from multiversx_sdk import core

import utils
from utils.utils_chain import Account

def confirm_continuation(yes: bool = False):
    if (yes):
        return

    answer = input("Continue? (y/n)")
    if answer.lower() not in ["y", "yes"]:
        print("Confirmation not given. Will stop.")
        exit(1)


class BunchOfAccounts:
    def __init__(self, items: List[Account]) -> None:
        self.accounts = items

    @classmethod
    def load_accounts_from_files(cls, files: List[Path]):
        loaded: List[Account] = []

        for file in files:
            # Assume multi-account PEM files.
            key_pairs = pem.parse_all(file)

            for seed, pubkey in key_pairs:
                account = Account()
                account.secret_key = seed.hex()
                account.address = Address(pubkey)
                loaded.append(account)

        # Perform some deduplication (workaround)
        addresses: Set[str] = set()
        deduplicated: List[Account] = []
        for account in loaded:
            address = account.address.bech32()
            if address not in addresses:
                addresses.add(address)
                deduplicated.append(account)

        print(f"loaded {len(deduplicated)} accounts from {len(files)} PEM files.")
        return BunchOfAccounts(deduplicated)

    def get_account(self, address: Address) -> Account:
        return next(account for account in self.accounts if account.address.bech32() == address.bech32())

    def get_all(self) -> List[Account]:
        return self.accounts

    def __len__(self):
        return len(self.accounts)

    def get_not_in_shard(self, shard: int):
        return [account for account in self.accounts if get_shard_of_address(account.address) != shard]

    def get_in_shard(self, shard: int) -> List[Account]:
        return [account for account in self.accounts if get_shard_of_address(account.address) == shard]

    def sync_nonces(self, proxy: ProxyNetworkProvider):
        print("Sync nonces for", len(self.accounts), "accounts")

        def sync_nonce(account: Account):
            account.sync_nonce(proxy)

        Pool(100).map(sync_nonce, self.accounts)

        print("Done")
    
    def store_nonces(self, file: str):
        # We load the previously stored data in order to display a nice delta (for debugging purposes)
        data: Any = utils.read_json_file(file) or dict() if path.exists(file) else dict()

        for account in self.accounts:
            address = account.address.bech32()
            previous_nonce = data.get(address, 0)
            current_nonce = account.nonce
            data[address] = current_nonce

            if previous_nonce != current_nonce:
                print("Nonce delta", current_nonce - previous_nonce, "for", address)

        utils.write_json_file(file, data)

    def load_nonces(self, file: Path):
        if not path.exists(file):
            print("no nonces to load")
            return

        data = utils.read_json_file(file) or dict()

        for account in self.accounts:
            address = account.address.bech32()
            account.nonce = data.get(address, 0)

        print("Loaded nonces for", len(self.accounts), "accounts")


def split_to_chunks(items: Any, chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def get_shard_of_address(address: Address) -> int:
    pub_key = address.pubkey()
    num_shards = 3
    mask_high = int("11", 2)
    mask_low = int("01", 2)

    last_byte_of_pub_key = pub_key[31]

    if is_address_of_metachain(address):
        return METACHAIN_ID

    shard = last_byte_of_pub_key & mask_high
    if shard > num_shards - 1:
        shard = last_byte_of_pub_key & mask_low

    return shard


def is_address_of_metachain(address: Address):
    pub_key = address.pubkey()

    metachain_prefix = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    pub_key_prefix = pub_key[0:len(metachain_prefix)]
    if pub_key_prefix == metachain_prefix:
        return True

    zero_address = bytearray(32)
    if pub_key == zero_address:
        return True

    return False


def broadcast_transactions(transactions: List[Transaction], proxy: ProxyNetworkProvider, chunk_size: int, sleep: int = 0, confirm_yes: bool = False):
    chunks = list(split_to_chunks(transactions, chunk_size))

    print(f"{len(transactions)} transactions have been prepared, in {len(chunks)} chunks of size {chunk_size}")
    confirm_continuation(yes=confirm_yes)

    chunk_index = 0
    hash_dict: dict = {}
    for chunk in chunks:
        print("... chunk", chunk_index, "out of", len(chunks))

        bunch = BunchOfTransactionsNew()
        for transaction in chunk:
            bunch.transactions.append(transaction)

        num_sent, hashes = bunch.send(proxy)
        if len(chunk) != num_sent:
            print(f"sent {num_sent} instead of {len(chunk)}")

        hash_dict.update(dict(hashes))

        chunk_index += 1

        if sleep is not None:
            time.sleep(sleep)

    return hash_dict

def broadcast_transactions_new(transactions: List[Transaction], proxy: ProxyNetworkProvider, chunk_size: int, sleep: int = 0, confirm_yes: bool = False):
    chunks = list(split_to_chunks(transactions, chunk_size))

    print(f"{len(transactions)} transactions have been prepared, in {len(chunks)} chunks of size {chunk_size}")
    confirm_continuation(yes=confirm_yes)

    chunk_index = 0
    hash_dict: dict = {}
    for chunk in chunks:
        print("... chunk", chunk_index, "out of", len(chunks))

        bunch = BunchOfTransactionsNew()
        for transaction in chunk:
            bunch.transactions.append(transaction)

        num_sent, hashes = bunch.send(proxy)
        if len(chunk) != num_sent:
            print(f"sent {num_sent} instead of {len(chunk)}")

        hash_dict.update(dict(hashes))

        chunk_index += 1

        if sleep is not None:
            time.sleep(sleep)

    return hash_dict

def filter_bunch_of_accounts_by_shard(bunch: BunchOfAccounts, shard: str) -> BunchOfAccounts:
    accounts = bunch.get_in_shard(int(shard)) if shard else bunch.get_all()
    filtered_bunch = BunchOfAccounts(accounts)
    print(f"Filtered bunch of accounts by shard = {shard}. Original = {len(bunch)}, filtered = {len(filtered_bunch)}.")
    return filtered_bunch


def generate_minted_accounts(proxy, num_accounts, sender_account, value):
    pem_dir = "/tmp/pems"
    shutil.rmtree(pem_dir, ignore_errors=True)
    os.mkdir(pem_dir)

    for i in range(num_accounts):
        seed, pubkey = wallet.generate_pair()
        address = Address(pubkey)
        file_name = pem_dir+"/acc"+str(i)+".pem"
        pem.write(file_name, seed, pubkey, name=address.bech32())

    accounts = []
    for pem_file in os.listdir(pem_dir):
        pem_file = path.join(pem_dir, pem_file)
        account = Account(pem_file=pem_file)
        accounts.append(account)
    network = proxy.get_network_config()
    sender_account.sync_nonce(proxy)

    for account in accounts:
        tx = Transaction()
        tx.nonce = sender_account.nonce
        tx.value = value
        tx.sender = sender_account.address.bech32()
        tx.receiver = account.address.bech32()
        tx.gas_price = network.min_gas_price
        tx.gas_limit = 50000
        tx.data = ""
        tx.chain_id = network.chain_id
        tx.version = network.min_tx_version
        tx.sign(sender_account)
        tx.send(proxy)

        print(f"minted account {account.address.bech32()}")
        sender_account.nonce += 1

        dictionary = tx.to_dictionary()
        proxy.send_transaction_and_wait_for_result(dictionary)

    return accounts

class BunchOfTransactionsNew:
    def __init__(self):
        self.transactions: List[Transaction] = []

    def add_prepared(self, transaction: Transaction):
        self.transactions.append(transaction)

    def add(self, sender: Account, receiver_address: str, nonce: Any, value: Any, data: str, gas_price: int,
            gas_limit: int, chain: str, version: int, options: int):
        tx = Transaction()
        tx.nonce = int(nonce)
        tx.value = str(value)
        tx.receiver = receiver_address
        tx.sender = sender.address.bech32()
        tx.gas_price = gas_price
        tx.gas_limit = gas_limit
        tx.data = data
        tx.chain_id = chain
        tx.version = version
        tx.options = options

        self.transactions.append(tx)

    def add_tx(self, tx):
        self.transactions.append(tx)

    def sign(self, proxy: ProxyNetworkProvider, deployer: Account):
        transaction_computer = TransactionComputer()
        for transaction in self.transactions:
            transaction.signature = deployer.sign_transaction(transaction_computer.compute_bytes_for_signing(transaction))

    def send(self, proxy: ProxyNetworkProvider):
        logger.info(f"BunchOfTransactions.send: {len(self.transactions)} transactions")

        num_sent, hashes = proxy.send_transactions(self.transactions)
        # num_sent, hashes = proxy.send_transaction(self.transactions[1])

        logger.info(f"Sent: {num_sent}")
        logger.info(f"TxsHashes: {hashes}")
        return num_sent, hashes