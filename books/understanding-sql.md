---
title: Understanding SQL and Relational Databases
subtitle: A foundations guide, from first principles to real-world practice
tag: Relational Foundations
accent: "#2E5AAC"
flavor: sharp
order: 1
---

# Understanding SQL and Relational Databases

*A foundations guide, from first principles to real-world practice*

---

## Table of Contents

1. What a Relational Database Actually Is
2. Tables, Rows, Columns, and Types
3. Keys: How Rows Get Identity
4. Relationships: How Tables Connect
5. The SQL Language, Part 1: Reading Data
6. Joins: Combining Tables
7. Aggregation: Asking Questions of Groups
8. The SQL Language, Part 2: Writing Data
9. Constraints: The Database as a Guardian
10. Transactions and ACID
11. Indexes: Why Queries Are Fast (or Slow)
12. Normalization: Designing Good Schemas
13. Schema Migrations: Evolving a Live Database
14. ORMs: Talking to SQL from Python
15. Strengths, Limits, and When SQL Is the Right Tool

---

## Chapter 1: What a Relational Database Actually Is

A relational database stores data as a set of **tables**. Each table is a grid: columns define what kind of information is stored, rows hold the actual records. The word "relational" does not refer to relationships between tables (a common misconception). It comes from the mathematical term *relation*, which is what a table formally is: a set of tuples over named attributes.

The model was proposed by E.F. Codd at IBM in 1970, and its core promise is still the reason SQL dominates fifty years later: you describe **what** data you want, and the database figures out **how** to get it. This is called declarative querying. You never write "loop over the users file, check each record's city field". You write:

```sql
SELECT name FROM users WHERE city = 'Delhi';
```

The database engine (PostgreSQL, MySQL, SQLite, SQL Server, Oracle) parses this, builds a query plan, decides whether to use an index or scan the whole table, and returns the result. The engine is free to change strategies as the data grows, and your query stays the same.

Three ideas define the relational world, and every chapter of this book expands on one of them:

- **Schema first.** The shape of the data is declared before any data exists, and the database enforces it.
- **Integrity is the database's job.** Rules like "every order must belong to a real customer" are declared once and enforced automatically.
- **Data is normalized.** Each fact is stored in exactly one place, and queries reassemble facts as needed.

## Chapter 2: Tables, Rows, Columns, and Types

A table is created with a `CREATE TABLE` statement that declares every column and its type:

```sql
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    is_active   BOOLEAN DEFAULT TRUE,
    balance     NUMERIC(10, 2) DEFAULT 0.00,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

Read this line by line:

- `id SERIAL PRIMARY KEY`: an auto-incrementing integer (1, 2, 3, ...) that uniquely identifies each row. `SERIAL` is PostgreSQL syntax; MySQL uses `AUTO_INCREMENT`, SQLite uses `INTEGER PRIMARY KEY`.
- `VARCHAR(50) NOT NULL`: a string up to 50 characters that can never be null. If an insert omits it, the insert fails.
- `UNIQUE`: no two rows can share the same email. The database rejects duplicates with an error.
- `NUMERIC(10, 2)`: an exact decimal with 10 total digits, 2 after the point. Used for money, because floating point types like `FLOAT` introduce rounding errors.
- `DEFAULT NOW()`: if the insert does not supply a value, the current timestamp is used.

### Common types you will meet everywhere

| Type | What it holds | Notes |
|---|---|---|
| `INTEGER` / `BIGINT` | Whole numbers | `BIGINT` for IDs at scale |
| `VARCHAR(n)` / `TEXT` | Strings | `TEXT` is unbounded |
| `BOOLEAN` | true/false | MySQL fakes it with `TINYINT(1)` |
| `NUMERIC(p, s)` | Exact decimals | Always use for money |
| `TIMESTAMP` / `DATE` | Time values | Prefer `TIMESTAMPTZ` in Postgres |
| `JSON` / `JSONB` | Embedded JSON | Postgres can index inside `JSONB` |
| `UUID` | Random unique IDs | Alternative to serial integers |

The important cultural point: in SQL, **types are enforced**. Inserting the string `'abc'` into an `INTEGER` column is an error, not a silent coercion. The schema is a contract, and the database is the enforcer of that contract.

### NULL, the special non-value

`NULL` means "no value" and behaves strangely on purpose. `NULL = NULL` is not true, it is `NULL`. You test for it with `IS NULL` and `IS NOT NULL`. Any arithmetic or comparison involving `NULL` produces `NULL`. This trips up every beginner at least once, usually inside a `WHERE` clause that mysteriously drops rows.

## Chapter 3: Keys: How Rows Get Identity

### Primary keys

Every well-designed table has a **primary key (PK)**: one column (or a combination) whose value uniquely identifies each row and can never be null. Two common styles:

- **Surrogate keys**: an artificial auto-increment integer or UUID with no business meaning. This is the default choice in almost all applications.
- **Natural keys**: a real-world attribute like a national ID or ISBN. These look clean but age badly, because real-world identifiers change more often than people expect.

### Foreign keys

A **foreign key (FK)** is a column in one table that holds the primary key of a row in another table. It is both a pointer and a rule:

```sql
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    total       NUMERIC(10, 2) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

