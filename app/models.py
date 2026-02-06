from datetime import datetime
from . import db


class Politician(db.Model):
    __tablename__ = "politicians"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    party = db.Column(db.String(100), nullable=True)
    electorate = db.Column(db.String(200), nullable=True)
    chamber = db.Column(db.String(20), nullable=True)  # House or Senate
    aph_id = db.Column(db.String(50), nullable=True, unique=True)

    investments = db.relationship("Investment", backref="politician", lazy=True)
    policies = db.relationship("Policy", backref="politician", lazy=True)


class Investment(db.Model):
    __tablename__ = "investments"
    id = db.Column(db.Integer, primary_key=True)
    politician_id = db.Column(db.Integer, db.ForeignKey("politicians.id"), nullable=False)
    asset_type = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(200), nullable=True)
    value = db.Column(db.Float, nullable=True)
    date = db.Column(db.Date, nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    source_hash = db.Column(db.String(64), nullable=True, index=True)
    raw_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    correlations = db.relationship("Correlation", backref="investment", lazy=True)


class Policy(db.Model):
    __tablename__ = "policies"
    id = db.Column(db.Integer, primary_key=True)
    politician_id = db.Column(db.Integer, db.ForeignKey("politicians.id"), nullable=False)
    bill_name = db.Column(db.String(300), nullable=True)
    vote = db.Column(db.String(50), nullable=True)
    date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    source_hash = db.Column(db.String(64), nullable=True, index=True)
    raw_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    correlations = db.relationship("Correlation", backref="policy", lazy=True)


class Correlation(db.Model):
    __tablename__ = "correlations"
    id = db.Column(db.Integer, primary_key=True)
    politician_id = db.Column(db.Integer, db.ForeignKey("politicians.id"), nullable=False)
    investment_id = db.Column(db.Integer, db.ForeignKey("investments.id"), nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey("policies.id"), nullable=False)
    suspicion_score = db.Column(db.Float, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    politician = db.relationship("Politician", backref="correlations")
