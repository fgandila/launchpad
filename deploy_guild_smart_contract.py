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
provider = ProxyNetworkProvider("https://proxy-shadowfork-three.elrond.ro")

# Get account for the signing wallet
test_account = provider.get_account(test_address)

# Get network configuration
network_config = provider.get_network_config()

# Load the signer from the pem file for the signing wallet
signer = UserSigner.from_pem_file(
    Path(config["signingWalletPemPath"]),
)

# Create a smart contract transaction factory
sc_factory = SmartContractTransactionsFactory(network_config)

# Load the bytecode of the smart contract
bytecode = Path("/home/multiversx/Documents/guilds_py/wasm/guild-sc.wasm").read_bytes()

deploy_transaction = sc_factory.create_transaction_for_deploy(
    sender=test_address,
    bytecode=bytecode,
    arguments=[
        config["farmingToken"],  # farming_token_id
        1000000000000,  # division_safety_constant
        Address.from_bech32(config["guildConfigScAddressModel"]),  # config_sc_address
        test_address,  # guild_master_address
        test_address,  # mut admins
    ],
    gas_limit=500000000,
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
print("Guild deploy transaction hash:", result)

# Wait for the transaction to be included in a block
import time

time.sleep(5)

retry_count = 5
try:
    while (
        retry_count > 0 and not provider.get_transaction_status(result).is_successful()
    ):
        retry_count -= 1
        time.sleep(5)

    if retry_count == 0:
        raise Exception("Transaction failed")

    print("Transaction successful")
    tx_details = provider.get_transaction(result)
    guild_contract_address = tx_details.logs.events[0].address.to_bech32()
    print("Guild contract address:", guild_contract_address)

    config["guildScAddressModel"] = guild_contract_address
    with open("config_file.yaml", "w") as file:
        yaml.dump(config, file)

except Exception as e:
    print(e)
    print("Transaction failed")
