from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Account, Rule, WorkerTrigger
from app.imap_client_utils import list_mailboxes

accounts_bp = Blueprint("accounts", __name__, url_prefix="/accounts")
@accounts_bp.route("/<int:account_id>/receive", methods=["POST"])
def receive_now(account_id):
    account = Account.query.get_or_404(account_id)
    
    # Create a trigger for the worker to process this account immediately
    trigger = WorkerTrigger(account_id=account.id)
    db.session.add(trigger)
    db.session.commit()
    
    flash(f"{account.name}の即時受信をリクエストしました。ワーカーが次のサイクルで処理します。", "success")
    return redirect(url_for("accounts.index"))

@accounts_bp.route("/mailboxes", methods=["POST"])
def fetch_mailboxes():
    host = request.form.get("imap_host")
    port = int(request.form.get("imap_port", 993))
    user = request.form.get("imap_user")
    password = request.form.get("imap_password")
    ssl_mode = request.form.get("ssl_mode")
    use_ssl = request.form.get("use_ssl") == "true"
    mailboxes = list_mailboxes(host, port, user, password, use_ssl, ssl_mode)
    return {"mailboxes": mailboxes}


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
            ssl_mode=request.form.get("ssl_mode", "ssl"),
            enabled="enabled" in request.form,
            mailbox_name=request.form.get("mailbox_name", "INBOX"),
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
        account.ssl_mode = request.form.get("ssl_mode", "ssl")
        account.enabled = "enabled" in request.form
        account.mailbox_name = request.form.get("mailbox_name", "INBOX")
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
