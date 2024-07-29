from multiversx_sdk import (
    TransactionComputer,
)
from pathlib import Path
import time
import yaml

from utilities import get_default_data, tx_success

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

# Call deployGuild function
deploy_guild_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_factory_address,
    function="deployGuild",
    gas_limit=42000000,
    arguments=[],
)

deploy_guild_tx.nonce = nonce_holder.get_nonce_then_increment()
deploy_guild_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(deploy_guild_tx)
)


result = provider.send_transaction(deploy_guild_tx)
print("Deploy Guild transaction hash:", result)
time.sleep(3)

# Get deployed guild address
deployed_guild_address = ""
if tx_success(result, provider):
    deployed_guild_address = (
        provider.get_transaction(result).logs.events[1].address.to_bech32()
    )

    print("Deployed Guild address:", deployed_guild_address)
else:
    print("Deploy Guild transaction failed")
    exit(1)

config["deployedGuildAddress"] = deployed_guild_address

# Write config
with open("config_file.yaml", "w") as file:
    yaml.dump(config, file)