`REFERENCES users(id)` means: every `orders.user_id` must match an existing `users.id`. Try to insert an order for user 999 when no such user exists, and the database refuses. Try to delete a user who still has orders, and the database refuses that too (by default). This property is called **referential integrity**, and it is one of the strongest guarantees relational databases offer. Your data cannot silently rot into a state where orders point at ghosts.

### Cascade behavior

You can tell the FK what to do when the parent row disappears:

```sql
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
```

- `ON DELETE CASCADE`: deleting a user automatically deletes all their orders.
- `ON DELETE SET NULL`: orders survive but their `user_id` becomes null.
- `ON DELETE RESTRICT` (default): the delete is blocked while children exist.

This single declaration replaces what would otherwise be careful, easy-to-forget cleanup code in the application.

## Chapter 4: Relationships: How Tables Connect

Relational design recognizes three relationship shapes.

### One-to-many (the workhorse)

One user has many orders; each order belongs to one user. Implemented with a foreign key on the "many" side, exactly as in the previous chapter. This covers the vast majority of relationships in real schemas.

### One-to-one

One user has one profile. Implemented as a separate table whose primary key is *also* a foreign key to the parent, or with a `UNIQUE` foreign key. Used to split rarely-accessed or optional data out of a hot table.

### Many-to-many (the junction table)

Students take many courses; courses have many students. Neither table can hold the FK, because both sides are "many". The solution is a third table, called a **junction table** (also association table or join table):

```sql
CREATE TABLE enrollments (
    student_id  INTEGER REFERENCES students(id),
    course_id   INTEGER REFERENCES courses(id),
    enrolled_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (student_id, course_id)
);
```

Each row is one link. The composite primary key prevents duplicate enrollments. Junction tables often grow extra columns of their own (a grade, a timestamp, a role), at which point they quietly become real entities.

Recognizing these three shapes on sight is most of what "reading a schema" means.

## Chapter 5: The SQL Language, Part 1: Reading Data

`SELECT` is the heart of SQL. Its clauses always appear in this order:

```sql
SELECT columns
FROM table
WHERE row_filter
GROUP BY grouping
HAVING group_filter
ORDER BY sorting
LIMIT count OFFSET skip;
```

A few examples, from trivial to useful:

```sql
-- Everything (fine for exploring, avoid in application code)
SELECT * FROM users;

-- Specific columns, filtered and sorted
SELECT username, email
FROM users
WHERE is_active = TRUE AND created_at > '2026-01-01'
ORDER BY created_at DESC
LIMIT 20;

-- Pattern matching and set membership
SELECT * FROM users WHERE email LIKE '%@iitd.ac.in';
SELECT * FROM orders WHERE status IN ('pending', 'processing');

-- Ranges and null checks
SELECT * FROM orders WHERE total BETWEEN 100 AND 500;
SELECT * FROM users WHERE deleted_at IS NULL;
```

Key operators to have in your fingers: `=`, `<>` (not equal), `<`, `>`, `AND`, `OR`, `NOT`, `IN`, `BETWEEN`, `LIKE` (with `%` as wildcard), `IS NULL`.

### Logical execution order

