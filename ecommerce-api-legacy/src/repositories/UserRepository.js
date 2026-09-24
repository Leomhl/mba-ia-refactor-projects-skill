'use strict';

const { hashPassword } = require('../services/PasswordHasher');

/** User data access. Receives the connection, does not create it (playbook RP-05). */
class UserRepository {
    constructor(db, config) {
        this.db = db;
        this.config = config;
    }

    findByEmail(email) {
        return this.db.get('SELECT * FROM users WHERE email = ?', [email]);
    }

    findById(id) {
        return this.db.get(
            'SELECT id, name, email, active FROM users WHERE id = ?',
            [id],
        );
    }

    async create({ name, email, password }) {
        const hash = await hashPassword(password, this.config.security.bcryptRounds);
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, hash],
        );
        return { id: lastID, name, email };
    }

    /**
     * Logical deactivation.
     *
     * Physical deletion left enrollments and payments orphaned — the financial
     * report would start listing "Unknown" with amounts still counted.
     * Accounting records cannot disappear because the account holder left.
     */
    async deactivate(id) {
        const { changes } = await this.db.run(
            'UPDATE users SET active = 0 WHERE id = ? AND active = 1',
            [id],
        );
        return changes > 0;
    }
}

module.exports = { UserRepository };
