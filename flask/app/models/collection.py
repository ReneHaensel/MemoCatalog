from __future__ import annotations

from datetime import date, datetime

from app.extensions import db


class UserCollectionEntry(db.Model):
    __tablename__ = "user_collection_entries"
    __table_args__ = (db.UniqueConstraint("user_id", "base_note_id", name="uq_collection_note"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    base_note_id = db.Column(
        db.Integer, db.ForeignKey("base_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition = db.Column(db.String(120), nullable=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    personal_notes = db.Column(db.Text, nullable=True)
    acquired_at = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="collection_entries")
    base_note = db.relationship("BaseNote", back_populates="collection_entries")

    @property
    def item_label(self) -> str:
        return self.base_note.title


class WishlistEntry(db.Model):
    __tablename__ = "wishlist_entries"
    __table_args__ = (db.UniqueConstraint("user_id", "base_note_id", name="uq_wishlist_note"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    base_note_id = db.Column(
        db.Integer, db.ForeignKey("base_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="wishlist_entries")
    base_note = db.relationship("BaseNote", back_populates="wishlist_entries")
