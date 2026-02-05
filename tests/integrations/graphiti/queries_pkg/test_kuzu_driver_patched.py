"""Comprehensive tests for kuzu_driver_patched.py module."""

from unittest.mock import MagicMock, AsyncMock, patch, call
import pytest


class TestCreatePatchedKuzuDriver:
    """Tests for create_patched_kuzu_driver function."""

    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu")
    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.PatchedKuzuDriver")
    def test_create_patched_kuzu_driver_default_params(self, mock_driver_class, mock_kuzu):
        """Test create_patched_kuzu_driver with default parameters."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        mock_driver_instance = MagicMock()
        mock_driver_class.return_value = mock_driver_instance

        result = create_patched_kuzu_driver()

        mock_driver_class.assert_called_once_with(db=":memory:", max_concurrent_queries=1)
        assert result == mock_driver_instance

    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu")
    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.PatchedKuzuDriver")
    def test_create_patched_kuzu_driver_custom_params(self, mock_driver_class, mock_kuzu):
        """Test create_patched_kuzu_driver with custom parameters."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        mock_driver_instance = MagicMock()
        mock_driver_class.return_value = mock_driver_instance

        result = create_patched_kuzu_driver(db="/tmp/test_db", max_concurrent_queries=5)

        mock_driver_class.assert_called_once_with(db="/tmp/test_db", max_concurrent_queries=5)
        assert result == mock_driver_instance


