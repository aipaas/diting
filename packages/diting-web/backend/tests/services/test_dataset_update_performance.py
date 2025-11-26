"""Performance tests for dataset update operations."""

import pytest
import time
from uuid import uuid4

from diting_web.models.dataset import Dataset, DatasetRow
from diting_web.schemas.dataset import DatasetDataUpdate
from diting_web.services.dataset.dataset_service import DatasetService


class TestDatasetUpdatePerformance:
    """Performance tests for dataset update operations."""

    @pytest.mark.asyncio
    async def test_update_large_dataset_performance(self, db_session):
        """Test that updating a large dataset completes in reasonable time.
        
        This test verifies the O(n²) performance fix by ensuring that:
        1. Updating 100+ rows completes within acceptable time
        2. No O(n²) query pattern exists (would cause timeout)
        
        Before fix: 100 rows × 100 queries = ~10+ seconds
        After fix:  1 query + indexing = <1 second
        """
        # Arrange: Create a dataset with 100 rows
        user_id = uuid4()
        dataset = Dataset(
            name="Performance Test Dataset",
            description="Large dataset for performance testing",
            created_by=user_id,
            row_count=100,
            columns={"columns": ["id", "name", "value"]},
        )
        db_session.add(dataset)
        await db_session.flush()
        
        # Create 100 rows
        rows = []
        for i in range(100):
            row = DatasetRow(
                dataset_id=dataset.id,
                row_index=i,
                data={
                    "id": i,
                    "name": f"Item {i}",
                    "value": f"Value {i}",
                }
            )
            rows.append(row)
        db_session.add_all(rows)
        await db_session.commit()
        await db_session.refresh(dataset)
        
        # Prepare update data (modify 50 rows)
        preview_data = []
        for i in range(50):
            preview_data.append({
                "id": i,
                "name": f"Item {i}",
                "value": f"Updated Value {i}",  # Changed value
            })
        
        data_update = DatasetDataUpdate(
            preview_data=preview_data,
            row_count=100,
        )
        
        # Act: Time the update operation
        service = DatasetService(db_session)
        start_time = time.time()
        
        updated_dataset = await service.update_dataset_data(
            dataset_id=dataset.id,
            data_update=data_update,
            user_id=user_id,
            is_admin=True,
        )
        
        elapsed_time = time.time() - start_time
        
        # Assert: Update should complete quickly (< 2 seconds for 50 updates)
        # Before fix: This would take 5+ seconds due to O(n²) queries
        # After fix: Should complete in < 2 seconds
        assert elapsed_time < 2.0, (
            f"Dataset update took {elapsed_time:.2f}s, expected < 2.0s. "
            f"This indicates the O(n²) performance issue may still exist."
        )
        
        # Verify data was actually updated
        await db_session.refresh(dataset)
        result = await db_session.execute(
            db_session.query(DatasetRow)
            .filter(DatasetRow.dataset_id == dataset.id)
            .order_by(DatasetRow.row_index)
        )
        updated_rows = result.scalars().all()
        
        # Check first 50 rows were updated
        for i in range(50):
            assert updated_rows[i].data["value"] == f"Updated Value {i}"
        
        # Check remaining rows unchanged
        for i in range(50, 100):
            assert updated_rows[i].data["value"] == f"Value {i}"

    @pytest.mark.asyncio
    async def test_update_with_content_matching(self, db_session):
        """Test that reordered data can still be matched correctly.
        
        This verifies the content-hash matching strategy works when
        preview_data is in different order than database rows.
        """
        # Arrange: Create dataset with identifiable rows
        user_id = uuid4()
        dataset = Dataset(
            name="Content Match Test",
            description="Test content-based matching",
            created_by=user_id,
            row_count=10,
            columns={"columns": ["id", "name", "category"]},
        )
        db_session.add(dataset)
        await db_session.flush()
        
        # Create rows with unique identifiers
        original_data = [
            {"id": 1, "name": "Apple", "category": "Fruit"},
            {"id": 2, "name": "Banana", "category": "Fruit"},
            {"id": 3, "name": "Carrot", "category": "Vegetable"},
        ]
        
        for idx, data in enumerate(original_data):
            row = DatasetRow(
                dataset_id=dataset.id,
                row_index=idx,
                data=data,
            )
            db_session.add(row)
        await db_session.commit()
        
        # Prepare reordered update (reverse order)
        preview_data = [
            {"id": 3, "name": "Carrot", "category": "Root Vegetable"},  # Updated
            {"id": 2, "name": "Banana", "category": "Tropical Fruit"},  # Updated
            {"id": 1, "name": "Apple", "category": "Fruit"},             # Unchanged
        ]
        
        data_update = DatasetDataUpdate(
            preview_data=preview_data,
            row_count=3,
        )
        
        # Act: Update with reordered data
        service = DatasetService(db_session)
        await service.update_dataset_data(
            dataset_id=dataset.id,
            data_update=data_update,
            user_id=user_id,
            is_admin=True,
        )
        
        # Assert: Verify correct rows were updated based on content match
        result = await db_session.execute(
            db_session.query(DatasetRow)
            .filter(DatasetRow.dataset_id == dataset.id)
            .order_by(DatasetRow.row_index)
        )
        updated_rows = result.scalars().all()
        
        # Row 0 (Apple) should be unchanged
        assert updated_rows[0].data["category"] == "Fruit"
        
        # Row 1 (Banana) should be updated
        assert updated_rows[1].data["category"] == "Tropical Fruit"
        
        # Row 2 (Carrot) should be updated
        assert updated_rows[2].data["category"] == "Root Vegetable"

    @pytest.mark.asyncio
    async def test_update_partial_rows(self, db_session):
        """Test updating only a subset of rows."""
        # Arrange: Create dataset with 20 rows
        user_id = uuid4()
        dataset = Dataset(
            name="Partial Update Test",
            description="Test partial row updates",
            created_by=user_id,
            row_count=20,
            columns={"columns": ["index", "status"]},
        )
        db_session.add(dataset)
        await db_session.flush()
        
        for i in range(20):
            row = DatasetRow(
                dataset_id=dataset.id,
                row_index=i,
                data={"index": i, "status": "original"},
            )
            db_session.add(row)
        await db_session.commit()
        
        # Update only rows 5, 10, 15
        preview_data = [
            {"index": 5, "status": "updated"},
            {"index": 10, "status": "updated"},
            {"index": 15, "status": "updated"},
        ]
        
        data_update = DatasetDataUpdate(
            preview_data=preview_data,
            row_count=20,
        )
        
        # Act
        service = DatasetService(db_session)
        await service.update_dataset_data(
            dataset_id=dataset.id,
            data_update=data_update,
            user_id=user_id,
            is_admin=True,
        )
        
        # Assert: Only specific rows should be updated
        result = await db_session.execute(
            db_session.query(DatasetRow)
            .filter(DatasetRow.dataset_id == dataset.id)
            .order_by(DatasetRow.row_index)
        )
        all_rows = result.scalars().all()
        
        updated_indices = {5, 10, 15}
        for i, row in enumerate(all_rows):
            if i in updated_indices:
                assert row.data["status"] == "updated", f"Row {i} should be updated"
            else:
                assert row.data["status"] == "original", f"Row {i} should remain original"

    @pytest.mark.asyncio
    async def test_query_count_optimization(self, db_session, monkeypatch):
        """Test that update operation executes minimal database queries.
        
        This test verifies that the optimization reduced query count from O(n) to O(1).
        """
        # Track database query count
        query_count = 0
        original_execute = db_session.execute
        
        async def counting_execute(*args, **kwargs):
            nonlocal query_count
            query_count += 1
            return await original_execute(*args, **kwargs)
        
        monkeypatch.setattr(db_session, "execute", counting_execute)
        
        # Arrange: Create dataset with 50 rows
        user_id = uuid4()
        dataset = Dataset(
            name="Query Count Test",
            created_by=user_id,
            row_count=50,
            columns={"columns": ["id", "value"]},
        )
        db_session.add(dataset)
        await db_session.flush()
        
        for i in range(50):
            row = DatasetRow(
                dataset_id=dataset.id,
                row_index=i,
                data={"id": i, "value": f"Value {i}"},
            )
            db_session.add(row)
        await db_session.commit()
        
        # Reset counter after setup
        query_count = 0
        
        # Prepare update for all 50 rows
        preview_data = [
            {"id": i, "value": f"Updated {i}"}
            for i in range(50)
        ]
        
        data_update = DatasetDataUpdate(
            preview_data=preview_data,
            row_count=50,
        )
        
        # Act
        service = DatasetService(db_session)
        await service.update_dataset_data(
            dataset_id=dataset.id,
            data_update=data_update,
            user_id=user_id,
            is_admin=True,
        )
        
        # Assert: Should have minimal queries (not 50+)
        # Expected queries:
        # 1. Get dataset by ID
        # 2. Select all DatasetRows (the optimized query)
        # 3. Count rows (optional)
        # Total: ~2-4 queries regardless of preview_data size
        #
        # Before fix: Would have 50+ queries (one per preview_row)
        assert query_count < 10, (
            f"Expected < 10 queries, but got {query_count}. "
            f"The O(n²) optimization may not be working correctly."
        )

