"""API routes for strategy management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.models.models import User
from app.services.code_validator import validate_strategy_code
from app.services.strategy_loader import list_strategy_info
from app.services.workspace import (
    delete_strategy_file,
    list_strategy_files,
    read_strategy_file,
    rename_strategy_file,
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


class StrategyFileRename(BaseModel):
    """Request body for renaming a strategy file."""

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
def validate_strategy(data: CodeValidationRequest, current_user: User = Depends(get_current_user)):
    """Validate strategy code without saving it.

    Args:
        data: Code to validate.
        current_user: Current authenticated user.

    Returns:
        Validation result with errors and warnings.
    """
    result = validate_strategy_code(data.code)
    return CodeValidationResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.get("")
def list_strategies(current_user: User = Depends(get_current_user)):
    """List all available strategies with metadata for the current user."""
    return list_strategy_info(current_user.id)


@router.get("/files")
def list_strategy_file_names(current_user: User = Depends(get_current_user)):
    """List all strategy file names in the current user's workspace."""
    files = list_strategy_files(current_user.id)
    return [{"filename": f.name} for f in files]


@router.get("/files/{filename}")
def get_strategy_file(filename: str, current_user: User = Depends(get_current_user)):
    """Get the contents of a strategy file.

    Args:
        filename: Name of the strategy file.
        current_user: Current authenticated user.

    Returns:
        Strategy file contents.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        content = read_strategy_file(current_user.id, filename)
        return StrategyFileResponse(filename=filename, content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files")
def create_strategy_file(data: StrategyFileCreate, current_user: User = Depends(get_current_user)):
    """Create or update a strategy file.

    Args:
        data: Strategy filename and content.
        current_user: Current authenticated user.

    Returns:
        Success message with filename, validation warnings if any.

    Raises:
        400: If filename, content is invalid, or code validation fails.
    """
    try:
        # Validate the code first
        validation_result = validate_strategy_code(data.content)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Code validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                },
            )

        file_path = write_strategy_file(current_user.id, data.filename, data.content)
        response = {
            "message": "Strategy file saved successfully",
            "filename": file_path.name,
        }

        # Include warnings if any
        if validation_result.warnings:
            response["warnings"] = validation_result.warnings

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/files/{filename}")
def update_strategy_file(filename: str, data: StrategyFileCreate, current_user: User = Depends(get_current_user)):
    """Update an existing strategy file.

    Args:
        filename: Name of the file to update.
        data: New strategy content.
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
        validation_result = validate_strategy_code(data.content)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Code validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                },
            )

        write_strategy_file(current_user.id, filename, data.content)
        response = {"message": "Strategy file updated successfully", "filename": filename}

        # Include warnings if any
        if validation_result.warnings:
            response["warnings"] = validation_result.warnings

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/{filename}/rename")
def rename_strategy(filename: str, data: StrategyFileRename, current_user: User = Depends(get_current_user)):
    """Rename a strategy file.

    Args:
        filename: Current name of the strategy file.
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
        new_path = rename_strategy_file(current_user.id, filename, data.new_filename)
        return {
            "message": "Strategy file renamed successfully",
            "old_filename": filename,
            "new_filename": new_path.name,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy file not found: {filename}")
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/files/{filename}")
def delete_strategy(filename: str, current_user: User = Depends(get_current_user)):
    """Delete a strategy file.

    Args:
        filename: Name of the strategy file to delete.
        current_user: Current authenticated user.

    Returns:
        Success message.

    Raises:
        404: If file not found.
        400: If filename is invalid.
    """
    try:
        delete_strategy_file(current_user.id, filename)
        return {"message": "Strategy file deleted successfully", "filename": filename}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy file not found: {filename}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
