from multiversx_sdk import (
    Address,
    ContractQueryBuilder,
    Token,
    TokenTransfer,
    TransactionComputer,
)
import time

from utilities import get_default_data, to_decimal, tx_success

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

guild_address = Address.from_bech32(config["deployedGuildAddress"])

# Transfer token to the guild factory
builder = ContractQueryBuilder(
    contract=guild_address,
    function="getFarmTokenId",
    call_arguments=[],
    caller=test_address,
)

query = builder.build()
query_response = provider.query_contract(query)
import base64
import binascii

farm_token_id = query_response.get_return_data_parts()[0].decode("utf-8")
# print(base64.b64decode(query_response.return_data[0]))
data_parts = query_response.get_return_data_parts()
farm_token = Token(farm_token_id, nonce=1)
farming_token_transfer = TokenTransfer(farm_token, to_decimal(500000, 18))
farmin_token_stake_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_address,
    function="closeGuild",
    token_transfers=[farming_token_transfer],
    gas_limit=30000000,
)

farmin_token_stake_tx.nonce = nonce_holder.get_nonce_then_increment()
farmin_token_stake_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(farmin_token_stake_tx)
)

result = provider.send_transaction(farmin_token_stake_tx)

print("Close Guild transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Close Guild transaction failed")
else:
    print("Close Guild staked successfully")
