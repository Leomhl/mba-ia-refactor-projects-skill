'use strict';

class ReportController {
    constructor({ reportService }) {
        this.reportService = reportService;
        this.financial = this.financial.bind(this);
    }

    async financial(_req, res, next) {
        try {
            res.status(200).json(await this.reportService.financialReport());
        } catch (erro) {
            next(erro);
        }
    }
}

module.exports = { ReportController };
