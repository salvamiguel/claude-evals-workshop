# Bad: hardcoded credentials
API_KEY = "sk-prod-abc123secret"
DB_PASSWORD = "supersecret123"

import requests


# Bad: writes to local filesystem instead of cloud storage
def save_report(data, filename):
    with open(f"/tmp/{filename}", "w") as f:
        f.write(str(data))


# Bad: God class — mixes HTTP, eval, IO into one method
class DataManager:
    def do_everything(self, user_expression, filename, url, table):
        # Bad: no timeout on HTTP call
        data = requests.get(url).json()
        # Bad: dynamic code execution on user input — noqa: S307
        result = eval(user_expression)  # noqa: S307
        save_report(result, filename)
        return result
