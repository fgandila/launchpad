import concurrent.futures as cf
import random
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path
from typing import Dict
from multiversx_sdk import ProxyNetworkProvider
import config
import utils
from utils.utils_chain import Account
from multiversx_sdk import Address
from multiversx_sdk.network_providers.accounts import AccountOnNetwork
from multiversx_sdk.network_providers import ProxyNetworkProvider
from multiversx_sdk import Transaction

PERIODADDTICKETS = "add_tickets"
PERIODCONFIRMSTART = "confirm_start"
PERIODSELECTWINNERS = "select_winners"
PERIODCLAIM = "claim"


class LaunchpadView:
    def __init__(self, fnct_name: str, result_types: list, args: list = []):
        self.view_query = ""
        self.args = args
        self.result_types = result_types


class AccountStateTracker:
    def __init__(self, account_address: str, owner: bool):
        self.address = account_address  # Bech32 address
        self.is_owner = owner
        self.is_blacklisted = False
        self.is_refunded = False
        self.num_tickets = 0
        self.energy_tickets = 0
        self.social_tickets = 0
        self.num_confirmed_tickets = 0
        self.nft_confirmed = 0
        self.winning_tickets = []
        self.winning_nft = 0
        self.guaranteed_tickets = 0

    def blacklist_account(self):
        self.is_blacklisted = True

    def whitelist_account(self):
        self.is_blacklisted = False

    def refunded_account(self):
        self.is_refunded = True

    def add_tickets(self, num: int):
        self.num_tickets += num

    def add_energy_tickets(self, num: int):
        self.num_tickets += num
        self.energy_tickets += num

    def add_social_tickets(self, num: int):
        self.num_tickets += num
        self.social_tickets += num

    def add_guaranteed_ticket(self):
        self.guaranteed_tickets += 1

    def add_confirmed_tickets(self, num: int):
        if num <= self.num_tickets - self.num_confirmed_tickets:
            self.num_confirmed_tickets += num
            return True
        return False

    def add_nft_confirmed(self):
        self.nft_confirmed = 1

    def set_winning_tickets(self, ticket_ids: list):
        self.winning_tickets.extend(ticket_ids)

    def set_winning_nft(self):
        self.winning_nft = 1


lp_contract_owner = dict()
lp_period_tracker = dict()
lp_endpoint_permissions = dict()
lp_accounts_state_tracker: Dict[str, AccountStateTracker] = dict()
lp_txhash_tracker = dict()
lp_missed_txs = 0
lp_total_guaranteed_tickets = 0


class LaunchpadPeriodTracker:
    def __init__(self, confirm_time: int, select_winners_time: int, claim_time: int, proxy: str, epoch_based: bool,
                 vesting_claim_start: int = 0, vesting_initial_release: int = 0, vesting_times: int = 0, vesting_percentage: int = 0, vesting_period: int = 0):
        self.confirm_time = confirm_time
        self.select_winners_time = select_winners_time
        self.claim_time = claim_time
        self.current_period = ""
        self.last_contract_time = 0
        self.last_update_time = datetime.now()
        self.deploy_time = datetime.now()
        self.proxy = ProxyNetworkProvider(proxy)
        self.time_unit = "epoch" if epoch_based else "block"
        self.vesting_claim_start = vesting_claim_start
        self.vesting_initial_release = vesting_initial_release
        self.vesting_times = vesting_times
        self.vesting_percentage = vesting_percentage
        self.vesting_period = vesting_period

    def update_period(self):
        # TODO: create an alarm mechanism to avoid unnecessary API request if rounds/epoch not passed

        # update the period as rare as possible to avoid API overload
        time_now = datetime.now()
        time_since_last_update = time_now - self.last_update_time
        if time_since_last_update > timedelta(seconds=2):
            network_status = self.proxy.get_network_status(config.OWNER_SHARD)
            current_time = network_status.current_epoch if self.time_unit == "epoch" else network_status.current_round
            self.last_update_time = time_now
            self.last_contract_time = current_time
        else:
            current_time = self.last_contract_time

        if current_time < self.confirm_time:
            self.current_period = PERIODADDTICKETS

        if self.confirm_time <= current_time < self.select_winners_time:
            self.current_period = PERIODCONFIRMSTART

        if self.select_winners_time <= current_time < self.claim_time:
            self.current_period = PERIODSELECTWINNERS

        if self.claim_time <= current_time:
            self.current_period = PERIODCLAIM

    def get_current_period(self) -> str:
        return self.current_period


