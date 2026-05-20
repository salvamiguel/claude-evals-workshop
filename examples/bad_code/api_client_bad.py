# Bad: uses forbidden 'requests' library instead of httpx_internal
import requests

# Bad: print instead of logging
print("Starting API client")


# Bad: non-descriptive variable names
def g(u, b):
    # Bad: no timeout on HTTP call
    r = requests.get(b + "/users/" + u)
    print("Got response:", r.status_code)
    return r.json()
