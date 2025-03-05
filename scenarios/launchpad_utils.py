from pathlib import Path
from typing import Any

from multiversx_sdk import (Address, SmartContractTransactionsFactory,
                            TransactionsFactoryConfig)
from multiversx_sdk.abi.abi import Abi


class GuaranteedTicketInfo:
    def __init__(self, guaranteed_tickets: int, min_confirmed_tickets: int):
        self.guaranteed_tickets = guaranteed_tickets
        self.min_confirmed_tickets = min_confirmed_tickets

class UnlockMilestone:
    def __init__(self, release_epoch: int, percentage: int):
        self.release_epoch = release_epoch
        self.percentage = percentage