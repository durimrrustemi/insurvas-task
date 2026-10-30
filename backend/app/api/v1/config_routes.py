from fastapi import APIRouter

from app.config import app_config

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_config():
    return {
        "countries": [
            {
                "code": c.code,
                "name": c.name,
                "english_baseline": c.english_baseline,
                "timezone": c.timezone,
                "preferred_channels": c.preferred_channels,
                "cities": c.cities,
            }
            for c in app_config.countries
        ],
        "criterion_weights": app_config.criterion_weights,
        "signals": {
            criterion: {
                key: {"weight": sig.weight, "description": sig.description}
                for key, sig in sigs.items()
            }
            for criterion, sigs in app_config.signals.items()
        },
        "gates": {
            name: {
                "description": gate.description,
                "required_before": gate.required_before,
            }
            for name, gate in app_config.gates.items()
        },
        "cadence": {
            "follow_up_days": app_config.cadence.follow_up_days,
            "intents": app_config.cadence.intents,
            "channel_limits": app_config.cadence.channel_limits,
            "reminder_days": app_config.cadence.reminder_days,
            "stale_stage_days": app_config.cadence.stale_stage_days,
            "max_follow_ups": app_config.cadence.max_follow_ups,
        }
        if app_config.cadence
        else None,
    }
