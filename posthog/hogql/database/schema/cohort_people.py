from typing import Dict, List

from posthog.hogql.database.models import (
    StringDatabaseField,
    IntegerDatabaseField,
    Table,
    LazyJoin,
    LazyTable,
    FieldOrTable,
)
from posthog.hogql.database.schema.persons import join_with_persons_table

COHORT_PEOPLE_FIELDS = {
    "person_id": StringDatabaseField(name="person_id"),
    "cohort_id": IntegerDatabaseField(name="cohort_id"),
    "team_id": IntegerDatabaseField(name="team_id"),
    "person": LazyJoin(
        from_field=["person_id"],
        join_table="persons",
        join_function=join_with_persons_table,
    ),
}


def select_from_cohort_people_table(requested_fields: Dict[str, List[str | int]]):
    from posthog.hogql import ast

    table_name = "raw_cohort_people"

    # must always include the person and cohort ids regardless of what other fields are requested
    requested_fields = {
        "person_id": ["person_id"],
        "cohort_id": ["cohort_id"],
        **requested_fields,
    }
    fields: List[ast.Expr] = [
        ast.Alias(alias=name, expr=ast.Field(chain=[table_name] + chain)) for name, chain in requested_fields.items()
    ]

    return ast.SelectQuery(
        select=fields,
        select_from=ast.JoinExpr(table=ast.Field(chain=[table_name])),
        group_by=[ast.Field(chain=[name]) for name, chain in requested_fields.items()],
        having=ast.CompareOperation(
            op=ast.CompareOperationOp.Gt,
            left=ast.Call(name="sum", args=[ast.Field(chain=[table_name, "sign"])]),
            right=ast.Constant(value=0),
        ),
    )


class RawCohortPeople(Table):
    fields: Dict[str, FieldOrTable] = {
        **COHORT_PEOPLE_FIELDS,
        "sign": IntegerDatabaseField(name="sign"),
        "version": IntegerDatabaseField(name="version"),
    }

    def to_printed_clickhouse(self, context):
        return "cohortpeople"

    def to_printed_hogql(self):
        return "raw_cohort_people"


class CohortPeople(LazyTable):
    fields: Dict[str, FieldOrTable] = COHORT_PEOPLE_FIELDS

    def lazy_select(self, requested_fields: Dict[str, List[str | int]], context, node):
        return select_from_cohort_people_table(requested_fields)

    def to_printed_clickhouse(self, context):
        return "cohortpeople"

    def to_printed_hogql(self):
        return "cohort_people"
