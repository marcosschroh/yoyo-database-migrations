# Transactions


Each migration runs in a separate transaction. Savepoints are used
to isolate steps within each migration.

If an error occurs during a step and the step has ``ignore_errors`` set,
then that individual step will be rolled back and
execution will pick up from the next step.
If ``ignore_errors`` is not set then the entire migration will be rolled back
and execution stopped.

Note that some databases (eg MySQL) do not support rollback on DDL statements
(eg ``CREATE ...`` and ``ALTER ...`` statements). For these databases
you may need to manually intervene to reset the database state
should errors occur in your migration.

Using ``group`` allows you to nest steps, giving you control of where
rollbacks happen. For example:

```python
group([
    step("ALTER TABLE employees ADD tax_code TEXT",
    step("CREATE INDEX tax_code_idx ON employees (tax_code)")
    ], ignore_errors='all'
)
step("UPDATE employees SET tax_code='C' WHERE pay_grade < 4")
step("UPDATE employees SET tax_code='B' WHERE pay_grade >= 6")
step("UPDATE employees SET tax_code='A' WHERE pay_grade >= 8")
```