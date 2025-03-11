from pathlib import Path

HOME = Path().home()
DEFAULT_WORKSPACE = Path(__file__).parent

# ------------ For normal operation, modify below ------------ #

PROXY_CHAIN_SIMULATOR = "http://localhost:8085"
OBSERVER_META = "http://localhost:55802"

# DEFAULT_PROXY = PROXY_CHAIN_SIMULATOR
# DEFAULT_API = PROXY_CHAIN_SIMULATOR
DEFAULT_PROXY = "https://devnet-gateway.multiversx.com"    
DEFAULT_API = "https://devnet-api.multiversx.com"                              # API to be used for ALL operations
GRAPHQL = 'https://graph.xexchange.com/graphql'                              # GraphQL service; only needed for the upgrader scripts
HISTORY_PROXY = ""                                                          # Proxy to be used for history operations; not used for the moment
# TODO: try to override the default issue token price with testnet definition to tidy code up
DEFAULT_ISSUE_TOKEN_PRICE = 50000000000000000                               # 0.05 EGLD - change only if different setup on nets

# Operation wallets
DEFAULT_ACCOUNTS = DEFAULT_WORKSPACE.absolute() / "wallets" / "wallet1.pem"     # Accounts to be used for user operations
DEFAULT_OWNER = DEFAULT_WORKSPACE.absolute() / "wallets" / "deployer.pem"         # DEX owner address
DEFAULT_ADMIN = DEFAULT_WORKSPACE.absolute() / "wallets" / "wallet2.pem"         # DEX admin address
DEX_OWNER_ADDRESS = "erd1ss6u80ruas2phpmr82r42xnkd6rxy40g9jl69frppl4qez9w2jpsqj8x97"  # Only needed for shadowforks
DEX_ADMIN_ADDRESS = "erd1ss6u80ruas2phpmr82r42xnkd6rxy40g9jl69frppl4qez9w2jpsqj8x97"  # Only needed for shadowforks
OWNER_SHARD = "1"


# Used DEX deploy configuration
DEFAULT_CONFIG_SAVE_PATH = DEFAULT_WORKSPACE.absolute() / "dex_deploy" / "configs-mainnet"   # Deploy configuration folder
DEPLOY_STRUCTURE_JSON = DEFAULT_CONFIG_SAVE_PATH / "deploy_structure.json"  # Deploy structure - change only if needed

FORCE_CONTINUE_PROMPT = False                                               # Force continue prompt for all operations

# DEX contract bytecode paths
PRICE_DISCOVERY_BYTECODE_PATH = DEFAULT_WORKSPACE.absolute() / "wasm" / "price-discovery" / "price-discovery.wasm"
PRICE_DISCOVERY_ABI = DEFAULT_WORKSPACE.absolute() / "wasm" / "price-discovery" / "price-discovery.abi.json"

# ------------ Generic configuration below; Modify only in case of framework changes ------------ #
TOKENS_CONTRACT_ADDRESS = "erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzllls8a5w6u"
SF_CONTROL_ADDRESS = "erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqplllst77y4l"
ZERO_CONTRACT_ADDRESS = "erd1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq6gq4hu"

# Upgrader scripts output directory
UPGRADER_OUTPUT_FOLDER = DEFAULT_CONFIG_SAVE_PATH / "upgrader_outputs"

DEFAULT_GAS_BASE_LIMIT_ISSUE = 60000000
DEFAULT_TOKEN_PREFIX = "TDEX"     # limit yourself to max 6 chars to allow automatic ticker build
DEFAULT_TOKEN_SUPPLY_EXP = 27       # supply to be minted in exponents of 10
DEFAULT_TOKEN_DECIMALS = 18         # decimals on minted tokens in exponents of 10
DEFAULT_MINT_VALUE = 1  # EGLD      # TODO: don't go sub-unitary cause headaches occur. just don't be cheap for now...

CROSS_SHARD_DELAY = 60
INTRA_SHARD_DELAY = 10

DUMMY_PROXY = "dummy"

OBSERVER_META = "http://localhost:55802"

# nets
mainnet = "https://gateway.multiversx.com"
testnet = "https://testnet-gateway.multiversx.com"
devnet = "https://devnet-gateway.multiversx.com"

chain_id = "chain"

# relative path to chain-simulator
chain_simulator_path = DEFAULT_WORKSPACE.absolute() / "chainsimulator"

# config for cli flags for starting chain simulator
log_level = '"*:DEBUG,process:TRACE"'
num_validators_per_shard = "10"
num_validators_meta = "10"
num_waiting_validators_per_shard = "6"
num_waiting_validators_meta = "6"
# real config after staking v4 full activation: eligible = 10 *4 , waiting = (6-2) *4, qualified =  2*4
# qualified nodes from auction will stay in wiating 2 epochs

rounds_per_epoch = "50"
def get_default_tokens_file():
    return DEFAULT_CONFIG_SAVE_PATH / "tokens.json"


def get_default_log_file():
    return DEFAULT_WORKSPACE / "logs" / "trace.log"
