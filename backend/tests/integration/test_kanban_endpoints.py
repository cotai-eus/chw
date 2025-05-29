"""
Integration tests for Kanban board management API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestKanbanEndpoints:
    """Test Kanban board management API endpoints."""
    
    def test_get_boards_list(self, client: TestClient, auth_headers):
        """Test getting list of Kanban boards."""
        response = client.get("/api/v1/kanban/boards/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_board_success(self, client: TestClient, auth_headers, test_company):
        """Test successful Kanban board creation."""
        board_data = {
            "name": "Test Kanban Board",
            "description": "Board for testing purposes",
            "company_id": test_company.id,
            "columns": [
                {"name": "To Do", "order": 1},
                {"name": "In Progress", "order": 2},
                {"name": "Done", "order": 3}
            ]
        }
        
        response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == board_data["name"]
        assert data["description"] == board_data["description"]
        assert data["company_id"] == board_data["company_id"]
        assert len(data["columns"]) == 3
    
    def test_get_board_by_id(self, client: TestClient, auth_headers, test_company):
        """Test getting specific Kanban board by ID."""
        # First create a board
        board_data = {
            "name": "Test Board for Get",
            "description": "Test board",
            "company_id": test_company.id,
            "columns": [
                {"name": "Backlog", "order": 1},
                {"name": "Active", "order": 2}
            ]
        }
        
        create_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        created_board = create_response.json()
        
        # Get the board
        response = client.get(f"/api/v1/kanban/boards/{created_board['id']}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_board["id"]
        assert data["name"] == board_data["name"]
    
    def test_get_nonexistent_board(self, client: TestClient, auth_headers):
        """Test getting non-existent Kanban board."""
        response = client.get("/api/v1/kanban/boards/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_update_board_success(self, client: TestClient, auth_headers, test_company):
        """Test successful Kanban board update."""
        # Create board first
        board_data = {
            "name": "Original Board Name",
            "description": "Original description",
            "company_id": test_company.id,
            "columns": [{"name": "Column 1", "order": 1}]
        }
        
        create_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        created_board = create_response.json()
        
        # Update board
        update_data = {
            "name": "Updated Board Name",
            "description": "Updated description"
        }
        
        response = client.put(
            f"/api/v1/kanban/boards/{created_board['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_delete_board_success(self, client: TestClient, auth_headers, test_company):
        """Test successful Kanban board deletion."""
        # Create board first
        board_data = {
            "name": "Board to Delete",
            "description": "This board will be deleted",
            "company_id": test_company.id,
            "columns": [{"name": "Column 1", "order": 1}]
        }
        
        create_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        created_board = create_response.json()
        
        # Delete board
        response = client.delete(f"/api/v1/kanban/boards/{created_board['id']}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify board is deleted
        get_response = client.get(f"/api/v1/kanban/boards/{created_board['id']}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_get_cards_list(self, client: TestClient, auth_headers):
        """Test getting list of Kanban cards."""
        response = client.get("/api/v1/kanban/cards/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_card_success(self, client: TestClient, auth_headers, test_company):
        """Test successful Kanban card creation."""
        # First create a board with columns
        board_data = {
            "name": "Board for Cards",
            "description": "Board to test cards",
            "company_id": test_company.id,
            "columns": [
                {"name": "To Do", "order": 1},
                {"name": "Done", "order": 2}
            ]
        }
        
        board_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        board = board_response.json()
        column_id = board["columns"][0]["id"]
        
        # Create card
        card_data = {
            "title": "Test Card",
            "description": "This is a test card",
            "column_id": column_id,
            "board_id": board["id"],
            "priority": "medium",
            "assignee_id": None,
            "due_date": "2024-12-31T23:59:59"
        }
        
        response = client.post("/api/v1/kanban/cards/", json=card_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == card_data["title"]
        assert data["description"] == card_data["description"]
        assert data["column_id"] == card_data["column_id"]
        assert data["priority"] == card_data["priority"]
    
    def test_get_card_by_id(self, client: TestClient, auth_headers, test_company):
        """Test getting specific Kanban card by ID."""
        # Create board and card first
        board_data = {
            "name": "Board for Card Test",
            "company_id": test_company.id,
            "columns": [{"name": "Test Column", "order": 1}]
        }
        
        board_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        board = board_response.json()
        column_id = board["columns"][0]["id"]
        
        card_data = {
            "title": "Get Card Test",
            "description": "Card for get test",
            "column_id": column_id,
            "board_id": board["id"],
            "priority": "high"
        }
        
        create_response = client.post("/api/v1/kanban/cards/", json=card_data, headers=auth_headers)
        created_card = create_response.json()
        
        # Get the card
        response = client.get(f"/api/v1/kanban/cards/{created_card['id']}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_card["id"]
        assert data["title"] == card_data["title"]
    
    def test_update_card_success(self, client: TestClient, auth_headers, test_company):
        """Test successful Kanban card update."""
        # Create board and card first
        board_data = {
            "name": "Board for Update Test",
            "company_id": test_company.id,
            "columns": [
                {"name": "Column 1", "order": 1},
                {"name": "Column 2", "order": 2}
            ]
        }
        
        board_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        board = board_response.json()
        column_id = board["columns"][0]["id"]
        
        card_data = {
            "title": "Original Card Title",
            "description": "Original description",
            "column_id": column_id,
            "board_id": board["id"],
            "priority": "low"
        }
        
        create_response = client.post("/api/v1/kanban/cards/", json=card_data, headers=auth_headers)
        created_card = create_response.json()
        
        # Update card
        update_data = {
            "title": "Updated Card Title",
            "description": "Updated description",
            "priority": "high"
        }
        
        response = client.put(
            f"/api/v1/kanban/cards/{created_card['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["priority"] == update_data["priority"]
    
    def test_move_card_between_columns(self, client: TestClient, auth_headers, test_company):
        """Test moving card between columns."""
        # Create board with multiple columns
        board_data = {
            "name": "Board for Move Test",
            "company_id": test_company.id,
            "columns": [
                {"name": "To Do", "order": 1},
                {"name": "In Progress", "order": 2},
                {"name": "Done", "order": 3}
            ]
        }
        
        board_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        board = board_response.json()
        from_column_id = board["columns"][0]["id"]
        to_column_id = board["columns"][1]["id"]
        
        # Create card in first column
        card_data = {
            "title": "Card to Move",
            "description": "This card will be moved",
            "column_id": from_column_id,
            "board_id": board["id"],
            "priority": "medium"
        }
        
        create_response = client.post("/api/v1/kanban/cards/", json=card_data, headers=auth_headers)
        created_card = create_response.json()
        
        # Move card to second column
        move_data = {
            "column_id": to_column_id,
            "position": 0
        }
        
        response = client.post(
            f"/api/v1/kanban/cards/{created_card['id']}/move", 
            json=move_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["column_id"] == to_column_id
    
    def test_delete_card_success(self, client: TestClient, auth_headers, test_company):
        """Test successful Kanban card deletion."""
        # Create board and card first
        board_data = {
            "name": "Board for Delete Test",
            "company_id": test_company.id,
            "columns": [{"name": "Test Column", "order": 1}]
        }
        
        board_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        board = board_response.json()
        column_id = board["columns"][0]["id"]
        
        card_data = {
            "title": "Card to Delete",
            "description": "This card will be deleted",
            "column_id": column_id,
            "board_id": board["id"],
            "priority": "low"
        }
        
        create_response = client.post("/api/v1/kanban/cards/", json=card_data, headers=auth_headers)
        created_card = create_response.json()
        
        # Delete card
        response = client.delete(f"/api/v1/kanban/cards/{created_card['id']}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify card is deleted
        get_response = client.get(f"/api/v1/kanban/cards/{created_card['id']}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_get_board_cards(self, client: TestClient, auth_headers, test_company):
        """Test getting all cards for a specific board."""
        # Create board and cards
        board_data = {
            "name": "Board with Cards",
            "company_id": test_company.id,
            "columns": [{"name": "Test Column", "order": 1}]
        }
        
        board_response = client.post("/api/v1/kanban/boards/", json=board_data, headers=auth_headers)
        board = board_response.json()
        column_id = board["columns"][0]["id"]
        
        # Create multiple cards
        for i in range(3):
            card_data = {
                "title": f"Test Card {i}",
                "description": f"Description {i}",
                "column_id": column_id,
                "board_id": board["id"],
                "priority": "medium"
            }
            client.post("/api/v1/kanban/cards/", json=card_data, headers=auth_headers)
        
        # Get all cards for the board
        response = client.get(f"/api/v1/kanban/boards/{board['id']}/cards", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
    
    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to Kanban endpoints."""
        response = client.get("/api/v1/kanban/boards/")
        assert response.status_code == 401
    
    def test_company_isolation(self, client: TestClient, auth_headers, test_company):
        """Test that Kanban boards are isolated by company."""
        response = client.get("/api/v1/kanban/boards/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # All boards should belong to the same company as the authenticated user
        for board in data:
            if "company_id" in board:
                assert board["company_id"] == test_company.id
    
    @pytest.mark.slow
    def test_kanban_performance(self, client: TestClient, auth_headers):
        """Test Kanban endpoint performance."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/kanban/boards/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second


@pytest.mark.integration
@pytest.mark.asyncio
class TestKanbanEndpointsAsync:
    """Test Kanban endpoints with async client."""
    
    async def test_kanban_workflow_async(self, async_client: AsyncClient, auth_headers, test_company):
        """Test complete Kanban workflow asynchronously."""
        # Create board
        board_data = {
            "name": "Async Kanban Board",
            "description": "Board created asynchronously",
            "company_id": test_company.id,
            "columns": [
                {"name": "Backlog", "order": 1},
                {"name": "Sprint", "order": 2},
                {"name": "Review", "order": 3},
                {"name": "Done", "order": 4}
            ]
        }
        
        board_response = await async_client.post(
            "/api/v1/kanban/boards/", 
            json=board_data, 
            headers=auth_headers
        )
        
        assert board_response.status_code == 201
        board = board_response.json()
        
        # Create multiple cards concurrently
        import asyncio
        
        card_data_list = [
            {
                "title": f"Async Card {i}",
                "description": f"Card {i} created asynchronously",
                "column_id": board["columns"][0]["id"],
                "board_id": board["id"],
                "priority": "medium"
            }
            for i in range(5)
        ]
        
        # Create cards concurrently
        tasks = [
            async_client.post("/api/v1/kanban/cards/", json=data, headers=auth_headers)
            for data in card_data_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_creates = [r for r in results if not isinstance(r, Exception) and r.status_code == 201]
        assert len(successful_creates) == 5
        
        # Get all cards
        cards_response = await async_client.get(
            f"/api/v1/kanban/boards/{board['id']}/cards", 
            headers=auth_headers
        )
        
        assert cards_response.status_code == 200
        cards_data = cards_response.json()
        assert len(cards_data) == 5
