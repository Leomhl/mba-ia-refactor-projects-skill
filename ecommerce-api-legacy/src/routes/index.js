'use strict';

const express = require('express');

const { requireAdmin } = require('../middlewares/requireAdmin');

/**
 * Route declarations: path, method, middleware and handler.
 * No logic — this file is the API's public contract.
 */
function createRouter({ config, checkoutController, reportController, userController }) {
    const router = express.Router();
    const admin = requireAdmin(config);

    router.post('/api/checkout', checkoutController.create);

    // The financial report and user removal now require an administrative
    // token: they exposed revenue and student data without authentication.
    router.get('/api/admin/financial-report', admin, reportController.financial);
    router.delete('/api/users/:id', admin, userController.remove);

    return router;
}

module.exports = { createRouter };
