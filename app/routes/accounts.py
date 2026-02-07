from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Account

accounts_bp = Blueprint("accounts", __name__, url_prefix="/accounts")


@accounts_bp.route("/")
def index():
    accounts = Account.query.order_by(Account.name).all()
    return render_template("accounts/index.html", accounts=accounts)


@accounts_bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        account = Account(
            name=request.form["name"],
            imap_host=request.form["imap_host"],
            imap_port=int(request.form.get("imap_port", 993)),
            imap_user=request.form["imap_user"],
            imap_password=request.form["imap_password"],
            use_ssl="use_ssl" in request.form,
            enabled="enabled" in request.form,
        )
        db.session.add(account)
        db.session.commit()
        flash("アカウントを作成しました。", "success")
        return redirect(url_for("accounts.index"))
    return render_template("accounts/form.html", account=None)


@accounts_bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
def edit(account_id):
    account = Account.query.get_or_404(account_id)
    if request.method == "POST":
        account.name = request.form["name"]
        account.imap_host = request.form["imap_host"]
        account.imap_port = int(request.form.get("imap_port", 993))
        account.imap_user = request.form["imap_user"]
        if request.form.get("imap_password"):
            account.imap_password = request.form["imap_password"]
        account.use_ssl = "use_ssl" in request.form
        account.enabled = "enabled" in request.form
        db.session.commit()
        flash("アカウントを更新しました。", "success")
        return redirect(url_for("accounts.index"))
    return render_template("accounts/form.html", account=account)


@accounts_bp.route("/<int:account_id>/delete", methods=["POST"])
def delete(account_id):
    account = Account.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    flash("アカウントを削除しました。", "success")
    return redirect(url_for("accounts.index"))
