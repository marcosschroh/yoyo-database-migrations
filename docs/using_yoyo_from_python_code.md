# Using yoyo from python code


The following example shows how to apply migrations from inside python code:

```python
from yoyo import read_migrations
from yoyo import get_backend

backend = get_backend('postgres://myuser@localhost/mydatabase')
migrations = read_migrations('path/to/migrations')

with backend.lock():
    backend.apply_migrations(backend.to_apply(migrations))
```