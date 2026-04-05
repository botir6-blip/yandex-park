from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for

from app.config import settings
from app.db import db_session
from app.services.admin_service import authenticate_admin, get_admin, update_admin_password
from app.services.audit_service import log_action
from app.services.driver_service import ensure_wallet, get_driver, search_drivers
from app.services.settings_service import get_setting, set_setting
from app.services.transaction_service import get_driver_transactions
from app.services.wallet_service import adjust_wallet, available_to_withdraw
from app.services.withdrawal_service import get_withdrawal, list_withdrawals, update_withdrawal_status


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = settings.secret_key

    @app.context_processor
    def inject_globals():
        admin = None
        if session.get("admin_id"):
            with db_session() as db:
                admin = get_admin(db, session["admin_id"])
        return {"current_admin": admin}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            login = request.form.get("login", "").strip()
            password = request.form.get("password", "")
            with db_session() as db:
                admin = authenticate_admin(db, login, password)
                if admin:
                    session["admin_id"] = admin.id
                    return redirect(url_for("dashboard"))
            flash("Логин ёки пароль нотўғри.", "error")
        return render_template("login.html")

    @app.route("/health")
    def health():
        return {"ok": True}, 200

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @admin_required
    def dashboard():
        with db_session() as db:
            drivers = search_drivers(db, None)
            withdrawals = list_withdrawals(db, None)
            pending = [w for w in withdrawals if w.status in ("new", "accepted")]
            stats = {
                "drivers_total": len(drivers),
                "pending_withdrawals": len(pending),
                "withdrawals_total": len(withdrawals),
                "support_contact": get_setting(db, "support_contact", "@support"),
            }
            return render_template("dashboard.html", stats=stats, withdrawals=pending[:10])

    @app.route("/drivers")
    @admin_required
    def drivers_page():
        query = request.args.get("q", "").strip()
        with db_session() as db:
            drivers = search_drivers(db, query)
            for d in drivers:
                ensure_wallet(db, d)
            return render_template("drivers.html", drivers=drivers, query=query)

    @app.route("/drivers/<int:driver_id>", methods=["GET", "POST"])
    @admin_required
    def driver_detail(driver_id: int):
        with db_session() as db:
            driver = get_driver(db, driver_id)
            if not driver:
                flash("Ҳайдовчи топilmadi.", "error")
                return redirect(url_for("drivers_page"))

            wallet = ensure_wallet(db, driver)

            if request.method == "POST":
                main_delta = request.form.get("main_delta", "0").strip() or "0"
                bonus_delta = request.form.get("bonus_delta", "0").strip() or "0"
                reserve_new = request.form.get("reserve_new", "").strip()
                comment = request.form.get("comment", "").strip() or "Admin adjustment"

                try:
                    reserve_value = None if reserve_new == "" else reserve_new
                    tx_type = "balance_adjustment_plus"
                    if main_delta.startswith("-"):
                        tx_type = "balance_adjustment_minus"
                    adjust_wallet(
                        db,
                        driver,
                        main_delta=main_delta,
                        bonus_delta=bonus_delta,
                        reserve_new=reserve_value,
                        transaction_type=tx_type if reserve_value is None else "reserve_changed",
                        comment=comment,
                        admin_id=session["admin_id"],
                    )
                    log_action(
                        db,
                        action="wallet_adjustment",
                        entity_type="driver_wallet",
                        entity_id=driver.id,
                        admin_id=session["admin_id"],
                        details={
                            "main_delta": main_delta,
                            "bonus_delta": bonus_delta,
                            "reserve_new": reserve_new,
                            "comment": comment,
                        },
                        ip_address=request.remote_addr,
                    )
                    flash("Баланс янгиланди.", "success")
                except Exception as exc:
                    flash(str(exc), "error")

            txs = get_driver_transactions(db, driver.id, 20)
            withdrawals = [w for w in driver.withdrawals][-20:]
            return render_template(
                "driver_detail.html",
                driver=driver,
                wallet=wallet,
                available=available_to_withdraw(wallet),
                transactions=txs,
                withdrawals=withdrawals,
            )

    @app.route("/withdrawals")
    @admin_required
    def withdrawals_page():
        status = request.args.get("status", "").strip() or None
        with db_session() as db:
            rows = list_withdrawals(db, status)
            return render_template("withdrawals.html", withdrawals=rows, status=status or "")

    @app.route("/withdrawals/<int:withdrawal_id>/<string:action>", methods=["POST"])
    @admin_required
    def withdrawals_action(withdrawal_id: int, action: str):
        note = request.form.get("note", "").strip() or None
        with db_session() as db:
            withdrawal = get_withdrawal(db, withdrawal_id)
            if not withdrawal:
                flash("Сўров топilmadi.", "error")
                return redirect(url_for("withdrawals_page"))
            try:
                update_withdrawal_status(db, withdrawal, action, admin_id=session["admin_id"], note=note)
                log_action(
                    db,
                    action=f"withdrawal_{action}",
                    entity_type="withdrawal",
                    entity_id=withdrawal.id,
                    admin_id=session["admin_id"],
                    details={"note": note},
                    ip_address=request.remote_addr,
                )
                flash("Статус янгиланди.", "success")
            except Exception as exc:
                flash(str(exc), "error")
        return redirect(url_for("withdrawals_page"))

    @app.route("/settings", methods=["GET", "POST"])
    @admin_required
    def settings_page():
        keys = [
            "deposit_commission_percent",
            "global_min_reserve_balance",
            "min_withdraw_amount",
            "max_withdraw_amount",
            "support_contact",
            "default_language",
        ]
        with db_session() as db:
            if request.method == "POST":
                form_action = request.form.get("form_action", "settings").strip()

                if form_action == "password":
                    admin = get_admin(db, session["admin_id"])
                    current_password = request.form.get("current_password", "")
                    new_password = request.form.get("new_password", "")
                    confirm_password = request.form.get("confirm_password", "")

                    if not admin:
                        flash("Админ топилмади.", "error")
                    elif not authenticate_admin(db, admin.login, current_password):
                        flash("Жорий пароль нотўғри.", "error")
                    elif len(new_password) < 6:
                        flash("Янги пароль камида 6 та белгидан иборат бўлиши керак.", "error")
                    elif new_password != confirm_password:
                        flash("Янги пароль ва тасдиқлаш бир хил эмас.", "error")
                    elif current_password == new_password:
                        flash("Янги пароль жорий парольдан фарқ қилиши керак.", "error")
                    else:
                        update_admin_password(db, admin, new_password)
                        log_action(
                            db,
                            action="admin_password_changed",
                            entity_type="admin",
                            entity_id=admin.id,
                            admin_id=admin.id,
                            details={"login": admin.login},
                            ip_address=request.remote_addr,
                        )
                        db.commit()
                        flash("Пароль муваффақиятли алмаштирилди.", "success")
                else:
                    for key in keys:
                        value = request.form.get(key, "").strip()
                        if value:
                            set_setting(db, key, value)
                    db.commit()
                    flash("Созламалар сақланди.", "success")

            values = {key: get_setting(db, key, "") for key in keys}
            return render_template("settings.html", values=values)

    return app