# Add a new period tracker for specified SC address.
# Dict is useful in case of testrun with multiple deployed SCs.
# Function should be called as an initializer after SC deploy.
def add_period_tracker_for_address(contract_address: str, confirm_time: int, select_winners_time: int, claim_time: int,
                                   proxy: str, epochs_based: bool, 
                                   vesting_claim_start: int = 0, vesting_initial_release: int = 0, vesting_times: int = 0, vesting_percentage: int = 0, vesting_period: int = 0):
    global lp_period_tracker
    lp_period_tracker[contract_address] = LaunchpadPeriodTracker(confirm_time, select_winners_time, claim_time,
                                                                 proxy, epochs_based,
                                                                 vesting_claim_start, vesting_initial_release, vesting_times, vesting_percentage, vesting_period)


# Update the period tracker state based on network data for the specified SC
# Function should be called as often as needed, based
# on the necessities of the component using the launchpad periods.
def update_period_tracker_for_address(contract_address: str):
    global lp_period_tracker
    lp_period_tracker[contract_address].update_period()


# Returns the state of the period tracker as it was last updated
def get_current_period_for_address(contract_address: str) -> str:
    return lp_period_tracker[contract_address].get_current_period()


def set_contract_owner(contract_address: str, owner_account: Account):
    global lp_contract_owner
    if contract_address not in lp_contract_owner.keys():
        lp_contract_owner[contract_address] = owner_account


def get_contract_owner(contract_address: str) -> Account:
    return lp_contract_owner[contract_address]


def increment_contract_owner_nonce(contract_address: str):
    global lp_contract_owner
    lp_contract_owner[contract_address].nonce += 1


def sync_contract_owner_nonces(proxy: ProxyNetworkProvider):
    global lp_contract_owner
    for sc in lp_contract_owner.keys():
        lp_contract_owner[sc].sync_nonce(proxy)

class LaunchpadEndpoint:
    def __init__(self, fnct_name: str, active_in_periods: list, owner_only: bool):
        self.fnct_name = fnct_name
        self.active_in_periods = active_in_periods
        self.owner_only = owner_only

    def is_allowed_in_period(self, period: str) -> bool:
        return True if period in self.active_in_periods else False

    def is_owner_only(self) -> bool:
        return self.owner_only


def create_endpoint_permission_dict() -> dict:
    endpoint_dict = dict()
    endpoint_dict["confirmTickets"] = LaunchpadEndpoint("confirmTickets", [PERIODCONFIRMSTART], False)
    endpoint_dict["setUnlockSchedule"] = LaunchpadEndpoint("setUnlockSchedule", [PERIODADDTICKETS], True)
    endpoint_dict["confirmNft"] = LaunchpadEndpoint("confirmNft", [PERIODCONFIRMSTART], False)
    endpoint_dict["addTickets"] = LaunchpadEndpoint("addTickets", [PERIODADDTICKETS], True)
    endpoint_dict["addMoreGuaranteedTickets"] = LaunchpadEndpoint("addMoreGuaranteedTickets", [PERIODADDTICKETS], True)
    endpoint_dict["filterTickets"] = LaunchpadEndpoint("filterTickets", [PERIODSELECTWINNERS], False)
    endpoint_dict["selectWinners"] = LaunchpadEndpoint("selectWinners", [PERIODSELECTWINNERS], False)
    endpoint_dict["selectNftWinners"] = LaunchpadEndpoint("selectWinners", [PERIODSELECTWINNERS], False)
    endpoint_dict["distributeGuaranteedTickets"] = LaunchpadEndpoint("distributeGuaranteedTickets", [PERIODSELECTWINNERS], False)
    endpoint_dict["claimTicketPayment"] = LaunchpadEndpoint("claimTicketPayment", [PERIODCLAIM], True)
    endpoint_dict["claimLaunchpadTokens"] = LaunchpadEndpoint("claimLaunchpadTokens", [PERIODCLAIM], False)
    endpoint_dict["depositLaunchpadTokens"] = LaunchpadEndpoint("depositLaunchpadTokens", [PERIODADDTICKETS, PERIODCONFIRMSTART], True)
    endpoint_dict["setTicketPaymentToken"] = LaunchpadEndpoint("setTicketPaymentToken", [PERIODADDTICKETS], True)
    endpoint_dict["setTicketPrice"] = LaunchpadEndpoint("setTicketPrice", [PERIODADDTICKETS], True)
    endpoint_dict["setLaunchpadTokensPerWinningTicket"] = LaunchpadEndpoint("setLaunchpadTokensPerWinningTicket", [PERIODADDTICKETS], True)
    endpoint_dict["setConfirmationPeriodStartEpoch"] = LaunchpadEndpoint("setConfirmationPeriodStartEpoch", [PERIODADDTICKETS], True)
    endpoint_dict["setWinnerSelectionStartEpoch"] = LaunchpadEndpoint("setWinnerSelectionStartEpoch", [PERIODADDTICKETS], True)
    endpoint_dict["setClaimStartEpoch"] = LaunchpadEndpoint("setClaimStartEpoch", [PERIODADDTICKETS], True)
    endpoint_dict["setConfirmationPeriodStartRound"] = LaunchpadEndpoint("setConfirmationPeriodStartBlock",
                                                                         [PERIODADDTICKETS], True)
    endpoint_dict["setWinnerSelectionStartRound"] = LaunchpadEndpoint("setWinnerSelectionStartRound",
                                                                      [PERIODADDTICKETS], True)
    endpoint_dict["setClaimStartRound"] = LaunchpadEndpoint("setClaimStartBlock", [PERIODADDTICKETS], True)
    endpoint_dict["removeAddressFromBlacklist"] = LaunchpadEndpoint("removeAddressFromBlacklist", [PERIODADDTICKETS, PERIODCONFIRMSTART, PERIODSELECTWINNERS], True)
    endpoint_dict["addAddressToBlacklist"] = LaunchpadEndpoint("addAddressToBlacklist", [PERIODADDTICKETS, PERIODCONFIRMSTART, PERIODSELECTWINNERS], True)
    return endpoint_dict


