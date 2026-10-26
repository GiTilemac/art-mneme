"""Uploads the ArtMneme dashboard and alert rule to Grafana Cloud (run with `make grafana-cloud`).

The same files that the local Grafana loads at start (observability/grafana/) are sent through the Grafana API,
with the local data source and address replaced by Grafana Cloud's. The Grafana address and a service-account
token are read from SSM (/artmneme/grafana-url, /artmneme/grafana-token) with the AWS profile in SSM_PROFILE.
Running it again updates both in place.
"""

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
FOLDER = "ArtMneme"
LOCAL_GRAFANA = "http://localhost:3000"


def ssm(name: str) -> str:
    return subprocess.run(
        ["aws", "ssm", "get-parameter", "--profile", os.environ.get("SSM_PROFILE", "artmneme-deploy"),
         "--with-decryption", "--name", name, "--query", "Parameter.Value", "--output", "text"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def api(method: str, path: str, body=None, ok=(200, 201, 202)):
    request = urllib.request.Request(
        GRAFANA + path, method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read() or "null")
    except urllib.error.HTTPError as error:
        if error.code in ok:
            return None
        raise SystemExit(f"{method} {path} failed: {error.code} {error.read().decode()[:300]}") from None


GRAFANA = ssm("/artmneme/grafana-url").rstrip("/")
TOKEN = ssm("/artmneme/grafana-token")

# Grafana Cloud's own Prometheus (Mimir) data source, e.g. "grafanacloud-<stack>-prom".
sources = [s for s in api("GET", "/api/datasources") if s["type"] == "prometheus"]
prometheus = next((s for s in sources if s["name"].endswith("-prom")), sources[0] if sources else None)
if prometheus is None:
    raise SystemExit("No Prometheus data source found in this Grafana.")

# The folder "ArtMneme": the existing one (whatever its ID), or a new one.
folder = next((f for f in api("GET", "/api/folders") if f["title"] == FOLDER), None) or api(
    "POST", "/api/folders", {"title": FOLDER}
)
FOLDER_UID = folder["uid"]

dashboard = json.loads((HERE / "grafana/dashboards/artmneme-app.json").read_text())
dashboard.pop("id", None)
for variable in dashboard["templating"]["list"]:
    if variable["name"] == "datasource":
        variable["current"] = {"text": prometheus["name"], "value": prometheus["uid"]}
api("POST", "/api/dashboards/db", {"dashboard": dashboard, "folderUid": FOLDER_UID, "overwrite": True})

group = json.loads((HERE / "grafana/provisioning/alerting/artwork-creation-failures.json").read_text())["groups"][0]
for rule in group["rules"]:
    rule = json.loads(json.dumps(rule).replace(LOCAL_GRAFANA, GRAFANA))
    for query in rule["data"]:
        if query["datasourceUid"] == "prometheus":
            query["datasourceUid"] = prometheus["uid"]
    rule = {**rule, "folderUID": FOLDER_UID, "ruleGroup": group["name"], "orgID": 1}
    # Create the rule the first time, update it afterwards (a rule group update cannot create a rule with a fixed ID).
    exists = api("GET", f"/api/v1/provisioning/alert-rules/{rule['uid']}", ok=(404,)) is not None
    if exists:
        api("PUT", f"/api/v1/provisioning/alert-rules/{rule['uid']}", rule)
    else:
        api("POST", "/api/v1/provisioning/alert-rules", rule)
current = api("GET", f"/api/v1/provisioning/folder/{FOLDER_UID}/rule-groups/{group['name']}")
api("PUT", f"/api/v1/provisioning/folder/{FOLDER_UID}/rule-groups/{group['name']}", {**current, "interval": 60})

print(f"Uploaded to {GRAFANA} (data source {prometheus['name']}):")
print(f"  dashboard  {GRAFANA}/d/{dashboard['uid']}/")
print(f"  alert      {GRAFANA}/alerting/list (folder ArtMneme)")
