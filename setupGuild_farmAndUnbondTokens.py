from multiversx_sdk import (
    Address,
    TransactionComputer,
)
import time

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

guild_address = Address.from_bech32(config["deployedGuildAddress"])

# Register farm token
register_farm_token_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_address,
    function="registerFarmToken",
    gas_limit=70000000,
    # arguments=[],
    # "UTKFARM", "UTKFARM", 18,""
    native_transfer_amount=50000000000000000
    # 000000000000000, 
)

register_farm_token_tx.nonce = nonce_holder.get_nonce_then_increment()
register_farm_token_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(register_farm_token_tx)
)

result = provider.send_transaction(register_farm_token_tx)
print("Register Farm Token transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Register Farm Token transaction failed")
else:
    print("Farm token registered successfully")

# Register unbnd token
register_unbond_token_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_address,
    function="registerUnbondToken",
    gas_limit=70000000,
    # arguments=["UTKUNBND", "UTKUNBND", 18, ""],
    native_transfer_amount=50000000000000000,
)

register_unbond_token_tx.nonce = nonce_holder.get_nonce_then_increment()
register_unbond_token_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(register_unbond_token_tx)
)

result = provider.send_transaction(register_unbond_token_tx)
print("Register Unbond Token transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Register Unbond Token transaction failed")
else:
    print("Unbond token registered successfully")

# Set transfer role for farm token
set_transfer_role_farm_token_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_address,
    function="setTransferRoleFarmToken",
    gas_limit=70000000,
)

set_transfer_role_farm_token_tx.nonce = nonce_holder.get_nonce_then_increment()
set_transfer_role_farm_token_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(set_transfer_role_farm_token_tx)
)

result = provider.send_transaction(set_transfer_role_farm_token_tx)
print("Set Transfer Role Farm Token transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Set Transfer Role transaction failed")
else:
    print("Transfer role set for farm token")

# Set transfer role for unbnd token
set_transfer_role_unbond_token_tx = sc_factory.create_transaction_for_execute(
    sender=test_address,
    contract=guild_address,
    function="setTransferRoleUnbondToken",
    gas_limit=70000000,
)

set_transfer_role_unbond_token_tx.nonce = nonce_holder.get_nonce_then_increment()
set_transfer_role_unbond_token_tx.signature = signer.sign(
    TransactionComputer().compute_bytes_for_signing(set_transfer_role_unbond_token_tx)
)

result = provider.send_transaction(set_transfer_role_unbond_token_tx)
print("Set Transfer Role Unbond Token transaction hash:", result)
time.sleep(3)
tx_status = tx_success(result, provider)
if not tx_status:
    print("Set Transfer Role Unbnd Token transaction failed")
else:
#     print("Transfer role set for unbnd token")

    print("Roles and farm tokens set successfully")
