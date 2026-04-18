"""Unit tests for app.services.sql_validator.

The validator is the security boundary between LLM-generated SQL and the
database. These tests exercise every branch and a handful of sneaky inputs
that a compromised/jailbroken model might try.
"""

from __future__ import annotations

import pytest

from app.services.sql_validator import SQLValidationError, validate_sql


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
class TestAllowedSelects:
    def test_simple_select_passes(self):
        out = validate_sql("SELECT id, name FROM cpu WHERE price < 500")
        assert "SELECT" in out.upper()
        assert not out.endswith(";")

    def test_trailing_semicolon_is_stripped(self):
        out = validate_sql("SELECT name FROM gpu;  ")
        assert not out.endswith(";")

    def test_whitespace_only_is_stripped(self):
        out = validate_sql("   SELECT name FROM cpu   ")
        assert out.startswith("SELECT")

    def test_join_across_catalog_tables_passes(self):
        # Not a meaningful JOIN (no FK), but validator only checks safety.
        sql = """
            SELECT c.name, g.name
            FROM cpu c JOIN gpu g ON c.id = g.id
            WHERE c.price < 500
        """
        validate_sql(sql)

    def test_aggregate_and_group_by_allowed(self):
        validate_sql(
            "SELECT COUNT(*) AS n, AVG(price) AS avg_p FROM gpu GROUP BY chipset"
        )

    def test_subquery_allowed(self):
        validate_sql(
            "SELECT name FROM cpu "
            "WHERE price = (SELECT MIN(price) FROM cpu)"
        )

    def test_order_by_limit_allowed(self):
        validate_sql("SELECT name FROM gpu ORDER BY price DESC LIMIT 5")


# ---------------------------------------------------------------------------
# Empty / unparseable input
# ---------------------------------------------------------------------------
class TestMalformedInput:
    def test_empty_string_rejected(self):
        with pytest.raises(SQLValidationError, match="Empty"):
            validate_sql("")

    def test_only_whitespace_rejected(self):
        with pytest.raises(SQLValidationError, match="Empty"):
            validate_sql("   \n\t  ")

    def test_only_semicolon_rejected(self):
        with pytest.raises(SQLValidationError, match="Empty"):
            validate_sql(";;;")

    def test_garbage_rejected(self):
        with pytest.raises(SQLValidationError):
            # sqlglot may raise ParseError OR return something unusable.
            validate_sql("this is not sql at all @@@")


# ---------------------------------------------------------------------------
# Statement-type enforcement
# ---------------------------------------------------------------------------
class TestStatementTypeEnforcement:
    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO cpu (name, core_count, price) VALUES ('x', 4, 1.0)",
            "UPDATE cpu SET price = 0",
            "DELETE FROM cpu",
            "DROP TABLE cpu",
            "CREATE TABLE hacked (id INT)",
            "ALTER TABLE cpu ADD COLUMN owned_by TEXT",
            "GRANT ALL PRIVILEGES ON cpu TO public",
            "TRUNCATE cpu",
        ],
    )
    def test_destructive_dml_ddl_rejected(self, sql: str):
        with pytest.raises(SQLValidationError):
            validate_sql(sql)

    def test_multiple_statements_rejected(self):
        with pytest.raises(SQLValidationError, match="exactly one"):
            validate_sql("SELECT 1; SELECT 2")

    def test_select_followed_by_delete_rejected(self):
        # Classic SQL-injection pattern the LLM might emit via string-concat.
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT * FROM cpu; DELETE FROM cpu")

    def test_select_into_rejected(self):
        # SELECT ... INTO creates a new table — not read-only.
        with pytest.raises(SQLValidationError, match="INTO"):
            validate_sql("SELECT id, name INTO cpu_copy FROM cpu")


