# Yoyo database migrations

Yoyo is a Python database schema migration tool. You write migrations as Python
scripts containing raw SQL statements or Python functions.
They can be as simple as this:

```python
# file: migrations/0001.create-foo.py

from yoyo import step

steps = [
    step(
        "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
        "DROP TABLE foo"
    )
]
```
