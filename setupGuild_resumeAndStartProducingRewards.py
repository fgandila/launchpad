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

# Resume guild on guild factory

resume_guild_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_factory_address,
    function="resumeGuild",
    gas_limit=20000000,
    arguments=[guild_address],
)

resume_guild_tx.nonce = nonce_holder.get_nonce_then_increment()
resume_guild_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(resume_guild_tx)
)

result = provider.send_transaction(resume_guild_tx)

print("Resume Guild transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Resume Guild transaction failed")

print("Guild resumed successfully")

# Transfer token to the guild factory
farming_token = Token(config["farmingToken"])
farming_token_transfer = TokenTransfer(farming_token, to_decimal(500000, 18))
farmin_token_stake_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_address,
    function="stakeFarm",
    token_transfers=[farming_token_transfer],
    gas_limit=50000000,
)

farmin_token_stake_tx.nonce = nonce_holder.get_nonce_then_increment()
farmin_token_stake_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(farmin_token_stake_tx)
)

result = provider.send_transaction(farmin_token_stake_tx)

print("Stake Farm Token transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Stake Farm Token transaction failed")
else:
    print("Farm token staked successfully")