# ---------------------------------------------------------------------------
# Table allow-listing (role-based)
# ---------------------------------------------------------------------------
class TestTableAllowlist:
    def test_user_can_query_catalog_tables(self):
        for table in ("cpu", "gpu", "mobo", "memory", "case", "storage",
                      "cpu_cooler", "psu", "case_fans"):
            validate_sql(f"SELECT id FROM {table}", user_role="user")

    @pytest.mark.parametrize(
        "table", ["users", "threads", "messages", "builds", "build_parts"],
    )
    def test_user_cannot_query_app_tables(self, table: str):
        with pytest.raises(SQLValidationError, match="not allowed for your role"):
            validate_sql(f"SELECT id FROM {table}", user_role="user")

    @pytest.mark.parametrize(
        "table", ["users", "threads", "messages", "builds", "build_parts",
                  "cpu", "gpu"],
    )
    def test_admin_can_query_app_and_catalog_tables(self, table: str):
        # password_hash is blocked separately; select a safe column.
        validate_sql(f"SELECT id FROM {table}", user_role="admin")

    def test_unknown_table_rejected_for_user(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT id FROM secret_table", user_role="user")

    def test_unknown_table_rejected_for_admin(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT id FROM secret_table", user_role="admin")

    @pytest.mark.parametrize(
        "sys_ref",
        [
            "SELECT * FROM pg_catalog.pg_tables",
            "SELECT * FROM information_schema.tables",
            "SELECT * FROM pg_roles",
            "SELECT * FROM pg_shadow",
        ],
    )
    def test_system_catalogs_always_rejected(self, sys_ref: str):
        with pytest.raises(SQLValidationError):
            # Even with admin role, system tables are off-limits.
            validate_sql(sys_ref, user_role="admin")


# ---------------------------------------------------------------------------
# Column denylist
# ---------------------------------------------------------------------------
class TestColumnDenylist:
    def test_password_hash_explicit_select_rejected_for_admin(self):
        with pytest.raises(SQLValidationError, match="password_hash"):
            validate_sql("SELECT id, password_hash FROM users", user_role="admin")

    def test_password_hash_aliased_rejected(self):
        # Aliasing shouldn't bypass — we look at the column name itself.
        with pytest.raises(SQLValidationError, match="password_hash"):
            validate_sql(
                "SELECT id, password_hash AS ph FROM users",
                user_role="admin",
            )

    def test_password_hash_in_where_rejected(self):
        with pytest.raises(SQLValidationError, match="password_hash"):
            validate_sql(
                "SELECT id FROM users WHERE password_hash = 'x'",
                user_role="admin",
            )

    def test_star_on_users_rejected(self):
        # SELECT * on users would leak password_hash — must be rejected outright.
        with pytest.raises(SQLValidationError, match="SELECT \\*"):
            validate_sql("SELECT * FROM users", user_role="admin")

    def test_star_on_catalog_table_is_fine_for_admin(self):
        # No sensitive columns on catalog tables — star is OK.
        validate_sql("SELECT * FROM cpu", user_role="admin")


# ---------------------------------------------------------------------------
# Role-default behaviour
# ---------------------------------------------------------------------------
class TestKnownLimitations:
    """These behaviours are intentional side-effects of the strict allowlist.

    They are documented as tests so that if the validator is ever updated to
    be more permissive, the change is explicit and reviewed.
    """

    def test_cte_alias_is_treated_as_unauthorised_table(self):
        # `cheap_gpu` is a CTE alias, not a real table, but the validator sees
        # it as a Table node outside the allowlist and rejects it. Users should
        # avoid CTEs until this is explicitly supported.
        with pytest.raises(SQLValidationError, match="not allowed for your role"):
            validate_sql(
                "WITH cheap_gpu AS (SELECT * FROM gpu WHERE price < 300) "
                "SELECT name FROM cheap_gpu",
                user_role="user",
            )

    def test_union_at_root_is_rejected(self):
        # Root UNION / UNION ALL is not in _ALLOWED_NODES; only plain SELECT is.
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            validate_sql("SELECT name FROM cpu UNION ALL SELECT name FROM gpu")


class TestRoleDefault:
    def test_missing_role_defaults_to_user(self):
        # Default is user — so app-tables must be rejected by default.
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT id FROM users")

    def test_unknown_role_string_treated_as_user(self):
        # Any string that isn't exactly "admin" collapses to user-level access.
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT id FROM users", user_role="hacker")