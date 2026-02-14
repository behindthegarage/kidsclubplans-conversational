

# =============================================================================
# PHASE 4: Generation & Novelty Tools
# =============================================================================

@register_tool("blend_activities")
def blend_activities_tool(
    activity_ids_or_titles: List[str],
    blend_focus: str = "balanced",
    target_age_group: Optional[str] = None,
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a novel activity by blending 2+ existing activities.
    Combines the best elements of each into something new.
    """
    vector_store = _context.get("vector_store") if _context else None
    
    # Fetch source activities
    source_activities = []
    
    if vector_store:
        from .rag import search_activities as rag_search
        
        for identifier in activity_ids_or_titles:
            # Try searching by title or ID
            results = rag_search(vector_store, identifier, limit=3)
            if results:
                # Take best match
                source_activities.append(results[0])
    
    if len(source_activities) < 2:
        return {
            "success": False,
            "error": f"Could only find {len(source_activities)} of {len(activity_ids_or_titles)} requested activities. Need at least 2 to blend.",
            "found_activities": [a.get("title") for a in source_activities]
        }
    
    # Extract elements from each activity
    titles = [a.get("title", "") for a in source_activities]
    descriptions = [a.get("description", "") for a in source_activities if a.get("description")]
    all_supplies = []
    for act in source_activities:
        if act.get("supplies"):
            all_supplies.extend([s.strip() for s in act.get("supplies").split(",") if s.strip()])
    all_supplies = list(set(all_supplies))  # Deduplicate
    
    # Determine activity types
    types = [a.get("type", "") for a in source_activities if a.get("type")]
    
    # Create blend based on focus
    focus_emphasis = {
        "physical": "active movement and physical engagement",
        "creative": "artistic expression and imagination",
        "educational": "learning objectives and skill development",
        "social": "collaboration and social interaction",
        "balanced": "multiple developmental domains"
    }
    
    # Generate blended title
    title_parts = [t.split()[0] for t in titles[:2]]  # Take first word of first two titles
    blended_title = f"{title_parts[0]}-{title_parts[1]} Fusion"
    
    # Determine target age
    age = target_age_group
    if not age and source_activities:
        age = source_activities[0].get("development_age_group", "6-10 years")
    
    # Generate description that combines elements
    combined_desc = " ".join(descriptions[:2]) if descriptions else ""
    
    blended_activity = {
        "title": blended_title,
        "description": f"A creative fusion activity combining elements from {', '.join(titles)}. Focus on {focus_emphasis.get(blend_focus, 'engaging play')}.",
        "source_activities": titles,
        "target_age": age,
        "duration_minutes": 30,  # Default, could be averaged from sources
        "supplies_needed": ", ".join(all_supplies[:6]) if all_supplies else "Varies by implementation",
        "instructions": f"1. Set up combining elements from {titles[0]} and {titles[1]}. 2. Guide children through the integrated activity. 3. Encourage creative adaptation. 4. Debrief on what they discovered combining both activities.",
        "indoor_outdoor": "either",
        "blend_focus": blend_focus,
        "source_types": types,
        "generated": True,
        "novelty_score": 0.85  # High novelty as it's a blend
    }
    
    return {
        "success": True,
        "blended_activity": blended_activity,
        "source_count": len(source_activities),
        "sources": titles
    }


@register_tool("analyze_database_gaps")
def analyze_database_gaps_tool(
    focus_areas: Optional[List[str]] = None,
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Analyze the activity database for gaps in coverage.
    Returns suggestions for what activities to add.
    """
    vector_store = _context.get("vector_store") if _context else None
    
    # Define expected coverage areas
    expected_age_groups = ["5-6 years", "7-8 years", "9-10 years", "11-12 years"]
    expected_themes = ["winter", "spring", "summer", "fall", "holiday", "space", "animals", "sports", "art", "science", "nature"]
    expected_types = ["Art", "Craft", "Science", "Physical", "Game", "Music", "Drama", "STEM"]
    expected_durations = [15, 30, 45, 60]
    
    gaps = []
    coverage = {
        "age_groups": {},
        "themes": {},
        "types": {},
        "low_prep": 0
    }
    
    if vector_store:
        from .rag import search_activities as rag_search
        
        # Sample each age group
        for age in expected_age_groups:
            try:
                results = rag_search(vector_store, f"activities for {age}", limit=20)
                count = len(results)
                coverage["age_groups"][age] = count
                if count < 5:
                    gaps.append({
                        "type": "age_group",
                        "area": age,
                        "current_count": count,
                        "severity": "high" if count < 3 else "medium",
                        "suggestion": f"Add more activities specifically for {age}"
                    })
            except Exception as e:
                logger.warning(f"Gap analysis failed for age {age}: {e}")
        
        # Sample themes
        for theme in expected_themes:
            try:
                results = rag_search(vector_store, f"{theme} activities", limit=10)
                count = len(results)
                coverage["themes"][theme] = count
                if count < 3:
                    gaps.append({
                        "type": "theme",
                        "area": theme,
                        "current_count": count,
                        "severity": "high" if count == 0 else "medium",
                        "suggestion": f"Add {theme}-themed activities"
                    })
            except Exception as e:
                logger.warning(f"Gap analysis failed for theme {theme}: {e}")
        
        # Check low-prep specifically
        try:
            results = rag_search(vector_store, "low prep easy setup minimal materials", limit=20)
            coverage["low_prep"] = len(results)
            if len(results) < 10:
                gaps.append({
                    "type": "prep_level",
                    "area": "low_prep",
                    "current_count": len(results),
                    "severity": "medium",
                    "suggestion": "Add more low-prep activities that require minimal setup"
                })
        except Exception as e:
            logger.warning(f"Gap analysis failed for low_prep: {e}")
        
        # Focus areas if specified
        if focus_areas:
            for area in focus_areas:
                try:
                    results = rag_search(vector_store, area, limit=10)
                    if len(results) < 3:
                        gaps.append({
                            "type": "focus_area",
                            "area": area,
                            "current_count": len(results),
                            "severity": "high" if len(results) == 0 else "medium",
                            "suggestion": f"Add activities related to '{area}'"
                        })
                except Exception as e:
                    logger.warning(f"Gap analysis failed for focus area {area}: {e}")
    
    # Sort gaps by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: severity_order.get(x["severity"], 3))
    
    return {
        "success": True,
        "gaps_found": len(gaps),
        "gaps": gaps[:10],  # Top 10 gaps
        "coverage_summary": coverage,
        "recommendations": [
            f"Priority: {g['suggestion']}" for g in gaps[:5]
        ]
    }


@register_tool("generate_from_supplies")
def generate_from_supplies_tool(
    supplies: List[str],
    age_group: str,
    duration_minutes: Optional[int] = None,
    indoor_outdoor: Optional[str] = "either",
    count: int = 3,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate activity ideas based ONLY on available supplies.
    Supply-first activity generation.
    """
    supplies_lower = [s.lower() for s in supplies]
    duration = duration_minutes or 30
    
    # Supply-based activity templates
    supply_combinations = {
        "paper_plates": {
            "matches": ["paper plate", "plates"],
            "activities": [
                {
                    "title": "Paper Plate Frisbees",
                    "description": f"Decorate paper plates, then use them for indoor frisbee toss games. Perfect for {age_group}.",
                    "supplies_needed": ["paper plates", "markers/crayons", "optional: stickers"],
                    "instructions": "1. Decorate plates with designs. 2. Practice tossing to partners. 3. Create target zones for accuracy games.",
                    "duration_minutes": duration
                },
                {
                    "title": "Paper Plate Masks",
                    "description": "Create character masks by cutting eye holes and decorating plates.",
                    "supplies_needed": ["paper plates", "scissors", "markers", "string/elastic"],
                    "instructions": "1. Cut eye holes. 2. Decorate as animals/characters. 3. Attach string to wear. 4. Have a mask parade.",
                    "duration_minutes": duration
                }
            ]
        },
        "balloons": {
            "matches": ["balloon"],
            "activities": [
                {
                    "title": "Balloon Keep-Up",
                    "description": "Cooperative game keeping balloons in the air without letting them touch the ground.",
                    "supplies_needed": ["balloons"],
                    "instructions": "1. Inflate balloons. 2. Groups work together to keep all balloons up. 3. Add challenges: no hands, one finger only, etc.",
                    "duration_minutes": duration
                },
                {
                    "title": "Balloon Tennis",
                    "description": "Play tennis using balloons and paper plate paddles.",
                    "supplies_needed": ["balloons", "paper plates", "popsicle sticks/pencils"],
                    "instructions": "1. Make paddles by attaching sticks to plates. 2. Hit balloon back and forth. 3. Set up a net line with string.",
                    "duration_minutes": duration
                }
            ]
        },
        "string_yarn": {
            "matches": ["string", "yarn", "ribbon"],
            "activities": [
                {
                    "title": "String Sculptures",
                    "description": "Create 3D art by wrapping string around objects or making hanging mobiles.",
                    "supplies_needed": ["string/yarn", "paper clips/coat hangers", "tape"],
                    "instructions": "1. Create framework with hangers. 2. Wrap string in patterns. 3. Hang and display creations.",
                    "duration_minutes": duration
                },
                {
                    "title": "String Phone",
                    "description": "Classic science activity exploring sound waves through string.",
                    "supplies_needed": ["string", "paper cups", "pencils"],
                    "instructions": "1. Poke holes in cup bottoms. 2. Thread string through. 3. Tie knots to secure. 4. Test across the room.",
                    "duration_minutes": 20
                }
            ]
        },
        "markers_crayons": {
            "matches": ["marker", "crayon", "colored pencil"],
            "activities": [
                {
                    "title": "Giant Collaborative Mural",
                    "description": "Large-scale art project on butcher paper or cardboard.",
                    "supplies_needed": ["markers/crayons", "large paper/cardboard"],
                    "instructions": "1. Unroll paper on floor/wall. 2. Assign sections or themes. 3. Fill with drawings and designs. 4. Display final mural.",
                    "duration_minutes": duration
                }
            ]
        },
        "cardboard_boxes": {
            "matches": ["cardboard", "box"],
            "activities": [
                {
                    "title": "Cardboard Challenge",
                    "description": "Open-ended building with cardboard boxes and tape.",
                    "supplies_needed": ["cardboard boxes", "tape", "scissors"],
                    "instructions": "1. Present challenge: build a vehicle/house/animal. 2. Cut and tape boxes together. 3. Decorate creations. 4. Share with group.",
                    "duration_minutes": 45
                }
            ]
        }
    }
    
    # Find matching templates
    matched_activities = []
    used_supplies = set()
    
    for key, template in supply_combinations.items():
        for supply in supplies_lower:
            if any(match in supply for match in template["matches"]):
                for activity in template["activities"]:
                    if activity["title"] not in [a["title"] for a in matched_activities]:
                        matched_activities.append(activity)
                        used_supplies.update(template["matches"])
                break
    
    # Generate generic activities using the supplies
    generic_templates = [
        {
            "title": f"{supplies[0].title()} Challenge",
            "description": f"Creative challenge using {', '.join(supplies[:3])} to solve a problem or create something new.",
            "supplies_needed": supplies[:4],
            "instructions": f"1. Present the challenge. 2. Provide {', '.join(supplies[:3])}. 3. Let children create and experiment. 4. Share results.",
            "duration_minutes": duration
        },
        {
            "title": "Supply Sort & Classify",
            "description": "Math/sorting activity using available supplies as manipulatives.",
            "supplies_needed": supplies[:4],
            "instructions": "1. Sort supplies by different attributes (color, size, material). 2. Count and compare groups. 3. Create patterns.",
            "duration_minutes": 20
        }
    ]
    
    # Combine and limit results
    all_activities = matched_activities + generic_templates
    selected = all_activities[:count]
    
    # Add metadata
    for i, act in enumerate(selected):
        act["indoor_outdoor"] = indoor_outdoor
        act["target_age"] = age_group
        act["generated"] = True
        act["supply_based"] = True
    
    return {
        "success": True,
        "supplies_provided": supplies,
        "count": len(selected),
        "activities": selected,
        "coverage_note": f"Found {len(matched_activities)} specific activities and {len(generic_templates)} generic templates for your supplies."
    }


@register_tool("save_activity")
def save_activity_tool(
    title: str,
    description: str,
    instructions: str,
    age_group: str,
    duration_minutes: int,
    supplies: List[str],
    activity_type: str = "Other",
    indoor_outdoor: str = "either",
    _context: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Save a generated or blended activity to the database.
    Makes it searchable for all users.
    """
    import uuid
    
    activity_id = str(uuid.uuid4())[:8]
    
    # Format for database storage
    activity_record = {
        "id": activity_id,
        "title": title,
        "description": description,
        "instructions": instructions,
        "target_age_group": age_group,
        "duration_minutes": duration_minutes,
        "supplies": ", ".join(supplies),
        "activity_type": activity_type,
        "indoor_outdoor": indoor_outdoor,
        "source": "user_generated",
        "created_at": datetime.now().isoformat(),
        "searchable_text": f"{title} {description} {activity_type} {age_group}"
    }
    
    # In a real implementation, this would:
    # 1. Save to SQLite/PostgreSQL
    # 2. Generate embeddings
    # 3. Upsert to Pinecone
    
    # For now, return success with instructions for manual save
    return {
        "success": True,
        "activity_id": activity_id,
        "saved": False,  # Not actually persisted yet
        "note": "Activity validated and ready for save. Full persistence requires vector DB upsert implementation.",
        "activity": activity_record,
        "next_steps": [
            "Activity can be added to local database",
            "Run embedding generation for vector search",
            "Will be available in future searches once indexed"
        ]
    }
