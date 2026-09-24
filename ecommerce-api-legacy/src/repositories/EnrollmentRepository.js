'use strict';

/** Enrollments, payments and the checkout audit trail. */
class EnrollmentRepository {
    constructor(db) {
        this.db = db;
    }

    /**
     * Writes enrollment, payment and audit entry in a single transaction.
     *
     * In the original code the three writes were chained callbacks with no
     * BEGIN/COMMIT: a failure midway left an active enrollment with no
     * recorded payment (playbook RP-08).
     */
    async enroll({ userId, courseId, amount, status }) {
        return this.db.transaction(async () => {
            const matricula = await this.db.run(
                'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
                [userId, courseId],
            );

            await this.db.run(
                'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
                [matricula.lastID, amount, status],
            );

            await this.db.run(
                "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
                [`Checkout curso ${courseId} por ${userId}`],
            );

            return matricula.lastID;
        });
    }

    /**
     * Financial report in a single query.
     *
     * Replaces the four levels of chained lookups — with 50 courses of 30
     * enrollments each, the previous version fired over 3,000 queries
     * (playbook RP-07).
     */
    financialReport() {
        return this.db.all(`
            SELECT c.id            AS course_id,
                   c.title         AS course,
                   u.name          AS student,
                   p.amount        AS amount,
                   p.status        AS status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u       ON u.id = e.user_id
            LEFT JOIN payments p    ON p.enrollment_id = e.id
            ORDER BY c.id, e.id
        `);
    }
}

module.exports = { EnrollmentRepository };