The clauses are *written* in one order but *evaluated* in another: `FROM`, then `WHERE`, then `GROUP BY`, then `HAVING`, then `SELECT`, then `ORDER BY`, then `LIMIT`. This explains a classic beginner error: you cannot use a column alias defined in `SELECT` inside `WHERE`, because `WHERE` runs first.

### Subqueries

A query can nest inside another:

```sql
SELECT username FROM users
WHERE id IN (SELECT user_id FROM orders WHERE total > 1000);
```

Subqueries are readable for small cases; joins (next chapter) usually scale better.

## Chapter 6: Joins: Combining Tables

Normalization splits facts across tables. Joins reassemble them. A join matches rows from two tables based on a condition, almost always PK = FK.

```sql
SELECT users.username, orders.total, orders.created_at
FROM users
JOIN orders ON orders.user_id = users.id
WHERE orders.total > 500;
```

### The join family

- **INNER JOIN** (or just `JOIN`): only rows that match on both sides. Users without orders vanish from the result.
- **LEFT JOIN**: every row from the left table, matched rows from the right, and `NULL`s where no match exists. "All users, with their orders if any."
- **RIGHT JOIN**: mirror image of LEFT, rarely used (people just swap the table order).
- **FULL OUTER JOIN**: everything from both sides, nulls where either side is missing.

The one to internalize deeply is LEFT JOIN, because "show me all X, even the ones without Y" is an everyday business question:

```sql
-- Users who have never ordered anything
SELECT users.username
FROM users
LEFT JOIN orders ON orders.user_id = users.id
WHERE orders.id IS NULL;
```

### Joining through a junction table

Many-to-many queries chain two joins:

```sql
SELECT students.name, courses.title
FROM students
JOIN enrollments ON enrollments.student_id = students.id
JOIN courses ON courses.id = enrollments.course_id;
```

Joins are the feature MongoDB and other document stores deliberately de-emphasize, which is why understanding them clarifies both worlds: SQL keeps data apart and joins at read time; document databases pre-join data at write time by embedding.

## Chapter 7: Aggregation: Asking Questions of Groups

Aggregate functions collapse many rows into one value: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`.

```sql
SELECT COUNT(*) FROM orders;
SELECT AVG(total) FROM orders WHERE status = 'completed';
```

`GROUP BY` runs aggregates per group instead of over the whole table:

```sql
-- Revenue per user
SELECT user_id, COUNT(*) AS order_count, SUM(total) AS revenue
FROM orders
GROUP BY user_id
ORDER BY revenue DESC;
```

Every column in the `SELECT` must either be inside an aggregate function or appear in `GROUP BY`. This rule feels bureaucratic until you realize it prevents ambiguous results.

`HAVING` filters *groups* after aggregation, the way `WHERE` filters rows before it:

```sql
-- Only users with more than 5 orders
SELECT user_id, COUNT(*) AS order_count
FROM orders
GROUP BY user_id
HAVING COUNT(*) > 5;
```

Combined with joins, this is the reporting engine of the business world:

```sql
SELECT users.username, SUM(orders.total) AS lifetime_value
FROM users
JOIN orders ON orders.user_id = users.id
GROUP BY users.username
HAVING SUM(orders.total) > 10000
ORDER BY lifetime_value DESC
LIMIT 10;
```

## Chapter 8: The SQL Language, Part 2: Writing Data

```sql
-- Insert
INSERT INTO users (username, email) VALUES ('lakshay', 'l@example.com');

-- Insert multiple rows
INSERT INTO users (username, email) VALUES
    ('a', 'a@x.com'),
    ('b', 'b@x.com');

-- Update
UPDATE users SET is_active = FALSE WHERE last_login < '2025-01-01';

-- Delete
DELETE FROM orders WHERE status = 'cancelled';
```

Two safety habits that separate professionals from horror stories:

1. **Never run `UPDATE` or `DELETE` without a `WHERE` clause** unless you truly mean every row. `UPDATE users SET is_active = FALSE;` deactivates every user in the system, instantly, with no confirmation prompt.
2. **Test destructive statements as a `SELECT` first.** Write `SELECT * FROM orders WHERE status = 'cancelled'`, eyeball the rows, then change the verb to `DELETE`.

Modern engines also support **upserts**, insert-or-update in one statement:

```sql
INSERT INTO settings (key, value) VALUES ('theme', 'dark')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

