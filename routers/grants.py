import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.models.grant import GrantDB, Grant, GrantSearchRequest, GrantSearchResponse # type: ignore
from core.models.pitch import Pitch # type: ignore
from core.auth import get_current_user # type: ignore
from core.models.user import User # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/grants", tags=["Grants"])


@router.post("/search", response_model=GrantSearchResponse)
async def search_grants(
    request: GrantSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    🔍 Search for grants matching the user's pitch profile
    
    Accepts:
        - pitch_id: ID of the uploaded pitch
        - industry: Industry filter
        - stage: Stage filter
        - country: Country filter
        - keywords: Additional keywords
        - max_results: Maximum number of results (default: 20)
    
    Returns:
        - List of matching grants sorted by relevance score
        - Total count
        - Search duration
    
    Example:
        POST /api/v1/grants/search
        {
            "pitch_id": "uuid-123",
            "industry": "Tech",
            "stage": "Seed",
            "country": "US",
            "keywords": ["AI", "SaaS"],
            "max_results": 20
        }
    """
    start_time = time.time()
    
    try:
        # 1. Get the pitch from database
        pitch = db.query(Pitch).filter(Pitch.id == request.pitch_id).first()
        
        if not pitch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pitch with ID {request.pitch_id} not found"
            )
        
        # Verify pitch belongs to current user
        if pitch.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this pitch"
            )
        
        # 2. Build query filters based on request and pitch data
        query = db.query(GrantDB)
        
        # Use request.industry or fallback to pitch.industry
        industry = request.industry or pitch.industry
        if industry:
            query = query.filter(GrantDB.industry_focus.contains([industry]))
        
        # Use request.stage or fallback to pitch.stage
        stage = request.stage or pitch.stage
        if stage:
            query = query.filter(GrantDB.stage_focus.contains([stage]))
        
        # Use request.country or fallback to pitch.country
        country = request.country or pitch.country
        if country:
            query = query.filter(
                (GrantDB.country_focus.contains([country])) |
                (GrantDB.country_focus.contains(["Global"]))
            )
        
        # 3. Execute query and get matching grants
        matching_grants = query.limit(request.max_results).all()
        
        if not matching_grants:
            logger.info(f"No grants found for pitch {request.pitch_id}")
            return GrantSearchResponse(
                total_found=0,
                grants=[],
                search_duration_seconds=time.time() - start_time,
            )
        
        # 4. Calculate relevance scores and convert to response model
        grant_responses = []
        for grant in matching_grants:
            relevance = calculate_relevance_score(
                pitch=pitch,
                grant=grant,
                keywords=request.keywords or []
            )
            
            grant_response = Grant(
                grant_id=grant.grant_id,
                name=grant.name,
                organization=grant.organization,
                portal=grant.portal,
                portal_url=grant.portal_url,
                description=grant.description,
                eligibility=grant.eligibility,
                funding_amount=grant.funding_amount,
                deadline=grant.deadline,
                industry_focus=grant.industry_focus or [],
                stage_focus=grant.stage_focus or [],
                country_focus=grant.country_focus or [],
                vibe=grant.vibe or "innovation",
                relevance_score=relevance,
                source=grant.source or "",
            )
            grant_responses.append(grant_response)
        
        # 5. Sort by relevance score (highest first)
        grant_responses.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 6. Calculate search duration
        search_duration = time.time() - start_time
        
        logger.info(f"✅ Found {len(grant_responses)} grants for pitch {request.pitch_id}")
        
        # 7. Return response
        return GrantSearchResponse(
            total_found=len(grant_responses),
            grants=grant_responses,
            search_duration_seconds=search_duration,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error searching grants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching grants: {str(e)}"
        )


def calculate_relevance_score(pitch, grant, keywords: list[str]) -> float:
    """
    Calculate relevance score between a pitch and a grant (0-1)
    
    Scoring logic:
    - Industry match: +0.30 (30%)
    - Stage match: +0.30 (30%)
    - Country match: +0.20 (20%)
    - Keywords match: +0.20 (20%)
    
    Total: 0-1.0
    """
    score = 0.0
    
    # Industry match (30%)
    if pitch.industry and grant.industry_focus:
        if pitch.industry in grant.industry_focus:
            score += 0.30
    
    # Stage match (30%)
    if pitch.stage and grant.stage_focus:
        if pitch.stage in grant.stage_focus:
            score += 0.30
    
    # Country match (20%)
    if pitch.country and grant.country_focus:
        if pitch.country in grant.country_focus or "Global" in grant.country_focus:
            score += 0.20
    
    # Keywords match (20%)
    if keywords and (grant.industry_focus or grant.keywords):
        grant_keywords = set(grant.industry_focus or []) | set(grant.keywords or [])
        matching_keywords = set(keywords) & grant_keywords
        if matching_keywords:
            keyword_match_ratio = len(matching_keywords) / max(len(keywords), 1)
            score += 0.20 * keyword_match_ratio
    
    return min(score, 1.0)  # Cap at 1.0
