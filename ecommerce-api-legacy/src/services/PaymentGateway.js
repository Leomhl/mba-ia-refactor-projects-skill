'use strict';

const { logger } = require('../infra/logger');

/**
 * Payment gateway.
 *
 * The approval rule lived as a ternary inside the HTTP handler
 * (`cc.startsWith("4") ? "PAID" : "DENIED"`). Isolated here, it can be
 * swapped for a real provider without touching a controller or route
 * (playbook RP-04).
 */
class PaymentGateway {
    constructor(apiKey) {
        this.apiKey = apiKey;
    }

    /**
     * Charges the card and returns the transaction status.
     * Keeps the original simulation: a card starting with 4 is approved.
     */
    async charge(card, amount) {
        if (!this.apiKey) {
            throw new Error('PAYMENT_GATEWAY_KEY não configurada');
        }

        const status = String(card).startsWith('4') ? 'PAID' : 'DENIED';

        // Last four digits only, and never the gateway key: the original log
        // printed the whole card alongside the production key.
        logger.info('payment.charge', {
            cardLast4: String(card).slice(-4),
            amount,
            status,
        });

        return { status, amount };
    }
}

module.exports = { PaymentGateway };
