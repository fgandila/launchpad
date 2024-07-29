from multiversx_sdk import (
    TransactionComputer,
)
import yaml

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

set_guild_master_tiers = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_factory_address,
    function="callConfigFunction",
    gas_limit=50000000,
    arguments=[
        "addGuildMasterTiers",
        4000000000000000000000000,
        1500,
        8000000000000000000000000,
        1750,
        12000000000000000000000000,
        2000,
    ],
)

set_guild_master_tiers.nonce = nonce_holder.get_nonce_then_increment()
set_guild_master_tiers.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(set_guild_master_tiers)
)

result = provider.send_transaction(set_guild_master_tiers)
print("Set Guild Master Tiers transaction hash:", result)

add_user_tiers_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_factory_address,
    function="callConfigFunction",
    gas_limit=50000000,
    arguments=["addUserTiers", 2500, 1000, 4000, 1250, 10000, 1500],
)

add_user_tiers_tx.nonce = nonce_holder.get_nonce_then_increment()
add_user_tiers_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(add_user_tiers_tx)
)

result = provider.send_transaction(add_user_tiers_tx)
print("Set User Tiers transaction hash:", result)
