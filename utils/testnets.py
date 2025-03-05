from pathlib import Path
from typing import Any, Dict

INTERNAL: Dict[str, Any] = {
    "fra": {
        "proxy": "http://144.126.246.1:8080",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "FRANKFURT",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "C100.pem",
    },
    "fra-many-users": {
        "proxy": "http://144.126.246.1:8080",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "FRANKFURT",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "D15000.pem",
    },
    "lon": {
        "proxy": "http://67.207.69.122:8080",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "LONDON",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "C100.pem",
    },
    "tor": {
        "proxy": "http://104.248.107.20:8080",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "TORONTO",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "C100.pem",
    },
    "ams": {
        "proxy": "http://161.35.247.163:8080",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "AMSTERDAM",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "C100.pem",
    },
    "ams-many-users": {
        "proxy": "http://161.35.247.163:8080",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "AMSTERDAM",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "D15000.pem",
    },
    "public-testnet": {
        "proxy": "https://testnet-gateway.multiversx.com",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "PUBLIC_TESTNET",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "C1.pem",
    },
    "public-devnet": {
        "proxy": "https://devnet-gateway.multiversx.com",
        "workspace-parent": Path(__file__).parent.absolute() / "workspace" / "testnets" / "PUBLIC_DEVNET",
        "minter": Path(__file__).parent.absolute() / "workspace" / "wallets" / "minter.pem",
        "accounts": Path(__file__).parent.absolute() / "workspace" / "wallets" / "C10.pem",
    }
}
