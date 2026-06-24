import tempfile
import unittest
from pathlib import Path

from northwind_agent.main import NorthwindDatabase, OllamaNorthwindAgent


class NorthwindDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = NorthwindDatabase(Path(self.tmp.name) / "northwind.db")
        self.db.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_select_query_returns_rows(self) -> None:
        rows = self.db.execute_select("SELECT ProductName FROM Products ORDER BY ProductID LIMIT 1")
        self.assertEqual(rows[0]["ProductName"], "Chai")

    def test_non_select_query_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.db.execute_select("DELETE FROM Products")


class ScriptedAgent(OllamaNorthwindAgent):
    def __init__(self, db, scripted):
        super().__init__(db)
        self.scripted = scripted
        self.calls = 0

    async def _chat(self, messages, stream, tools=None):
        entry = self.scripted[self.calls]
        self.calls += 1
        if stream:
            async def _gen():
                for chunk in entry:
                    yield chunk
            return _gen()
        return entry


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = NorthwindDatabase(Path(self.tmp.name) / "northwind.db")
        self.db.initialize()

    async def asyncTearDown(self) -> None:
        self.tmp.cleanup()

    async def test_agent_executes_tool_calls_then_streams(self) -> None:
        scripted = [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "run_sql_query",
                                "arguments": {
                                    "query": "SELECT ProductName FROM Products ORDER BY ProductID LIMIT 1"
                                },
                            }
                        }
                    ]
                }
            },
            [{"message": {"content": "Top product is Chai."}}],
        ]
        agent = ScriptedAgent(self.db, scripted)
        chunks = [chunk async for chunk in agent.stream_answer("What is top product?")]
        self.assertEqual("".join(chunks), "Top product is Chai.")


if __name__ == "__main__":
    unittest.main()
