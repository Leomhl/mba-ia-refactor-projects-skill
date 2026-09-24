from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from database import db


def agora():
    """Current timezone-aware instant.

    Replaces `datetime.utcnow()`, which returns a naive datetime and is
    deprecated in Python 3.12 (playbook RP-14).
    """
    return datetime.now(timezone.utc)


def como_utc(valor):
    """Normalizes a datetime read from the database to timezone-aware UTC.

    SQLite does not store the offset, so written values come back naive.
    Comparing naive against aware raises TypeError — the classic trap when
    migrating from `utcnow()` to `now(timezone.utc)`.
    """
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=agora)

    def to_dict(self):
        """Public representation of the user.

        The `password` field was removed: the hash used to ship in
        GET /users/<id>, POST /users, PUT /users/<id> and the login response.
        """
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, pwd):
        """Hashes with PBKDF2-SHA256 and a per-record salt.

        The previous code used unsalted MD5 — fast by design and reversible
        via rainbow table (playbook RP-12).
        """
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        """Verifies the password, transparently migrating legacy MD5 hashes."""
        if check_password_hash(self.password, pwd):
            return True

        if self._confere_md5_legado(pwd):
            # Correct password stored in the old format: rewrite it with the
            # new algorithm during login, without forcing a password reset.
            self.set_password(pwd)
            db.session.commit()
            return True

        return False

    def _confere_md5_legado(self, pwd):
        import hashlib

        if len(self.password) != 32 or '$' in self.password:
            return False
        return self.password == hashlib.md5(pwd.encode()).hexdigest()

    def is_admin(self):
        return self.role == 'admin'
