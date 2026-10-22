"""Conservative reservations for bounded fixture calls, stored with service state.

No adapter may advertise a hard monetary cap without an enforceable bound on
each in-flight call. The real harness capability remains unverified.
"""

from .store import Conflict


class Budget:
    def __init__(self, store):
        store._core()
        self.store = store
        store.db.executescript("""
            CREATE TABLE IF NOT EXISTS budgets
              (id TEXT PRIMARY KEY, cap INTEGER NOT NULL, spent INTEGER NOT NULL,
               concurrency INTEGER NOT NULL, depth INTEGER NOT NULL, stopped INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS reservations
              (id TEXT PRIMARY KEY, budget TEXT NOT NULL, amount INTEGER NOT NULL,
               state TEXT NOT NULL, actual INTEGER);
        """)

    def create(self, budget_id, cap_microusd, concurrency, depth):
        if (
            any(type(x) is not int or x < 0 for x in (cap_microusd, concurrency, depth))
            or concurrency == 0
        ):
            raise ValueError("invalid budget")
        with self.store.transaction():
            self.store.db.execute(
                "INSERT INTO budgets VALUES(?,?,0,?,?,0)",
                (budget_id, cap_microusd, concurrency, depth),
            )
            self.store._history(
                "budget.created", {"id": budget_id, "cap": cap_microusd}
            )

    def reserve(self, budget_id, operation_id, maximum_microusd, depth, *, enforceable):
        if not enforceable:
            raise PermissionError("adapter cannot bound in-flight cost")
        if (
            type(maximum_microusd) is not int
            or maximum_microusd < 0
            or type(depth) is not int
            or depth < 0
        ):
            raise ValueError("invalid reservation")
        db = self.store.db
        with self.store.transaction():
            prior = db.execute(
                "SELECT * FROM reservations WHERE id=?", (operation_id,)
            ).fetchone()
            if prior:
                if prior["budget"] != budget_id or prior["amount"] != maximum_microusd:
                    raise Conflict("reservation identity conflict")
                return prior["state"]
            row = db.execute(
                "SELECT * FROM budgets WHERE id=?", (budget_id,)
            ).fetchone()
            if not row:
                raise KeyError(budget_id)
            active = db.execute(
                "SELECT count(*),coalesce(sum(amount),0) FROM reservations WHERE budget=? AND state IN ('reserved','unknown')",
                (budget_id,),
            ).fetchone()
            if (
                self.store.stopped()
                or row["stopped"]
                or depth > row["depth"]
                or active[0] >= row["concurrency"]
            ):
                raise Conflict("budget admission refused")
            if row["spent"] + active[1] + maximum_microusd > row["cap"]:
                raise Conflict("budget exhausted")
            db.execute(
                "INSERT INTO reservations VALUES(?,?,?,'reserved',NULL)",
                (operation_id, budget_id, maximum_microusd),
            )
            self.store._history(
                "budget.reserved",
                {"operation": operation_id, "amount": maximum_microusd},
            )
        return "reserved"

    def settle(self, operation_id, actual_microusd):
        if actual_microusd is not None and (
            type(actual_microusd) is not int or actual_microusd < 0
        ):
            raise ValueError("invalid cost")
        db = self.store.db
        with self.store.transaction():
            row = db.execute(
                "SELECT * FROM reservations WHERE id=?", (operation_id,)
            ).fetchone()
            if not row:
                raise KeyError(operation_id)
            if row["state"] == "settled":
                if row["actual"] != actual_microusd:
                    raise Conflict("settlement conflict")
                return
            if actual_microusd is None:
                db.execute(
                    "UPDATE reservations SET state='unknown' WHERE id=?",
                    (operation_id,),
                )
            else:
                db.execute(
                    "UPDATE reservations SET state='settled',actual=? WHERE id=?",
                    (actual_microusd, operation_id),
                )
                db.execute(
                    "UPDATE budgets SET spent=spent+?,stopped=max(stopped,?) WHERE id=?",
                    (
                        actual_microusd,
                        int(actual_microusd > row["amount"]),
                        row["budget"],
                    ),
                )
            self.store._history(
                "budget.settled", {"operation": operation_id, "actual": actual_microusd}
            )

    def reconcile_absent(self, operation_id, transport):
        if not getattr(transport, "fake_backend", False):
            raise PermissionError("live reconciliation is not enabled")
        if transport.lookup(operation_id)["state"] != "absent":
            raise Conflict("reservation absence is not confirmed")
        self.settle(operation_id, 0)
