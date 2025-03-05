import requests
from config import DEFAULT_PROXY
from utils.chain_sim.chain_commander import *
import time


def force_reset_validator_statistics():
    route = f"{DEFAULT_PROXY}/simulator/force-reset-validator-statistics"
    response = requests.post(route)
    response.raise_for_status()

    # add an extra block
    add_blocks(1)

    # wait 1 sec
    time.sleep(1)
