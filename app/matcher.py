"""Rule matching engine – evaluates conditions against an email message."""

import re
from app.models import RuleCondition


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


def evaluate_rule(rule, *, from_address: str, subject: str, account_id: int, account_name: str) -> bool:
    """
    Evaluate all conditions on *rule* against the given email fields.
    All conditions must match (AND logic).
    Returns True if every condition passes.
    """
    if not rule.conditions:
        return False  # No conditions → never match

    for cond in rule.conditions:
        if cond.field == RuleCondition.FIELD_FROM:
            if not matches_condition(cond, from_address):
                return False
        elif cond.field == RuleCondition.FIELD_SUBJECT:
            if not matches_condition(cond, subject):
                return False
        elif cond.field == RuleCondition.FIELD_ACCOUNT:
            # Account condition: check account_id matches
            if cond.account_id is not None and cond.account_id != account_id:
                return False
        else:
            return False  # Unknown field type
    return True
