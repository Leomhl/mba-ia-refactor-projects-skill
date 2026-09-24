'use strict';

const { ValidationError } = require('../middlewares/errors');

/**
 * Checkout payload validation (playbook RP-13).
 *
 * The original only checked the presence of four fields, with no type or
 * format checking, and applied the default password "123456" when `pwd` was
 * absent — creating accounts with predictable credentials. Here the password
 * becomes mandatory; a minimum length is not enforced because it would change
 * the contract current clients rely on (see "Out of scope" in the report).
 *
 * The abbreviated names (usr, eml, pwd, c_id) are a public contract consumed
 * by existing clients and were kept; the translation to readable names
 * happens here, at the edge.
 */
function validarCheckout(body = {}) {
    const { usr, eml, pwd, c_id: courseId, card } = body;

    if (!usr || !eml || !courseId || !card) {
        throw new ValidationError('Bad Request');
    }

    if (typeof eml !== 'string' || !eml.includes('@')) {
        throw new ValidationError('Email inválido');
    }

    const cursoId = Number(courseId);
    if (!Number.isInteger(cursoId) || cursoId < 1) {
        throw new ValidationError('c_id deve ser um inteiro positivo');
    }

    const cartao = String(card).replace(/\s/g, '');
    if (!/^\d{13,19}$/.test(cartao)) {
        throw new ValidationError('Número de cartão inválido');
    }

    if (typeof pwd !== 'string' || pwd.length === 0) {
        throw new ValidationError('Senha é obrigatória');
    }

    return {
        name: String(usr).trim(),
        email: eml.trim().toLowerCase(),
        password: pwd,
        courseId: cursoId,
        card: cartao,
    };
}

module.exports = { validarCheckout };
