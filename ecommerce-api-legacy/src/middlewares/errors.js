'use strict';

const { logger } = require('../infra/logger');

/** Application error hierarchy (playbook RP-11). */
class AppError extends Error {
    constructor(message, statusCode = 500) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') {
        super(message, 400);
    }
}

class NotFoundError extends AppError {
    constructor(message = 'Recurso não encontrado') {
        super(message, 404);
    }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autorizado') {
        super(message, 401);
    }
}

class PaymentDeclinedError extends AppError {
    constructor(message = 'Pagamento recusado') {
        super(message, 400);
    }
}

/**
 * Error middleware. Registered after the routes; handlers call next(err)
 * instead of repeating try/catch with their own response.
 */
function errorHandler(err, _req, res, _next) {
    if (err instanceof AppError) {
        return res.status(err.statusCode).json({ error: err.message });
    }

    // Unexpected error: detail to the log, generic message in the response.
    logger.error('request.unhandled_error', {
        name: err.name,
        message: err.message,
    });
    return res.status(500).json({ error: 'Erro interno' });
}

function notFoundHandler(_req, res) {
    res.status(404).json({ error: 'Rota não encontrada' });
}

module.exports = {
    AppError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    PaymentDeclinedError,
    errorHandler,
    notFoundHandler,
};
