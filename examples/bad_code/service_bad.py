# Bad: hardcoded secrets — never store credentials in source code
API_KEY = "sk-prod-abc123secret"
DB_PASSWORD = "supersecret123"

import requests


# Bad: writes to local filesystem for persistent storage instead of cloud
def save_report(data, filename):
    with open(f"/tmp/{filename}", "w") as f:
        f.write(str(data))
    print(f"Saved to /tmp/{filename}")


# Bad: God class — mezcla HTTP, DB, business logic y I/O en un solo metodo
class DataManager:
    def do_everything(self, user_expression, filename, url, table):
        # Bad: no timeout on HTTP call
        data = requests.get(url).json()
        # Bad: dynamic code execution on user input — critical security risk
        result = eval(user_expression)
        save_report(result, filename)
        return result
