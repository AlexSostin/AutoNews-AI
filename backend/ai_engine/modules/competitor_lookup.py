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

        # Fallback hierarchy:
        # 1. Same fuel + body (current segment_qs)
        # 2. Same body (any fuel)
        # 3. Same fuel (any body)
        # 4. All cars
        if count < 2:
            if body_type:
                fallback_qs = qs.filter(body_type__iexact=body_type)
                if fallback_qs.count() >= 2:
                    segment_qs = fallback_qs
                    count = segment_qs.count()
            
            if count < 2 and fuel_type:
                fallback_qs = qs.filter(fuel_type__iexact=fuel_type)
                if fallback_qs.count() >= 2:
                    segment_qs = fallback_qs
                    count = segment_qs.count()
            
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

        # ── Step 5: Cooldown filter ──────────────────────────────────────────
        # Exclude competitors that appeared ≥2 times in the last 7 days.
        # This prevents the same car (e.g. Aito M7) from dominating every comparison.
        COOLDOWN_DAYS = 7
        COOLDOWN_MAX_APPEARANCES = 2

        overused = set()  # (make_lower, model_lower) pairs on cooldown
        try:
            from django.utils import timezone as _tz
            from datetime import timedelta
            cutoff = _tz.now() - timedelta(days=COOLDOWN_DAYS)
            recent_usage = (
                CompetitorPairLog.objects
                .filter(created_at__gte=cutoff)
                .values('competitor_make', 'competitor_model')
                .annotate(usage_count=Count('id'))
                .filter(usage_count__gte=COOLDOWN_MAX_APPEARANCES)
            )
            for row in recent_usage:
                pair = (row['competitor_make'].lower(), row['competitor_model'].lower())
                overused.add(pair)
                logger.info(
                    f"competitor_lookup: cooldown — {row['competitor_make']} {row['competitor_model']} "
                    f"used {row['usage_count']}x in last {COOLDOWN_DAYS} days, skipping"
                )
        except Exception as e:
            logger.debug(f"competitor_lookup: cooldown check failed (non-fatal): {e}")

        # Apply cooldown filter to segment queryset
        if overused:
            for make_l, model_l in overused:
                segment_qs = segment_qs.exclude(
                    Q(make__iexact=make_l) & Q(model_name__iexact=model_l)
                )

        # ── Step 6: ML ranking ───────────────────────────────────────────────
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

        # Convert to list for scoring
        candidates = list(segment_qs.select_related('article')[:50])

        if not candidates:
            return "", []

        import random

        def _candidate_weight(v):
            """Calculate selection weight: body match × engagement × spec richness."""
            key = (v.make.lower(), v.model_name.lower())
            avg_eng, _ = score_map.get(key, (None, 0))

            # Body type match bonus
            body_bonus = 2.0 if (body_type and v.body_type
                                  and v.body_type.lower() == body_type.lower()) else 1.0

            # Engagement score (default 1.0 for unknown)
            eng_weight = max(avg_eng, 0.1) if avg_eng is not None else 1.0

            # Spec richness (1-5)
            spec_richness = sum([
                1 if v.power_hp else 0,
                1 if v.range_wltp or v.range_km else 0,
                1 if v.price_usd_from else 0,
                1 if v.battery_kwh else 0,
                1 if v.acceleration_0_100 else 0,
            ]) or 1  # minimum 1

            return body_bonus * eng_weight * spec_richness

        # ── Step 7: weighted random selection ────────────────────────────────
        # ALL slots are picked via weighted random sampling.
        # Enforce brand diversity: no two competitors from the same make.
        selected = []
        used_makes = set()
        pool = list(candidates)

        for _ in range(max_competitors):
            # Filter pool by brand diversity
            eligible = [c for c in pool if c.make.lower() not in used_makes]
            if not eligible:
                # Fallback: allow same brand, different model
                eligible = [c for c in pool if c.id not in {s.id for s in selected}]
            if not eligible:
                break

            weights = [_candidate_weight(c) for c in eligible]
            total = sum(weights)
            if total == 0:
                pick = random.choice(eligible)
            else:
                # Weighted random selection
                pick = random.choices(eligible, weights=weights, k=1)[0]

            selected.append(pick)
            used_makes.add(pick.make.lower())
            pool = [c for c in pool if c.id != pick.id]

        # ── Step 8: Hard price guard ──────────────────────────────────────────
        # Even after all fallbacks, never return a competitor whose price is
        # wildly different from the subject car. This prevents nonsensical
        # comparisons (e.g. $21K SUV vs $58K luxury sedan).
        if price_usd and price_usd > 0:
            price_lo = int(price_usd * 0.4)
            price_hi = int(price_usd * 2.5)
            before_count = len(selected)
            selected = [
                c for c in selected
                if not c.price_usd_from  # keep cars with unknown price (benefit of doubt)
                or (price_lo <= c.price_usd_from <= price_hi)
            ]
            removed = before_count - len(selected)
            if removed:
                logger.info(
                    f"competitor_lookup: hard price guard removed {removed} competitor(s) "
                    f"outside ${price_lo:,}–${price_hi:,} range"
                )

        if not selected:
            return "", []

        # ── Step 9: format for prompt ────────────────────────────────────────
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
            "\nMake sure to compare the subject car against ALL of the provided competitors above to provide a comprehensive market overview."
            "\nCRITICAL: Do NOT invent or fabricate competitor data. Use ONLY the cars listed above."
            "\nIf no cars are listed, do NOT include a 'How It Compares' section."
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

    # Sanitize: strip non-Latin chars + deduplicate consecutive words
    try:
        from ai_engine.modules.content_sanitizer import sanitize_car_name
        name = sanitize_car_name(name)
    except ImportError:
        pass
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
