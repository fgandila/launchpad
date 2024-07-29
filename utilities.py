from multiversx_sdk import (
    AccountNonceHolder,
    Address,
    Token,
    TokenComputer,
    TokenTransfer,
    TransactionComputer,
)
from multiversx_sdk import Transaction
from pathlib import Path
from multiversx_sdk import SmartContractTransactionsFactory
import time

from multiversx_sdk import ProxyNetworkProvider
from multiversx_sdk import UserSigner
import yaml


def tx_success(tx, provider: ProxyNetworkProvider):

    while provider.get_transaction_status(tx).is_pending():
        time.sleep(1)

    if provider.get_transaction_status(tx).is_failed():
        return False
    return True


def get_default_data():

    # Read config
    with open("config_file.yaml", "r") as file:
        config = yaml.safe_load(file)

    # Signing wallet bech32 address
    test_address = Address.from_bech32(config["signingWalletAddress"])
    guild_factory_address = Address.from_bech32(config["guildFactoryScAddress"])

    # Network provider
    provider = ProxyNetworkProvider("https://proxy-shadowfork-three.elrond.ro")

    # Get account for the signing wallet
    test_account = provider.get_account(test_address)

    # Get network configuration
    network_config = provider.get_network_config()

    # Load the signer from the pem file for the signing wallet
    signer = UserSigner.from_pem_file(
        Path(config["signingWalletPemPath"]),
    )

    # Nonce holder
    nonce_holder = AccountNonceHolder(test_account.nonce)

    sc_factory = SmartContractTransactionsFactory(network_config)

    return (
        config,
        test_address,
        guild_factory_address,
        provider,
        network_config,
        signer,
        nonce_holder,
        sc_factory,
    )


def to_decimal(value: int, decimals: int):
    return value * (10**decimals)
