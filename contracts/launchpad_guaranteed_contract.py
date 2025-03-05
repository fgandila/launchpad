import random
from itertools import cycle
import time
import config
from typing import Any, List, Dict

from contracts.contract import Contract, FlowConfig
from contracts.tracks import TrackOfContract
from scenarios import flow_control
from multiversx_sdk.core import Transaction
from scenarios.launchpad_utils import GuaranteedTicketInfo, UnlockMilestone
from multiversx_sdk.network_providers.network_config import NetworkConfig
from utils import tokens_tracks
from utils.waits import wait_idle_blockchain, wait_num_of_rounds
from multiversx_sdk.network_providers import ElrondProxy

from pathlib import Path
from multiversx_sdk import (AccountNonceHolder, Address, ProxyNetworkProvider, SmartContractTransactionsFactory, TransactionComputer,
                            TransactionsFactoryConfig, TransferTransactionsFactory, UserSigner, Transaction)
from multiversx_sdk.abi.abi import Abi
from multiversx_sdk import Token, TokenTransfer
from multiversx_sdk_cli.projects import Project
from utils.utils_chain import Account, BunchOfAccounts
from typing import List

class PreparedQuery:
    def __init__(self, track: TrackOfContract, function_name: str, arguments: List[str], caller: Address = None, value: int = 0) -> None:
        self.track = track
        self.contract = SmartContract(address=track.address)
        self.function = function_name
        self.arguments = arguments
        self.caller = caller
        self.value = value


class ContractLaunchpadV4(Contract):
    def get_name(self):
        # this contract is used to test the launchpad with pure guaranteed tickets coming from stake & energy
        return "launchpad-v4"

    def run_flow(self, caller: Account, track: TrackOfContract, network_config: NetworkConfig, flow_config: FlowConfig) -> List[Transaction]:
        chain_id = network_config.chain_id
        tx_version = network_config.min_transaction_version
        gas_price = config.DEFAULT_GAS_PRICE
        provider = ProxyNetworkProvider(config.DEFAULT_PROXY)

        contract = SmartContract(address=track.address)
        contractAbi = config.CONTRACT_ABI
        abi = Abi.load(contractAbi)
        factory_config = TransactionsFactoryConfig(config.CHAIN_ID)
        transactions_factory = SmartContractTransactionsFactory(factory_config, abi)
        allusers = UserSigner.from_pem_file_all(config.DEFAULT_ACCOUNTS)
        owner = flow_control.get_contract_owner(track.address.bech32())
        nonce_holder = AccountNonceHolder(owner.nonce)
        transactions: List[Transaction] = []
        transactions_new: List[Transaction] = []
        expected_results: List[bool] = []

        flow_control.update_period_tracker_for_address(track.address.bech32())
        current_lp_period = flow_control.get_current_period_for_address(track.address.bech32())
        flow_control.add_account_tracker_for_address(caller.address.bech32(), track.deployer.bech32())

        global_gas_limit = 0     # set to 0 to disable global override

        max_tickets = config.MAX_TICKETS_TO_CONFIRM
        ticket_tiers = config.TICKET_TIERS
        energy_tiers = config.ENERGY_TIERS
        tokens_per_win_ticket = config.TOKENS_PER_WINNING_TICKET
        ticket_price = config.TICKET_PRICE
        winning_tickets = config.NR_WINNING_TICKETS
        tokens_per_win_ticket_new = config.TOKENS_PER_WINNING_TICKET_NEW

