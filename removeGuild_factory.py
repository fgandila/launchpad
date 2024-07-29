from multiversx_sdk import (
    Address,
    ContractQueryBuilder,
    TransactionComputer,
)
import time

from utilities import get_default_data

(
    config,
    test_address,
    guild_factory_address,
    provider,
    network_config,
    signer,
    nonce_holder,
    sc_factory,
) = get_default_data()

builder = ContractQueryBuilder(
    contract=guild_factory_address,
    function="getAllGuilds",
    call_arguments=[],
    caller=test_address,
)

query = builder.build()
query_response = provider.query_contract(query)
import base64
import binascii

# print(base64.b64decode(query_response.return_data[0]))

data_parts = query_response.get_return_data_parts()

guild_address = None
for part in data_parts:

    owner_address = Address(part[32:], "erd").to_bech32()
    if owner_address == test_address.to_bech32():
        guild_address = Address(part[:32], "erd")
        break

if guild_address is not None:
    # Remove guild
    remove_guild_tx = sc_factory.create_transaction_for_execute(
        sender=test_address,
        contract=guild_factory_address,
        function="closeGuildNoRewardsRemaining",
        gas_limit=5000000,
        arguments=[guild_address, test_address],
    )

    remove_guild_tx.nonce = nonce_holder.get_nonce_then_increment()
    remove_guild_tx.signature = signer.sign(
        TransactionComputer().compute_bytes_for_signing(remove_guild_tx)
    )

    result = provider.send_transaction(remove_guild_tx)
    print("Remove Guild transaction hash:", result)
