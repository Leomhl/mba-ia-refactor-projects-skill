'use strict';

/** Financial report aggregation. */
class ReportService {
    constructor({ enrollmentRepository }) {
        this.enrollmentRepository = enrollmentRepository;
    }

    /**
     * Builds the report from a single JOIN query, grouping in memory.
     * The output shape matches the original endpoint.
     */
    async financialReport() {
        const linhas = await this.enrollmentRepository.financialReport();

        const porCurso = new Map();

        for (const linha of linhas) {
            if (!porCurso.has(linha.course_id)) {
                porCurso.set(linha.course_id, {
                    course: linha.course,
                    revenue: 0,
                    students: [],
                });
            }

            // LEFT JOIN returns the course even with no enrollment: that row
            // has a null student and must not become a student in the report.
            if (linha.student === null && linha.amount === null) continue;

            const curso = porCurso.get(linha.course_id);

            if (linha.status === 'PAID') {
                curso.revenue += linha.amount;
            }

            curso.students.push({
                student: linha.student ?? 'Unknown',
                paid: linha.amount ?? 0,
            });
        }

        return [...porCurso.values()];
    }
}

module.exports = { ReportService };
