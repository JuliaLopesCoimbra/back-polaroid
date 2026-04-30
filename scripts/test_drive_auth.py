import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parents[1] / "service_account.json"


def main() -> int:
    if not SERVICE_ACCOUNT_FILE.exists():
        print(f"[ERRO] service_account.json nao encontrado em: {SERVICE_ACCOUNT_FILE}")
        return 1

    print(f"[INFO] Usando credencial: {SERVICE_ACCOUNT_FILE}")
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    about = service.about().get(fields="user,storageQuota").execute()

    user = about.get("user", {})
    quota = about.get("storageQuota", {})
    print("[OK] Autenticacao com Google Drive concluida.")
    print(f"[INFO] Usuario: {user.get('displayName', 'N/A')}")
    print(f"[INFO] Email: {user.get('emailAddress', 'N/A')}")
    print(f"[INFO] Limite storage: {quota.get('limit', 'N/A')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
