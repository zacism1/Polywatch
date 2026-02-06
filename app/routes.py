from flask import Blueprint, render_template, abort
from .models import Politician


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    politicians = Politician.query.order_by(Politician.name.asc()).all()
    total_count = Politician.query.count()
    house_count = Politician.query.filter_by(chamber="House").count()
    senate_count = Politician.query.filter_by(chamber="Senate").count()
    return render_template(
        "index.html",
        politicians=politicians,
        total_count=total_count,
        house_count=house_count,
        senate_count=senate_count,
    )


@main_bp.route("/politician/<int:pol_id>")
def politician_detail(pol_id):
    politician = Politician.query.get(pol_id)
    if not politician:
        abort(404)

    investments = sorted(politician.investments, key=lambda i: i.date or i.created_at, reverse=True)
    policies = sorted(politician.policies, key=lambda p: p.date or p.created_at, reverse=True)
    correlations = sorted(politician.correlations, key=lambda c: c.created_at, reverse=True)

    return render_template(
        "politician.html",
        politician=politician,
        investments=investments,
        policies=policies,
        correlations=correlations,
    )
