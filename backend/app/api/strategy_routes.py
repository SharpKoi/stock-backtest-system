"""API routes for strategy management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.strategy_loader import list_strategy_info
from app.services.workspace import (
    delete_strategy_file,
    list_strategy_files,
    read_strategy_file,
    write_strategy_file,
)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class StrategyFileCreate(BaseModel):
    """Request body for creating/updating a strategy file."""

    filename: str
    content: str


class StrategyFileResponse(BaseModel):
    """Response containing strategy file details."""

    filename: str
    content: str


@router.get("")
def list_strategies():
    """List all available strategies with metadata."""
    return list_strategy_info()


@router.get("/files")
def list_strategy_file_names():
    """List all strategy file names in the workspace."""
    files = list_strategy_files()
    return [{"filename": f.name} for f in files]


@router.get("/files/{filename}")
def get_strategy_file(filename: str):
    """Get the contents of a strategy file.

    Args:
        filename: Name of the strategy file.

    Returns:
        Strategy file contents.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        content = read_strategy_file(filename)
        return StrategyFileResponse(filename=filename, content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files")
def create_strategy_file(data: StrategyFileCreate):
    """Create or update a strategy file.

    Args:
        data: Strategy filename and content.

    Returns:
        Success message with filename.

    Raises:
        400: If filename or content is invalid.
    """
    try:
        file_path = write_strategy_file(data.filename, data.content)
        return {
            "message": "Strategy file saved successfully",
            "filename": file_path.name,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/files/{filename}")
def update_strategy_file(filename: str, data: StrategyFileCreate):
    """Update an existing strategy file.

    Args:
        filename: Name of the file to update.
        data: New strategy content.

    Returns:
        Success message.

    Raises:
        400: If filename or content is invalid.
    """
    try:
        # Ensure the filename in path matches the one in body
        if data.filename != filename:
            raise ValueError("Filename mismatch between path and body")

        write_strategy_file(filename, data.content)
        return {"message": "Strategy file updated successfully", "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/files/{filename}")
def delete_strategy(filename: str):
    """Delete a strategy file.

    Args:
        filename: Name of the strategy file to delete.

    Returns:
        Success message.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        delete_strategy_file(filename)
        return {"message": "Strategy file deleted successfully", "filename": filename}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
