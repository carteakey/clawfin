"""
SimpleFin Bridge API client.

Flow:
1. User gets a setup token from simplefin.org
2. We exchange it for a permanent access URL (base64-encoded credentials)
3. We use the access URL to fetch /accounts (balances + transactions)

Docs: https://www.simplefin.org/protocol.html
"""
import base64
import httpx
from datetime import datetime, date


class SimpleFinClient:
    """Client for the SimpleFin Bridge API."""

    CLAIM_URL = "https://bridge.simplefin.org/simplefin/claim"

    def __init__(self, access_url: str | None = None):
        self.access_url = access_url
        self._base_url: str | None = None
        self._auth: tuple[str, str] | None = None

        if access_url:
            self._parse_access_url(access_url)

    def _parse_access_url(self, url: str):
        """Extract base URL and credentials from the access URL."""
        # Access URL format: https://username:password@bridge.simplefin.org/simplefin
        from urllib.parse import urlparse
        parsed = urlparse(url)
        self._auth = (parsed.username or "", parsed.password or "")
        self._base_url = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            self._base_url += f":{parsed.port}"
        self._base_url += parsed.path

    @staticmethod
    async def exchange_setup_token(setup_token: str) -> str:
        """
        Exchange a one-time setup token for a permanent access URL.

        The setup token is base64-encoded and contains a claim URL.
        POST to the claim URL returns the access URL.
        """
        claim_url = base64.b64decode(setup_token.strip()).decode("utf-8")

        async with httpx.AsyncClient() as client:
            response = await client.post(claim_url, timeout=30)
            response.raise_for_status()
            return response.text.strip()

    async def fetch_accounts(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """
        Fetch accounts and transactions from SimpleFin.

        Returns the full /accounts response:
        {
            "accounts": [
                {
                    "id": "...",
                    "name": "...",
                    "org": {"name": "...", ...},
                    "balance": "1234.56",
                    "currency": "CAD",
                    "transactions": [
                        {"id": "...", "posted": 1234567890, "amount": "-12.34", "description": "...", ...},
                        ...
                    ]
                }
            ]
        }
        """
        if not self._base_url or not self._auth:
            raise ValueError("No access URL configured. Run setup first.")

        params = {}
        if start_date:
            params["start-date"] = str(int(datetime.combine(start_date, datetime.min.time()).timestamp()))
        if end_date:
            params["end-date"] = str(int(datetime.combine(end_date, datetime.min.time()).timestamp()))

        async with httpx.AsyncClient(auth=self._auth) as client:
            url = f"{self._base_url}/accounts"
            response = await client.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def normalize_accounts(raw_data: dict) -> list[dict]:
        """Convert SimpleFin response to our Account format."""
        accounts = []
        for acct in raw_data.get("accounts", []):
            org_name = acct.get("org", {}).get("name", "Unknown")
            accounts.append({
                "institution": org_name,
                "name": acct.get("name", "Account"),
                "balance": float(acct.get("balance", 0)),
                "currency": acct.get("currency", "CAD").upper(),
                "external_id": acct.get("id", ""),
                "source": "simplefin",
            })
        return accounts

    @staticmethod
    def normalize_transactions(raw_data: dict) -> list[dict]:
        """Convert SimpleFin transactions to our Transaction format."""
        transactions = []
        for acct in raw_data.get("accounts", []):
            acct_id = acct.get("id", "")
            currency = acct.get("currency", "CAD").upper()

            for tx in acct.get("transactions", []):
                posted = tx.get("posted", 0)
                tx_date = datetime.fromtimestamp(posted).date() if posted else date.today()

                amount = float(tx.get("amount", 0))
                description = tx.get("description", "").strip()
                merchant = tx.get("payee", description).strip() or description

                transactions.append({
                    "date": tx_date.isoformat(),
                    "amount": amount,
                    "merchant": merchant,
                    "currency": currency,
                    "description": description,
                    "source": "simplefin",
                    "external_account_id": acct_id,
                })

        return transactions


# ─── Fixture mode for testing ────────────────────────────────────────

class MockSimpleFinClient(SimpleFinClient):
    """Mock client that returns fixture data instead of calling the API."""

    def __init__(self):
        super().__init__(access_url=None)
        self._fixture_data = {
            "accounts": [
                {
                    "id": "mock-chequing-001",
                    "name": "Chequing",
                    "org": {"name": "Mock Bank"},
                    "balance": "2450.00",
                    "currency": "CAD",
                    "transactions": [
                        {"id": "tx-1", "posted": 1711900800, "amount": "-45.30", "description": "LOBLAWS #1234", "payee": "Loblaws"},
                        {"id": "tx-2", "posted": 1711814400, "amount": "-4.50", "description": "TIM HORTONS #567", "payee": "Tim Hortons"},
                        {"id": "tx-3", "posted": 1711814400, "amount": "-4.50", "description": "TIM HORTONS #567", "payee": "Tim Hortons"},
                        {"id": "tx-4", "posted": 1711728000, "amount": "3200.00", "description": "PAYROLL DEPOSIT", "payee": "Employer Inc"},
                    ],
                }
            ]
        }

    async def fetch_accounts(self, start_date=None, end_date=None) -> dict:
        return self._fixture_data