# Initializes the dictionary containing endpoint permissions.
# Function should be called as an initializer before starting to run the test flows.
def init_endpoint_permissions():
    global lp_endpoint_permissions
    lp_endpoint_permissions = create_endpoint_permission_dict()


# Adds state tracker for the given address if not already existing
def add_account_tracker_for_address(address: str, owner: str):
    global lp_accounts_state_tracker
    if address not in lp_accounts_state_tracker.keys():
        is_owner = False
        if address == owner:
            is_owner = True
        lp_accounts_state_tracker[address] = AccountStateTracker(address, is_owner)


def update_account_lp_status(address: str, contract, proxy):
    global lp_accounts_state_tracker
    address_obj = Address(address)

    # Get winning ticket ids per account
    result = contract.query(proxy, "getWinningTicketIdsForAddress", ["0x" + address_obj.hex()])
    for ticket_id in result:
        lp_accounts_state_tracker[address].set_winning_tickets([ticket_id.number])
        # print(f'{ticket_id.number}')

    # Get NFT winnings per account
    # result = contract.query(proxy, "hasUserWonNft", ["0x" + address_obj.hex()])
    # if result[0] != "":
    #     lp_accounts_state_tracker[address].set_winning_nft()
        # print(f'Won NFT.')


def set_account_tracking_winning_status(proxy_url: str):
    print(f"Setting the account tracking status for winning tickets")
    proxy = ProxyNetworkProvider(proxy_url)
    global lp_accounts_state_tracker

    # check only a few accounts to reduce API overload when needed
    if config.NR_ACCOUNTS_TO_SAMPLE > 0:
        account_sample_pool = random.sample(list(lp_accounts_state_tracker.values()),
                                            min(config.NR_ACCOUNTS_TO_SAMPLE, len(lp_accounts_state_tracker)))
    else:
        account_sample_pool = lp_accounts_state_tracker.values()

    print("Setting state for", len(account_sample_pool), "accounts out of", len(lp_accounts_state_tracker))

    for contract_addr in lp_contract_owner.keys():
        contract = SmartContract(Address(contract_addr))
        with cf.ThreadPoolExecutor(100) as executor:
            futures = []
            for tracked_account in account_sample_pool:
                futures.append(executor.submit(update_account_lp_status, tracked_account.address, contract, proxy))
            cf.wait(futures)


