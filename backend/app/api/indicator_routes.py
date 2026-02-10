"""API routes for indicator management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.models.models import User
from app.services.code_validator import validate_indicator_code
from app.services.indicator_loader import discover_indicators, list_indicator_info
from app.services.indicators import (
    BUILTIN_INDICATORS,
    get_builtin_indicator_source,
    register_custom_indicator,
)
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


class CodeValidationRequest(BaseModel):
    """Request body for code validation."""

    code: str


class CodeValidationResponse(BaseModel):
    """Response for code validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


@router.post("/validate", response_model=CodeValidationResponse)
def validate_indicator(data: CodeValidationRequest, current_user: User = Depends(get_current_user)):
    """Validate indicator code without saving it.

    Args:
        data: Code to validate.
        current_user: Current authenticated user.

    Returns:
        Validation result with errors and warnings.
    """
    result = validate_indicator_code(data.code)
    return CodeValidationResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.get("")
def list_indicators(current_user: User = Depends(get_current_user)):
    """List all available indicators (built-in + custom) with metadata.

    Args:
        current_user: Current authenticated user.

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
    custom_indicators = list_indicator_info(current_user.id)
    for indicator in custom_indicators:
        result.append({
            "name": indicator["name"],
            "class_name": indicator["class_name"],
            "type": "custom",
            "docstring": indicator["docstring"],
        })

    return result


@router.get("/files")
def list_indicator_file_names(current_user: User = Depends(get_current_user)):
    """List all indicator file names in the current user's workspace.

    Args:
        current_user: Current authenticated user.

    Returns:
        List of indicator filenames.
    """
    files = list_indicator_files(current_user.id)
    return [{"filename": f.name} for f in files]


@router.get("/builtin/{indicator_name}/source")
def get_builtin_indicator_source_endpoint(indicator_name: str):
    """Get source code of a built-in indicator.

    Args:
        indicator_name: Name of the built-in indicator (e.g., 'sma', 'ema', 'rsi').

    Returns:
        Source code of the indicator function.

    Raises:
        404: If indicator not found or source unavailable.
    """
    source = get_builtin_indicator_source(indicator_name)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail=f"Built-in indicator not found or source unavailable: {indicator_name}"
        )
    return {"indicator_name": indicator_name, "source": source}


@router.get("/files/{filename}")
def get_indicator_file(filename: str, current_user: User = Depends(get_current_user)):
    """Get the contents of an indicator file.

    Args:
        filename: Name of the indicator file.
        current_user: Current authenticated user.

    Returns:
        Indicator file contents.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        content = read_indicator_file(current_user.id, filename)
        return IndicatorFileResponse(filename=filename, content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Indicator file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files")
def create_indicator_file(data: IndicatorFileCreate, current_user: User = Depends(get_current_user)):
    """Create or update an indicator file.

    Args:
        data: Indicator filename and content.
        current_user: Current authenticated user.

    Returns:
        Success message with filename, validation warnings if any.

    Raises:
        400: If filename, content is invalid, or code validation fails.
    """
    try:
        # Validate the code first
        validation_result = validate_indicator_code(data.content)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Code validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                },
            )

        file_path = write_indicator_file(current_user.id, data.filename, data.content)
        response = {
            "message": "Indicator file saved successfully",
            "filename": file_path.name,
        }

        # Include warnings if any
        if validation_result.warnings:
            response["warnings"] = validation_result.warnings

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/files/{filename}")
def update_indicator_file(filename: str, data: IndicatorFileCreate, current_user: User = Depends(get_current_user)):
    """Update an existing indicator file.

    Args:
        filename: Name of the file to update.
        data: New indicator content.
        current_user: Current authenticated user.

    Returns:
        Success message with validation warnings if any.

    Raises:
        400: If filename, content is invalid, or code validation fails.
    """
    try:
        # Ensure the filename in path matches the one in body
        if data.filename != filename:
            raise ValueError("Filename mismatch between path and body")

        # Validate the code first
        validation_result = validate_indicator_code(data.content)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Code validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                },
            )

        write_indicator_file(current_user.id, filename, data.content)
        response = {"message": "Indicator file updated successfully", "filename": filename}

        # Include warnings if any
        if validation_result.warnings:
            response["warnings"] = validation_result.warnings

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/{filename}/rename")
def rename_indicator(filename: str, data: IndicatorFileRename, current_user: User = Depends(get_current_user)):
    """Rename an indicator file.

    Args:
        filename: Current name of the indicator file.
        data: New filename.
        current_user: Current authenticated user.

    Returns:
        Success message with old and new filename.

    Raises:
        404: If file not found.
        409: If file with new name already exists.
        400: If filename is invalid.
    """
    try:
        new_path = rename_indicator_file(current_user.id, filename, data.new_filename)
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
def delete_indicator(filename: str, current_user: User = Depends(get_current_user)):
    """Delete an indicator file.

    Args:
        filename: Name of the indicator file to delete.
        current_user: Current authenticated user.

    Returns:
        Success message.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        delete_indicator_file(current_user.id, filename)
        return {"message": "Indicator file deleted successfully", "filename": filename}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Indicator file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reload")
def reload_indicators(current_user: User = Depends(get_current_user)):
    """Reload custom indicators from current user's workspace (development endpoint).

    This endpoint re-scans the user's indicators directory and updates the registry.
    Useful during development to pick up changes without restarting the server.

    Args:
        current_user: Current authenticated user.

    Returns:
        Success message with count of loaded indicators.
    """
    custom_indicators = discover_indicators(current_user.id)
    for name, cls in custom_indicators.items():
        register_custom_indicator(name, cls)

    return {
        "message": "Indicators reloaded successfully",
        "count": len(custom_indicators),
    }
