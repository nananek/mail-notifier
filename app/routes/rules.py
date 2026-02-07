from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models import Rule, RuleCondition, Account, DiscordWebhook, NotificationFormat

rules_bp = Blueprint("rules", __name__, url_prefix="/rules")


@rules_bp.route("/")
def index():
    rules = Rule.query.order_by(Rule.position).all()
    return render_template("rules/index.html", rules=rules)


@rules_bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        webhook_id = _resolve_webhook(request.form)
        max_pos = db.session.query(db.func.max(Rule.position)).scalar() or 0
        format_id = int(request.form.get("notification_format_id") or 0) or None
        rule = Rule(
            name=request.form["name"],
            discord_webhook_id=webhook_id,
            notification_format_id=format_id,
            position=max_pos + 1,
            enabled="enabled" in request.form,
        )
        db.session.add(rule)
        db.session.flush()
        _save_conditions(rule, request.form)
        db.session.commit()
        flash("ルールを作成しました。", "success")
        return redirect(url_for("rules.index"))

    accounts = Account.query.order_by(Account.name).all()
    webhooks = DiscordWebhook.query.order_by(DiscordWebhook.name).all()
    formats = NotificationFormat.query.order_by(NotificationFormat.name).all()
    return render_template("rules/form.html", rule=None, accounts=accounts, webhooks=webhooks, formats=formats)


@rules_bp.route("/<int:rule_id>/edit", methods=["GET", "POST"])
def edit(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    if request.method == "POST":
        rule.name = request.form["name"]
        rule.discord_webhook_id = _resolve_webhook(request.form)
        rule.notification_format_id = int(request.form.get("notification_format_id") or 0) or None
        rule.enabled = "enabled" in request.form

        RuleCondition.query.filter_by(rule_id=rule.id).delete()
        _save_conditions(rule, request.form)

        db.session.commit()
        flash("ルールを更新しました。", "success")
        return redirect(url_for("rules.index"))

    accounts = Account.query.order_by(Account.name).all()
    webhooks = DiscordWebhook.query.order_by(DiscordWebhook.name).all()
    formats = NotificationFormat.query.order_by(NotificationFormat.name).all()
    return render_template("rules/form.html", rule=rule, accounts=accounts, webhooks=webhooks, formats=formats)


@rules_bp.route("/<int:rule_id>/delete", methods=["POST"])
def delete(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    flash("ルールを削除しました。", "success")
    return redirect(url_for("rules.index"))


@rules_bp.route("/reorder", methods=["POST"])
def reorder():
    """Accept JSON array of rule IDs in desired order."""
    order = request.get_json()
    if not order or not isinstance(order, list):
        return jsonify({"error": "invalid payload"}), 400

    for position, rule_id in enumerate(order, start=1):
        Rule.query.filter_by(id=rule_id).update({"position": position})
    db.session.commit()
    return jsonify({"status": "ok"})


@rules_bp.route("/<int:rule_id>/toggle", methods=["POST"])
def toggle(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    rule.enabled = not rule.enabled
    db.session.commit()
    flash(
        f"ルール「{rule.name}」を{'有効' if rule.enabled else '無効'}にしました。",
        "success",
    )
    return redirect(url_for("rules.index"))


def _resolve_webhook(form):
    """Return webhook ID – create a new webhook if requested."""
    webhook_id = form.get("discord_webhook_id")
    if webhook_id == "__new__":
        wh = DiscordWebhook(
            name=form["new_webhook_name"],
            url=form["new_webhook_url"],
        )
        db.session.add(wh)
        db.session.flush()
        return wh.id
    return int(webhook_id) if webhook_id else None


def _save_conditions(rule, form):
    """Parse dynamically-added condition rows from the form."""
    idx = 0
    while True:
        field = form.get(f"cond_field_{idx}")
        if field is None:
            break
        match_type = form.get(f"cond_match_{idx}", "contains")
        pattern = form.get(f"cond_pattern_{idx}", "")
        account_id = form.get(f"cond_account_{idx}")

        if field and pattern:
            cond = RuleCondition(
                rule_id=rule.id,
                field=field,
                match_type=match_type,
                pattern=pattern,
                account_id=int(account_id) if account_id else None,
            )
            db.session.add(cond)
        idx += 1