def check_account_tracking_status(proxy_url: str):
    print("### Tracked state of accounts below")
    proxy = ProxyNetworkProvider(proxy_url)
    check_failed = {"getTotalNumberOfTicketsForAddress": False,
                    "getNumberOfConfirmedTicketsForAddress": False,
                    "getConfirmedNFTForAddress": False,
                    "isUserBlacklisted": False}

    account_sample_pool = []
    # check only a few accounts to reduce API overload when needed
    if config.NR_ACCOUNTS_TO_SAMPLE > 0:
        account_sample_pool = random.sample(list(lp_accounts_state_tracker.values()),
                                            min(config.NR_ACCOUNTS_TO_SAMPLE, len(lp_accounts_state_tracker)))
    else:
        account_sample_pool = lp_accounts_state_tracker.values()

    print("Checking state for", len(account_sample_pool), "accounts out of", len(lp_accounts_state_tracker))
    for tracked_account in account_sample_pool:
        for contract_addr in lp_contract_owner.keys():
            contract = SmartContract(Address(contract_addr))
            account = Account(tracked_account.address)

            """ DEBUG PURPOSES - shows gathered stats for each account
            print("Account:", tracked_account.address,
                  "blacklist status:", tracked_account.is_blacklisted,
                  "no of tickets:", tracked_account.num_tickets,
                  "no of confirmed tickets:", tracked_account.num_confirmed_tickets)
            """

            # Check expected number of tickets per account
            result = contract.query(proxy, "getTotalNumberOfTicketsForAddress", ["0x" + account.address.hex()])
            if tracked_account.num_tickets != 0:
                if result[0] == "" or result[0].number != tracked_account.num_tickets:
                    print("Expected number of tickets not matching for account:", tracked_account.address,
                          "Expected:", tracked_account.num_tickets,
                          "Got:", 0 if result[0] == "" else result[0].number)
                    check_failed["getTotalNumberOfTicketsForAddress"] = True

            # Check expected number of confirmed tickets per account
            result = contract.query(proxy, "getNumberOfConfirmedTicketsForAddress", ["0x" + account.address.hex()])
            if tracked_account.num_confirmed_tickets != 0:
                if result[0] == "" or result[0].number != tracked_account.num_confirmed_tickets:
                    print("Expected number of confirmed tickets not matching for account:", tracked_account.address,
                          "Expected:", tracked_account.num_confirmed_tickets,
                          "Got:", 0 if result[0] == "" else result[0].number)
                    check_failed["getNumberOfConfirmedTicketsForAddress"] = True

            # Check expected number of confirmed NFTs per account
            result = contract.query(proxy, "hasUserConfirmedNft", ["0x" + account.address.hex()])
            if tracked_account.nft_confirmed != 0:
                if result[0] == "" or result[0].number != tracked_account.nft_confirmed:
                    print("Expected number of confirmed NFTs not matching for account:", tracked_account.address,
                          "Expected:", tracked_account.nft_confirmed,
                          "Got:", 0 if result[0] == "" else result[0].number)
                    check_failed["getConfirmedNFTForAddress"] = True

            # Check blacklist status for account
            result = contract.query(proxy, "isUserBlacklisted", ["0x" + account.address.hex()])
            if tracked_account.is_blacklisted:
                if result[0] == "" or result[0].number != 1:
                    print("Expected account to be blacklisted but was not:", tracked_account.address)
                    check_failed["isUserBlacklisted"] = True

    if not check_failed["getTotalNumberOfTicketsForAddress"]:
        print("All expected number of tickets for addresses matched.")
    if not check_failed["getNumberOfConfirmedTicketsForAddress"]:
        print("All expected confirmed number of tickets for addresses matched.")
    if not check_failed["getConfirmedNFTForAddress"]:
        print("All expected confirmed number of NFTs for addresses matched.")
    if not check_failed["isUserBlacklisted"]:
        print("All expected blacklist statuses for accounts matched.")


def save_account_tracking_exp_status(filename: str):
    time_now = datetime.now()
    deploy_time = next(iter(lp_period_tracker.values())).deploy_time
    out_filename = str(time_now.year) + str(time_now.month) + str(time_now.day) + \
                   str(time_now.hour) + str(time_now.minute) + "_" + str(deploy_time.minute) + str(deploy_time.second) + \
                   "_" + filename + ".json"
    filepath = str(config.DEFAULT_WORKSPACE) + "//results//" + out_filename
    print("Saving account tracking statuses in file:", filepath)

    utils.ensure_folder(Path(filepath).parent)
    with open(filepath, "w") as f:
        dump_data = []
        for tracked_account in lp_accounts_state_tracker.values():
            dump_data.append({
                "index": list(lp_accounts_state_tracker.keys()).index(tracked_account.address),
                "address": tracked_account.address,
                "added_tickets": tracked_account.num_tickets,
                "energy_tickets": tracked_account.energy_tickets,
                "confirmed_tickets": tracked_account.num_confirmed_tickets,
                "confirmed_nfts": tracked_account.nft_confirmed,
                "blacklisted": tracked_account.is_blacklisted,
                "guaranteed_tickets": tracked_account.guaranteed_tickets,
                "winning_tickets": tracked_account.winning_tickets,
                "winning_nft": tracked_account.winning_nft
            })
        utils.dump_out_json(dump_data, f)


