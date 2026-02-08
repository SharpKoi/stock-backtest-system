"""API routes for indicator management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.indicator_loader import discover_indicators, list_indicator_info
from app.services.indicators import BUILTIN_INDICATORS, register_custom_indicator
from app.services.workspace import (
    delete_indicator_file,
    list_indicator_files,
    read_indicator_file,
    rename_indicator_file,
    write_indicator_file,
)

router = APIRouter(prefix="/api/indicators", tags=["indicators"])


class IndicatorFileCreate(BaseModel):
    """Request body for creating/updating an indicator file."""

    filename: str
    content: str


class IndicatorFileResponse(BaseModel):
    """Response containing indicator file details."""

    filename: str
    content: str


class IndicatorFileRename(BaseModel):
    """Request body for renaming an indicator file."""

    new_filename: str


@router.get("")
def list_indicators():
    """List all available indicators (built-in + custom) with metadata.

    Returns:
        List of indicators with metadata. Built-in indicators have 'type': 'builtin',
        custom indicators have 'type': 'custom'.
    """
    result = []

    # Add built-in indicators
    for name in BUILTIN_INDICATORS.keys():
        result.append({
            "name": name,
            "type": "builtin",
            "docstring": f"Built-in {name.upper()} indicator",
        })

    # Add custom indicators
    custom_indicators = list_indicator_info()
    for indicator in custom_indicators:
        result.append({
            "name": indicator["name"],
            "class_name": indicator["class_name"],
            "type": "custom",
            "docstring": indicator["docstring"],
        })

    return result


@router.get("/files")
def list_indicator_file_names():
    """List all indicator file names in the workspace."""
    files = list_indicator_files()
    return [{"filename": f.name} for f in files]


@router.get("/files/{filename}")
def get_indicator_file(filename: str):
    """Get the contents of an indicator file.

    Args:
        filename: Name of the indicator file.

    Returns:
        Indicator file contents.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        content = read_indicator_file(filename)
        return IndicatorFileResponse(filename=filename, content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Indicator file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files")
def create_indicator_file(data: IndicatorFileCreate):
    """Create or update an indicator file.

    Args:
        data: Indicator filename and content.

    Returns:
        Success message with filename.

    Raises:
        400: If filename or content is invalid.
    """
    try:
        file_path = write_indicator_file(data.filename, data.content)
        return {
            "message": "Indicator file saved successfully",
            "filename": file_path.name,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/files/{filename}")
def update_indicator_file(filename: str, data: IndicatorFileCreate):
    """Update an existing indicator file.

    Args:
        filename: Name of the file to update.
        data: New indicator content.

    Returns:
        Success message.

    Raises:
        400: If filename or content is invalid.
    """
    try:
        # Ensure the filename in path matches the one in body
        if data.filename != filename:
            raise ValueError("Filename mismatch between path and body")

        write_indicator_file(filename, data.content)
        return {"message": "Indicator file updated successfully", "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/{filename}/rename")
def rename_indicator(filename: str, data: IndicatorFileRename):
    """Rename an indicator file.

    Args:
        filename: Current name of the indicator file.
        data: New filename.

    Returns:
        Success message with old and new filename.

    Raises:
        404: If file not found.
        409: If file with new name already exists.
        400: If filename is invalid.
    """
    try:
        new_path = rename_indicator_file(filename, data.new_filename)
        return {
            "message": "Indicator file renamed successfully",
            "old_filename": filename,
            "new_filename": new_path.name,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Indicator file not found: {filename}")
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/files/{filename}")
def delete_indicator(filename: str):
    """Delete an indicator file.

    Args:
        filename: Name of the indicator file to delete.

    Returns:
        Success message.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        delete_indicator_file(filename)
        return {"message": "Indicator file deleted successfully", "filename": filename}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Indicator file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reload")
def reload_indicators():
    """Reload custom indicators from workspace (development endpoint).

    This endpoint re-scans the indicators directory and updates the registry.
    Useful during development to pick up changes without restarting the server.

    Returns:
        Success message with count of loaded indicators.
    """
    custom_indicators = discover_indicators()
    for name, cls in custom_indicators.items():
        register_custom_indicator(name, cls)

    return {
        "message": "Indicators reloaded successfully",
        "count": len(custom_indicators),
    }
