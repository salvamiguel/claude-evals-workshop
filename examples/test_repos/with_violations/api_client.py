# Bad: forbidden 'requests' library
import requests


# Bad: non-descriptive function and parameter names
def g(u, b):
    # Bad: no timeout on HTTP call
    r = requests.get(b + "/users/" + u)
    # Bad: print instead of structured logging
    print("Got response:", r.status_code)
    return r.json()