def get_and_save_contract_state(proxy_url: str, filename: str):
    print(f"Saving contract state in file: {filename}")

    proxy = ProxyNetworkProvider(proxy_url)
    contract_address = list(lp_contract_owner.keys())[0]

    time_now = datetime.now()
    deploy_time = next(iter(lp_period_tracker.values())).deploy_time
    out_filename = str(time_now.year) + str(time_now.month) + str(time_now.day) + \
                   str(time_now.hour) + str(time_now.minute) + "_" + str(deploy_time.minute) + str(deploy_time.second) + \
                   "_" + filename + ".json"
    filepath = str(config.DEFAULT_WORKSPACE) + "//results//" + out_filename

    utils.ensure_folder(Path(filepath).parent)
    with open(filepath, "w") as f:
        contract_state = proxy.get_keys(contract_address)
        utils.dump_out_json(contract_state, f)


def check_claim_payment_status(proxy_url: str):
    print("### Current status for claim payment below:")
    # TODO: track the claimTicketPayment tx and use the data inside the SCRs to do the checks


def get_winners_selected_status(proxy_url: str) -> bool:
    print("### Current status of winners select below:")
    proxy = ElrondProxy(proxy_url)
    for contract_addr in lp_contract_owner.keys():
        contract = SmartContract(Address(contract_addr))
        result = contract.query(proxy, "wereWinnersSelected", [])
        if result[0] == "":
            print("selectWinners not yet complete.")
            return False
        else:
            print("selectWinners completed.")
            return True

    print("WARNING: Inconclusive result!")
    return False


# TODO: filter tickets status: SCRs have to be processed to take the latest status. If one of them is completed, it's done.
# TODO: wereWinnersSelected has view available

def add_txhash_expected_results(hashes: dict, results: list, transactions: list = []):
    global lp_txhash_tracker, lp_missed_txs

    if len(hashes) != len(results):
        print("####### WARNING: number of tx hashes not equal to number of expected results")

    for i, _ in enumerate(results):
        if not str(i) in hashes.keys():
            print("####### WARNING: no hash generated for transaction:", i, "nonce:",
                  transactions[i].nonce, "sender:", transactions[i].sender, "receiver:",
                  transactions[i].receiver, "Will skip in final checks.")
            lp_missed_txs += 1
        else:
            lp_txhash_tracker[hashes[str(i)]] = results[i]
            """ DEBUG PURPOSES - shows data for each generated tx hash track
            print("Created results track for index", i, "hash", hashes[str(i)], results[i], "data", transactions[int(i)].data, "nonce:",
                  transactions[i].nonce, "sender:", transactions[i].sender, "receiver:", transactions[i].receiver)
            """


def check_txhash_results(proxy_url: str):
    print("### Transaction execution results below:")
    proxy = ProxyNetworkProvider(proxy_url)

    tx_sample_pool = {}
    # check only a few hashes to reduce API overload when needed
    if config.NR_TX_TO_SAMPLE > 0:
        selected_list = random.sample(list(lp_txhash_tracker.items()),
                                      min(config.NR_TX_TO_SAMPLE, len(lp_txhash_tracker)))
        for key, value in selected_list:
            tx_sample_pool[key] = value
    else:
        tx_sample_pool = lp_txhash_tracker

    print("Checking expected results for", len(tx_sample_pool), "tx hashes out of", len(lp_txhash_tracker))
    for txhash, result in tx_sample_pool.items():
        chain_result = dict()
        try:
            chain_result = proxy.get_transaction(txhash).raw
        except:
            pass

        if "status" not in chain_result.keys():
            print("### FAIL: TX Hash not found:", txhash)
        else:
            if bool(chain_result["status"] == "success") != bool(result):
                link = proxy_url + "/transaction/" + txhash
                print("### FAIL: Expected result not matched in tx hash:", link, "Result:", chain_result["status"],
                      "instead of", "success" if result else "fail")


def save_txhash_exp_results(filename: str):
    print("Saving tx hash expected results in file:", filename)

    time_now = datetime.now()
    deploy_time = next(iter(lp_period_tracker.values())).deploy_time
    out_filename = str(time_now.year) + str(time_now.month) + str(time_now.day) + \
                   str(time_now.hour) + str(time_now.minute) + "_" + str(deploy_time.minute) + str(deploy_time.second) + \
                   "_" + filename + ".json"
    filepath = str(config.DEFAULT_WORKSPACE) + "//results//" + out_filename

    utils.ensure_folder(Path(filepath).parent)
    with open(filepath, "w") as f:
        dump_data = []
        for key, value in lp_txhash_tracker.items():
            dump_data.append({
                "index": list(lp_txhash_tracker.keys()).index(key),
                "txhash": key,
                "expected_result": value
            })
        utils.dump_out_json(dump_data, f)
