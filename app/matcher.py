"""Rule matching engine – evaluates conditions against an email message."""

import re
import logging
from app.models import RuleCondition

logger = logging.getLogger(__name__)


def matches_condition(condition: RuleCondition, value: str) -> bool:
    """Check if *value* satisfies a single condition."""
    pattern = condition.pattern
    match_type = condition.match_type

    if match_type == RuleCondition.MATCH_PREFIX:
        return value.lower().startswith(pattern.lower())
    elif match_type == RuleCondition.MATCH_SUFFIX:
        return value.lower().endswith(pattern.lower())
    elif match_type == RuleCondition.MATCH_CONTAINS:
        return pattern.lower() in value.lower()
    elif match_type == RuleCondition.MATCH_REGEX:
        try:
            return bool(re.search(pattern, value, re.IGNORECASE))
        except re.error:
            return False
    return False


def evaluate_rule(rule, *, from_address: str, to_address: str, subject: str, account_id: int, account_name: str) -> bool:
    """
    Evaluate all conditions on *rule* against the given email fields.
    All conditions must match (AND logic).
    Returns True if every condition passes.
    """
    if not rule.conditions:
        return False  # No conditions → never match

    logger.debug("Evaluating rule '%s' for account_id=%d (%s)", rule.name, account_id, account_name)
    
    for cond in rule.conditions:
        if cond.field == RuleCondition.FIELD_FROM:
            if not matches_condition(cond, from_address):
                logger.debug("  Condition failed: FROM '%s' does not match pattern '%s'", from_address, cond.pattern)
                return False
        elif cond.field == RuleCondition.FIELD_TO:
            if not matches_condition(cond, to_address):
                logger.debug("  Condition failed: TO '%s' does not match pattern '%s'", to_address, cond.pattern)
                return False
        elif cond.field == RuleCondition.FIELD_SUBJECT:
            if not matches_condition(cond, subject):
                logger.debug("  Condition failed: SUBJECT '%s' does not match pattern '%s'", subject, cond.pattern)
                return False
        else:
            logger.debug("  Condition failed: Unknown field type '%s'", cond.field)
            return False  # Unknown field type
    
    logger.debug("  All conditions passed for rule '%s'", rule.name)
    return True
