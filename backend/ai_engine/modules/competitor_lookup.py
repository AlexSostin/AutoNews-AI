"""
Competitor Lookup — finds relevant cars from the database to inject into article prompts.

Two-phase approach:
1. Rule-based: filter VehicleSpecs by same fuel_type + body_type, proximity of power/price
2. ML-ranked: after enough data accumulates in CompetitorPairLog, sort candidates by
   average engagement_score so well-performing competitor pairs surface first.

Entry points:
    get_competitor_context(make, model_name, fuel_type, body_type, power_hp, price_usd)
        → str: formatted block ready for prompt injection
        → empty string if no suitable competitors found (always safe to call)

    log_competitor_pairs(article_id, subject_make, subject_model, competitors)
        → None: persists CompetitorPairLog rows; called after article is saved

    format_competitor_line(v)
        → str: one-line summary of a VehicleSpecs object for the prompt
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Public: build competitor context string for the prompt
# ─────────────────────────────────────────────────────────

def get_competitor_context(
    make: str = "",
    model_name: str = "",
    fuel_type: str = "",
    body_type: str = "",
    power_hp: Optional[int] = None,
    price_usd: Optional[int] = None,
    max_competitors: int = 3,
) -> tuple[str, list[dict]]:
    """
    Return (prompt_block, competitors_list) where:
      - prompt_block: formatted string for injection into the article prompt,
        or empty string if no suitable competitors found.
      - competitors_list: list of dicts with raw competitor data for logging.

    Safe to call even if DB is empty — always returns ("", []) on any error.
    """
    try:
        from news.models.vehicles import VehicleSpecs
        from django.db.models import Avg, Count, Q
        from news.models.system import CompetitorPairLog

        # ── Step 1: candidate pool ───────────────────────────────────────────
        qs = VehicleSpecs.objects.all()

        # Exclude the subject car itself
        if make and model_name:
            qs = qs.exclude(
                Q(make__iexact=make) & Q(model_name__iexact=model_name)
            )

        # Must have at least a make and model to be useful
        qs = qs.exclude(make="").exclude(model_name="")

        # ── Step 2: relevant segment filter ─────────────────────────────────
        segment_qs = qs

        # Primary: same fuel_type
        if fuel_type:
            segment_qs = segment_qs.filter(fuel_type__iexact=fuel_type)

        # Secondary: same body_type
        if body_type:
            segment_qs = segment_qs.filter(body_type__iexact=body_type)

        count = segment_qs.count()

        # Fall back to fuel_type only if body_type narrowed too much
        if count < 2 and fuel_type and body_type:
            segment_qs = qs.filter(fuel_type__iexact=fuel_type)
            count = segment_qs.count()

        # Fall back to all cars (e.g. new fuel type with no history)
        if count < 2:
            segment_qs = qs

        # ── Step 3: power proximity filter (±60%) ───────────────────────────
        if power_hp and power_hp > 0:
            lo = int(power_hp * 0.4)
            hi = int(power_hp * 1.6)
            power_qs = segment_qs.filter(
                power_hp__gte=lo,
                power_hp__lte=hi,
            )
            if power_qs.count() >= 2:
                segment_qs = power_qs

        # ── Step 4: price proximity filter (±50%) ──────────────────────────
        if price_usd and price_usd > 0:
            lo = int(price_usd * 0.5)
            hi = int(price_usd * 1.5)
            price_qs = segment_qs.filter(price_usd_from__gte=lo, price_usd_from__lte=hi)
            if price_qs.count() >= 2:
                segment_qs = price_qs

        # ── Step 5: ML ranking ───────────────────────────────────────────────
        # Annotate each candidate with its average engagement score from log history
        # Candidates with no history get avg_engagement=None → sort them last
        try:
            pair_scores = (
                CompetitorPairLog.objects
                .filter(
                    competitor_make__in=segment_qs.values_list('make', flat=True),
                    engagement_score_at_log__isnull=False,
                )
                .values('competitor_make', 'competitor_model')
                .annotate(
                    avg_engagement=Avg('engagement_score_at_log'),
                    pair_count=Count('id'),
                )
            )
            # Build lookup: (make_lower, model_lower) → avg_engagement
            score_map = {
                (row['competitor_make'].lower(), row['competitor_model'].lower()): (
                    row['avg_engagement'],
                    row['pair_count'],
                )
                for row in pair_scores
            }
        except Exception:
            score_map = {}

        # Convert to list so we can sort
        candidates = list(segment_qs.select_related('article')[:50])

        def sort_key(v):
            """Sort: ML-scored > spec-rich > alphabetical."""
            key = (v.make.lower(), v.model_name.lower())
            avg_eng, pair_cnt = score_map.get(key, (None, 0))
            # Primary: known engagement (higher = better), unknown = -1
            eng_sort = avg_eng if avg_eng is not None else -1.0
            # Secondary: how many specs are filled (more = richer candidate)
            spec_richness = sum([
                1 if v.power_hp else 0,
                1 if v.range_wltp or v.range_km else 0,
                1 if v.price_usd_from else 0,
                1 if v.battery_kwh else 0,
                1 if v.acceleration_0_100 else 0,
            ])
            return (-eng_sort, -spec_richness)

        candidates.sort(key=sort_key)

        # ── Step 6: pick top N ───────────────────────────────────────────────
        selected = candidates[:max_competitors]
        if not selected:
            return "", []

        # ── Step 7: format for prompt ────────────────────────────────────────
        lines = []
        competitors_data = []
        for v in selected:
            line, data = _format_competitor_line(v)
            lines.append(f"• {line}")
            competitors_data.append(data)

        block = (
            "CARS ALREADY IN OUR DATABASE — USE FOR COMPARISON in the 'How It Compares' section:\n"
            + "\n".join(lines)
            + "\n\nWhen writing the 'How It Compares' section, cite these exact figures from our database."
        )
        return block, competitors_data

    except Exception as e:
        logger.warning(f"competitor_lookup: get_competitor_context failed: {e}")
        return "", []


def _format_competitor_line(v) -> tuple[str, dict]:
    """Format a VehicleSpecs object → (prompt line, data dict for logging)."""
    parts = []

    # Year + Make + Model + Trim
    year = v.model_year or v.year or ""
    name_parts = [str(year) if year else "", v.make, v.model_name]
    if v.trim_name:
        name_parts.append(v.trim_name)
    name = " ".join(p for p in name_parts if p).strip()
    parts.append(name)

    spec_parts = []

    # Power
    if v.power_hp:
        spec_parts.append(f"{v.power_hp} hp")
    elif v.power_kw:
        spec_parts.append(f"{v.power_kw} kW")

    # Range (prefer WLTP, then EPA, then CLTC, then generic)
    range_val = v.range_wltp or v.range_epa or v.range_cltc or v.range_km
    range_label = ""
    if v.range_wltp:
        range_label = "WLTP"
    elif v.range_epa:
        range_label = "EPA"
    elif v.range_cltc:
        range_label = "CLTC"
    if range_val:
        spec_parts.append(f"{range_val} km{' ' + range_label if range_label else ''}")

    # Battery
    if v.battery_kwh:
        spec_parts.append(f"{v.battery_kwh} kWh")

    # 0-100
    if v.acceleration_0_100:
        spec_parts.append(f"0-100 in {v.acceleration_0_100}s")

    # Price
    if v.price_usd_from:
        price_str = f"from ${v.price_usd_from:,}"
        if v.price_usd_to:
            price_str = f"${v.price_usd_from:,}–${v.price_usd_to:,}"
        spec_parts.append(price_str)

    line = name + (": " + " / ".join(spec_parts) if spec_parts else "")

    data = {
        "make": v.make,
        "model": v.model_name,
        "trim": v.trim_name or "",
        "power_hp": v.power_hp,
        "range_km": range_val,
        "price_usd": v.price_usd_from,
    }

    return line, data


# ─────────────────────────────────────────────────────────
# Public: log competitor pairs for ML training
# ─────────────────────────────────────────────────────────

def log_competitor_pairs(
    article_id: int,
    subject_make: str,
    subject_model: str,
    competitors: list[dict],
    selection_method: str = "rule_based",
) -> None:
    """
    Save CompetitorPairLog rows after article generation.
    Called from content_generator.py after the article is saved.
    Non-fatal: any error is logged and swallowed.
    """
    if not competitors:
        return
    try:
        from news.models.system import CompetitorPairLog

        rows = []
        for c in competitors:
            rows.append(CompetitorPairLog(
                article_id=article_id,
                subject_make=subject_make,
                subject_model=subject_model,
                competitor_make=c.get("make", ""),
                competitor_model=c.get("model", ""),
                competitor_trim=c.get("trim", ""),
                competitor_power_hp=c.get("power_hp"),
                competitor_range_km=c.get("range_km"),
                competitor_price_usd=c.get("price_usd"),
                selection_method=selection_method,
            ))
        CompetitorPairLog.objects.bulk_create(rows, ignore_conflicts=True)
        logger.info(
            f"competitor_lookup: logged {len(rows)} pairs for article {article_id} "
            f"({subject_make} {subject_model})"
        )
    except Exception as e:
        logger.warning(f"competitor_lookup: log_competitor_pairs failed: {e}")
