'use strict';

/**
 * Configuration read from the environment (playbook RP-01).
 *
 * The previous `config` object carried the database password, gateway key and
 * SMTP user as versioned literals.
 */

const flag = (nome, padrao = 'false') =>
    String(process.env[nome] ?? padrao).trim().toLowerCase() === 'true';

const config = {
    env: process.env.NODE_ENV || 'development',
    port: Number(process.env.PORT || 3000),

    db: {
        path: process.env.DB_PATH || ':memory:',
        verbose: flag('DB_VERBOSE'),
    },

    payment: {
        // With no key configured the gateway refuses to operate, instead of
        // silently falling back to an embedded value.
        gatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    },

    security: {
        bcryptRounds: Number(process.env.BCRYPT_ROUNDS || 12),
        adminToken: process.env.ADMIN_TOKEN || '',
    },

    logLevel: process.env.LOG_LEVEL || 'info',
};

config.isProduction = config.env === 'production';

module.exports = { config };
