from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models import FailureLog, WorkerState

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


@maintenance_bp.route("/")
def index():
    state = WorkerState.query.get(1)
    logs = (
        FailureLog.query.order_by(FailureLog.created_at.desc()).limit(100).all()
    )
    return render_template("maintenance/index.html", state=state, logs=logs)


@maintenance_bp.route("/worker/toggle", methods=["POST"])
def toggle_worker():
    state = WorkerState.query.get(1)
    if state is None:
        state = WorkerState(id=1, is_running=True, poll_interval=60)
        db.session.add(state)
    state.is_running = not state.is_running
    db.session.commit()
    status = "再開" if state.is_running else "停止"
    flash(f"ワーカーを{status}しました。", "success")
    return redirect(url_for("maintenance.index"))


@maintenance_bp.route("/worker/interval", methods=["POST"])
def set_interval():
    state = WorkerState.query.get(1)
    interval = int(request.form.get("poll_interval", 60))
    if interval < 10:
        interval = 10
    state.poll_interval = interval
    db.session.commit()
    flash(f"ポーリング間隔を {interval} 秒に設定しました。", "success")
    return redirect(url_for("maintenance.index"))


@maintenance_bp.route("/worker/timezone", methods=["POST"])
def set_timezone():
    state = WorkerState.query.get(1)
    if state is None:
        state = WorkerState(id=1, is_running=True, poll_interval=60)
        db.session.add(state)
    timezone_name = request.form.get("display_timezone", "UTC")
    state.display_timezone = timezone_name
    db.session.commit()
    flash(f"表示タイムゾーンを {timezone_name} に設定しました。", "success")
    return redirect(url_for("maintenance.index"))


@maintenance_bp.route("/logs/clear", methods=["POST"])
def clear_logs():
    FailureLog.query.delete()
    db.session.commit()
    flash("失敗ログをすべて削除しました。", "success")
    return redirect(url_for("maintenance.index"))


@maintenance_bp.route("/logs/cleanup", methods=["POST"])
def cleanup_old_logs():
    """Delete failure logs older than 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    deleted = FailureLog.query.filter(FailureLog.created_at < cutoff).delete()
    db.session.commit()
    flash(f"30日以上前のログを {deleted} 件削除しました。", "success")
    return redirect(url_for("maintenance.index"))


# ── JSON API for status checks ───────────────────────────────────
@maintenance_bp.route("/api/status")
def api_status():
    state = WorkerState.query.get(1)
    return jsonify(
        {
            "is_running": state.is_running if state else False,
            "poll_interval": state.poll_interval if state else 60,
        }
    )
