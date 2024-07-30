from multiversx_sdk import Address, TokenComputer, TransactionComputer
from multiversx_sdk import Transaction
from pathlib import Path
from multiversx_sdk import SmartContractTransactionsFactory

from multiversx_sdk import ProxyNetworkProvider
from multiversx_sdk import UserSigner
import yaml

# Read config
with open("config_file.yaml", "r") as file:
    config = yaml.safe_load(file)

# Signing wallet bech32 address
test_address = Address.from_bech32(config["signingWalletAddress"])

# Network provider
provider = ProxyNetworkProvider(config["defaultPROXY"])

# Get account for the signing wallet
test_account = provider.get_account(test_address)

# Get network configuration
network_config = provider.get_network_config()

# Load the signer from the pem file for the signing wallet
signer = UserSigner.from_pem_file(
    Path(config["signingWalletPemPath"]),
)


sc_factory = SmartContractTransactionsFactory(network_config)
bytecode = Path("/home/multiversx/Documents/guilds_py/wasm/guild-factory.wasm").read_bytes()

deploy_transaction = sc_factory.create_transaction_for_deploy(
    sender=test_address,
    bytecode=bytecode,
    arguments=[
        Address.from_bech32(config["guildScAddressModel"]),  # guild_sc_source_address
        config["farmingToken"],  # farming_token_id
        config["divisionSafetyConstant"],  # division_safety_constant
        test_address,  # admins
    ],
    gas_limit=60000000,
    is_upgradeable=True,
    is_readable=True,
    is_payable=True,
    is_payable_by_sc=True,
)
deploy_transaction.nonce = test_account.nonce

transaction_computer = TransactionComputer()

deploy_transaction.signature = signer.sign(
    transaction_computer.compute_bytes_for_signing(deploy_transaction)
)

result = provider.send_transaction(deploy_transaction)
print("Guild factory deploy transaction hash:", result)

import time

time.sleep(5)
retry_count = 5

try:
    while (
        retry_count > 0 and not provider.get_transaction_status(result).is_successful()
    ):
        retry_count -= 1
        time.sleep(3)

    if retry_count == 0:
        raise Exception("Transaction failed")

    print("Transaction successful")
    guild_factory_address = (
        provider.get_transaction(result).logs.events[0].address.to_bech32()
    )

    print("Guild factory address:", guild_factory_address)

    with open("config_file.yaml", "w") as file:
        config["guildFactoryScAddress"] = guild_factory_address
        yaml.dump(config, file)

except Exception as e:
    print(e)
