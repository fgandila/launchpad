from multiversx_sdk import Address, TokenComputer, TransactionComputer
from multiversx_sdk import Transaction
from pathlib import Path
from multiversx_sdk import SmartContractTransactionsFactory
import time
import yaml
from multiversx_sdk import ProxyNetworkProvider
from multiversx_sdk import UserSigner

with open("config_file.yaml", "r") as file:
    config = yaml.safe_load(file)

test_address = Address.from_bech32(config["signingWalletAddress"])

provider = ProxyNetworkProvider("https://proxy-shadowfork-three.elrond.ro")
test_account = provider.get_account(test_address)
network_config = provider.get_network_config()
signer = UserSigner.from_pem_file(
    Path("./defi-wallet.pem"),
)

from multiversx_sdk.abi.biguint_value import BigUIntValue
from multiversx_sdk.abi.bytes_value import BytesValue
from multiversx_sdk.abi.fields import Field
from multiversx_sdk.abi.serializer import Serializer
from multiversx_sdk.abi.small_int_values import U64Value, U32Value
from multiversx_sdk.abi.struct_value import StructValue

serializer = Serializer(parts_separator="@")

init_args = StructValue(
    fields=[
        Field(name="total_staking_tokens_minted", value=BigUIntValue(10000000000)),
        Field(name="max_staked_tokens", value=BigUIntValue(100000000000000)),
        Field(name="user_unbond_epochs", value=U64Value(1)),
        Field(name="guild_master_unbond_epochs", value=U64Value(1)),
        Field(name="min_stake_user", value=BigUIntValue(100)),
        Field(name="min_stake_guild_master", value=BigUIntValue(500000)),
        Field(name="base_farm_token_id", value=BytesValue(b"UTKFARM")),
        Field(name="base_unbond_token_id", value=BytesValue(b"UTKUNBND")),
        Field(name="base_token_display_name", value=BytesValue(b"sUTK")),
        Field(name="tokens_decimals", value=U32Value(18)),
        Field(name="seconds_per_block", value=U64Value(6)),
        Field(name="per_block_reward_amount", value=BigUIntValue(20000)),
    ]
)

ctor_data = serializer.serialize_to_parts([init_args])

sc_factory = SmartContractTransactionsFactory(network_config)
bytecode = Path(
    "/home/multiversx/Documents/guilds_py/wasm/guild-sc-config.wasm"
).read_bytes()

deploy_config_sc_data = serializer.serialize_to_parts([init_args, BytesValue(bytecode)])

deploy_transaction = sc_factory.create_transaction_for_deploy(
    sender=test_address,
    bytecode=bytecode,
    arguments=ctor_data,
    gas_limit=40000000,
    is_upgradeable=True,
    is_readable=True,
    is_payable=True,
    is_payable_by_sc=True,
)
print(deploy_transaction.data)
deploy_transaction.nonce = test_account.nonce

print(isinstance(ctor_data[0], bytes))

transaction_computer = TransactionComputer()

deploy_transaction.signature = signer.sign(
    transaction_computer.compute_bytes_for_signing(deploy_transaction)
)

# print("Transaction:", deploy_transaction.__dict__)
# print("Transaction data:", deploy_transaction.data)

result = provider.send_transaction(deploy_transaction)
print("Guild Config transaction hash:", result)
time.sleep(5)

retry_count = 5
try:
    # wait for tx success
    while (
        retry_count > 0 and not provider.get_transaction_status(result).is_successful()
    ):
        print(provider.get_transaction_status(result))
        print(retry_count)
        time.sleep(5)
        retry_count -= 1

    if retry_count == 0:
        raise Exception("Transaction failed")

    tx_details = provider.get_transaction(result)

    config_contract_address = tx_details.logs.events[0].address.to_bech32()

    data = {}
    with open("config_file.yaml", "r") as file:
        data = yaml.safe_load(file)

    data["guildConfigScAddressModel"] = config_contract_address

    with open("config_file.yaml", "w") as file:
        yaml.dump(data, file)

except Exception as e:
    print(e)


        # Field(name="base_farm_token_id", value=BytesValue(b"UTKFARM")),
        # Field(name="base_unbond_token_id", value=BytesValue(b"UTKUNBND")),
        # Field(name="base_token_display_name", value=BytesValue(b"sUTK")),