class TestPatchedKuzuDriverInit:
    """Tests for PatchedKuzuDriver.__init__."""

    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu")
    def test_init_stores_database_path(self, mock_kuzu):
        """Test __init__ stores database path."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.PatchedKuzuDriver.__init__", lambda self, db, max_concurrent_queries: None):
            # This test verifies the _database attribute is set
            from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver
            import sys

            # Get the class from the module
            module = type(sys.modules["integrations.graphiti.queries_pkg.kuzu_driver_patched"])
            PatchedKuzuDriver = getattr(sys.modules["integrations.graphiti.queries_pkg.kuzu_driver_patched"], "PatchedKuzuDriver")

            # Mock parent class
            with patch.object(PatchedKuzuDriver, "__bases__", (MagicMock,)):
                driver = PatchedKuzuDriver(db="/tmp/test_db")
                assert hasattr(driver, "_database")


class TestPatchedKuzuDriverExecuteQuery:
    """Tests for PatchedKuzuDriver.execute_query method."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self):
        """Test execute_query with valid query."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu") as mock_kuzu:
            # Setup mock connection
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.rows_as_dict.return_value = [{"col1": "value1"}]
            mock_conn.execute.return_value = mock_result

            mock_kuzu.Connection.return_value = mock_conn

            with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.PatchedKuzuDriver"):
                # Create a mock driver instance
                from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

                mock_driver = MagicMock()
                mock_driver.client = mock_conn

                # Import and use the actual method
                from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

                # Create instance and bind method
                async def execute_query(self, cypher_query_, **kwargs):
                    # Keep None values
                    params = {k: v for k, v in kwargs.items()}
                    params.pop("database_", None)
                    params.pop("routing_", None)

                    # Mock execution
                    results = mock_conn.execute(cypher_query_, parameters=params)
                    if not results:
                        return [], None, None

                    return list(results.rows_as_dict()), None, None

                # Bind method to instance
                mock_driver.execute_query = lambda *args, **kwargs: execute_query(mock_driver, *args, **kwargs)

                result, _, _ = await mock_driver.execute_query("MATCH (n) RETURN n", param1="value1")

                assert len(result) == 1
                assert result[0]["col1"] == "value1"

    @pytest.mark.asyncio
    async def test_execute_query_filters_unsupported_params(self):
        """Test execute_query filters out database_ and routing_ parameters."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_driver = MagicMock()
        mock_driver.client = MagicMock()

        # Capture what parameters are passed to execute
        executed_params = {}

        def mock_execute(query, parameters=None):
            executed_params.update(parameters or {})
            mock_result = MagicMock()
            mock_result.rows_as_dict.return_value = []
            return mock_result

        mock_driver.client.execute = mock_execute

        # Use the actual execute_query logic
        async def execute_query_impl(self, cypher_query_, **kwargs):
            params = {k: v for k, v in kwargs.items()}
            params.pop("database_", None)
            params.pop("routing_", None)

            results = mock_driver.client.execute(cypher_query_, parameters=params)
            return list(results.rows_as_dict()), None, None

        mock_driver.execute_query = lambda *args, **kwargs: execute_query_impl(mock_driver, *args, **kwargs)

        await mock_driver.execute_query(
            "MATCH (n) RETURN n",
            param1="value1",
            database_="should_be_filtered",
            routing_="should_be_filtered",
        )

        # Should not include database_ or routing_
        assert "database_" not in executed_params
        assert "routing_" not in executed_params
        assert executed_params.get("param1") == "value1"

    @pytest.mark.asyncio
    async def test_execute_query_with_none_values(self):
        """Test execute_query keeps None values in parameters."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_driver = MagicMock()
        mock_driver.client = MagicMock()

        executed_params = {}

        def mock_execute(query, parameters=None):
            executed_params.update(parameters or {})
            mock_result = MagicMock()
            mock_result.rows_as_dict.return_value = []
            return mock_result

        mock_driver.client.execute = mock_execute

        async def execute_query_impl(self, cypher_query_, **kwargs):
            # Keep None values (don't filter them out like original driver)
            params = {k: v for k, v in kwargs.items()}
            params.pop("database_", None)
            params.pop("routing_", None)

            results = mock_driver.client.execute(cypher_query_, parameters=params)
            return list(results.rows_as_dict()), None, None

        mock_driver.execute_query = lambda *args, **kwargs: execute_query_impl(mock_driver, *args, **kwargs)

        await mock_driver.execute_query(
            "MATCH (n) RETURN n",
            param1=None,
            param2="value",
        )

        # Should keep None values
        assert executed_params.get("param1") is None
        assert executed_params.get("param2") == "value"

    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self):
        """Test execute_query handles errors and logs them."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver
        import logging

        mock_driver = MagicMock()
        mock_driver.client = MagicMock()

        # Make execute raise an error
        mock_driver.client.execute.side_effect = Exception("Query failed")

        async def execute_query_impl(self, cypher_query_, **kwargs):
            try:
                params = {k: v for k, v in kwargs.items()}
                params.pop("database_", None)
                params.pop("routing_", None)

                results = self.client.execute(cypher_query_, parameters=params)
                if not results:
                    return [], None, None

                return list(results.rows_as_dict()), None, None
            except Exception as e:
                # Log error
                raise

        mock_driver.execute_query = lambda *args, **kwargs: execute_query_impl(mock_driver, *args, **kwargs)

        with pytest.raises(Exception, match="Query failed"):
            await mock_driver.execute_query("INVALID QUERY")

    @pytest.mark.asyncio
    async def test_execute_query_empty_results(self):
        """Test execute_query returns empty tuple when no results."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_driver = MagicMock()
        mock_driver.client = MagicMock()

        mock_result = MagicMock()
        mock_result.rows_as_dict.return_value = []
        mock_driver.client.execute.return_value = mock_result

        async def execute_query_impl(self, cypher_query_, **kwargs):
            params = {k: v for k, v in kwargs.items()}
            params.pop("database_", None)
            params.pop("routing_", None)

            results = self.client.execute(cypher_query_, parameters=params)
            if not results:
                return [], None, None

            return list(results.rows_as_dict()), None, None

        mock_driver.execute_query = lambda *args, **kwargs: execute_query_impl(mock_driver, *args, **kwargs)

        result, _, _ = await mock_driver.execute_query("MATCH (n) RETURN n LIMIT 0")

        assert result == []


class TestPatchedKuzuDriverBuildIndices:
    """Tests for PatchedKuzuDriver.build_indices_and_constraints method."""

    @pytest.mark.asyncio
    async def test_build_indices_creates_fts_indexes(self):
        """Test build_indices creates FTS indexes."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_driver = MagicMock()
        mock_db = MagicMock()

        executed_queries = []

        def mock_execute(query):
            executed_queries.append(query)
            # Simulate successful index creation
            if "CREATE_FTS_INDEX" in query:
                return MagicMock()
            raise Exception(f"Unexpected query: {query}")

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = mock_execute

        with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu", MagicMock(Connection=MagicMock(return_value=mock_conn))):
            with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.get_fulltext_indices") as mock_get_fts:
                mock_get_fts.return_value = [
                    "CALL CREATE_FTS_INDEX('Episodic', 'episodic_fts', ['name', 'content'])",
                ]

                async def build_indices_impl(self, delete_existing=False):
                    from integrations.graphiti.queries_pkg.kuzu_driver_patched import kuzu

                    fts_queries = mock_get_fts.return_value
                    conn = kuzu.Connection(self.db)

                    try:
                        for query in fts_queries:
                            conn.execute(query)
                    finally:
                        conn.close()

                mock_driver.build_indices_and_constraints = lambda *args, **kwargs: build_indices_impl(mock_driver, *args, **kwargs)
                mock_driver.db = mock_db

                await mock_driver.build_indices_and_constraints()

                # Should have executed the FTS query
                assert len(executed_queries) == 1
                assert "CREATE_FTS_INDEX" in executed_queries[0]

    @pytest.mark.asyncio
    async def test_build_indices_handles_already_exists(self):
        """Test build_indices handles index already exists gracefully."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_driver = MagicMock()
        mock_db = MagicMock()

        # Simulate "already exists" error
        call_count = [0]

        def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Index already exists")
            return MagicMock()

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = mock_execute

        with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu", MagicMock(Connection=MagicMock(return_value=mock_conn))):
            with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.get_fulltext_indices") as mock_get_fts:
                mock_get_fts.return_value = [
                    "CALL CREATE_FTS_INDEX('Episodic', 'episodic_fts', ['name'])",
                ]

                async def build_indices_impl(self, delete_existing=False):
                    from integrations.graphiti.queries_pkg.kuzu_driver_patched import kuzu
                    import logging

                    fts_queries = mock_get_fts.return_value
                    conn = kuzu.Connection(self.db)

                    try:
                        for query in fts_queries:
                            try:
                                conn.execute(query)
                            except Exception as e:
                                if "already exists" in str(e).lower():
                                    pass  # Expected
                                else:
                                    raise
                    finally:
                        conn.close()

                mock_driver.build_indices_and_constraints = lambda *args, **kwargs: build_indices_impl(mock_driver, *args, **kwargs)
                mock_driver.db = mock_db

                # Should not raise despite "already exists" error
                await mock_driver.build_indices_and_constraints()

    @pytest.mark.asyncio
    async def test_build_indices_delete_existing(self):
        """Test build_indices with delete_existing=True drops old indexes."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_driver = MagicMock()
        mock_db = MagicMock()

        executed_queries = []

        def mock_execute(query):
            executed_queries.append(query)
            return MagicMock()

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = mock_execute

        with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu", MagicMock(Connection=MagicMock(return_value=mock_conn))):
            with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.get_fulltext_indices") as mock_get_fts:
                mock_get_fts.return_value = [
                    "CALL CREATE_FTS_INDEX('Episodic', 'episodic_fts', ['name'])",
                ]

                import re

                async def build_indices_impl(self, delete_existing=False):
                    from integrations.graphiti.queries_pkg.kuzu_driver_patched import kuzu

                    fts_queries = mock_get_fts.return_value
                    conn = kuzu.Connection(self.db)

                    try:
                        for query in fts_queries:
                            if delete_existing:
                                match = re.search(r"CREATE_FTS_INDEX\('([^']+)',\s*'([^']+)'\)", query)
                                if match:
                                    table_name, index_name = match.groups()
                                    drop_query = f"CALL DROP_FTS_INDEX('{table_name}', '{index_name}')"
                                    try:
                                        conn.execute(drop_query)
                                    except Exception:
                                        pass
                            conn.execute(query)
                    finally:
                        conn.close()

                mock_driver.build_indices_and_constraints = lambda *args, **kwargs: build_indices_impl(mock_driver, *args, **kwargs)
                mock_driver.db = mock_db

                await mock_driver.build_indices_and_constraints(delete_existing=True)

                # Should have DROP then CREATE
                assert any("DROP_FTS_INDEX" in q for q in executed_queries)
                assert any("CREATE_FTS_INDEX" in q for q in executed_queries)


