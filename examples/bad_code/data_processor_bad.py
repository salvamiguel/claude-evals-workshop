# Bad: wildcard import pollutes namespace
from datetime import *

# Bad: forbidden DB library instead of internal_db_client
import psycopg2


# Bad: magic numbers scattered in logic (30, 0.75)
def process(records):
    result = []
    for r in records:
        if r["age"] < 30 and r["score"] > 0.75:
            result.append(r)
    # Bad: bare except hides errors
    try:
        conn = psycopg2.connect("host=localhost dbname=prod")
        conn.execute("INSERT INTO processed VALUES (%s)", [result])
    except:
        pass
    return result
