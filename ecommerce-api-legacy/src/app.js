'use strict';

const express = require('express');

const { config } = require('./config');
const { createDatabase } = require('./infra/db');
const { initSchema } = require('./infra/schema');
const { logger } = require('./infra/logger');

const { UserRepository } = require('./repositories/UserRepository');
const { CourseRepository } = require('./repositories/CourseRepository');
const { EnrollmentRepository } = require('./repositories/EnrollmentRepository');

const { PaymentGateway } = require('./services/PaymentGateway');
const { CheckoutService } = require('./services/CheckoutService');
const { ReportService } = require('./services/ReportService');
const { UserService } = require('./services/UserService');

const { CheckoutController } = require('./controllers/CheckoutController');
const { ReportController } = require('./controllers/ReportController');
const { UserController } = require('./controllers/UserController');

const { createRouter } = require('./routes');
const { errorHandler, notFoundHandler } = require('./middlewares/errors');

/**
 * Composition root: wires the dependency graph and returns the application.
 *
 * It is the only place that knows concrete implementations — which allows
 * replacing them in tests without touching any layer (playbook RP-05).
 */
async function createApp(overrides = {}) {
    const db = overrides.db || createDatabase(config);
    await initSchema(db, config);

    const userRepository = new UserRepository(db, config);
    const courseRepository = new CourseRepository(db);
    const enrollmentRepository = new EnrollmentRepository(db);
    const paymentGateway = overrides.paymentGateway
        || new PaymentGateway(config.payment.gatewayKey);

    const checkoutService = new CheckoutService({
        userRepository,
        courseRepository,
        enrollmentRepository,
        paymentGateway,
    });
    const reportService = new ReportService({ enrollmentRepository });
    const userService = new UserService({ userRepository });

    const app = express();
    app.use(express.json());

    app.use(createRouter({
        config,
        checkoutController: new CheckoutController({ checkoutService }),
        reportController: new ReportController({ reportService }),
        userController: new UserController({ userService }),
    }));

    app.use(notFoundHandler);
    app.use(errorHandler);

    return { app, db };
}

async function start() {
    const { app } = await createApp();

    app.listen(config.port, () => {
        logger.info('server.started', { port: config.port, env: config.env });
    });
}

if (require.main === module) {
    start().catch((erro) => {
        logger.error('server.start_failed', { message: erro.message });
        process.exit(1);
    });
}

module.exports = { createApp, start };