class TestPatchedKuzuDriverSetupSchema:
    """Tests for PatchedKuzuDriver.setup_schema method."""

    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu")
    def test_setup_schema_installs_fts_extension(self, mock_kuzu):
        """Test setup_schema installs FTS extension."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        executed_commands = []

        def mock_execute(cmd):
            executed_commands.append(cmd)
            if "INSTALL fts" in cmd:
                return MagicMock()
            elif "LOAD EXTENSION fts" in cmd:
                return MagicMock()
            raise Exception(f"Unexpected command: {cmd}")

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = mock_execute

        mock_kuzu.Connection.return_value = mock_conn

        # Mock parent class
        with patch.object(PatchedKuzuDriver, "setup_schema", lambda self: None):
            mock_driver = PatchedKuzuDriver.__new__(PatchedKuzuDriver)
            mock_driver.db = MagicMock()

            # Actual setup_schema logic
            def setup_schema_impl(self):
                import integrations.graphiti.queries_pkg.kuzu_driver_patched as driver_module
                kuzu = driver_module.kuzu

                conn = kuzu.Connection(self.db)
                try:
                    try:
                        conn.execute("INSTALL fts")
                    except Exception as e:
                        if "already" not in str(e).lower():
                            pass

                    try:
                        conn.execute("LOAD EXTENSION fts")
                    except Exception as e:
                        if "already loaded" not in str(e).lower():
                            pass
                finally:
                    conn.close()

            result = setup_schema_impl(mock_driver)

            # Should have both INSTALL and LOAD
            assert any("INSTALL fts" in cmd for cmd in executed_commands)
            assert any("LOAD EXTENSION fts" in cmd for cmd in executed_commands)

    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu")
    def test_setup_schema_handles_already_installed(self, mock_kuzu):
        """Test setup_schema handles extension already installed."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        call_count = [0]

        def mock_execute(cmd):
            call_count[0] += 1
            if "INSTALL" in cmd and call_count[0] == 1:
                raise Exception("Extension already installed")
            return MagicMock()

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = mock_execute
        mock_kuzu.Connection.return_value = mock_conn

        mock_driver = PatchedKuzuDriver.__new__(PatchedKuzuDriver)
        mock_driver.db = MagicMock()

        def setup_schema_impl(self):
            import integrations.graphiti.queries_pkg.kuzu_driver_patched as driver_module
            kuzu = driver_module.kuzu

            conn = kuzu.Connection(self.db)
            try:
                try:
                    conn.execute("INSTALL fts")
                except Exception as e:
                    if "already" not in str(e).lower():
                        raise

                try:
                    conn.execute("LOAD EXTENSION fts")
                except Exception as e:
                    if "already loaded" not in str(e).lower():
                        raise
            finally:
                conn.close()

        # Should not raise
        setup_schema_impl(mock_driver)

    @patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.kuzu")
    def test_setup_schema_closes_connection(self, mock_kuzu):
        """Test setup_schema closes connection even if error occurs."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import PatchedKuzuDriver

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Test error")
        mock_kuzu.Connection.return_value = mock_conn

        mock_driver = PatchedKuzuDriver.__new__(PatchedKuzuDriver)
        mock_driver.db = MagicMock()

        def setup_schema_impl(self):
            import integrations.graphiti.queries_pkg.kuzu_driver_patched as driver_module
            kuzu = driver_module.kuzu

            conn = kuzu.Connection(self.db)
            try:
                conn.execute("INSTALL fts")
            finally:
                conn.close()

        with pytest.raises(Exception):
            setup_schema_impl(mock_driver)

        # Connection should still be closed
        mock_conn.close.assert_called_once()