# = random.randint(1, max_tickets)
        def confirmTickets(num: int):
            price: int = ticket_price
            # num = flow_control.lp_accounts_state_tracker[caller.address.bech32()].num_tickets
            value = num * price
            gas_limit = 15000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "confirmTickets", [str(num)], gas_price, gas_limit, value, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["confirmTickets"].is_allowed_in_period(current_lp_period)
            if is_allowed:
                # TODO: additional condition needed to check whether launchpad tokens have been deposited
                result = flow_control.lp_accounts_state_tracker[caller.address.bech32()].add_confirmed_tickets(num)
                expected_results.append(True if result else False)
            else:
                expected_results.append(False)

        def confirmTicketsNew(num: int = random.randint(1, max_tickets), price: int = ticket_price):
            value = num * price
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            
            for user in allusers:
                key = user.get_pubkey()
                if(Address.new_from_hex(key.hex(), "erd") == caller.address):
                    signer = user
                else: 
                    signer = None
                    print("Missing signer")
            args = num

            transaction = transactions_factory.create_transaction_for_execute(
                    sender=Address.new_from_bech32(caller.address.bech32()),
                    contract=Address.new_from_bech32(contract.address.bech32()),
                    function="confirmTickets",
                    gas_limit=gas_limit,
                    arguments=[args],
                    native_transfer_amount=value

                )
            
            transaction.nonce = nonce_holder.get_nonce_then_increment()
            transaction.signature = signer.sign(
                        TransactionComputer().compute_bytes_for_signing(transaction)
                    )
            result = provider.send_transaction(transaction)
            time.sleep(2)
            
            transaction = provider.get_transaction(result) 
            transactions_new.append(transaction)
            
            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["confirmTickets"].is_allowed_in_period(current_lp_period)
            if is_allowed:
                # TODO: additional condition needed to check whether launchpad tokens have been deposited
                result = flow_control.lp_accounts_state_tracker[caller.address.bech32()].add_confirmed_tickets(num)
                expected_results.append(True if result else False)
            else:
                expected_results.append(False)            

        # this will make the Account Owner to add the caller address in the ticket pool
        def addTicketsOwner(num: int = random.choice(ticket_tiers)):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            signer = allusers[0]
            guaranteedtickets = random.randrange(0, 5, 1)
            guaranteedtickets2 = random.choice(ticket_tiers)
            pairs: list[list[Any]] = []
            pairs.append([
                      Address.new_from_bech32(caller.address.bech32()),
                      num,
                      [[1,64],[1,128]]
                    #   [1,1],[1,1]
                    #   [[1,0]]
                      ])

            transaction = transactions_factory.create_transaction_for_execute(
                    sender=Address.new_from_bech32(owner.address.bech32()),
                    contract=Address.new_from_bech32(contract.address.bech32()),
                    function="addTickets",
                    gas_limit=gas_limit,
                    arguments=[pairs]
                )
            
            transaction.nonce = nonce_holder.get_nonce_then_increment()
            transaction.signature = signer.sign(
                        TransactionComputer().compute_bytes_for_signing(transaction)
                    )

            transactions_new.append(provider.send_transaction(transaction))
            
            

            print("Nonce tickets add:", owner.nonce)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            if flow_control.lp_endpoint_permissions["addTickets"].is_allowed_in_period(current_lp_period):
                flow_control.lp_accounts_state_tracker[caller.address.bech32()].add_tickets(num)
                expected_results.append(True)
            else:
                expected_results.append(False)

        # This function will split the total number of accounts in batch TXs to addTickets
        # use hint-volume arg to set number of accounts per tx
        def addTicketsBatchesOwner():
            gas_limit = 600000000
            signer = allusers[0]
            guaranteedtickets = random.choice(ticket_tiers)
            guaranteedtickets2 = random.choice(ticket_tiers)
            bunch_of_accounts = BunchOfAccounts.load_accounts_from_files([config.DEFAULT_ACCOUNTS])
            # bunch_of_accounts = filter_bunch_of_accounts_by_shard(bunch_of_accounts, args.from_shard)
            callers = bunch_of_accounts.get_all()

            allowed_flag = False
            if flow_control.lp_endpoint_permissions["addTickets"].is_allowed_in_period(current_lp_period):
                allowed_flag = True

            args_dict: Dict[int, List] = {}
            count = 0
            # split txs in number of accounts given by hint-volume

            def batch(acc_list, size):
                l = len(acc_list)
                for ndx in range(0, l, size):
                    yield acc_list[ndx:min(ndx + size, l)]
            for acc_slice in batch(callers, flow_config.hint_volume):
                arg_list = []
                for account in acc_slice:
                    flow_control.add_account_tracker_for_address(account.address.bech32(), track.deployer.bech32())
                    num = random.choice(ticket_tiers)
                    # num = 64

                    # add tickets from energy tier
                    energy_num = random.choice(energy_tiers)
                    # energy_num = 78

                    # cap the number of top tier accounts
                    if num == max(ticket_tiers):
                        if config.NR_MAX_ACCOUNTS_TOP_TIER > flow_control.lp_total_guaranteed_tickets:
                            flow_control.lp_total_guaranteed_tickets += 1
                            flow_control.lp_accounts_state_tracker[account.address.bech32()].add_guaranteed_ticket()
                        else:
                            num = random.choice(ticket_tiers[:-1])

                    arg_list.append("0x" + account.address.hex())
                    arg_list.append(num)
                    args_list_ext = []
                    # args_list_ext.append([num,num])
                    args_tickets_struct = [num,num]
                    args_list_ext.append(args_tickets_struct)
                    # args_tickets_struct.append([num,num])

                    pairs: list[list[Any]] = []
                    pairs.append([
                            Address.new_from_bech32(account.address.bech32()),
                            num+energy_num,
                            # []
                            [[1,64],[1,128]]
                    ])

                    transaction = transactions_factory.create_transaction_for_execute(
                                        sender=Address.new_from_bech32(owner.address.bech32()),
                                        contract=Address.new_from_bech32(contract.address.bech32()),
                                        function="addTickets",
                                        gas_limit=50_000_000,
                                        arguments=[pairs]
                                    )
                    transaction.nonce = nonce_holder.get_nonce_then_increment()
                    transaction.signature = signer.sign(
                            TransactionComputer().compute_bytes_for_signing(transaction)
                        )
                    # add tracking on tickets attempted to add
                    flow_control.lp_accounts_state_tracker[account.address.bech32()].add_tickets(num)
                    # args_tickets_struct.append(energy_num)
                    flow_control.lp_accounts_state_tracker[account.address.bech32()].add_energy_tickets(energy_num)

                    # args_list_ext.append(args_tickets_struct)
                    arg_list.append(args_list_ext)
                    transactions.append(transaction)
                
                # increase nonce for owner for each added transaction
                flow_control.increment_contract_owner_nonce(track.address.bech32())
                # track transaction results below
                if allowed_flag:
                    expected_results.append(True)
                else:
                    expected_results.append(False)

        # this will make the Account Owner to add the caller address in the ticket pool
        def addMoreGuaranteedTicketsOwner():
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(
                contract.execute(owner, "addMoreGuaranteedTickets", ["0x" + caller.address.hex()], gas_price, gas_limit,
                                 0, chain_id, tx_version))
            # print("Nonce tickets add:", owner.nonce)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            if flow_control.lp_endpoint_permissions["addMoreGuaranteedTickets"].is_allowed_in_period(current_lp_period):
                flow_control.lp_accounts_state_tracker[caller.address.bech32()].add_guaranteed_ticket()
                expected_results.append(True)
            else:
                expected_results.append(False)

        # this will try the endpoint from caller: can be either user or owner (more likely user if random)
        def addTickets(num: int = random.randrange(0, max_tickets, 10)):
            gas_limit = 600000000
            bunch_of_accounts = BunchOfAccounts.load_accounts_from_files([config.DEFAULT_ACCOUNTS])
            # bunch_of_accounts = filter_bunch_of_accounts_by_shard(bunch_of_accounts, args.from_shard)
            callers = bunch_of_accounts.get_all()

            allowed_flag = False
            if flow_control.lp_endpoint_permissions["addTickets"].is_allowed_in_period(current_lp_period):
                allowed_flag = True
            count = 0
            # split txs in number of accounts given by hint-volume

            pairs: list[list[Any]] = []
            

            def batch(acc_list, size):
                l = len(acc_list)
                for ndx in range(0, l, size):
                    yield acc_list[ndx:min(ndx + size, l)]
            for acc_slice in batch(callers, flow_config.hint_volume):
                arg_list = []
                for account in acc_slice:
                    flow_control.add_account_tracker_for_address(account.address.bech32(), track.deployer.bech32())
                    num = random.choice(ticket_tiers)

                    # cap the number of top tier accounts
                    if num == max(ticket_tiers):
                        if config.NR_MAX_ACCOUNTS_TOP_TIER > flow_control.lp_total_guaranteed_tickets:
                            flow_control.lp_total_guaranteed_tickets += 1
                            flow_control.lp_accounts_state_tracker[account.address.bech32()].add_guaranteed_ticket()
                        else:
                            num = random.choice(ticket_tiers[:-1])

                    pairs.append([
                      Address.new_from_bech32(account.address.bech32()),
                      num,
                      [GuaranteedTicketInfo(flow_control.lp_total_guaranteed_tickets, flow_control.lp_total_guaranteed_tickets+1)]
                      ])
                    # add tracking on tickets attempted to add
                    flow_control.lp_accounts_state_tracker[account.address.bech32()].add_tickets(num)

                    # add tickets from energy tier
                    energy_num = random.choice(energy_tiers)
                    flow_control.lp_accounts_state_tracker[account.address.bech32()].add_energy_tickets(energy_num)
                
                transaction = transactions_factory.create_transaction_for_execute(
                    sender=Address.new_from_bech32(owner.address.bech32()),
                    contract=Address.new_from_bech32(contract.address.bech32()),
                    function="addTickets",
                    gas_limit=50_000_000,
                    arguments=[pairs]
                )

                print(transaction.data)
                transactions_new.append(transaction)

                # increase nonce for owner for each added transaction
                flow_control.increment_contract_owner_nonce(track.address.bech32())
                # track transaction results below
                if allowed_flag:
                    expected_results.append(True)
                else:
                    expected_results.append(False)
                    
        def filterTickets():
            gas_limit = 200000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "filterTickets", [], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["filterTickets"].is_allowed_in_period(current_lp_period)
            expected_results.append(is_allowed)

        def selectWinners():
            gas_limit = 250000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "selectWinners", [], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["selectWinners"].is_allowed_in_period(current_lp_period)
            expected_results.append(is_allowed)

        def selectNftWinners():
            gas_limit = 600000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "selectNftWinners", [], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["selectNftWinners"].is_allowed_in_period(current_lp_period)
            expected_results.append(is_allowed)

        def secondarySelectionStep():
            gas_limit = 150000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "distributeGuaranteedTickets", [], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["distributeGuaranteedTickets"].is_allowed_in_period(current_lp_period)
            expected_results.append(is_allowed)

        def claimTicketPayment():
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "claimTicketPayment", [], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["claimTicketPayment"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)

        def claimTicketPaymentOwner():
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(owner, "claimTicketPayment", [], gas_price, gas_limit, 0, chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["claimTicketPayment"].is_allowed_in_period(current_lp_period)
            expected_results.append(is_allowed)

        def claimNftPaymentOwner():
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(owner, "claimNftPayment", [], gas_price, gas_limit, 0, chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def claimLaunchpadTokens():
            gas_limit = 40000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "claimLaunchpadTokens", [], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["claimLaunchpadTokens"].is_allowed_in_period(current_lp_period)
            expected_results.append(is_allowed)

        def depositLaunchpadTokensFromAcc(acc: Account):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            total = tokens_per_win_ticket_new * winning_tickets  # tokens_per_win_ticket * winning_tickets
            bunch_of_tokens = tokens_tracks.BunchOfTracks.load(config.get_default_tokens_file())
            tokens_for_account = bunch_of_tokens.get_tokens_by_holder(caller.address)
            signer = allusers[0]


            if len(tokens_for_account) == 0:
                print("############### ERROR: no tokens available to execute depositLaunchpadTokens function.")
                token_id = "0x" + "NOTOKEN-12345".encode("utf-8").hex()
            else:
                token_id = "0x" + tokens_for_account[0].encode("utf-8").hex()

            # token = Token("")
            token_new = Token(tokens_for_account[0])
            transfer = TokenTransfer(token_new, total)

            transaction = transactions_factory.create_transaction_for_execute(
                sender=Address.new_from_bech32(owner.address.bech32()),
                contract=Address.new_from_bech32(contract.address.bech32()),                
                function="depositLaunchpadTokens",
                gas_limit=gas_limit,
                arguments=[],
                token_transfers=[transfer]
            )
            transaction.nonce = nonce_holder.get_nonce_then_increment()
            transaction.signature = signer.sign(
                        TransactionComputer().compute_bytes_for_signing(transaction)
                    )

            result = provider.send_transaction(transaction)
            time.sleep(3)
            transaction = provider.get_transaction(result)
            transactions_new.append(transaction)


            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["depositLaunchpadTokens"].is_allowed_in_period(
                current_lp_period) and (acc.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)
            # TODO: this will most likely expect false positives for cases when tokens are not matching. Have to be fixed properly.

        def depositLaunchpadTokensOwner():
            depositLaunchpadTokensFromAcc(owner)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def depositLaunchpadTokens():
            depositLaunchpadTokensFromAcc(caller)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def setUnlockScheduleOwner(claim_start_round: int, initial_release_percentage: int):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            signer = allusers[0]

            arguments: list[list[Any]] = []
            proxy = ProxyNetworkProvider(config.DEFAULT_PROXY)
            # claim_start_round = provider.get_network_status(lp_config.OWNER_SHARD).current_round + 1000
            second_round = claim_start_round + period_track.vesting_period
            third_round = second_round + period_track.vesting_period
            fourth_round = third_round + period_track.vesting_period
            print(claim_start_round)
            # last_release_percentage = 3400


            arguments.append([claim_start_round,initial_release_percentage])
            arguments.append([second_round,initial_release_percentage])
            arguments.append([third_round,initial_release_percentage])
            arguments.append([fourth_round,initial_release_percentage])
                    

            transaction = transactions_factory.create_transaction_for_execute(
                    sender=Address.new_from_bech32(owner.address.bech32()),
                    contract=Address.new_from_bech32(contract.address.bech32()),
                    function="setUnlockSchedule",
                    gas_limit=gas_limit,
                    arguments=[arguments]
            )

            transaction.nonce = nonce_holder.get_nonce_then_increment()
            transaction.signature = signer.sign(
                        TransactionComputer().compute_bytes_for_signing(transaction)
                    )

            result = provider.send_transaction(transaction)
            wait_num_of_rounds(proxy, 3)
            transaction = provider.get_transaction(result)
            wait_num_of_rounds(proxy, 1)
            transactions_new.append(transaction)
 
            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setUnlockSchedule"].is_allowed_in_period(
                current_lp_period)
            expected_results.append(is_allowed)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def setTicketPaymentToken(token_name: str = "DUMMYTKN-1234"):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            new_token_id = "0x" + token_name.encode("utf-8").hex()
            transactions.append(contract.execute(caller, "setTicketPaymentToken", [new_token_id], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setTicketPaymentToken"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)
            # TODO: have to handle proper token checking

        def setTicketPrice(new_price: int = ticket_price):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "setTicketPrice", [new_price], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setTicketPrice"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)

        def setLaunchpadTokensPerWinningTicket(new_token_q: int = tokens_per_win_ticket):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "setLaunchpadTokensPerWinningTicket", [new_token_q], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setLaunchpadTokensPerWinningTicket"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)

        def setConfirmationPeriodStartBlock(new_block: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "setConfirmationPeriodStartBlock", [new_block], gas_price, gas_limit, 0, chain_id, tx_version))
            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setConfirmationPeriodStartBlock"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)

        def setWinnerSelectionStartBlock(new_block: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "setWinnerSelectionStartBlock", [new_block], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setWinnerSelectionStartBlock"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)

        def setClaimStartRound(new_block: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "setClaimStartRound", [new_block], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setClaimStartRound"].is_allowed_in_period(
                current_lp_period) and (caller.address.bech32() == track.deployer.bech32())
            expected_results.append(is_allowed)

        def setConfirmationPeriodStartBlockOwner(new_block: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(owner, "setWinnerSelectionStartRound", [new_block], gas_price, gas_limit, 0, chain_id, tx_version))
            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setWinnerSelectionStartRound"].is_allowed_in_period(
                current_lp_period)
            expected_results.append(is_allowed)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def setConfirmationPeriodStartBlockOwnerNew(new_block: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            signer = allusers[0]
        
            arguments = [new_block]

            transaction = transactions_factory.create_transaction_for_execute(
                    sender=Address.new_from_bech32(owner.address.bech32()),
                    contract=Address.new_from_bech32(contract.address.bech32()),
                    function="setWinnerSelectionStartBlock",
                    gas_limit=gas_limit,
                    arguments=[arguments]
            )

            transaction.nonce = nonce_holder.get_nonce_then_increment()
            transaction.signature = signer.sign(
                        TransactionComputer().compute_bytes_for_signing(transaction)
                    )

            result = provider.send_transaction(transaction)
            time.sleep(3)
            transaction = provider.get_transaction(result)
            transactions_new.append(transaction)
            
            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setWinnerSelectionStartBlock"].is_allowed_in_period(
                current_lp_period)
            expected_results.append(is_allowed)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def setWinnerSelectionStartRoundOwner(new_round: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(owner, "setWinnerSelectionStartRound", [new_round], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setWinnerSelectionStartBlock"].is_allowed_in_period(
                current_lp_period)
            expected_results.append(is_allowed)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def setClaimStartRoundOwner(new_block: int = 100):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(owner, "setClaimStartRound", [new_block], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            is_allowed = flow_control.lp_endpoint_permissions["setClaimStartRound"].is_allowed_in_period(
                current_lp_period)
            expected_results.append(is_allowed)
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        # this will call the endpoint from caller account: either user or owner (more likely user if random)
        def removeAddressFromBlacklist(addr: Address = caller.address):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "removeAddressFromBlacklist", ["0x"+addr.hex()], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            if track.deployer.bech32() == caller.address.bech32() and \
                    flow_control.lp_endpoint_permissions["removeAddressFromBlacklist"].is_allowed_in_period(current_lp_period):
                flow_control.lp_accounts_state_tracker[addr.bech32()].whitelist_account()
                expected_results.append(True)
            else:
                expected_results.append(False)

        # this will call the endpoint from caller account: either user or owner (more likely user if random)
        def addAddressToBlacklist(addr: Address = caller.address):
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(contract.execute(caller, "addAddressToBlacklist", ["0x"+addr.hex()], gas_price, gas_limit, 0, chain_id, tx_version))

            # track results below
            if track.deployer.bech32() == caller.address.bech32() and \
                    flow_control.lp_endpoint_permissions["addAddressToBlacklist"].is_allowed_in_period(current_lp_period):
                flow_control.lp_accounts_state_tracker[addr.bech32()].blacklist_account()
                expected_results.append(True)
            else:
                expected_results.append(False)

        # this will call the endpoint from owner account to whitelist the caller account
        def removeAddressFromBlacklistOwner():
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(
                contract.execute(owner, "removeAddressFromBlacklist", ["0x" + caller.address.hex()], gas_price, gas_limit, 0,
                                 chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            if flow_control.lp_endpoint_permissions["removeAddressFromBlacklist"].is_allowed_in_period(current_lp_period):
                flow_control.lp_accounts_state_tracker[caller.address.bech32()].whitelist_account()
                expected_results.append(True)
            else:
                expected_results.append(False)

        # this will call the endpoint from owner account to blacklist the caller account
        def addAddressToBlacklistOwner():
            gas_limit = 6000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(
                contract.execute(owner, "addAddressToBlacklist", ["0x" + caller.address.hex()], gas_price, gas_limit, 0,
                                 chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            if flow_control.lp_endpoint_permissions["addAddressToBlacklist"].is_allowed_in_period(current_lp_period):
                flow_control.lp_accounts_state_tracker[caller.address.bech32()].blacklist_account()
                expected_results.append(True)
            else:
                expected_results.append(False)

        # this will call the endpoint from owner account to blacklist the caller account
        def addUsersToBlacklistOwner():
            gas_limit = 12000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(
                contract.execute(owner, "addUsersToBlacklist", ["0x" + caller.address.hex()], gas_price,
                                 gas_limit, 0,
                                 chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            if flow_control.lp_endpoint_permissions["addAddressToBlacklist"].is_allowed_in_period(
                    current_lp_period):
                flow_control.lp_accounts_state_tracker[caller.address.bech32()].blacklist_account()
                expected_results.append(True)
            else:
                expected_results.append(False)

        def addUsersToBlacklistBatchesOwner():
            gas_limit = 600000000
            bunch_of_accounts = BunchOfAccounts.load_accounts_from_files([config.DEFAULT_ACCOUNTS])
            # bunch_of_accounts = filter_bunch_of_accounts_by_shard(bunch_of_accounts, args.from_shard)
            callers = bunch_of_accounts.get_all()

            allowed_flag = False
            if flow_control.lp_endpoint_permissions["addAddressToBlacklist"].is_allowed_in_period(current_lp_period):
                allowed_flag = True

            args_dict: Dict[int, List] = {}
            count = 0
            # split txs in number of accounts given by hint-volume

            def batch(acc_list, size):
                l = len(acc_list)
                for ndx in range(0, l, size):
                    yield acc_list[ndx:min(ndx + size, l)]
            for acc_slice in batch(callers, flow_config.hint_volume):
                arg_list = []
                for account in acc_slice:
                    arg_list.append("0x" + account.address.hex())
                    # add tracking on tickets attempted to blacklist
                    if flow_control.lp_endpoint_permissions["addAddressToBlacklist"].is_allowed_in_period(
                            current_lp_period):
                        flow_control.lp_accounts_state_tracker[caller.address.bech32()].blacklist_account()

                transactions.append(contract.execute(owner, "addUsersToBlacklist", arg_list,
                                                     gas_price, gas_limit, 0, chain_id, tx_version))
                # increase nonce for owner for each added transaction
                flow_control.increment_contract_owner_nonce(track.address.bech32())
                # track transaction results below
                if allowed_flag:
                    expected_results.append(True)
                else:
                    expected_results.append(False)

        # this will call the endpoint from owner account to blacklist the caller account
        def refundUserByOwner():
            gas_limit = 12000000 if global_gas_limit == 0 else global_gas_limit
            transactions.append(
                contract.execute(owner, "refundUserTickets", ["0x" + caller.address.hex()], gas_price,
                                 gas_limit, 0,
                                 chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

            # track results below
            if flow_control.lp_endpoint_permissions["addAddressToBlacklist"].is_allowed_in_period(
                    current_lp_period):
                flow_control.lp_accounts_state_tracker[caller.address.bech32()].blacklist_account()
                expected_results.append(True)
            else:
                expected_results.append(False)

        def issueMisterySftOwner(token_name: str = "LNCHSFT"):
            gas_limit = 100000000 if global_gas_limit == 0 else global_gas_limit

            new_token_id = "0x" + token_name.encode("utf-8").hex()
            transactions.append(
                contract.execute(owner, "issueMysterySft", [new_token_id, new_token_id], gas_price, gas_limit,
                                 lp_config.DEFAULT_ISSUE_TOKEN_PRICE, chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def createInitialSftsOwner():
            gas_limit = 100000000 if global_gas_limit == 0 else global_gas_limit

            transactions.append(
                contract.execute(owner, "createInitialSfts", [], gas_price, gas_limit,
                                 0, chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())

        def setTransferRoleOwner(address: str = ""):
            gas_limit = 100000000 if global_gas_limit == 0 else global_gas_limit
            args = ["0x" + Address(address).hex()] if address != "" else []
            transactions.append(
                contract.execute(owner, "setTransferRole", args, gas_price, gas_limit,
                                 0, chain_id, tx_version))
            flow_control.increment_contract_owner_nonce(track.address.bech32())


        # Start flows
        if flow_config.mode == "random-endpoints":
            endpoints_list = [confirmTickets, addTickets, filterTickets, selectWinners, claimTicketPayment,
                              claimLaunchpadTokens, addTicketsOwner,
                              depositLaunchpadTokens, setTicketPaymentToken, setTicketPrice,
                              setLaunchpadTokensPerWinningTicket,
                              setConfirmationPeriodStartBlock, setWinnerSelectionStartBlock, setClaimStartRound,
                              removeAddressFromBlacklist,
                              addAddressToBlacklist, removeAddressFromBlacklistOwner, addAddressToBlacklistOwner,
                              claimNftPaymentOwner, selectNftWinners]

            retrieved = random.choice(endpoints_list)
            """ DEBUG PURPOSES
            print(retrieved.__name__)
            """
            retrieved()

        if flow_config.mode == "random-endpoints-no-alter":
            endpoints_list = [confirmTickets, addTickets, filterTickets, selectWinners, claimTicketPayment,
                              claimLaunchpadTokens, addTicketsOwner,
                              depositLaunchpadTokens, removeAddressFromBlacklist,
                              addAddressToBlacklist, removeAddressFromBlacklistOwner, addAddressToBlacklistOwner,
                              claimNftPaymentOwner, selectNftWinners]
            random.choice(endpoints_list)()

        if flow_config.mode == "random-endpoints-no-blacklist":
            endpoints_list = [confirmTickets, addTickets, filterTickets, selectWinners, claimTicketPayment,
                              claimLaunchpadTokens, addTicketsOwner,
                              depositLaunchpadTokens, setTicketPaymentToken, setTicketPrice,
                              setLaunchpadTokensPerWinningTicket,
                              setConfirmationPeriodStartBlock, setWinnerSelectionStartBlock, setClaimStartRound,
                              claimTicketPaymentOwner, selectNftWinners]
            random.choice(endpoints_list)()

        if flow_config.mode == "owner-add-accounts":
            addTicketsOwner()

        if flow_config.mode == "owner-add-account-batches":
            addTicketsBatchesOwner()

        if flow_config.mode == "owner-add-guaranteed-tickets":
            addMoreGuaranteedTicketsOwner()

        if flow_config.mode == "owner-set-unlock-schedule":
            period_track = next(iter(flow_control.lp_period_tracker.values()))
            setUnlockScheduleOwner(period_track.vesting_claim_start, period_track.vesting_initial_release)


        if flow_config.mode == "confirm-some-owned":
            owned = flow_control.lp_accounts_state_tracker[caller.address.bech32()].num_tickets
            confirmTickets(random.randint(0, owned))

        if flow_config.mode == "confirm-all":
            owned = flow_control.lp_accounts_state_tracker[caller.address.bech32()].num_tickets
            # owned = 129
            confirmTickets(owned)

        if flow_config.mode == "confirm-all-new":
            owned = flow_control.lp_accounts_state_tracker[caller.address.bech32()].num_tickets
            confirmTicketsNew(owned)

        if flow_config.mode == "confirm-all-but-one":
            owned = flow_control.lp_accounts_state_tracker[caller.address.bech32()].num_tickets - 1
            confirmTickets(owned)

        if flow_config.mode == "owner-blacklist-accounts":
            addAddressToBlacklistOwner()

        if flow_config.mode == "owner-blacklist-users":
            addUsersToBlacklistOwner()

        if flow_config.mode == "owner-refunds-user":
            refundUserByOwner()

        if flow_config.mode == "owner-blacklist-users-batches":
            addUsersToBlacklistBatchesOwner()

        if flow_config.mode == "owner-deposit-lp-tokens":
            depositLaunchpadTokensOwner()

        if flow_config.mode == "owner-claim-payment":
            claimTicketPaymentOwner()

        if flow_config.mode == "owner_claim_nft_payment":
            claimNftPaymentOwner()

        if flow_config.mode == "claim-tokens":
            claimLaunchpadTokens()

        if flow_config.mode == "filter-tickets":
            filterTickets()

        if flow_config.mode == "select-winners":
            selectWinners()

        if flow_config.mode == "select-nft-winners":
            selectNftWinners()

        if flow_config.mode == "select-secondary-step":
            secondarySelectionStep()

        if flow_config.mode == "set-ticket-price":
            setTicketPrice()

        if flow_config.mode == "owner-issue-mistery-sft":
            issueMisterySftOwner()

        if flow_config.mode == "owner-create_initial_sfts":
            createInitialSftsOwner()

        if flow_config.mode == "owner-set-transfer-role":
            setTransferRoleOwner()

        if flow_config.mode == "owner-set-confirmation-block":
            period_track = next(iter(flow_control.lp_period_tracker.values()))
            setConfirmationPeriodStartBlockOwner(period_track.confirm_time)

        if flow_config.mode == "owner-set-winners-select-block":
            period_track = next(iter(flow_control.lp_period_tracker.values()))
            setWinnerSelectionStartRoundOwner(period_track.select_winners_time)

        if flow_config.mode == "owner-set-claim-round":
            period_track = next(iter(flow_control.lp_period_tracker.values()))
            setClaimStartRound(period_track.claim_time)

        """ DEBUG PURPOSES
        for tx in transactions:
            print("Sending:", tx.data, "for address:", caller.address)
        """

        return transactions, expected_results

    def prepare_queries(self, track: TrackOfContract, accounts: List[Account], input_data: Any) -> List[PreparedQuery]:
        queries: List[PreparedQuery] = []

        queries.extend([PreparedQuery(track, "currentFunds", [])])
        queries.extend([PreparedQuery(track, "status", [])])

        return queries

# TODO:
# - write files with acquired account states & tx hashes for statistics and later data analysis
# - expected result on executed flow: if I expect it to succeed despite the fact that it's sent in the wrong epoch
# - gas tracing report on selectWinners & filterTickets
# - refactor
# - tweak the default values
# - improve the owner account retrieval ? perhaps shards and deployers pool aspects?
# - randomize call parameters and track the state altering changes (ticket size/price, epochs)
