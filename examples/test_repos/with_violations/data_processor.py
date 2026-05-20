# Bad: wildcard import
from datetime import *

# Bad: forbidden DB library
import psycopg2


def process(records):
    result = []
    for r in records:
        # Bad: magic numbers 30 and 0.75
        if r["age"] < 30 and r["score"] > 0.75:
            result.append(r)
    try:
        conn = psycopg2.connect("host=localhost dbname=prod")
        conn.execute("INSERT INTO processed VALUES (%s)", [result])
    # Bad: bare except hides errors
    except:
        pass
    return result
