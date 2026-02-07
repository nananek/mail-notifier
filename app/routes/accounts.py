from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Account, Rule
from app.imap_client_utils import list_mailboxes
from app.imap_client import fetch_new_messages
from app.notify import evaluate_and_notify

accounts_bp = Blueprint("accounts", __name__, url_prefix="/accounts")
@accounts_bp.route("/<int:account_id>/receive", methods=["POST"])
def receive_now(account_id):
    account = Account.query.get_or_404(account_id)
    # last_uidが未設定なら最新メールのUIDを取得してセット
    if account.last_uid == 0 or account.last_uid is None:
        try:
            import imaplib
            ssl_mode = getattr(account, 'ssl_mode', None)
            if ssl_mode == "ssl":
                conn = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
            elif ssl_mode == "starttls":
                conn = imaplib.IMAP4(account.imap_host, account.imap_port)
                conn.starttls()
            elif ssl_mode == "none":
                conn = imaplib.IMAP4(account.imap_host, account.imap_port)
            else:
                # Legacy fallback
                if account.use_ssl:
                    if account.imap_port == 993:
                        conn = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
                    else:
                        conn = imaplib.IMAP4(account.imap_host, account.imap_port)
                        conn.starttls()
                else:
                    conn = imaplib.IMAP4(account.imap_host, account.imap_port)
            conn.login(account.imap_user, account.imap_password)
            status, _ = conn.select(account.mailbox_name, readonly=True)
            if status == "OK":
                status, data = conn.uid("search", None, "*")
                if status == "OK" and data[0]:
                    uid_list = data[0].split()
                    if uid_list:
                        account.last_uid = int(uid_list[-1])
                        db.session.commit()
                        flash(f"初期化: Last UIDを{account.last_uid}に設定しました。", "info")
            conn.close()
            conn.logout()
        except Exception as exc:
            flash(f"Last UID初期化に失敗: {exc}", "danger")
            return redirect(url_for("accounts.index"))
    try:
        messages = list(fetch_new_messages(
            host=account.imap_host,
            port=account.imap_port,
            user=account.imap_user,
            password=account.imap_password,
            use_ssl=account.use_ssl,
            last_uid=account.last_uid if account.last_uid else None,
            mailbox_name=account.mailbox_name,
            ssl_mode=getattr(account, 'ssl_mode', None),
        ))
        count = len(messages)
        if count:
            notified = 0
            for msg in messages:
                if evaluate_and_notify(account, msg):
                    notified += 1
            account.last_uid = max(m.uid for m in messages)
            db.session.commit()
            flash(f"{count}件の新着メールを受信し、{notified}件を通知しました。", "success")
        else:
            flash("新着メールはありません。", "info")
    except Exception as exc:
        flash(f"受信に失敗しました: {exc}", "danger")
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