## Chapter 9: Constraints: The Database as a Guardian

Constraints are rules attached to the schema that the engine enforces on every write, from every application, forever. This is the philosophical core of relational databases: **the database defends its own correctness**, rather than trusting each application to behave.

- `NOT NULL`: the column must always have a value.
- `UNIQUE`: no duplicates in this column (or combination of columns).
- `PRIMARY KEY`: `NOT NULL` + `UNIQUE`, one per table.
- `FOREIGN KEY ... REFERENCES`: the value must exist in the parent table.
- `CHECK`: an arbitrary boolean rule, e.g. `CHECK (price >= 0)` or `CHECK (age BETWEEN 0 AND 150)`.
- `DEFAULT`: not a rule, but a value filled in when none is supplied.

Why this matters in practice: a bug in one code path cannot create a negative price, an order without a customer, or two accounts with the same email. The invalid write is rejected at the last line of defense. Systems that move to schemaless databases lose this safety net and must rebuild it in application code, which is precisely why constraint awareness matters when comparing SQL with MongoDB.

## Chapter 10: Transactions and ACID

A **transaction** groups several statements into one all-or-nothing unit:

```sql
BEGIN;
UPDATE accounts SET balance = balance - 500 WHERE id = 1;
UPDATE accounts SET balance = balance + 500 WHERE id = 2;
COMMIT;
```

If anything fails between `BEGIN` and `COMMIT` (a constraint violation, a crash, a `ROLLBACK`), *neither* update happens. Money is never half-transferred.

The famous ACID acronym describes what transactions guarantee:

- **Atomicity**: all statements apply, or none do.
- **Consistency**: the database moves from one valid state to another; constraints hold before and after.
- **Isolation**: concurrent transactions do not see each other's half-finished work. (Engines offer levels of isolation, from `READ COMMITTED` to `SERIALIZABLE`, trading strictness for speed.)
- **Durability**: once committed, data survives crashes and power loss, because it is written to a log on disk before the commit returns.

ACID transactions across multiple tables are effortless and cheap in SQL. This is a genuine differentiator: many NoSQL systems either lack multi-document transactions or make them expensive and conditional. Any workload where partial writes are unacceptable (payments, inventory, bookings) leans on this heavily.

## Chapter 11: Indexes: Why Queries Are Fast (or Slow)

Without an index, `SELECT * FROM users WHERE email = 'x@y.com'` reads every row in the table: a **full table scan**, O(n). An index is a separate sorted structure (almost always a **B-tree**) that maps column values to row locations, making lookups O(log n):

```sql
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_orders_user_created ON orders (user_id, created_at);
```

Facts worth knowing:

- **Primary keys and UNIQUE constraints create indexes automatically.** This is why lookups by ID are always fast.
- **Foreign key columns are NOT auto-indexed** in most engines. Forgetting to index FK columns is the single most common cause of slow joins in real applications.
- **Composite indexes** cover multiple columns, and column order matters: an index on `(user_id, created_at)` accelerates queries filtering by `user_id`, or by both, but not queries filtering only by `created_at`.
- **Indexes cost writes.** Every `INSERT`/`UPDATE` must maintain every index on the table. You index what you query, not everything.
- `EXPLAIN` (or `EXPLAIN ANALYZE`) shows the query plan, revealing whether an index was used or a scan happened. Reading query plans is the core skill of SQL performance work.

## Chapter 12: Normalization: Designing Good Schemas

Normalization is the discipline of storing each fact exactly once. The classic normal forms, in plain language:

- **1NF**: every cell holds a single atomic value. No comma-separated lists inside a column, no repeating column groups like `phone1, phone2, phone3`.
- **2NF**: every non-key column depends on the *whole* primary key. Only relevant for composite keys; if a column depends on just part of the key, it belongs in another table.
- **3NF**: non-key columns depend *only* on the key, not on each other. If `orders` stores `customer_id` and also `customer_city`, the city depends on the customer, not the order, and belongs in the customers table.

The practical payoff: **update anomalies disappear**. If a customer's city is stored in one place, changing it is one `UPDATE` of one row. Stored in a thousand order rows, it requires a mass update and will eventually drift into inconsistency.

