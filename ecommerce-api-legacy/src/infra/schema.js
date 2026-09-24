'use strict';

const { hashPassword } = require('../services/PasswordHasher');

/**
 * Schema with declared referential integrity (playbook RP-09).
 *
 * The original tables had no FOREIGN KEY at all, which let enrollments and
 * payments point at nonexistent users.
 *
 * Policy per relationship:
 *  - enrollments.user_id    RESTRICT — a user with enrollments is not deleted;
 *                           removal is logical (active = 0).
 *  - enrollments.course_id  RESTRICT — a course with enrollments is not deleted.
 *  - payments.enrollment_id RESTRICT — accounting history does not disappear.
 */
const SCHEMA = `
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    pass TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE RESTRICT,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_enrollment ON payments(enrollment_id);
`;

async function initSchema(db, config) {
    await db.exec(SCHEMA);

    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) return;

    // The sample password was written in plaintext by the original INSERT.
    const senhaInicial = await hashPassword('123', config.security.bcryptRounds);

    await db.transaction(async () => {
        await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
            'Leonan',
            'leonan@fullcycle.com.br',
            senhaInicial,
        ]);
        await db.run(
            'INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)',
            ['Clean Architecture', 997.0, 'Docker', 497.0],
        );
        await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, ?)',
            ['PAID'],
        );
    });
}

module.exports = { initSchema, SCHEMA };
