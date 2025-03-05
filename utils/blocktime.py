from argparse import ArgumentParser
import sys
from multiversx_sdk import ProxyNetworkProvider
from multiversx_sdk import ApiNetworkProvider

from typing import List

import datetime

"""
Script to determine a target block nonce starting from a humanlike date-time.
Example usage:
$ python3 blocktime.py --net=devnet --shard=1 --date="22/10/25 20:00"
"""

DEVPROXY_URL = "https://devnet-gateway.elrond.com"
TESTPROXY_URL = "https://testnet-gateway.elrond.com"
MAINPROXY_URL = "https://gateway.elrond.com"

DEVAPI_URL = "https://devnet-api.multiversx.com"
TESTAPI_URL = "https://testnet-api.multiversx.com"
MAINAPI_URL = "https://api.multiversx.com"

BLOCK_DURATION = 6
ROUND_DURATION = 6


def _get_block_by_nonce(proxy: ProxyNetworkProvider, shard_id: int, block_nonce: int):
        url = f"{proxy.url}/block/{shard_id}/by-nonce/{block_nonce}"
        response = proxy.do_get(url)
        payload = response.get("block")
        return payload


def main(cli_args: List[str]):
    parser = ArgumentParser()
    parser.add_argument("--net", required=True)
    parser.add_argument("--shard", required=True)
    parser.add_argument("--date", required=True)    # localtime format as: "22/10/24 20:00"

    args = parser.parse_args(cli_args)
    if args.net == "mainnet":
        proxy = ProxyNetworkProvider(MAINPROXY_URL)
    elif args.net == "devnet":
        proxy = ProxyNetworkProvider(DEVPROXY_URL)
    elif args.net == "testnet":
        proxy = ProxyNetworkProvider(TESTPROXY_URL)
    else:
        print("Invalid net")
        return

    if int(args.shard) not in [0, 1, 2]:
        print("Invalid shard")
        return
    shard = args.shard

    last_nonce = proxy.get_network_status(shard).nonce
    last_round = proxy.get_network_status(shard).current_round
    block_data = _get_block_by_nonce(proxy, shard, last_nonce)

    if not block_data:
        return

    block_timestamp = block_data["timestamp"]

    # target_date = datetime.datetime(2022, 10, 24, 20, 00, 00)
    # date_string = "22/10/24 20:00"
    target_date = datetime.datetime.strptime(args.date, '%y/%m/%d %H:%M')
    td_timestamp = int(target_date.timestamp())
    
    print(f"Calculating from block: {last_nonce} round: {last_round} shard: {shard}")
    print(f"Current date: {datetime.datetime.fromtimestamp(block_timestamp)} (timestamp of last produced block)")
    print(f"Target date: {target_date}")

    delta_timestamp = td_timestamp - block_timestamp
    delta_blocks = delta_timestamp // BLOCK_DURATION
    delta_rounds = delta_timestamp // ROUND_DURATION
    target_block = last_nonce + delta_blocks
    target_round = last_round + delta_rounds

    # print(f"\nTarget block: {target_block}")
    print(f"Target time: {td_timestamp}")

    return target_block, target_round, td_timestamp


if __name__ == "__main__":
    main(sys.argv[1:])