The practical cost: normalized data is spread across tables, so reads need joins. This is the eternal tradeoff, and it explains **denormalization**: deliberately duplicating data (a cached `order_count` on the user row, a snapshot of the product price on the order line) to make hot reads cheaper, accepting the burden of keeping copies in sync. Mature schemas are normalized by default and denormalized surgically, with reasons written down.

## Chapter 13: Schema Migrations: Evolving a Live Database

The schema is code-adjacent: it changes as the product changes. But unlike code, you cannot just redeploy it, because the database is full of data that must survive the change. **Migrations** solve this: small, versioned, ordered scripts that transform the schema step by step.

The raw SQL for schema change is DDL (Data Definition Language):

```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
ALTER TABLE users DROP COLUMN legacy_flag;
ALTER TABLE users RENAME COLUMN username TO handle;
```

In practice nobody runs these by hand. A migration tool keeps a folder of scripts and a bookkeeping table inside the database recording which have run. In the Python world the standard tool is **Alembic** (paired with SQLAlchemy). A project using it has:

```
alembic.ini
alembic/
    env.py
    versions/
        20260114_a1b2c3_create_users.py
        20260201_d4e5f6_add_orders.py
```

Each version file has an `upgrade()` function applying the change and a `downgrade()` reversing it:

```python
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20)))

def downgrade():
    op.drop_column('users', 'phone')
```

Running `alembic upgrade head` applies all pending migrations in order, on your laptop, in CI, and in production, guaranteeing every environment has the same schema. Migrations are the operational heartbeat of a SQL codebase: the full history of the database's shape, in version control, reviewable in pull requests. When a project abandons SQL entirely, this whole apparatus becomes dead weight and should be removed, and its absence is one of the clearest signs a codebase no longer depends on a relational store.

## Chapter 14: ORMs: Talking to SQL from Python

An **ORM** (Object-Relational Mapper) maps tables to classes and rows to objects, so application code manipulates objects and the ORM emits SQL. The dominant Python ORM is **SQLAlchemy**; Django has its own built-in ORM.

A SQLAlchemy model:

```python
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    orders = relationship("Order", back_populates="user")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    user = relationship("User", back_populates="orders")
```

And the plumbing that connects it to a real database, which in a FastAPI app usually looks like:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://user:pass@localhost/mydb")
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Usage reads like Python but executes as SQL:

```python
user = db.query(User).filter(User.email == "l@x.com").first()
user.orders  # lazy-loads via a JOIN or second query
db.add(Order(user_id=user.id, total=499.00))
db.commit()
```

Two ideas to understand about ORMs:

- **The session is a unit of work.** Changes accumulate in memory and flush to the database on `commit()`, wrapped in a transaction.
- **Lazy loading and the N+1 problem.** Accessing `user.orders` inside a loop over 100 users fires 100 extra queries. Eager loading (`joinedload`, `selectinload`) fetches related rows in one go. N+1 is the most common ORM performance bug in existence.

An ORM does not hide SQL so much as generate it; strong developers read the generated SQL when things get slow.

## Chapter 15: Strengths, Limits, and When SQL Is the Right Tool

**Where SQL excels:**

- Structured data with stable, well-understood shape.
- Strong integrity requirements: money, inventory, identity, anything where wrong data is expensive.
- Ad-hoc querying and reporting: joins plus aggregation answer questions nobody anticipated at design time.
- Multi-row, multi-table transactional workflows.
- A 50-year ecosystem: every language, every BI tool, every hire knows it.

**Where it strains:**

- Rapidly evolving or heterogeneous data shapes, where every change is a migration.
- Deeply nested data that must be shredded across many tables and rejoined constantly.
- Horizontal scaling: classic SQL scales up (bigger machine) more naturally than out (many machines), though modern distributed SQL systems have narrowed this gap.

The mature position is not "SQL vs NoSQL" as a religion but as a fit question: what shape is the data, what guarantees does the business need, what queries will be asked? Relational databases remain the default answer for most transactional applications, and the burden of proof sits on the alternative. Understanding *why* (constraints, transactions, joins, normalization) is exactly what this book has tried to build.

---

*End of guide.*
