'use strict';

const { logger } = require('../infra/logger');
const { UnauthorizedError } = require('./errors');

/**
 * Requires an administrative token.
 *
 * The financial report and user removal were reachable without any check —
 * exposing company revenue and student data to anonymous requests.
 */
function requireAdmin(config) {
    return (req, _res, next) => {
        const esperado = config.security.adminToken;

        if (!esperado) {
            logger.warn('admin.token_nao_configurado', { path: req.path });
            return next(new UnauthorizedError('ADMIN_TOKEN não configurado'));
        }

        if (req.get('X-Admin-Token') !== esperado) {
            logger.warn('admin.acesso_negado', { path: req.path });
            return next(new UnauthorizedError('Token administrativo inválido'));
        }

        return next();
    };
}

module.exports = { requireAdmin };
