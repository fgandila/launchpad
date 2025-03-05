from time import sleep

from multiversx_sdk.network_providers import ProxyNetworkProvider


def wait_idle_blockchain(proxy: ProxyNetworkProvider, waited_idle_blocks: int = 7, period: int = 5):
    num_idle_blocks = 0

    while True:
        sleep(period)

        nonce = proxy.get_network_status("metachain").nonce
        hyperblock = proxy.get_hyperblock(nonce)
        num_txs = hyperblock["numTxs"]
        print(f"Hyperblock ({nonce}), txs = {num_txs}. Idleness = {num_idle_blocks} / {waited_idle_blocks}")

        is_idle = num_txs == 0
        if is_idle:
            num_idle_blocks += 1
        else:
            num_idle_blocks = 0

        if num_idle_blocks > waited_idle_blocks:
            return


def wait_num_of_rounds(proxy: ProxyNetworkProvider, wait_blocks: int = 7):
    num_waited = 0
    time = 6    # TODO: fetch network configuration for round time

    while num_waited < wait_blocks:
        sleep(time)
        num_waited += 1
        print("Waited ", num_waited, " rounds out of ", wait_blocks)

    return

