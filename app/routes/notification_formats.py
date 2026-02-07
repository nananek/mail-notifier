from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import NotificationFormat

notification_formats_bp = Blueprint("notification_formats", __name__, url_prefix="/notification_formats")

@notification_formats_bp.route("/")
def index():
    formats = NotificationFormat.query.order_by(NotificationFormat.name).all()
    return render_template("notification_formats/index.html", formats=formats)

@notification_formats_bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        fmt = NotificationFormat(
            name=request.form["name"],
            template=request.form["template"],
        )
        db.session.add(fmt)
        db.session.commit()
        flash("フォーマットを作成しました。", "success")
        return redirect(url_for("notification_formats.index"))
    return render_template("notification_formats/form.html", fmt=None)

@notification_formats_bp.route("/<int:format_id>/edit", methods=["GET", "POST"])
def edit(format_id):
    fmt = NotificationFormat.query.get_or_404(format_id)
    if request.method == "POST":
        fmt.name = request.form["name"]
        fmt.template = request.form["template"]
        db.session.commit()
        flash("フォーマットを更新しました。", "success")
        return redirect(url_for("notification_formats.index"))
    return render_template("notification_formats/form.html", fmt=fmt)

@notification_formats_bp.route("/<int:format_id>/delete", methods=["POST"])
def delete(format_id):
    fmt = NotificationFormat.query.get_or_404(format_id)
    db.session.delete(fmt)
    db.session.commit()
    flash("フォーマットを削除しました。", "success")
    return redirect(url_for("notification_formats.index"))
