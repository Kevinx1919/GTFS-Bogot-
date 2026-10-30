"""Dobles mínimos para probar bloques de notebooks sin Spark, red ni Databricks.

Ejecutan el código versionado; no certifican el motor Spark ni transacciones Delta.
"""

import ast
from contextlib import contextmanager
from pathlib import Path
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

NOTEBOOKS = Path(__file__).resolve().parents[1] / "databricks" / "notebooks"


def cell_source(notebook: str, marker: str) -> str:
    content = json.loads((NOTEBOOKS / notebook).read_text(encoding="utf-8-sig"))
    matches = [
        "".join(cell["source"])
        for cell in content["cells"]
        if cell["cell_type"] == "code" and marker in "".join(cell["source"])
    ]
    if len(matches) != 1:
        raise AssertionError(f"Se esperaba un bloque para {notebook}: {marker}")
    return matches[0]


def execute_function(source: str, name: str, namespace: dict) -> None:
    """Carga una función real sin ejecutar las escrituras del resto del bloque."""
    definitions = [
        node for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(definitions) != 1:
        raise AssertionError(f"Función no encontrada: {name}")
    module = ast.Module(body=definitions, type_ignores=[])
    exec(compile(module, "<notebook-function>", "exec"), namespace)


class Expression:
    def __init__(self, evaluate, name=None):
        self.evaluate = evaluate
        self.name = name

    def _compare(self, other, operation):
        other = other if isinstance(other, Expression) else Expression(lambda row, value=other: value)
        def evaluate(row):
            left, right = self.evaluate(row), other.evaluate(row)
            return None if left is None or right is None else operation(left, right)
        return Expression(evaluate)

    def __eq__(self, other):
        return self._compare(other, lambda left, right: left == right)

    def __ne__(self, other):
        return self._compare(other, lambda left, right: left != right)

    def __or__(self, other):
        def evaluate(row):
            values = self.evaluate(row), other.evaluate(row)
            if True in values:
                return True
            return None if None in values else False
        return Expression(evaluate)

    def __invert__(self):
        return Expression(lambda row: None if self.evaluate(row) is None else not self.evaluate(row))

    def isNull(self):
        return Expression(lambda row: self.evaluate(row) is None)

    def isin(self, *values):
        return Expression(lambda row: self.evaluate(row) in values)

    def alias(self, name):
        return Expression(self.evaluate, name)


class Functions:
    @staticmethod
    def col(name):
        return Expression(lambda row: row.get(name), name)

    @staticmethod
    def lit(value):
        return Expression(lambda row: value)

    @staticmethod
    def trim(column):
        column = Functions.col(column) if isinstance(column, str) else column
        return Expression(lambda row: None if column.evaluate(row) is None else column.evaluate(row).strip())


class Frame:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, expression):
        return Frame(row for row in self.rows if expression.evaluate(row) is True)

    def count(self):
        return len(self.rows)

    def select(self, *columns):
        expressions = [Functions.col(column) if isinstance(column, str) else column for column in columns]
        return Frame({column.name: column.evaluate(row) for column in expressions} for row in self.rows)

    def distinct(self):
        unique = {tuple(sorted(row.items())) for row in self.rows}
        return Frame(dict(row) for row in unique)

    def unionByName(self, other):
        return Frame(self.rows + other.rows)

    def withColumnRenamed(self, old, new):
        return Frame({new if key == old else key: value for key, value in row.items()} for row in self.rows)

    def join(self, other, key, how):
        if how != "left_anti":
            raise AssertionError(f"Join no soportado por este doble: {how}")
        parent_keys = {row[key] for row in other.rows}
        return Frame(row for row in self.rows if row[key] not in parent_keys)

    def orderBy(self, *args):
        return self


class SparkDouble:
    def __init__(self, tables=None):
        self.tables = tables or {}
        self.catalog = SimpleNamespace(tableExists=lambda name: name in self.tables)

    def table(self, name):
        return Frame(self.tables[name])

    def createDataFrame(self, rows, schema=None):
        # Los DataFrames de display no participan en la lógica bajo prueba.
        return Frame([])


class LocalVolume:
    """Volume de prueba limitado al TemporaryDirectory de cada caso."""
    def __init__(self):
        self.put_count = 0

    def mkdirs(self, path):
        Path(path).mkdir(parents=True, exist_ok=True)

    def ls(self, path):
        return [SimpleNamespace(name=file.name) for file in Path(path).iterdir()]

    def put(self, path, content, overwrite=False):
        with Path(path).open("w" if overwrite else "x", encoding="utf-8") as file:
            file.write(content)
        self.put_count += 1

    def head(self, path):
        return Path(path).read_text(encoding="utf-8")


@contextmanager
def spark_type_stubs():
    class DataType:
        def __init__(self, *args, **kwargs):
            pass

    pyspark = ModuleType("pyspark")
    sql = ModuleType("pyspark.sql")
    types = ModuleType("pyspark.sql.types")
    for name in ("ArrayType", "BooleanType", "IntegerType", "LongType", "StringType", "StructField", "StructType", "TimestampType"):
        setattr(types, name, DataType)
    sql.functions = Functions
    pyspark.sql = sql
    pyspark.StorageLevel = SimpleNamespace(MEMORY_AND_DISK="test")
    with patch.dict(sys.modules, {"pyspark": pyspark, "pyspark.sql": sql, "pyspark.sql.types": types}):
        yield
