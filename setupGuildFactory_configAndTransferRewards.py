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

from multiversx_sdk import ProxyNetworkProvider
from multiversx_sdk import UserSigner
import yaml

from utilities import to_decimal

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
config_sc_bytecode = Path(config["guildConfigBYTEPATH"]).read_bytes()

from multiversx_sdk.abi.biguint_value import BigUIntValue
from multiversx_sdk.abi.bytes_value import BytesValue
from multiversx_sdk.abi.fields import Field
from multiversx_sdk.abi.serializer import Serializer
from multiversx_sdk.abi.small_int_values import U64Value, U32Value
from multiversx_sdk.abi.struct_value import StructValue

serializer = Serializer(parts_separator="@")

init_args = StructValue(
    fields=[
        Field(
            name="total_staking_tokens_minted",
            value=BigUIntValue(400000000000000000000000000),
        ),
        Field(name="max_staked_tokens", value=BigUIntValue(12000000000000000000000000)),
        Field(name="user_unbond_epochs", value=U64Value(1)),
        Field(name="guild_master_unbond_epochs", value=U64Value(1)),
        Field(name="min_stake_user", value=BigUIntValue(100000000000000000000)),
        Field(
            name="min_stake_guild_master", value=BigUIntValue(500000000000000000000000)
        ),
        Field(name="base_farm_token_id", value=BytesValue(b"UTKFARM")),
        Field(name="base_unbond_token_id", value=BytesValue(b"UTKUNBND")),
        Field(name="base_token_display_name", value=BytesValue(b"sUTK")),
        Field(name="tokens_decimals", value=U32Value(18)),
        Field(name="seconds_per_block", value=U64Value(6)),
        Field(name="per_block_reward_amount", value=BigUIntValue(40000000000000000)),
    ]
)

deploy_config_sc_data = serializer.serialize_to_parts(
    [init_args, BytesValue(config_sc_bytecode)]
)


deploy_config_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_factory_address,
    function="deployConfigSc",
    gas_limit=50000000,
    arguments=deploy_config_sc_data,
)

deploy_config_tx.nonce = nonce_holder.get_nonce_then_increment()
deploy_config_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(deploy_config_tx)
)


result = provider.send_transaction(deploy_config_tx)
print("Guild Config transaction hash:", result)

# Transfer token to the guild factory
farming_token = Token(config["farmingToken"])
farming_token_transfer = TokenTransfer(farming_token, to_decimal(10000, 18))
transfer_rewards_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_factory_address,
    function="depositRewardsAdmins",
    gas_limit=10000000,
    token_transfers=[farming_token_transfer],
)

transfer_rewards_tx.nonce = nonce_holder.get_nonce_then_increment()

transfer_rewards_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(transfer_rewards_tx)
)

result = provider.send_transaction(transfer_rewards_tx)

print("Transfer rewards transaction hash:", result)
