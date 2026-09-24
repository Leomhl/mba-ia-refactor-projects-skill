'use strict';

const { NotFoundError, PaymentDeclinedError } = require('../middlewares/errors');
const { logger } = require('../infra/logger');

/**
 * Checkout flow: enrolling a student in a course, with payment.
 *
 * The rule lived inside the HTTP handler, in nested callbacks. Here it is
 * testable by injecting fake repositories and gateway (playbook RP-04,
 * RP-05).
 */
class CheckoutService {
    constructor({ userRepository, courseRepository, enrollmentRepository, paymentGateway }) {
        this.userRepository = userRepository;
        this.courseRepository = courseRepository;
        this.enrollmentRepository = enrollmentRepository;
        this.paymentGateway = paymentGateway;
    }

    async execute({ name, email, password, courseId, card }) {
        const curso = await this.courseRepository.findActiveById(courseId);
        if (!curso) {
            throw new NotFoundError('Curso não encontrado');
        }

        const usuario = await this.#encontrarOuCriarUsuario({ name, email, password });

        const cobranca = await this.paymentGateway.charge(card, curso.price);
        if (cobranca.status !== 'PAID') {
            // A declined charge stops before any write: the original code had
            // the same ordering, but without a transaction the following
            // writes could fail halfway.
            throw new PaymentDeclinedError();
        }

        const matriculaId = await this.enrollmentRepository.enroll({
            userId: usuario.id,
            courseId: curso.id,
            amount: curso.price,
            status: cobranca.status,
        });

        logger.info('checkout.concluido', {
            enrollmentId: matriculaId,
            userId: usuario.id,
            courseId: curso.id,
        });

        return { msg: 'Sucesso', enrollment_id: matriculaId };
    }

    async #encontrarOuCriarUsuario({ name, email, password }) {
        const existente = await this.userRepository.findByEmail(email);
        if (existente) return existente;

        return this.userRepository.create({ name, email, password });
    }
}

module.exports = { CheckoutService };
