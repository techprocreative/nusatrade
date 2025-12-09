"""Admin settings API endpoints for runtime configuration."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import encrypt_setting_value, decrypt_setting_value
from app.models.settings import SystemSetting, SettingCategory
from app.models.user import User


router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class SettingUpdate(BaseModel):
    """Request model for updating a setting."""
    value: Optional[str] = None
    category: SettingCategory
    is_encrypted: bool = False
    description: Optional[str] = None


class SettingResponse(BaseModel):
    """Response model for a setting."""
    key: str
    value: Optional[str]  # Masked if encrypted
    category: SettingCategory
    is_encrypted: bool
    description: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]

    class Config:
        from_attributes = True


class TestConnectionResponse(BaseModel):
    """Response model for connection tests."""
    success: bool
    message: str
    details: Optional[dict] = None


# ============================================
# Settings Endpoints
# ============================================

@router.get("/settings", response_model=List[SettingResponse])
def list_settings(
    category: Optional[SettingCategory] = None,
    current_user: User = Depends(deps.get_current_admin_user),
    db: Session = Depends(deps.get_db),
):
    """List all system settings (admin only)."""
    query = db.query(SystemSetting).filter(SystemSetting.is_active == True)
    
    if category:
        query = query.filter(SystemSetting.category == category)
    
    settings = query.all()
    
    # Mask encrypted values for security
    result = []
    for s in settings:
        result.append(SettingResponse(
            key=s.key,
            value="***ENCRYPTED***" if s.is_encrypted else s.value,
            category=s.category,
            is_encrypted=s.is_encrypted,
            description=s.description,
            updated_at=s.updated_at,
            updated_by=s.updated_by,
        ))
    
    return result


@router.get("/settings/{key}", response_model=SettingResponse)
def get_setting(
    key: str,
    current_user: User = Depends(deps.get_current_admin_user),
    db: Session = Depends(deps.get_db),
):
    """Get a specific setting (admin only)."""
    setting = db.query(SystemSetting).filter(
        SystemSetting.key == key,
        SystemSetting.is_active == True
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    return SettingResponse(
        key=setting.key,
        value="***ENCRYPTED***" if setting.is_encrypted else setting.value,
        category=setting.category,
        is_encrypted=setting.is_encrypted,
        description=setting.description,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by,
    )


@router.put("/settings/{key}")
def update_setting(
    key: str,
    update: SettingUpdate,
    current_user: User = Depends(deps.get_current_admin_user),
    db: Session = Depends(deps.get_db),
):
    """Update a system setting (admin only)."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    
    if not setting:
        # Create new setting
        setting = SystemSetting(key=key)
        db.add(setting)
    
    # Encrypt value if needed
    if update.is_encrypted and update.value:
        setting.value = encrypt_setting_value(update.value)
    else:
        setting.value = update.value
    
    setting.category = update.category
    setting.is_encrypted = update.is_encrypted
    setting.description = update.description
    setting.updated_by = str(current_user.id)
    
    db.commit()
    db.refresh(setting)
    
    # Invalidate cache and reload LLM client if AI provider settings changed
    if update.category == SettingCategory.AI_PROVIDER:
        try:
            from app.core.settings_service import SettingsService
            from app.api.v1.ai import llm_client
            
            # Invalidate cache
            service = SettingsService(db)
            service.invalidate_cache(key)
            
            # Reload LLM client with new config
            llm_client.reload_config(db)
        except Exception as e:
            # Log error but don't fail the update
            import logging
            logging.warning(f"Failed to reload LLM client: {e}")
    
    return {
        "message": "Setting updated successfully",
        "key": key,
    }


@router.delete("/settings/{key}")
def delete_setting(
    key: str,
    current_user: User = Depends(deps.get_current_admin_user),
    db: Session = Depends(deps.get_db),
):
    """Soft delete a setting (admin only)."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    setting.is_active = False
    setting.updated_by = str(current_user.id)
    db.commit()
    
    return {"message": "Setting deleted successfully"}


# ============================================
# Connection Test Endpoints
# ============================================

@router.post("/test-llm", response_model=TestConnectionResponse)
async def test_llm_connection(
    current_user: User = Depends(deps.get_current_admin_user),
    db: Session = Depends(deps.get_db),
):
    """Test LLM connection with current settings."""
    try:
        # Get LLM settings from database
        api_key_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "llm_api_key",
            SystemSetting.is_active == True
        ).first()
        
        base_url_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "llm_base_url",
            SystemSetting.is_active == True
        ).first()
        
        model_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "llm_model",
            SystemSetting.is_active == True
        ).first()
        
        if not api_key_setting or not api_key_setting.value:
            return TestConnectionResponse(
                success=False,
                message="LLM API key not configured"
            )
        
        # Decrypt API key
        api_key = decrypt_setting_value(api_key_setting.value) if api_key_setting.is_encrypted else api_key_setting.value
        base_url = base_url_setting.value if base_url_setting else None
        model = model_setting.value if model_setting else "gpt-4-turbo-preview"
        
        # Test connection
        import openai
        import time
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
        )
        response_time = int((time.time() - start_time) * 1000)
        
        return TestConnectionResponse(
            success=True,
            message="LLM connection successful",
            details={
                "provider": base_url or "OpenAI",
                "model": model,
                "response_time_ms": response_time,
            }
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"LLM connection failed: {str(e)}"
        )


@router.post("/test-redis", response_model=TestConnectionResponse)
async def test_redis_connection(
    current_user: User = Depends(deps.get_current_admin_user),
    db: Session = Depends(deps.get_db),
):
    """Test Redis connection with current settings."""
    try:
        redis_url_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "redis_url",
            SystemSetting.is_active == True
        ).first()
        
        if not redis_url_setting or not redis_url_setting.value:
            return TestConnectionResponse(
                success=False,
                message="Redis URL not configured"
            )
        
        redis_url = decrypt_setting_value(redis_url_setting.value) if redis_url_setting.is_encrypted else redis_url_setting.value
        
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        
        return TestConnectionResponse(
            success=True,
            message="Redis connection successful"
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Redis connection failed: {str(e)}"
        )
