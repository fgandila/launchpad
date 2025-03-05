import sys
import time
from argparse import ArgumentParser
from typing import List

import config
from utils import wait_idle_blockchain, wait_num_of_rounds, testnets
from multiversx_sdk import ProxyNetworkProvider
# from arrows.AutomaticTests.ProxyExtension import ProxyExtension
from scenarios import flow_control
from scenarios.steps import sync_tokens
from scenarios.steps import (step_0_issue_tokens, step_2_deploy_contract, step_2_deploy_contract_new, step_4_execute, step_4_execute_new)


def main(cli_args: List[str]):
    parser = ArgumentParser()
    parser.add_argument("--testnet", required=True)
    parser.add_argument("--skip-minting", action="store_true", default=False)
    parser.add_argument("--skip-issue", action="store_true", default=False)
    parser.add_argument("--skip-result-checking", action="store_true", default=False)
    parser.add_argument("--unlocked", action="store_true", default=False)      # contract with unlocked epoch changes
    args = parser.parse_args(cli_args)

    testnet = testnets.INTERNAL[args.testnet]
    proxy_url = testnet["proxy"]
    workspace = testnet["workspace-parent"] / "CONTRACTS_LP"
    accounts = testnet["accounts"]
    minter = testnet["minter"]
    proxy = ProxyNetworkProvider(proxy_url)
    # extended_proxy = ProxyExtension(proxy_url)

    config.DEFAULT_PROXY = proxy_url
    config.DEFAULT_WORKSPACE = workspace
    config.DEFAULT_ACCOUNTS = accounts
    config.DEFAULT_MINTER = minter

    # MINT ACCOUNTS #################################################################################################

    # minter is sending funds to the accounts
    # if not args.skip_minting:
    #     print("###### Started sending funds to accounts:")
    #     minting_payment_tokens = str(lp_config.DEFAULT_MINT_VALUE)
    #     step_0_mint.main(["--value", minting_payment_tokens, "--proxy", config.DEFAULT_PROXY, "--yes"])
    #     wait_num_of_rounds(proxy)   # TODO: replace fixed number of rounds with tx hash status (there's something existing I think)

    # ISSUE TOKEN #################################################################################################

    # generate launchpad token
    token_name = config.DEFAULT_TOKEN_PREFIX
    token_supply = str(config.DEFAULT_TOKEN_SUPPLY_EXP)
    token_decimals = str(config.DEFAULT_TOKEN_DECIMALS)


    if not args.skip_issue:
        print("###### Started issuing tokens:")
        if "esdt-issue-cost" in testnet:
            step_0_issue_tokens.main(["--tokens-prefix", token_name, "--value", testnet["esdt-issue-cost"],
                                      "--supply-exp", token_supply, "--num-decimals", token_decimals,
                                      "--proxy", config.DEFAULT_PROXY, "--yes"])
        else:
            step_0_issue_tokens.main(["--tokens-prefix", token_name,
                                      "--supply-exp", token_supply, "--num-decimals", token_decimals,
                                      "--proxy", config.DEFAULT_PROXY, "--yes"])
        wait_num_of_rounds(proxy)

    # synchronize on created tokens
    print("###### Syncing tokens for tracks:")
    sync_tokens.main(["--tokens-prefix", token_name, "--proxy", config.DEFAULT_PROXY])

    # # DEPLOY CONTRACT #################################################################################################

    # deploy contract "launchpad"
    config.CONTRACTS_ENABLED = ["launchpad-v4"]
    step_1_prepare_binaries.main([])
    step_2_deploy_contract_new.main(["--proxy", config.DEFAULT_PROXY, "--yes"])   # with confirmation to continue
    wait_num_of_rounds(proxy, 3)
    # wait_idle_blockchain(proxy)

    # initialize the endpoint permissions data
    flow_control.init_endpoint_permissions()

    current_block = extended_proxy.get_network_status(2).current_nonce
    current_round = extended_proxy.get_network_status(2).current_round

    period_track = next(iter(flow_control.lp_period_tracker.values()))
    confirm_round = period_track.confirm_time
    winners_select_round = period_track.select_winners_time
    claim_round = period_track.claim_time
    vesting_start = period_track.vesting_claim_start
    vesting_period = period_track.vesting_period
    vesting_times = period_track.vesting_times

    no_ticket_accounts_added = config.NR_ACCOUNTS_TO_ADD
    no_confirmed_accounts = config.NR_ACCOUNTS_TO_CONFIRM
    no_winners_claimed = config.NR_WINNERS_TO_CLAIM
    no_blacklisted_accounts = config.NR_ACCOUNTS_TO_BLACKLIST
    no_refunded_accounts = config.NR_ACCOUNTS_TO_REFUND
    no_accounts_guaranteed_ticket = config.NR_ACCOUNTS_GUARANTEED_TICKET

    wait_time_next_period = config.WAIT_TIME_NEXT_PERIOD
    wait_blocks_owner = config.WAIT_BLOCKS_OWNER
    wait_blocks_cross_shard = config.WAIT_BLOCKS_CROSS_SHARD

    contract_shard = config.OWNER_SHARD

    # begin flows
    # """ Happy path similar to what is expected to happen on launch """

    ## CONTRACT SETUP #################################################################################################

    # add tickets & deposit launchpad tokens
    print("###### Current block:", current_block)
    print("###### Current round:", current_round)

    print("###### Adding tickets for accounts:", no_ticket_accounts_added)
    step_4_execute_new.main(["--mode", "owner-add-accounts-new", "--num-repeat-over-tracks", str(no_ticket_accounts_added), "--sleep-between-chunks", "5", "--yes"])


    # step_4_execute_new.main(["--mode", "owner-add-account-batches-new", "--hint-volume", "500",
    #      "--chunk-size", "100", "--sleep-between-chunks", "10", "--yes"])

    # add tickets in batches

    # step_4_execute.main(["--mode", "owner-add-accounts", "--num-repeat-over-tracks", str(no_ticket_accounts_added), "--sleep-between-chunks", "5", "--yes"])

    # step_4_execute.main(
    #     ["--mode", "owner-add-account-batches-new", "--hint-volume", "200",
    #      "--chunk-size", "2", "--sleep-between-chunks", "5", "--yes"])

    # wait_num_of_rounds(proxy, wait_blocks_owner)
    # # check if expected txs were all performed
    # flow_control.save_account_tracking_exp_status("add_address_stats")
    # #if not args.skip_result_checking:
    # if False:
    #     flow_control.check_account_tracking_status(proxy_url)
    # else:
    #     flow_control.get_and_save_contract_state(proxy_url, "add_address_contract_state")

    print("###### Current block:", current_block)
    print("###### Current round:", current_round)

    # wait_num_of_rounds(proxy, 2)
    # print("###### Set vesting.")
    # step_4_execute_new.main(["--mode", "owner-set-unlock-schedule-new", "--sleep-between-repetitions", "5", "--yes"])
    # wait_num_of_rounds(proxy, wait_blocks_owner)

    # print("###### Depositing launchpad tokens.")
    # step_4_execute_new.main(["--mode", "owner-deposit-lp-tokens-new", "--sleep-between-repetitions", "5", "--yes"])
    # wait_num_of_rounds(proxy, wait_blocks_owner)

    # # CONFIRM TICKETS #################################################################################################

    # # confirm tickets & manage blacklists
    # if not args.unlocked:
    #     print("###### Started waiting for confirm round:", confirm_round)
    #     extended_proxy.wait_for_round(confirm_round, wait_time_next_period, contract_shard)
    # else:
    #     # current_block = extended_proxy.get_network_status(contract_shard).current_nonce
    #     current_round = extended_proxy.get_network_status(contract_shard).current_round
    #     confirm_round = current_round - 18
    #     period_track.confirm_time = confirm_round
    #     print("###### Alter hacked confirm block to:", confirm_round) #to be edited
    #     step_4_execute.main(["--mode", "owner-set-confirmation-block", "--sleep-between-repetitions", "1", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)

    # print("###### Current block:", current_block)
    # print("###### Current round:", current_round)

    # extended_proxy.wait_for_round(confirm_round, wait_time_next_period, contract_shard)
    # # ===============================================

    
    # print("###### Confirming tickets for accounts:", no_confirmed_accounts)
    # step_4_execute.main(
    #     ["--mode", "confirm-all", "--num-repeat-over-tracks", str(no_confirmed_accounts),
    #      "--chunk-size", "10", "--sleep-between-chunks", "10", "--yes"])
    # wait_num_of_rounds(proxy, wait_blocks_cross_shard)

    
    # # ===============================================
    # if no_blacklisted_accounts > 0:
    #     print("###### Blacklist accounts:", no_blacklisted_accounts)
    #     step_4_execute.main(
    #         ["--mode", "owner-blacklist-users", "--num-repeat-over-tracks", str(no_blacklisted_accounts),
    #          "--chunk-size", "20", "--sleep-between-chunks", "3", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)


    # REFUND USER
    step_4_execute.main(
            ["--mode", "owner-refunds-user", "--num-repeat-over-tracks", str(no_refunded_accounts),
             "--chunk-size", "20", "--sleep-between-chunks", "3", "--yes"])
    wait_num_of_rounds(proxy, wait_blocks_owner)
    # print("###### Blacklist accounts:", no_blacklisted_accounts)
    # step_4_execute.main(
    #     ["--mode", "owner-blacklist-users", "--num-repeat-over-tracks", str(no_blacklisted_accounts),
    #      "--chunk-size", "20", "--sleep-between-chunks", "3", "--yes"])
    # wait_num_of_rounds(proxy, wait_blocks_owner)

    # print("###### Claiming payment tokens from owner -> should fail")
    # step_4_execute.main(["--mode", "owner-claim-payment", "--sleep-between-repetitions", "1", "--yes"])
    # wait_num_of_rounds(proxy, wait_blocks_owner)
    # # #
    # print("###### Claiming launchpad tokens & refunds for number of accounts:", no_winners_claimed, " -> should fail")
    # step_4_execute.main(
    #     ["--mode", "claim-tokens", "--num-repeat-over-tracks", str(no_winners_claimed),
    #      "--chunk-size", "100", "--sleep-between-chunks", "3", "--yes"])

    # # check if expected txs were all performed
    # flow_control.save_account_tracking_exp_status("confirm_address_stats")
    # # if not args.skip_result_checking:
    # if False:
    #     flow_control.check_account_tracking_status(proxy_url)
    # else:
    #     flow_control.get_and_save_contract_state(proxy_url, "confirm_contract_state")

    # # # # # FILTER TICKETS #################################################################################################

    # # filter tickets & select winners
    # if not args.unlocked:
    #     print("###### Started waiting for winners select round:", winners_select_round)
    #     extended_proxy.wait_for_round(winners_select_round, wait_time_next_period, contract_shard)
    # else:
    #     current_round = extended_proxy.get_network_status(contract_shard).current_round
    #     winners_select_round = current_round - 2
    #     period_track.select_winners_time = winners_select_round
    #     print("###### Alter hacked winners select round to:", winners_select_round)
    #     step_4_execute.main(["--mode", "owner-set-winners-select-block", "--sleep-between-repetitions", "1", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)

    # # # # TODO: repeat filter and winning select as long as needed
    # print("###### Filtering tickets.")
    # repeat = 'y'
    # while repeat == 'y':
    #     step_4_execute.main(
    #         ["--mode", "filter-tickets", "--num-repeat", "1", "--num-repeat-over-tracks", "5",
    #          "--sleep-between-repetitions", "1", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)
    #     repeat = input('Repeat filtering? y/n ')

    # print("###### Selecting winning tickets.")
    # repeat = 'y'
    # while repeat == 'y':
    #     step_4_execute.main(
    #         ["--mode", "select-winners", "--num-repeat", "1", "--num-repeat-over-tracks", "5",
    #          "--sleep-between-repetitions", "1", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)
    #     repeat = input('Repeat selecting winners? y/n ')

    # # print("###### Distributing guaranteed tickets.")
    # repeat = 'y'
    # while repeat == 'y':
    #     step_4_execute.main(
    #         ["--mode", "select-secondary-step", "--num-repeat", "1", "--num-repeat-over-tracks", "5",
    #          "--sleep-between-repetitions", "1", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)
    #     repeat = input('Repeat selecting second step? y/n ')

    # # check selectWinners status
    # # flow_control.get_winners_selected_status(proxy_url)

    # # retrieve and save the winning status info for accounts
    # if not args.skip_result_checking:
    #     flow_control.set_account_tracking_winning_status(proxy_url)
    #     flow_control.save_account_tracking_exp_status("winning_address_stats")
    #     flow_control.get_and_save_contract_state(proxy_url, "winners_contract_state")
    # else:
    #     flow_control.get_and_save_contract_state(proxy_url, "winners_contract_state")

    # # # # # CLAIM TOKENS #################################################################################################

    # # claim tokens & refunds
    # if not args.unlocked:
    #     print("###### Started waiting for claim block:", claim_round)
    #     extended_proxy.wait_for_round(claim_round, wait_time_next_period, contract_shard)
    # else:
    #     current_round = extended_proxy.get_network_status(contract_shard).current_round
    #     claim_round = current_round - 6
    #     period_track.claim_time = claim_round
    #     print("###### Alter hacked claim block to:", claim_round)
    #     step_4_execute.main(["--mode", "owner-set-claim-block", "--sleep-between-repetitions", "1", "--yes"])
    #     wait_num_of_rounds(proxy, wait_blocks_owner)

    # extended_proxy.wait_for_round(claim_round, wait_time_next_period, contract_shard)
    # # request confirmation to continue

    # while repeat == 'n':
    #     repeat = input('First Continue? y/n ')

    # # first claim from users
    # print("###### Claiming launchpad tokens & refunds for number of accounts:", no_winners_claimed)
    # step_4_execute.main(
    #     ["--mode", "claim-tokens", "--num-repeat-over-tracks", str(no_winners_claimed),
    #      "--chunk-size", "300", "--sleep-between-chunks", "3", "--yes"])

    # wait_num_of_rounds(proxy, wait_blocks_cross_shard)

    # print("###### Claiming payment tokens from owner.")
    # step_4_execute.main(["--mode", "owner-claim-payment", "--sleep-between-repetitions", "1", "--yes"])
    # wait_num_of_rounds(proxy, wait_blocks_owner)

    # # vesting claim from users
    # for i in range(1, vesting_times+1):
    #     vesting_round = vesting_start + i * vesting_period
    #     print(f"###### Started waiting for claim {i} round: {vesting_round}")
    #     extended_proxy.wait_for_round(vesting_round, wait_time_next_period, contract_shard)

    #     # request confirmation to continue
    #     while repeat == 'n':
    #         repeat = input(f'Vesting {i} claims ready; Continue? y/n ')

    #     # vesting claim from users
    #     step_4_execute.main(
    #         ["--mode", "claim-tokens", "--num-repeat-over-tracks", str(no_winners_claimed),
    #         "--chunk-size", "300", "--sleep-between-chunks", "3", "--yes"])
    
    #     wait_num_of_rounds(proxy, wait_blocks_cross_shard)


    # # # failing claim from users
    # # step_4_execute.main(
    # #     ["--mode", "claim-tokens", "--num-repeat-over-tracks", str(no_winners_claimed),
    # #      "--chunk-size", "300", "--sleep-between-chunks", "3", "--yes"])
    
    # # wait_num_of_rounds(proxy, wait_blocks_cross_shard)

    # # # # # CONTRACT REPORT ################################################################################################

    # # report status
    # flow_control.save_account_tracking_exp_status("end_address_stats")
    # flow_control.save_txhash_exp_results("end_tx_hashes")
    # if not args.skip_result_checking:
    #     # flow_control.check_account_tracking_status(proxy_url)  # this fails due to contract architecture
    #     flow_control.check_txhash_results(proxy_url)
    # else:
    #     flow_control.get_and_save_contract_state(proxy_url, "claim_contract_state")
    # print("###### Number of transaction hashes missed by erdpy:", flow_control.lp_missed_txs)

    # # if not args.skip_minting:
    # #     step_9_mint_back.main(["--proxy", config.DEFAULT_PROXY])


if __name__ == "__main__":
    main(sys.argv[1:])
