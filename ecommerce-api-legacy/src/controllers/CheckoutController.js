'use strict';

const { validarCheckout } = require('../validators/checkoutValidator');

/** Translates HTTP into a domain call. No business rules. */
class CheckoutController {
    constructor({ checkoutService }) {
        this.checkoutService = checkoutService;
        this.create = this.create.bind(this);
    }

    async create(req, res, next) {
        try {
            const entrada = validarCheckout(req.body);
            const resultado = await this.checkoutService.execute(entrada);
            res.status(200).json(resultado);
        } catch (erro) {
            next(erro);
        }
    }
}

module.exports = { CheckoutController };
